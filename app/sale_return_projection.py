import argparse
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection, Engine

SALE_RETURN_API_CODE = "sale_return_order_page"

_PROJECT_SQL = """
INSERT INTO sale_return_order (
  jijia_account_id, raw_data_id, source_primary_key, record_identity,
  market_id, return_date_time, order_id, seller_order_id,
  asin, msku, fnsku, sku, product_name, quantity,
  fulfillment_center_id, disposition, reason, status,
  source_created_at, source_updated_at, data_hash, sync_batch_no
)
SELECT
  raw.jijia_account_id,
  raw.id,
  raw.source_primary_key,
  raw.record_identity,
  CAST(
    NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.marketId')), 'null'), '')
    AS SIGNED
  ),
  STR_TO_DATE(
    NULLIF(
      NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.returnDateTime')), 'null'),
      ''
    ),
    '%Y-%m-%d %H:%i:%s'
  ),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.orderId')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.sellerOrderId')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.asin')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.msku')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.fnsku')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.sku')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.productName')), 'null'), ''),
  CAST(
    NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.quantity')), 'null'), '')
    AS SIGNED
  ),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.fulfillmentCenterId')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.disposition')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.reason')), 'null'), ''),
  NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.status')), 'null'), ''),
  STR_TO_DATE(
    NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.createTime')), 'null'), ''),
    '%Y-%m-%d %H:%i:%s'
  ),
  STR_TO_DATE(
    NULLIF(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(raw.raw_json, '$.updateTime')), 'null'), ''),
    '%Y-%m-%d %H:%i:%s'
  ),
  raw.data_hash,
  raw.sync_batch_no
FROM raw_api_data AS raw
WHERE raw.api_code = :api_code
  AND raw.source_primary_key IS NOT NULL
  {identity_filter}
ON DUPLICATE KEY UPDATE
  raw_data_id = VALUES(raw_data_id),
  record_identity = VALUES(record_identity),
  market_id = VALUES(market_id),
  return_date_time = VALUES(return_date_time),
  order_id = VALUES(order_id),
  seller_order_id = VALUES(seller_order_id),
  asin = VALUES(asin),
  msku = VALUES(msku),
  fnsku = VALUES(fnsku),
  sku = VALUES(sku),
  product_name = VALUES(product_name),
  quantity = VALUES(quantity),
  fulfillment_center_id = VALUES(fulfillment_center_id),
  disposition = VALUES(disposition),
  reason = VALUES(reason),
  status = VALUES(status),
  source_created_at = VALUES(source_created_at),
  source_updated_at = VALUES(source_updated_at),
  data_hash = VALUES(data_hash),
  sync_batch_no = VALUES(sync_batch_no)
"""


def project_sale_return_orders(
    connection: Connection,
    record_identities: Sequence[str] | None = None,
) -> int:
    """从当前 raw 快照幂等刷新退货订单查询投影。"""
    params: dict[str, Any] = {"api_code": SALE_RETURN_API_CODE}
    if record_identities is None:
        statement = text(_PROJECT_SQL.format(identity_filter=""))
    else:
        if not record_identities:
            return 0
        statement = text(
            _PROJECT_SQL.format(identity_filter="AND raw.record_identity IN :record_identities")
        ).bindparams(bindparam("record_identities", expanding=True))
        params["record_identities"] = list(record_identities)
    result = connection.execute(statement, params)
    return max(int(getattr(result, "rowcount", 0) or 0), 0)


def project_existing(
    engine: Engine,
    account_id: int | None = None,
    batch_size: int = 1000,
) -> int:
    """重建已有退货 raw 快照的当前查询投影，不访问积加 API。"""
    conditions = [
        "api_code = :api_code",
        "source_primary_key IS NOT NULL",
        "id > :last_id",
    ]
    params: dict[str, Any] = {
        "api_code": SALE_RETURN_API_CODE,
        "last_id": 0,
        "batch_size": max(batch_size, 1),
    }
    if account_id is not None:
        conditions.append("jijia_account_id = :account_id")
        params["account_id"] = account_id
    where_sql = " AND ".join(conditions)
    projected = 0
    while True:
        with engine.begin() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, record_identity "
                    f"FROM raw_api_data WHERE {where_sql} "
                    "ORDER BY id LIMIT :batch_size"
                ),
                params,
            ).all()
            if not rows:
                return projected
            identities = [str(row.record_identity) for row in rows]
            project_sale_return_orders(connection, identities)
        projected += len(rows)
        params["last_id"] = int(rows[-1].id)


def main(argv: list[str] | None = None) -> int:
    """提供受控的已有数据投影入口，只输出聚合结果。"""
    parser = argparse.ArgumentParser(description="重建退货订单当前查询投影")
    parser.add_argument("--account-id", type=int)
    args = parser.parse_args(argv)

    from app.config import load_settings
    from app.db import create_db_engine
    from app.sync_lock import sync_task_lock

    settings = load_settings()
    if settings.sync_lock_scope == "account" and (args.account_id is None or args.account_id <= 0):
        raise SystemExit("账号锁模式必须指定有效的 --account-id")
    engine = create_db_engine(settings)
    with sync_task_lock(
        engine,
        scope=settings.sync_lock_scope,
        account_id=args.account_id,
    ):
        projected = project_existing(engine, args.account_id)
    print(json.dumps({"status": "success", "projected": projected}))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
