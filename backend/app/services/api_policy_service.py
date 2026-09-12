import re
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter  # type: ignore[import-untyped]  # 第三方包未提供类型声明
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api_config_registry import REGISTRY_METADATA_KEY, load_published_api_configs
from backend.app.core.errors import ApiError
from backend.app.core.security import utc_now
from backend.app.models.account_api_policy import AccountApiPolicy, ScheduleMode, WindowMode
from backend.app.models.jijia_account import JijiaAccount, JijiaAccountStatus
from backend.app.models.sync_records import raw_api_data_stat_table, sync_api_log_table
from backend.app.schemas.api_policy import ApiPolicyBatchUpdateRequest, ApiPolicyUpdateRequest
from backend.app.services.audit_service import add_audit_log
from backend.app.services.m3_common import utc_iso

DAILY_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
MINIMUM_CRON_INTERVAL = timedelta(minutes=15)
SUPPORTED_POLICY_TIMEZONE = "Asia/Shanghai"
# 该阈值是 M2 临时安全限制，后续启用自动调度前仍需业务方确认。


def load_catalog(db: Session) -> list[dict[str, Any]]:
    """读取已经过受控发布的数据库运行时接口目录。"""
    return load_published_api_configs(db)


def catalog_item_data(item: dict[str, Any]) -> dict[str, object]:
    """暴露接口中心、策略页和任务创建共用的配置事实。"""
    path = str(item["path"])
    domain_code = next((part for part in path.split("/") if part), "other")
    date_window = item.get("date_window") or {}
    market_scope = item.get("market_scope") or {}
    param_source = item.get("param_source") or {}
    page = item.get("page") or {}
    primary_key = item.get("primary_key") or {}
    registry = item.get(REGISTRY_METADATA_KEY) or {}
    upstream_api_code = param_source.get("source_api_code")
    return {
        "apiCode": str(item["api_code"]),
        "name": str(item.get("name") or item["api_code"]),
        "method": str(item.get("method") or "POST"),
        "path": path,
        "domain": domain_code,
        "catalogEnabled": bool(registry.get("platformEnabled")),
        "platformEnabled": bool(registry.get("platformEnabled")),
        "systemConfigured": True,
        "officialExists": registry.get("officialDocId") is not None,
        "readOnlyVerified": bool(registry.get("readOnlyVerified")),
        "officialDocId": registry.get("officialDocId"),
        "classification": registry.get("classification"),
        "executionStage": registry.get("executionStage"),
        "configVersion": registry.get("configVersion"),
        "configHash": registry.get("configHash"),
        "publishedAt": registry.get("publishedAt"),
        "supportsDateWindow": bool(date_window.get("enabled")),
        "supportsMarketScope": bool(market_scope.get("enabled")),
        "canRunDirectly": upstream_api_code is None,
        "upstreamApiCode": str(upstream_api_code) if upstream_api_code else None,
        "listField": str(page.get("list_field") or ""),
        "primaryKeyField": str(primary_key.get("field") or ""),
        "dateField": str(item.get("date_field") or ""),
        "storageMode": str(item.get("storage_mode") or "latest_snapshot"),
        "sensitive": bool(item.get("sensitive_response")),
        "dataSummary": str(item.get("data_summary") or item.get("name") or item["api_code"]),
    }


def catalog_by_code(db: Session) -> dict[str, dict[str, Any]]:
    """构造接口编码索引，所有策略只能引用已知接口。"""
    return {str(item["api_code"]): item for item in load_catalog(db)}


def build_default_policy(
    account_id: int,
    api_code: str,
    supports_window: bool,
    actor_id: int | None,
) -> AccountApiPolicy:
    """构造默认关闭的账号策略，供账号验证和配置发布共用。"""
    return AccountApiPolicy(
        jijia_account_id=account_id,
        api_code=api_code,
        enabled=False,
        schedule_mode=ScheduleMode.MANUAL_ONLY,
        schedule_expr=None,
        timezone="Asia/Shanghai",
        window_mode=WindowMode.CHECKPOINT if supports_window else None,
        lookback_days=None,
        start_date=None,
        next_run_at=None,
        created_by=actor_id,
        updated_by=actor_id,
    )


def ensure_default_policies(
    db: Session,
    account: JijiaAccount,
    actor_id: int,
) -> None:
    """验证成功后为缺失接口建立默认关闭、仅手动策略。"""
    existing = set(
        db.scalars(
            select(AccountApiPolicy.api_code).where(AccountApiPolicy.jijia_account_id == account.id)
        ).all()
    )
    for item in load_catalog(db):
        api_code = str(item["api_code"])
        if api_code in existing:
            continue
        supports_window = bool((item.get("date_window") or {}).get("enabled"))
        db.add(build_default_policy(account.id, api_code, supports_window, actor_id))


