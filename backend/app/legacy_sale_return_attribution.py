import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from app.config import load_migration_settings
from app.db import create_db_engine
from backend.app.services.legacy_sale_return_attribution_service import (
    AttributionResult,
    run_legacy_sale_return_attribution,
)


def _positive_account_id(value: str) -> int:
    account_id = int(value)
    if account_id <= 0:
        raise argparse.ArgumentTypeError("target account id must be positive")
    return account_id


def _non_empty_account_code(value: str) -> str:
    account_code = value.strip()
    if not account_code:
        raise argparse.ArgumentTypeError("target account code must not be empty")
    return account_code


def _project_engine() -> Any:
    """只使用迁移专用配置创建引擎，不从运行配置推断目标账号。"""
    return create_db_engine(load_migration_settings())


def main(
    argv: Sequence[str] | None = None,
    engine_factory: Callable[[], Any] = _project_engine,
    runner: Callable[..., AttributionResult] = run_legacy_sale_return_attribution,
) -> int:
    """默认输出只读计划；双确认和 --execute 同时存在时才执行 DML。"""
    parser = argparse.ArgumentParser(description="退货单 legacy 数据账号归属工具")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target-account-id", type=_positive_account_id)
    target_group.add_argument("--target-account-code", type=_non_empty_account_code)
    parser.add_argument("--execute", action="store_true", help="显式执行已验证的归属计划")
    parser.add_argument(
        "--confirm-writers-stopped",
        action="store_true",
        help="确认 sale_return_order_page 已停止 legacy cron/CLI 和 Web Worker 写入",
    )
    parser.add_argument(
        "--confirm-snapshot-ready",
        action="store_true",
        help="确认目标数据库已建立可恢复快照或 PITR 恢复点",
    )
    args = parser.parse_args(argv)
    if args.execute and not (args.confirm_writers_stopped and args.confirm_snapshot_ready):
        parser.error("--execute requires both writer-stop and snapshot confirmations")

    engine = None
    mode = "execute" if args.execute else "dry-run"
    try:
        engine = engine_factory()
        result = runner(
            engine,
            target_account_id=args.target_account_id,
            target_account_code=args.target_account_code,
            execute=args.execute,
        )
    except Exception:
        result = AttributionResult(
            status="error",
            code="ATTRIBUTION_RUNTIME_FAILED",
            stage="engine",
            mode=mode,
            restore_required=False,
        )
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            result = AttributionResult(
                status="error",
                code="ATTRIBUTION_ENGINE_DISPOSE_FAILED",
                stage="dispose",
                mode=mode,
                restore_required=result.restore_required,
            )
    print(json.dumps(result.payload(), ensure_ascii=False, separators=(",", ":")))
    if result.status in {"planned", "success"}:
        return 0
    if result.status == "blocked":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
