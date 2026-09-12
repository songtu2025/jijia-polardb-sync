from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import or_, select

from backend.app.models.audit_log import AuditLog
from backend.app.models.sync_records import (
    raw_api_data_history_table,
    raw_api_data_table,
    sale_return_order_table,
)
from backend.app.services.m3_common import CompositeCursor, cursor_before


@dataclass(frozen=True, kw_only=True)
class RawDataFilters:
    """保存原始数据列表的已解析筛选条件。"""

    cursor: CompositeCursor | None
    account_id: int | None = None
    api_code: str | None = None
    sync_batch_no: str | None = None
    observed_sync_batch_no: str | None = None
    source_primary_key: str | None = None
    data_date_start: date | None = None
    data_date_end: date | None = None


@dataclass(frozen=True, kw_only=True)
class SaleReturnOrderFilters:
    """保存退货订单列表的已解析筛选条件。"""

    cursor: CompositeCursor | None
    account_id: int | None = None
    status: str | None = None
    return_date_start: date | None = None
    return_date_end: date | None = None
    order_id: str | None = None
    sku: str | None = None
    reason: str | None = None
    disposition: str | None = None
    fulfillment_center_id: str | None = None

    def has_filters(self) -> bool:
        """判断本次查询是否带有业务筛选条件。"""
        return any(
            value not in (None, "")
            for value in (
                self.account_id,
                self.status,
                self.return_date_start,
                self.return_date_end,
                self.order_id,
                self.sku,
                self.reason,
                self.disposition,
                self.fulfillment_center_id,
            )
        )


@dataclass(frozen=True, kw_only=True)
class AuditLogFilters:
    """保存审计日志列表的已解析筛选条件。"""

    cursor: CompositeCursor | None
    account_id: int | None = None
    actor_user_id: int | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    result: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


def apply_raw_data_filters(statement: Any, filters: RawDataFilters) -> Any:
    """把原始数据筛选条件应用到查询。"""
    if filters.account_id is not None:
        statement = statement.where(raw_api_data_table.c.jijia_account_id == filters.account_id)
    if filters.api_code:
        statement = statement.where(raw_api_data_table.c.api_code == filters.api_code)
    if filters.sync_batch_no:
        statement = statement.where(raw_api_data_table.c.sync_batch_no == filters.sync_batch_no)
    if filters.source_primary_key:
        statement = statement.where(
            raw_api_data_table.c.source_primary_key == filters.source_primary_key.strip()
        )
    if filters.observed_sync_batch_no:
        observed_in_batch = (
            select(raw_api_data_history_table.c.id)
            .where(
                raw_api_data_history_table.c.jijia_account_id
                == raw_api_data_table.c.jijia_account_id,
                raw_api_data_history_table.c.api_code == raw_api_data_table.c.api_code,
                raw_api_data_history_table.c.record_identity
                == raw_api_data_table.c.record_identity,
                raw_api_data_history_table.c.sync_batch_no == filters.observed_sync_batch_no,
            )
            .correlate(raw_api_data_table)
            .exists()
        )
        # 仅保存快照或内容未变化时没有新版本，最后观察批次仍是有效关联。
        statement = statement.where(
            or_(
                raw_api_data_table.c.sync_batch_no == filters.observed_sync_batch_no,
                observed_in_batch,
            )
        )
    if filters.data_date_start:
        statement = statement.where(raw_api_data_table.c.data_date >= filters.data_date_start)
    if filters.data_date_end:
        statement = statement.where(raw_api_data_table.c.data_date <= filters.data_date_end)
    if filters.cursor:
        statement = statement.where(
            cursor_before(
                raw_api_data_table.c.created_at,
                raw_api_data_table.c.id,
                filters.cursor,
            )
        )
    return statement


def apply_sale_return_order_filters(
    statement: Any,
    filters: SaleReturnOrderFilters,
) -> Any:
    """把退货订单筛选条件应用到查询。"""
    if filters.account_id is not None:
        statement = statement.where(
            sale_return_order_table.c.jijia_account_id == filters.account_id
        )
    if filters.return_date_start:
        statement = statement.where(
            sale_return_order_table.c.return_date_time
            >= datetime.combine(filters.return_date_start, time.min)
        )
    if filters.return_date_end:
        statement = statement.where(
            sale_return_order_table.c.return_date_time
            < datetime.combine(filters.return_date_end + timedelta(days=1), time.min)
        )
    for column, value in (
        (sale_return_order_table.c.status, filters.status),
        (sale_return_order_table.c.order_id, filters.order_id),
        (sale_return_order_table.c.sku, filters.sku),
        (sale_return_order_table.c.reason, filters.reason),
        (sale_return_order_table.c.disposition, filters.disposition),
        (
            sale_return_order_table.c.fulfillment_center_id,
            filters.fulfillment_center_id,
        ),
    ):
        if value:
            statement = statement.where(column == value.strip())
    if filters.cursor:
        statement = statement.where(
            cursor_before(
                sale_return_order_table.c.created_at,
                sale_return_order_table.c.id,
                filters.cursor,
            )
        )
    return statement


def apply_audit_log_filters(statement: Any, filters: AuditLogFilters) -> Any:
    """把审计日志筛选条件应用到查询。"""
    if filters.account_id is not None:
        statement = statement.where(AuditLog.jijia_account_id == filters.account_id)
    if filters.actor_user_id is not None:
        statement = statement.where(AuditLog.actor_user_id == filters.actor_user_id)
    if filters.action:
        statement = statement.where(AuditLog.action.contains(filters.action.strip()))
    if filters.resource_type:
        statement = statement.where(AuditLog.resource_type == filters.resource_type.strip())
    if filters.resource_id:
        statement = statement.where(AuditLog.resource_id == filters.resource_id.strip())
    if filters.result:
        statement = statement.where(AuditLog.result == filters.result)
    if filters.created_from:
        statement = statement.where(AuditLog.created_at >= _utc_naive(filters.created_from))
    if filters.created_to:
        statement = statement.where(AuditLog.created_at <= _utc_naive(filters.created_to))
    if filters.cursor:
        statement = statement.where(cursor_before(AuditLog.created_at, AuditLog.id, filters.cursor))
    return statement


def _utc_naive(value: datetime) -> datetime:
    """把 API 时区时间转成数据库统一使用的 UTC 无时区时间。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
