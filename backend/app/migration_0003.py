from collections.abc import Callable, Sequence
from typing import Any

from app.config import load_migration_settings
from app.db import create_db_engine
from backend.app.services.migration_0003_service import (
    MigrationResult,
    run_migration_0003,
)
from backend.app.services.migration_cli_service import run_controlled_migration_cli


def _project_engine() -> Any:
    """仅在双重确认通过后加载副本数据库配置。"""
    return create_db_engine(load_migration_settings())


def main(
    argv: Sequence[str] | None = None,
    engine_factory: Callable[[], Any] = _project_engine,
    runner: Callable[[Any], MigrationResult] = run_migration_0003,
) -> int:
    """在获批隔离副本上执行受控 0003，并只输出脱敏 JSON。"""
    return run_controlled_migration_cli(
        argv,
        description="M3 既有同步表 0003 受控副本迁移",
        engine_factory=engine_factory,
        runner=runner,
    )


if __name__ == "__main__":
    raise SystemExit(main())
