from collections.abc import Callable, Sequence
from typing import Any

from backend.app.services.migration_0003_service import MigrationResult
from backend.app.services.migration_0007_service import run_migration_0007
from backend.app.services.migration_cli_service import (
    project_migration_engine,
    run_controlled_migration_cli,
)


def main(
    argv: Sequence[str] | None = None,
    engine_factory: Callable[[], Any] = project_migration_engine,
    runner: Callable[[Any], MigrationResult] = run_migration_0007,
) -> int:
    """在获批隔离副本上执行统计表迁移并输出脱敏结果。"""
    return run_controlled_migration_cli(
        argv,
        description="raw_api_data_stat 0007 受控副本迁移",
        engine_factory=engine_factory,
        runner=runner,
    )


if __name__ == "__main__":
    raise SystemExit(main())
