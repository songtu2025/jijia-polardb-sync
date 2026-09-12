import argparse
import codecs
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SKIPPED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "coverage",
        "node_modules",
        "venv",
    }
)
EXAMPLE_ENV_FILENAMES = frozenset({".env.example", ".env.migration.example"})
SENSITIVE_ENV_KEYS = (
    "AWS_SECRET_ACCESS_KEY",
    "CREDENTIAL_ENCRYPTION_KEY",
    "DB_PASSWORD",
    "GITHUB_TOKEN",
    "JIJIA_APP_KEY",
    "MIGRATION_DB_PASSWORD",
    "OPENAI_API_KEY",
    "SMTP_PASSWORD",
)

PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:(?:RSA|EC|DSA|OPENSSH) )?PRIVATE KEY-----"
    r"|-----BEGIN PGP PRIVATE KEY BLOCK-----"
)
COMMON_TOKEN_PATTERN = re.compile(
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\bLTAI[A-Za-z0-9]{12,20}\b"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
    r"|\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{20,}\b"
)
CREDENTIAL_DSN_PATTERN = re.compile(
    r"\b(?:mysql(?:\+pymysql)?|postgres(?:ql)?|mongodb(?:\+srv)?|redis)"
    r"://[^/@:\s]+:[^/@\s]+@",
    re.IGNORECASE,
)
SENSITIVE_ENV_PATTERN = re.compile(
    rf"^\s*(?:export\s+|\$env:)?(?P<key>{'|'.join(SENSITIVE_ENV_KEYS)})"
    r"\s*[:=]\s*(?P<value>.*?)\s*$"
)

# 白名单只保存文件、规则、安全行 SHA-256 和允许出现次数，不保存敏感正文。
RULE_ALLOWLIST = {
    (
        "backend/tests/test_health.py",
        "CREDENTIAL_DSN",
        "9035a9ee05969f435904cfe1e544ecf7a0ff3e1a14566a658647d3a283735738",
    ): 1,
    (
        "backend/tests/test_legacy_sale_return_attribution.py",
        "CREDENTIAL_DSN",
        "c9e8d2ba2b8364135e2d67be08bd696f3ab12829b9a49fa81abce98f3032ecfc",
    ): 1,
    (
        "backend/tests/test_migration_0003.py",
        "CREDENTIAL_DSN",
        "c9e8d2ba2b8364135e2d67be08bd696f3ab12829b9a49fa81abce98f3032ecfc",
    ): 1,
    (
        "backend/tests/test_migration_preflight.py",
        "CREDENTIAL_DSN",
        "c9e8d2ba2b8364135e2d67be08bd696f3ab12829b9a49fa81abce98f3032ecfc",
    ): 2,
    (
        "backend/tests/test_release_preflight.py",
        "CREDENTIAL_DSN",
        "b2d5cd26a9f004df6caa4a5ab92b9140adc7569c17062efbe6c24cf1060ff3db",
    ): 1,
    (
        "backend/tests/test_release_preflight.py",
        "CREDENTIAL_DSN",
        "5940f7d8275bc5d56a73dd94fcd40a9a17cbbe39689f67c93aa4343ba4493fe4",
    ): 1,
    (
        "backend/tests/test_worker_entry.py",
        "CREDENTIAL_DSN",
        "1ef0159ef1856fd5f49a95e928ba787217ce5b2e09dae85293da8c7e196992ec",
    ): 1,
    (
        "scripts/check_sensitive_literals.py",
        "PRIVATE_KEY",
        "d2dfb5b23ae013030f498a74f616cb6ecf6907adb8cef32236526c881c219229",
    ): 1,
    (
        "tests/test_config_validation.py",
        "SENSITIVE_ENV",
        "eecf14c4cdb089cf5ab37dfe581c58e4aaae80e0b9562f4ed6a42ad4024b27de",
    ): 1,
    (
        "tests/test_main_error_logging.py",
        "CREDENTIAL_DSN",
        "3c58ee6a83bfa660d68e88905828dd1b23e267d1c464b5e245b39a3d6a2a5c8c",
    ): 3,
    (
        "tests/test_sync_lock.py",
        "CREDENTIAL_DSN",
        "3c58ee6a83bfa660d68e88905828dd1b23e267d1c464b5e245b39a3d6a2a5c8c",
    ): 1,
}


@dataclass(frozen=True, order=True)
class Finding:
    rule: str
    file: str
    line: int


class ScanError(RuntimeError):
    """表示扫描器无法安全完成候选文件检查。"""


