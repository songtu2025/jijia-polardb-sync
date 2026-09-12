import re
from pathlib import Path


def load_sql_statements(path: Path, expected_count: int) -> list[str]:
    """按项目受控 SQL 约定拆分语句并校验数量。"""
    script = path.read_text(encoding="utf-8")
    statements = [part.strip() for part in script.split(";") if _has_executable_sql(part)]
    if len(statements) != expected_count:
        raise RuntimeError(f"unexpected migration statement count: {path.name}")
    return statements


def _has_executable_sql(part: str) -> bool:
    without_blocks = re.sub(r"/\*.*?\*/", "", part, flags=re.DOTALL)
    without_comments = re.sub(r"--[^\n]*", "", without_blocks)
    return bool(without_comments.strip())
