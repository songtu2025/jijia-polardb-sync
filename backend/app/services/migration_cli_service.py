import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from app.config import load_migration_settings
from app.db import create_db_engine
from backend.app.services.migration_0003_service import MigrationResult


def project_migration_engine() -> Any:
    """加载与运行服务隔离的迁移数据库配置。"""
    return create_db_engine(load_migration_settings())


def run_controlled_migration_cli(
    argv: Sequence[str] | None,
    *,
    description: str,
    engine_factory: Callable[[], Any],
    runner: Callable[[Any], MigrationResult],
) -> int:
    """复用副本确认、脱敏输出和引擎关闭流程。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--confirm-isolated-replica",
        action="store_true",
        required=True,
        help="确认目标是获批执行 DDL 的隔离 MySQL/PolarDB 副本",
    )
    parser.add_argument(
        "--confirm-snapshot-ready",
        action="store_true",
        required=True,
        help="确认副本快照或 PITR 恢复点已经可用",
    )
    parser.parse_args(argv)

    engine = None
    try:
        engine = engine_factory()
        result = runner(engine)
    except Exception:
        result = MigrationResult(
            status="error",
            code="MIGRATION_RUNTIME_FAILED",
            stage="engine",
            ordinal=0,
            restore_required=False,
        )
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            result = MigrationResult(
                status="error",
                code="MIGRATION_ENGINE_DISPOSE_FAILED",
                stage="dispose",
                ordinal=result.ordinal,
                restore_required=result.restore_required,
            )
    print(json.dumps(result.payload(), ensure_ascii=False, separators=(",", ":")))
    if result.status == "success":
        return 0
    if result.status == "blocked":
        return 2
    return 1