def policy_data(
    policy: AccountApiPolicy,
    item: dict[str, Any],
    latest_run: Any | None = None,
) -> dict[str, object]:
    """合并官方目录展示字段与账号可编辑策略。"""
    return {
        **catalog_item_data(item),
        "id": policy.id,
        "accountId": policy.jijia_account_id,
        "enabled": policy.enabled,
        "scheduleMode": policy.schedule_mode.value,
        "scheduleExpr": policy.schedule_expr,
        "timezone": policy.timezone,
        "windowMode": policy.window_mode.value if policy.window_mode else None,
        "lookbackDays": policy.lookback_days,
        "startDate": policy.start_date.isoformat() if policy.start_date else None,
        "nextRunAt": utc_iso(policy.next_run_at),
        "recentRunStatus": latest_run["status"] if latest_run else None,
        "recentRunAt": utc_iso(latest_run["run_at"]) if latest_run else None,
    }


def list_catalog_data(
    db: Session,
    account_id: int | None = None,
) -> list[dict[str, object]]:
    """返回已接入接口及指定账号的策略、运行和数据闭环状态。"""
    policies: dict[str, AccountApiPolicy] = {}
    if account_id is not None:
        account = db.get(JijiaAccount, account_id)
        if account is None:
            raise ApiError(404, "ACCOUNT_NOT_FOUND", "积加账号不存在")
        policies = {
            policy.api_code: policy
            for policy in db.scalars(
                select(AccountApiPolicy).where(AccountApiPolicy.jijia_account_id == account_id)
            ).all()
        }

    latest_runs_query = select(
        sync_api_log_table.c.api_code,
        sync_api_log_table.c.status,
        func.coalesce(
            sync_api_log_table.c.finished_at,
            sync_api_log_table.c.created_at,
        ).label("run_at"),
        func.row_number()
        .over(
            partition_by=sync_api_log_table.c.api_code,
            order_by=sync_api_log_table.c.created_at.desc(),
        )
        .label("row_number"),
    )
    if account_id is not None:
        latest_runs_query = latest_runs_query.where(
            sync_api_log_table.c.jijia_account_id == account_id
        )
    ranked_runs = latest_runs_query.subquery()
    latest_runs = {
        str(row["api_code"]): row
        for row in db.execute(select(ranked_runs).where(ranked_runs.c.row_number == 1)).mappings()
    }
    if account_id is None:
        raw_counts_query = select(
            raw_api_data_stat_table.c.api_code,
            func.sum(raw_api_data_stat_table.c.record_count).label("record_count"),
        ).group_by(raw_api_data_stat_table.c.api_code)
    else:
        raw_counts_query = select(
            raw_api_data_stat_table.c.api_code,
            raw_api_data_stat_table.c.record_count,
        ).where(raw_api_data_stat_table.c.jijia_account_id == account_id)
    raw_counts = {
        str(row["api_code"]): int(row["record_count"])
        for row in db.execute(raw_counts_query).mappings()
    }

    result = []
    for item in load_catalog(db):
        api_code = str(item["api_code"])
        policy = policies.get(api_code)
        latest_run = latest_runs.get(api_code)
        record_count = raw_counts.get(api_code, 0)
        result.append(
            {
                **catalog_item_data(item),
                "accountPolicyExists": policy is not None if account_id is not None else None,
                "accountEnabled": bool(policy.enabled) if policy is not None else None,
                "recentRunStatus": latest_run["status"] if latest_run else None,
                "recentRunAt": utc_iso(latest_run["run_at"]) if latest_run else None,
                "rawRecordCount": record_count,
                "hasData": record_count > 0,
            }
        )
    return result


def list_account_policies(
    db: Session,
    account_id: int,
) -> list[dict[str, object]]:
    """按官方目录顺序返回账号策略。"""
    account = db.get(JijiaAccount, account_id)
    if account is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "积加账号不存在")
    policies = {
        policy.api_code: policy
        for policy in db.scalars(
            select(AccountApiPolicy).where(AccountApiPolicy.jijia_account_id == account_id)
        ).all()
    }
    ranked_runs = (
        select(
            sync_api_log_table.c.api_code,
            sync_api_log_table.c.status,
            func.coalesce(
                sync_api_log_table.c.finished_at,
                sync_api_log_table.c.created_at,
            ).label("run_at"),
            func.row_number()
            .over(
                partition_by=sync_api_log_table.c.api_code,
                order_by=sync_api_log_table.c.created_at.desc(),
            )
            .label("row_number"),
        )
        .where(sync_api_log_table.c.jijia_account_id == account_id)
        .subquery()
    )
    latest_runs = {
        str(row["api_code"]): row
        for row in db.execute(select(ranked_runs).where(ranked_runs.c.row_number == 1)).mappings()
    }
    return [
        policy_data(
            policies[str(item["api_code"])],
            item,
            latest_runs.get(str(item["api_code"])),
        )
        for item in load_catalog(db)
        if str(item["api_code"]) in policies
    ]


