from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

DATE_WINDOW = "date_window"
HISTORY_BACKFILL = "history_backfill"
UPDATE_INCREMENTAL = "update_incremental"
MANUAL_RANGE = "manual_range"
CHECKPOINT_KINDS = frozenset({DATE_WINDOW, HISTORY_BACKFILL, UPDATE_INCREMENTAL, MANUAL_RANGE})

LATEST_SNAPSHOT = "latest_snapshot"
HISTORY_ON_CHANGE = "history_on_change"
STORAGE_MODES = frozenset({LATEST_SNAPSHOT, HISTORY_ON_CHANGE})

BACKFILL_RUNNING = "backfill_running"
CHANGE_CATCHUP = "change_catchup"
INCREMENTAL_READY = "incremental_ready"


@dataclass(frozen=True)
class SyncContext:
    """携带一次同步任务的账号、checkpoint 和逻辑任务边界。"""

    jijia_account_id: int = 0
    checkpoint_kind: str = DATE_WINDOW
    sync_job_id: int | None = None
    window_start: date | None = None
    window_end: date | None = None
    frozen_window_end: date | None = None
    target_window_end: date | None = None
    backfill_started_at: datetime | None = None
    advance_checkpoint: bool = True

    def __post_init__(self) -> None:
        if self.jijia_account_id < 0:
            raise ValueError("jijia_account_id must be non-negative")
        if self.checkpoint_kind not in CHECKPOINT_KINDS:
            raise ValueError(f"unsupported checkpoint_kind: {self.checkpoint_kind}")
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("window_start and window_end must be provided together")
        if (
            self.window_start is not None
            and self.window_end is not None
            and self.window_start > self.window_end
        ):
            raise ValueError("window_start must not be after window_end")
        if self.checkpoint_kind == UPDATE_INCREMENTAL and self.frozen_window_end is not None:
            raise ValueError("update_incremental must not use frozen_window_end")
        window_limit = (
            self.target_window_end
            if self.checkpoint_kind == UPDATE_INCREMENTAL
            else self.frozen_window_end
        )
        if (
            self.window_end is not None
            and window_limit is not None
            and self.window_end > window_limit
        ):
            raise ValueError("window_end must not exceed the task target")


def closed_date_windows(
    start: date,
    frozen_end: date,
    window_days: int = 31,
) -> list[tuple[date, date]]:
    """生成连续、无重叠的闭区间日期窗口。"""
    if window_days < 1:
        raise ValueError("window_days must be positive")
    if start > frozen_end:
        return []

    windows = []
    window_start = start
    while window_start <= frozen_end:
        window_end = min(
            window_start + timedelta(days=window_days - 1),
            frozen_end,
        )
        windows.append((window_start, window_end))
        window_start = window_end + timedelta(days=1)
    return windows


@dataclass(frozen=True)
class BackfillSequence:
    """描述 returnDate 回填到 updateTime 增量的串行状态。"""

    backfill_started_at: datetime
    phase: str = BACKFILL_RUNNING
    backfill_completed_at: datetime | None = None
    catchup_completed_through: datetime | None = None

    def begin_change_catchup(self, completed_at: datetime) -> "BackfillSequence":
        """仅在回填完成后进入变化追赶，并以 T0 作为追赶起点。"""
        if self.phase != BACKFILL_RUNNING:
            raise ValueError("change catch-up can only follow history backfill")
        if completed_at < self.backfill_started_at:
            raise ValueError("backfill completion must not be before T0")
        return replace(
            self,
            phase=CHANGE_CATCHUP,
            backfill_completed_at=completed_at,
        )

    def complete_change_catchup(
        self,
        completed_through: datetime,
    ) -> "BackfillSequence":
        """变化追赶完成后才允许进入常规增量。"""
        if self.phase != CHANGE_CATCHUP:
            raise ValueError("incremental sync requires completed change catch-up")
        if completed_through < self.backfill_started_at:
            raise ValueError("catch-up watermark must not be before T0")
        return replace(
            self,
            phase=INCREMENTAL_READY,
            catchup_completed_through=completed_through,
        )
