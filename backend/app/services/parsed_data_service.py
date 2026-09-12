from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Text, and_, cast, or_, select
from sqlalchemy.orm import Session

from backend.app.core.errors import ApiError
from backend.app.models.audit_log import AuditLog
from backend.app.models.jijia_account import JijiaAccount
from backend.app.models.sync_records import raw_api_data_table
from backend.app.services.m3_common import (
    DEFAULT_PAGE_SIZE,
    cursor_before,
    cursor_datetime,
    decode_cursor_payload,
    encode_cursor_payload,
    json_value,
    page_size,
    utc_iso,
)

DATASET_API_CODES = {
    "stores": "amazon_shop_page",
    "products": "product_page",
    "inventory": "fba_inventory_v2_page",
    "warehouses": "fba_warehouse_page",
}


@dataclass(frozen=True)
class ParsedCursor:
    """解析数据分页需要记录展开后的行位置。"""

    created_at: datetime
    record_id: int
    item_index: int | None


def list_parsed_data(
    db: Session,
    dataset: str,
    cursor_value: str | None,
    actor_id: int,
    request_id: str,
    limit: int = DEFAULT_PAGE_SIZE,
    account_id: int | None = None,
    keyword: str | None = None,
) -> dict[str, object]:
    """只读解析已同步的原始快照，并仅返回各数据集允许展示的字段。"""
    api_code = DATASET_API_CODES.get(dataset)
    if api_code is None:
        raise ApiError(404, "PARSED_DATASET_NOT_FOUND", "数据类型不存在")

    cursor = _decode_parsed_cursor(cursor_value)
    size = page_size(limit)
    statement = (
        select(*raw_api_data_table.c, JijiaAccount.name.label("account_name"))
        .join(JijiaAccount, JijiaAccount.id == raw_api_data_table.c.jijia_account_id)
        .where(raw_api_data_table.c.api_code == api_code)
    )
    if account_id is not None:
        statement = statement.where(raw_api_data_table.c.jijia_account_id == account_id)
    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        statement = statement.where(
            or_(
                raw_api_data_table.c.source_primary_key.contains(normalized_keyword),
                cast(raw_api_data_table.c.raw_json, Text).contains(normalized_keyword),
            )
        )
    if cursor:
        if cursor.item_index is None:
            statement = statement.where(
                cursor_before(
                    raw_api_data_table.c.created_at,
                    raw_api_data_table.c.id,
                    cursor,
                )
            )
        else:
            statement = statement.where(
                or_(
                    raw_api_data_table.c.created_at < cursor.created_at,
                    and_(
                        raw_api_data_table.c.created_at == cursor.created_at,
                        raw_api_data_table.c.id <= cursor.record_id,
                    ),
                )
            )
    rows = db.execute(
        statement.order_by(
            raw_api_data_table.c.created_at.desc(),
            raw_api_data_table.c.id.desc(),
        ).limit(size + 1)
    ).all()

    items: list[dict[str, object]] = []
    next_cursor = None
    for row in rows:
        mapping = row._mapping
        raw = json_value(mapping["raw_json"])
        if not isinstance(raw, dict):
            continue
        projected = _project(dataset, raw)
        for index, fields in enumerate(projected):
            if _should_skip_projected_item(cursor, mapping, index):
                continue
            if len(items) >= size:
                previous = items[-1]
                next_cursor = _encode_parsed_cursor(
                    previous["sourceCreatedAt"],
                    previous["rawDataId"],
                    previous["sourceItemIndex"],
                )
                break
            item_id = str(mapping["id"])
            if len(projected) > 1:
                item_id = f"{item_id}:{fields.get('marketId') or index}"
            items.append(
                {
                    "id": item_id,
                    "rawDataId": mapping["id"],
                    "jijiaAccountId": mapping["jijia_account_id"],
                    "accountName": mapping["account_name"],
                    "apiCode": mapping["api_code"],
                    "dataDate": mapping["data_date"].isoformat() if mapping["data_date"] else None,
                    "lastObservedAt": utc_iso(mapping["last_observed_at"]),
                    "fields": fields,
                    "sourceCreatedAt": mapping["created_at"],
                    "sourceItemIndex": index,
                }
            )
        if next_cursor:
            break

    for item in items:
        item.pop("sourceCreatedAt", None)
        item.pop("sourceItemIndex", None)

    db.add(
        AuditLog(
            actor_user_id=actor_id,
            jijia_account_id=account_id,
            action="parsed_data.list",
            resource_type=dataset,
            resource_id="list",
            request_id=request_id,
            result="success",
            changes_json={
                "resultCount": len(items),
                "filtered": bool(account_id or normalized_keyword),
            },
        )
    )
    db.commit()
    return {"items": items, "nextCursor": next_cursor}


