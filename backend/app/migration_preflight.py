import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from app.config import load_migration_settings
from app.db import create_db_engine
from backend.app.services.migration_preflight_service import (
    PreflightResult,
    run_preflight,
)


def _project_engine() -> Any:
    """只在用户确认副本后读取项目数据库配置。"""
    return create_db_engine(load_migration_settings())


def main(
    argv: Sequence[str] | None = None,
    engine_factory: Callable[[], Any] = _project_engine,
    runner: Callable[[Any], PreflightResult] = run_preflight,
) -> int:
    """执行只读副本预检，并输出不含凭证的单行 JSON。"""
    parser = argparse.ArgumentParser(description="M3 既有同步表 0003 副本预检")
    parser.add_argument(
        "--confirm-isolated-replica",
        action="store_true",
        required=True,
        help="确认目标是允许只读扫描的隔离 MySQL/PolarDB 副本",
    )
    parser.parse_args(argv)

    engine = None
    payload: dict[str, object]
    exit_code: int
    try:
        engine = engine_factory()
        result = runner(engine)
        payload = result.payload()
        exit_code = 0 if result.status == "pass" else 2
    except Exception as error:
        payload = {
            "status": "error",
            "code": "PREFLIGHT_RUNTIME_ERROR",
            "errorType": type(error).__name__,
        }
        exit_code = 1
    if engine is not None:
        try:
            engine.dispose()
        except Exception as error:
            payload = {
                "status": "error",
                "code": "PREFLIGHT_RUNTIME_ERROR",
                "errorType": type(error).__name__,
            }
            exit_code = 1
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
