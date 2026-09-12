import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_sensitive_literals

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SensitiveLiteralCheckTest(unittest.TestCase):
    def test_current_worktree_passes(self):
        self.assertEqual(
            check_sensitive_literals.scan_repository(PROJECT_ROOT),
            [],
        )

    def test_deleted_tracked_file_is_not_treated_as_scan_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            candidate = root / "obsolete.txt"
            candidate.write_text("safe", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", "obsolete.txt"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            candidate.unlink()

            self.assertEqual(check_sensitive_literals.scan_repository(root), [])

    def test_high_confidence_literals_are_blocked_without_echoing_values(self):
        cases = (
            ("PRIVATE_KEY", "-----BEGIN " + "PRIVATE KEY-----"),
            ("COMMON_TOKEN", "AKIA" + "ABCDEFGHIJKLMNOP"),
            (
                "SENSITIVE_ENV",
                "JIJIA_APP_KEY" + "=real-value-that-must-not-leak",
            ),
            (
                "CREDENTIAL_DSN",
                "mysql+pymysql://" + "actual_user:actual_password@db.internal/prod",
            ),
        )
        for expected_rule, sensitive_value in cases:
            with self.subTest(rule=expected_rule), tempfile.TemporaryDirectory() as directory:
                root = self._init_repository(Path(directory))
                (root / "leak.txt").write_text(sensitive_value, encoding="utf-8")
                output = io.StringIO()

                with contextlib.redirect_stdout(output):
                    exit_code = check_sensitive_literals.main(["--project-root", str(root)])

                rendered = output.getvalue()
                self.assertEqual(exit_code, 1)
                self.assertEqual(
                    json.loads(rendered),
                    {"rule": expected_rule, "file": "leak.txt", "line": 1},
                )
                self.assertNotIn(sensitive_value, rendered)

    def test_allowlist_requires_exact_line_fingerprint(self):
        safe_line = "AKIA" + "ABCDEFGHIJKLMNOP"
        new_line = "AKIA" + "QRSTUVWXYZABCDEF"
        allowlist = {
            (
                "fixture.txt",
                "COMMON_TOKEN",
                check_sensitive_literals._line_fingerprint(safe_line),
            ): 1
        }

        with patch.object(check_sensitive_literals, "RULE_ALLOWLIST", allowlist):
            findings = check_sensitive_literals._scan_text(
                "fixture.txt",
                f"{safe_line}\n{safe_line}\n{new_line}",
            )

        self.assertEqual(
            findings,
            [
                check_sensitive_literals.Finding("COMMON_TOKEN", "fixture.txt", 2),
                check_sensitive_literals.Finding("COMMON_TOKEN", "fixture.txt", 3),
            ],
        )

    def test_utf8_sig_and_utf16_bom_literals_are_scanned_before_binary_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            token = "AKIA" + "ABCDEFGHIJKLMNOP"
            (root / "utf8-sig.txt").write_bytes(token.encode("utf-8-sig"))
            (root / "utf16.txt").write_bytes(token.encode("utf-16"))

            findings = check_sensitive_literals.scan_repository(root)

            self.assertIn(
                check_sensitive_literals.Finding("COMMON_TOKEN", "utf8-sig.txt", 1),
                findings,
            )
            self.assertIn(
                check_sensitive_literals.Finding("COMMON_TOKEN", "utf16.txt", 1),
                findings,
            )

    def test_runtime_env_dependencies_and_caches_are_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            (root / ".gitignore").write_text(
                ".env\n"
                "frontend/node_modules/\n"
                ".pytest_cache/\n"
                "coverage/\n"
                "frontend/dist/node_modules/\n",
                encoding="utf-8",
            )
            (root / ".env").write_text(
                "JIJIA_APP_KEY" + "=ignored-runtime-value",
                encoding="utf-8",
            )
            excluded_files = (
                root / "frontend" / "node_modules" / "package.js",
                root / ".pytest_cache" / "cache.txt",
                root / "coverage" / "coverage.txt",
                root / "frontend" / "dist" / "node_modules" / "package.js",
            )
            for candidate in excluded_files:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text("AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")

            original_read_bytes = Path.read_bytes

            def guarded_read_bytes(path: Path) -> bytes:
                relative = path.relative_to(root).as_posix()
                if relative == ".env" or any(
                    part in check_sensitive_literals.SKIPPED_DIRECTORY_NAMES
                    for part in Path(relative).parts[:-1]
                ):
                    raise AssertionError(f"不应读取受排除文件：{relative}")
                return original_read_bytes(path)

            with patch.object(Path, "read_bytes", guarded_read_bytes):
                self.assertEqual(
                    check_sensitive_literals.scan_repository(root),
                    [],
                )

    def test_forced_git_candidates_in_pruned_directory_names_are_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            relative_paths = (
                "frontend/node_modules/package.js",
                ".pytest_cache/cache.txt",
                "coverage/coverage.txt",
                "frontend/dist/node_modules/package.js",
            )
            (root / ".gitignore").write_text(
                "frontend/node_modules/\n.pytest_cache/\ncoverage/\nfrontend/dist/node_modules/\n",
                encoding="utf-8",
            )
            for relative_path in relative_paths:
                candidate = root / relative_path
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text("AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-f", "--", *relative_paths],
                cwd=root,
                check=True,
                capture_output=True,
            )

            findings = check_sensitive_literals.scan_repository(root)

            for relative_path in relative_paths:
                self.assertIn(
                    check_sensitive_literals.Finding(
                        "COMMON_TOKEN",
                        relative_path,
                        1,
                    ),
                    findings,
                )

    def test_git_candidates_named_build_or_dist_are_still_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            token = "AKIA" + "ABCDEFGHIJKLMNOP"
            candidates = (root / "build" / "app.js", root / "packages" / "dist" / "app.js")
            for candidate in candidates:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text(token, encoding="utf-8")

            findings = check_sensitive_literals.scan_repository(root)

            self.assertIn(
                check_sensitive_literals.Finding("COMMON_TOKEN", "build/app.js", 1),
                findings,
            )
            self.assertIn(
                check_sensitive_literals.Finding(
                    "COMMON_TOKEN",
                    "packages/dist/app.js",
                    1,
                ),
                findings,
            )

    def test_ignored_frontend_dist_text_assets_are_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            (root / ".gitignore").write_text("frontend/dist/\n", encoding="utf-8")
            asset = root / "frontend" / "dist" / "assets" / "app.js"
            asset.parent.mkdir(parents=True)
            asset.write_text("AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")

            findings = check_sensitive_literals.scan_repository(root)

            self.assertIn(
                check_sensitive_literals.Finding(
                    "COMMON_TOKEN",
                    "frontend/dist/assets/app.js",
                    1,
                ),
                findings,
            )

    def test_symlink_candidate_is_rejected_without_following_env_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            runtime_env = root / ".env"
            runtime_env.write_text(
                "JIJIA_APP_KEY" + "=runtime-value",
                encoding="utf-8",
            )
            link = root / "linked-secret"
            original_is_symlink = Path.is_symlink
            try:
                link.symlink_to(runtime_env)
                symlink_context = contextlib.nullcontext()
            except OSError:
                link.write_text("fallback", encoding="utf-8")

                def marked_symlink(path: Path) -> bool:
                    return path == link or original_is_symlink(path)

                symlink_context = patch.object(Path, "is_symlink", marked_symlink)

            original_read_bytes = Path.read_bytes

            def guarded_read_bytes(path: Path) -> bytes:
                if path in {link, runtime_env}:
                    raise AssertionError("符号链接及真实环境文件均不得读取")
                return original_read_bytes(path)

            with symlink_context, patch.object(Path, "read_bytes", guarded_read_bytes):
                findings = check_sensitive_literals.scan_repository(root)

            self.assertIn(
                check_sensitive_literals.Finding(
                    "SYMLINK_CANDIDATE",
                    "linked-secret",
                    0,
                ),
                findings,
            )

    def test_real_env_candidate_is_rejected_without_reading_and_examples_are_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._init_repository(Path(directory))
            runtime_env_files = (root / ".env.local", root / ".envrc")
            for runtime_env in runtime_env_files:
                runtime_env.write_text(
                    "JIJIA_APP_KEY" + "=runtime-value",
                    encoding="utf-8",
                )
            (root / ".env.example").write_text(
                "JIJIA_APP_KEY" + "=committed-real-value",
                encoding="utf-8",
            )
            (root / ".env.migration.example").write_text(
                "MIGRATION_DB_PASSWORD=your_migration_db_password",
                encoding="utf-8",
            )
            original_read_bytes = Path.read_bytes

            def guarded_read_bytes(path: Path) -> bytes:
                if path in runtime_env_files:
                    raise AssertionError("真实环境文件不得被读取")
                return original_read_bytes(path)

            with patch.object(Path, "read_bytes", guarded_read_bytes):
                findings = check_sensitive_literals.scan_repository(root)

            self.assertIn(
                check_sensitive_literals.Finding("REAL_ENV_FILE", ".env.local", 0),
                findings,
            )
            self.assertIn(
                check_sensitive_literals.Finding("REAL_ENV_FILE", ".envrc", 0),
                findings,
            )
            self.assertIn(
                check_sensitive_literals.Finding(
                    "SENSITIVE_ENV",
                    ".env.example",
                    1,
                ),
                findings,
            )
            self.assertNotIn(
                check_sensitive_literals.Finding(
                    "SENSITIVE_ENV",
                    ".env.migration.example",
                    1,
                ),
                findings,
            )

    def test_failure_output_escapes_all_control_characters(self):
        unsafe_path = "folder/evil\x1b[31m\n\tname.txt"
        rendered = check_sensitive_literals._render_finding(
            check_sensitive_literals.Finding("COMMON_TOKEN", unsafe_path, 7)
        )

        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\n", rendered)
        self.assertNotIn("\t", rendered)
        self.assertEqual(json.loads(rendered)["file"], unsafe_path)

    def test_check_script_orders_build_scan_and_diff_check(self):
        script = (PROJECT_ROOT / "scripts" / "check.ps1").read_text(encoding="utf-8")

        build = script.index('Invoke-Checked { npm run build } "Frontend build"')
        scan = script.index("scripts\\check_sensitive_literals.py")
        diff_check = script.index('Invoke-Checked { git diff --check } "Git diff check"')

        self.assertLess(build, scan)
        self.assertLess(scan, diff_check)

    @staticmethod
    def _init_repository(root: Path) -> Path:
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        return root


if __name__ == "__main__":
    unittest.main()