def scan_repository(project_root: Path) -> list[Finding]:
    """扫描 Git 候选文件和前端发布制品，返回不包含敏感正文的命中位置。"""
    root = project_root.resolve()
    findings: list[Finding] = []
    for relative_path in _candidate_paths(root):
        candidate = root / Path(PurePosixPath(relative_path))
        if candidate.is_symlink():
            findings.append(Finding("SYMLINK_CANDIDATE", relative_path, 0))
            continue
        # Git 会列出工作树中已删除但尚未提交的路径；文件已不存在时没有内容可扫描。
        if not candidate.exists():
            continue

        policy = _path_policy(relative_path)
        if policy == "real_env":
            findings.append(Finding("REAL_ENV_FILE", relative_path, 0))
            continue

        try:
            raw = candidate.read_bytes()
        except OSError as error:
            raise ScanError from error
        text = _decode_text(raw)
        if text is None:
            continue
        findings.extend(_scan_text(relative_path, text))
    return sorted(findings)


def _candidate_paths(project_root: Path) -> list[str]:
    candidates = set(_git_candidate_paths(project_root))
    candidates.update(_frontend_dist_paths(project_root))
    return sorted(candidates)


def _git_candidate_paths(project_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            cwd=project_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ScanError from error
    return [os.fsdecode(item).replace("\\", "/") for item in result.stdout.split(b"\0") if item]


def _frontend_dist_paths(project_root: Path) -> list[str]:
    """收集被 Git 忽略的实际前端发布制品，不进入依赖或缓存目录。"""
    dist_root = project_root / "frontend" / "dist"
    if dist_root.is_symlink():
        return ["frontend/dist"]
    if not dist_root.is_dir():
        return []

    candidates: list[str] = []
    for directory, directory_names, filenames in os.walk(dist_root, followlinks=False):
        current = Path(directory)
        retained_directories = []
        for name in directory_names:
            child = current / name
            if child.is_symlink():
                candidates.append(child.relative_to(project_root).as_posix())
            elif name not in SKIPPED_DIRECTORY_NAMES:
                retained_directories.append(name)
        directory_names[:] = retained_directories
        candidates.extend(
            (current / name).relative_to(project_root).as_posix() for name in filenames
        )
    return candidates


def _path_policy(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    if _is_real_env_filename(path.name):
        return "real_env"
    return "scan"


def _is_real_env_filename(filename: str) -> bool:
    if filename in EXAMPLE_ENV_FILENAMES:
        return False
    return filename.startswith(".env")


def _decode_text(raw: bytes) -> str | None:
    if raw.startswith(codecs.BOM_UTF8):
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_text(relative_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    allowed_occurrences: dict[tuple[str, str, str], int] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        matched_rules = []
        if PRIVATE_KEY_PATTERN.search(line):
            matched_rules.append("PRIVATE_KEY")
        if COMMON_TOKEN_PATTERN.search(line):
            matched_rules.append("COMMON_TOKEN")
        if CREDENTIAL_DSN_PATTERN.search(line):
            matched_rules.append("CREDENTIAL_DSN")
        env_match = SENSITIVE_ENV_PATTERN.search(line)
        if env_match and not _is_placeholder(env_match.group("value")):
            matched_rules.append("SENSITIVE_ENV")
        for rule in matched_rules:
            fingerprint = _line_fingerprint(line)
            allowlist_key = (relative_path, rule, fingerprint)
            used_count = allowed_occurrences.get(allowlist_key, 0)
            if used_count < RULE_ALLOWLIST.get(allowlist_key, 0):
                allowed_occurrences[allowlist_key] = used_count + 1
            else:
                findings.append(Finding(rule, relative_path, line_number))
    return findings


def _line_fingerprint(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").strip()
    if not normalized:
        return True
    lowered = normalized.lower()
    return lowered.startswith(
        (
            "${",
            "<",
            "example",
            "placeholder",
            "your-",
            "your_",
        )
    ) or lowered in {"change-me", "changeme"}


def _render_finding(finding: Finding) -> str:
    return json.dumps(
        {"rule": finding.rule, "file": finding.file, "line": finding.line},
        ensure_ascii=True,
        separators=(",", ":"),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查可提交文件中的高置信敏感字面量")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args(argv)
    try:
        findings = scan_repository(args.project_root)
    except ScanError:
        print(_render_finding(Finding("SCAN_ERROR", ".", 0)))
        return 2
    if not findings:
        print("sensitive literal scan passed")
        return 0
    for finding in findings:
        print(_render_finding(finding))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