def update_account_policy(
    db: Session,
    account_id: int,
    api_code: str,
    payload: ApiPolicyUpdateRequest,
    actor_id: int,
    request_id: str,
) -> dict[str, object]:
    """校验白名单策略字段并重新计算下次运行时间。"""
    account = db.get(JijiaAccount, account_id)
    if account is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "积加账号不存在")
    if account.status != JijiaAccountStatus.ACTIVE:
        raise ApiError(409, "ACCOUNT_NOT_ACTIVE", "账号验证通过后才能修改同步策略")

    item = catalog_by_code(db).get(api_code)
    if item is None:
        raise ApiError(404, "API_CATALOG_NOT_FOUND", "接口不在官方目录中")
    policy = db.scalar(
        select(AccountApiPolicy).where(
            AccountApiPolicy.jijia_account_id == account_id,
            AccountApiPolicy.api_code == api_code,
        )
    )
    if policy is None:
        raise ApiError(404, "API_POLICY_NOT_FOUND", "账号接口策略不存在")

    next_run_at, normalized_expr = _validated_policy_values(payload, item)
    _apply_policy(policy, payload, item, next_run_at, normalized_expr, actor_id)
    add_audit_log(
        db,
        actor_user_id=actor_id,
        jijia_account_id=account.id,
        action="api_policy.update",
        resource_type="account_api_policy",
        resource_id=policy.id,
        request_id=request_id,
        result="success",
        changes={
            "enabled": payload.enabled,
            "scheduleMode": payload.schedule_mode.value,
            "windowMode": payload.window_mode.value if payload.window_mode else None,
        },
    )
    db.commit()
    db.refresh(policy)
    return policy_data(policy, item)


def batch_update_account_policies(
    db: Session,
    account_id: int,
    payload: ApiPolicyBatchUpdateRequest,
    actor_id: int,
    request_id: str,
) -> list[dict[str, object]]:
    """在单个事务中校验并更新多个账号接口策略。"""
    account = db.get(JijiaAccount, account_id)
    if account is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "积加账号不存在")
    if account.status != JijiaAccountStatus.ACTIVE:
        raise ApiError(409, "ACCOUNT_NOT_ACTIVE", "账号验证通过后才能修改同步策略")

    api_codes = [item.api_code for item in payload.items]
    if len(api_codes) != len(set(api_codes)):
        raise ApiError(422, "API_POLICY_DUPLICATE", "批量策略中存在重复接口")
    catalog = catalog_by_code(db)
    policies = {
        policy.api_code: policy
        for policy in db.scalars(
            select(AccountApiPolicy)
            .where(
                AccountApiPolicy.jijia_account_id == account_id,
                AccountApiPolicy.api_code.in_(api_codes),
            )
            .with_for_update()
        ).all()
    }
    validated: list[
        tuple[AccountApiPolicy, ApiPolicyUpdateRequest, dict[str, Any], datetime | None, str | None]
    ] = []
    for batch_item in payload.items:
        item = catalog.get(batch_item.api_code)
        if item is None:
            raise ApiError(404, "API_CATALOG_NOT_FOUND", "接口不在官方目录中")
        policy = policies.get(batch_item.api_code)
        if policy is None:
            raise ApiError(404, "API_POLICY_NOT_FOUND", "账号接口策略不存在")
        update = ApiPolicyUpdateRequest.model_validate(batch_item.model_dump(exclude={"api_code"}))
        next_run_at, normalized_expr = _validated_policy_values(update, item)
        validated.append((policy, update, item, next_run_at, normalized_expr))

    for policy, update, item, next_run_at, normalized_expr in validated:
        _apply_policy(policy, update, item, next_run_at, normalized_expr, actor_id)
    add_audit_log(
        db,
        actor_user_id=actor_id,
        jijia_account_id=account.id,
        action="api_policy.batch_update",
        resource_type="jijia_account",
        resource_id=account.id,
        request_id=request_id,
        result="success",
        changes={"apiCodes": api_codes, "itemCount": len(api_codes)},
    )
    db.commit()
    for policy, *_ in validated:
        db.refresh(policy)
    return [policy_data(policy, item) for policy, _, item, _, _ in validated]


