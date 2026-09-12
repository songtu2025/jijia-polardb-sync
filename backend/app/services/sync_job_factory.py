import secrets
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.api_config_registry import REGISTRY_METADATA_KEY, api_config_snapshot
from backend.app.models.sync_job import SyncJob


@dataclass(frozen=True, kw_only=True)
class SyncJobSpec:
    """集中描述新任务的冻结业务参数。"""

    account_id: int
    api_code: str
    job_type: str
    trigger_type: str
    requested_by: int | None
    window_start: date | None
    window_end: date | None
    progress: dict[str, Any] | None
    retry_of_job_id: int | None = None
    schedule_slot_key: str | None = None
    task_no: str | None = None
    task_start: date | None = None
    task_end: date | None = None
    range_mode: str = "checkpoint"
    window_index: int = 1
    total_windows: int = 1
    advance_checkpoint: bool = True
    api_config: dict[str, Any] | None = None
    api_config_version: int | None = None
    api_config_hash: str | None = None
    api_config_snapshot_json: dict[str, Any] | None = None
    market_ids: list[int] | None = None


def build_sync_job(spec: SyncJobSpec, *, queued_at: datetime) -> SyncJob:
    """根据冻结规格创建尚未持久化的排队任务。"""
    api_config_version = spec.api_config_version
    api_config_hash = spec.api_config_hash
    api_config_snapshot_json = spec.api_config_snapshot_json
    if spec.api_config is not None:
        registry = spec.api_config.get(REGISTRY_METADATA_KEY) or {}
        api_config_version = int(registry["configVersion"])
        api_config_hash = str(registry["configHash"])
        api_config_snapshot_json = api_config_snapshot(spec.api_config)

    return SyncJob(
        job_no=f"job_{secrets.token_hex(12)}",
        task_no=spec.task_no,
        jijia_account_id=spec.account_id,
        api_code=spec.api_code,
        job_type=spec.job_type,
        trigger_type=spec.trigger_type,
        status="queued",
        schedule_slot_key=spec.schedule_slot_key,
        window_start=spec.window_start,
        window_end=spec.window_end,
        task_start=spec.task_start,
        task_end=spec.task_end,
        range_mode=spec.range_mode,
        window_index=spec.window_index,
        total_windows=spec.total_windows,
        advance_checkpoint=spec.advance_checkpoint,
        stop_after_current=False,
        progress_json=spec.progress,
        market_ids_json=list(spec.market_ids or []) or None,
        api_config_version=api_config_version,
        api_config_hash=api_config_hash,
        api_config_snapshot_json=api_config_snapshot_json,
        attempt_count=0,
        max_attempts=2,
        retry_of_job_id=spec.retry_of_job_id,
        requested_by=spec.requested_by,
        queued_at=queued_at,
    )