def _decode_parsed_cursor(value: str | None) -> ParsedCursor | None:
    if not value:
        return None
    try:
        decoded = decode_cursor_payload(value)
        item_index = int(decoded[2]) if len(decoded) > 2 else None
        return ParsedCursor(
            created_at=cursor_datetime(decoded[0]),
            record_id=int(decoded[1]),
            item_index=item_index,
        )
    except (ValueError, TypeError, IndexError) as error:
        raise ApiError(422, "CURSOR_INVALID", "分页游标无效") from error


def _encode_parsed_cursor(
    created_at: object,
    record_id: object,
    item_index: object,
) -> str:
    if (
        not isinstance(created_at, datetime)
        or not isinstance(record_id, int)
        or not isinstance(item_index, int)
    ):
        raise ApiError(500, "PARSED_CURSOR_INVALID", "解析数据分页游标生成失败")
    return encode_cursor_payload([utc_iso(created_at), record_id, item_index])


def _should_skip_projected_item(
    cursor: ParsedCursor | None,
    mapping: Any,
    item_index: int,
) -> bool:
    if cursor is None or cursor.item_index is None:
        return False
    return (
        mapping["id"] == cursor.record_id
        and mapping["created_at"] == cursor.created_at
        and item_index <= cursor.item_index
    )


def _project(dataset: str, raw: dict[str, Any]) -> list[dict[str, object]]:
    if dataset == "stores":
        markets = raw.get("marketListVos")
        rows = markets if isinstance(markets, list) else [raw]
        return [_store_fields(item) for item in rows if isinstance(item, dict)]
    if dataset == "products":
        return [_product_fields(raw)]
    if dataset == "inventory":
        return [_inventory_fields(raw)]
    return [_warehouse_fields(raw)]


def _store_fields(raw: dict[str, Any]) -> dict[str, object]:
    return _pick(
        raw,
        "marketId",
        "store",
        "marketName",
        "countryName",
        "areaName",
        "apiState",
        "adsState",
        "warehouseName",
        "authType",
        "recordDate",
    )


def _product_fields(raw: dict[str, Any]) -> dict[str, object]:
    fields = _pick(
        raw,
        "sku",
        "name",
        "briefName",
        "brandName",
        "categoryName",
        "productTypeName",
        "unit",
        "lastDate",
    )
    state = raw.get("state")
    fields["stateName"] = "正常" if state in {0, "0"} else "停用" if state in {1, "1"} else state
    return fields


def _inventory_fields(raw: dict[str, Any]) -> dict[str, object]:
    return _pick(
        raw,
        "sku",
        "msku",
        "fnsku",
        "asin",
        "productName",
        "warehouseName",
        "afnFulfillableQuantity",
        "reserved",
        "inTransitQty",
        "totalInventoryQty",
        "availableTurnoverDays",
        "updateTime",
    )


def _warehouse_fields(raw: dict[str, Any]) -> dict[str, object]:
    return _pick(
        raw,
        "name",
        "marketName",
        "country",
        "stateStr",
        "statusName",
        "typeName",
        "fbaProcurementMethodName",
        "transferWarehouseName",
        "createDate",
    )


def _pick(raw: dict[str, Any], *keys: str) -> dict[str, object]:
    return {key: _display_value(raw.get(key)) for key in keys}


def _display_value(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    return str(value)