def _validated_policy_values(
    payload: ApiPolicyUpdateRequest,
    item: dict[str, Any],
) -> tuple[datetime | None, str | None]:
    registry = item.get(REGISTRY_METADATA_KEY) or {}
    if payload.enabled and not bool(registry.get("platformEnabled")):
        raise ApiError(409, "API_CONFIG_DISABLED", "接口已被平台全局停用")
    supports_window = bool((item.get("date_window") or {}).get("enabled"))
    _validate_window(payload, supports_window)
    return _next_run_at(payload)


def _apply_policy(
    policy: AccountApiPolicy,
    payload: ApiPolicyUpdateRequest,
    item: dict[str, Any],
    next_run_at: datetime | None,
    normalized_expr: str | None,
    actor_id: int,
) -> None:
    """应用已完成校验的策略字段，提交由调用方统一控制。"""
    supports_window = bool((item.get("date_window") or {}).get("enabled"))
    policy.enabled = payload.enabled
    policy.schedule_mode = payload.schedule_mode
    policy.schedule_expr = normalized_expr
    policy.timezone = payload.timezone
    policy.window_mode = payload.window_mode if supports_window else None
    policy.lookback_days = (
        payload.lookback_days if payload.window_mode == WindowMode.LOOKBACK_DAYS else None
    )
    policy.start_date = payload.start_date if payload.window_mode == WindowMode.START_DATE else None
    policy.next_run_at = next_run_at if payload.enabled else None
    policy.updated_by = actor_id


def _validate_window(payload: ApiPolicyUpdateRequest, supports_window: bool) -> None:
    if not supports_window:
        if payload.window_mode or payload.lookback_days or payload.start_date:
            raise ApiError(422, "WINDOW_NOT_SUPPORTED", "该接口不支持日期窗口策略")
        return
    if payload.window_mode is None:
        raise ApiError(422, "WINDOW_MODE_REQUIRED", "请选择日期窗口策略")
    if (
        payload.window_mode != WindowMode.CHECKPOINT
        or payload.lookback_days is not None
        or payload.start_date is not None
    ):
        raise ApiError(422, "WINDOW_MODE_UNSUPPORTED", "当前仅支持检查点日期窗口")


def next_run_for_policy(
    policy: AccountApiPolicy,
    after_utc: datetime,
) -> datetime | None:
    """从当前 UTC 时刻计算已校验策略的下一计划时间。"""
    payload = ApiPolicyUpdateRequest(
        enabled=policy.enabled,
        schedule_mode=policy.schedule_mode,
        schedule_expr=policy.schedule_expr,
        timezone=policy.timezone,
    )
    return _next_run_at(payload, after_utc=after_utc)[0]


def _next_run_at(
    payload: ApiPolicyUpdateRequest,
    *,
    after_utc: datetime | None = None,
) -> tuple[datetime | None, str | None]:
    if payload.timezone != SUPPORTED_POLICY_TIMEZONE:
        raise ApiError(422, "TIMEZONE_UNSUPPORTED", "当前仅支持 Asia/Shanghai 时区")
    try:
        timezone = ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as error:
        raise ApiError(422, "TIMEZONE_INVALID", "时区名称无效") from error

    if payload.schedule_mode == ScheduleMode.MANUAL_ONLY:
        return None, None
    expression = (payload.schedule_expr or "").strip()
    current_utc = after_utc or utc_now()
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=UTC)
    else:
        current_utc = current_utc.astimezone(UTC)
    now_local = current_utc.astimezone(timezone)
    if payload.schedule_mode == ScheduleMode.DAILY:
        if not DAILY_PATTERN.fullmatch(expression):
            raise ApiError(422, "DAILY_TIME_INVALID", "每日计划必须使用 HH:MM 格式")
        hour, minute = (int(part) for part in expression.split(":"))
        candidate = datetime.combine(now_local.date(), time(hour, minute), timezone)
        if candidate <= now_local:
            candidate += timedelta(days=1)
        return candidate.astimezone(UTC).replace(tzinfo=None), expression

    if len(expression.split()) != 5 or not croniter.is_valid(expression):
        raise ApiError(422, "CRON_INVALID", "Cron 必须是有效的 5 段表达式")
    schedule = croniter(expression, now_local)
    first = schedule.get_next(datetime)
    second = schedule.get_next(datetime)
    if second - first < MINIMUM_CRON_INTERVAL:
        raise ApiError(422, "CRON_TOO_FREQUENT", "Cron 执行间隔不能小于 15 分钟")
    return first.astimezone(UTC).replace(tzinfo=None), expression
