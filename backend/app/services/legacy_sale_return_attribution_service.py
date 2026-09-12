from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection, Engine

from app.sync_lock import SYNC_TASK_LOCK_NAME
from backend.app.services.migration_0003_service import (
    collect_target_schema_snapshot,
    evaluate_target_schema,
)

API_CODE = "sale_return_order_page"
LEGACY_ACCOUNT_ID = 0

CANDIDATE_BATCH_BODY = """
SELECT sync_batch_no
FROM sync_api_log
WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code
UNION
SELECT sync_batch_no
FROM raw_api_data
WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code
UNION
SELECT sync_batch_no
FROM raw_api_data_history
WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code
UNION
SELECT sync_batch_no
FROM failed_request_log
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
  AND sync_batch_no IS NOT NULL
UNION
SELECT last_sync_batch_no AS sync_batch_no
FROM sync_checkpoint
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
  AND last_sync_batch_no IS NOT NULL
"""

CANDIDATE_BATCH_SQL = f"""
SELECT sync_batch_no
FROM ({CANDIDATE_BATCH_BODY}) AS candidate_batches
ORDER BY sync_batch_no
"""

BASELINE_RAW_IDS_SQL = """
SELECT r.id
FROM raw_api_data AS r
WHERE r.jijia_account_id = :legacy_account_id
  AND r.api_code = :api_code
  AND NOT EXISTS (
    SELECT 1
    FROM raw_api_data_history AS h
    WHERE h.jijia_account_id = :legacy_account_id
      AND h.api_code = r.api_code
      AND h.record_identity = r.record_identity
      AND h.data_hash = r.data_hash
  )
  AND NOT EXISTS (
    SELECT 1
    FROM raw_api_data_history AS h
    WHERE h.jijia_account_id = :target_account_id
      AND h.api_code = r.api_code
      AND h.record_identity = r.record_identity
      AND h.data_hash = r.data_hash
  )
ORDER BY r.id
"""

PLAN_SUMMARY_SQL = f"""
WITH candidate_batches AS ({CANDIDATE_BATCH_BODY})
SELECT
  (SELECT COUNT(*) FROM candidate_batches) AS candidate_batch_count,
  (SELECT COUNT(*) FROM sync_batch AS b
   JOIN candidate_batches AS cb ON cb.sync_batch_no = b.sync_batch_no
   WHERE b.jijia_account_id = :legacy_account_id) AS legacy_batch_count,
  (SELECT COUNT(*) FROM sync_api_log
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
    AS legacy_api_log_count,
  (SELECT COUNT(*) FROM failed_request_log
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
    AS legacy_failed_request_count,
  (SELECT COUNT(*) FROM raw_api_data
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
    AS legacy_raw_count,
  (SELECT COUNT(*) FROM raw_api_data_history
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
    AS legacy_history_count,
  (SELECT COUNT(*) FROM sync_checkpoint
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
    AS legacy_checkpoint_count,
  (SELECT COUNT(*) FROM candidate_batches AS cb
   LEFT JOIN sync_batch AS b ON b.sync_batch_no = cb.sync_batch_no
   WHERE b.id IS NULL) AS missing_batch_count,
  (SELECT COUNT(*) FROM sync_batch AS b
   JOIN candidate_batches AS cb ON cb.sync_batch_no = b.sync_batch_no
   WHERE BINARY b.message = BINARY 'mock sync finished') AS mock_batch_count,
  (SELECT COUNT(*) FROM sync_job AS j
   JOIN candidate_batches AS cb ON cb.sync_batch_no = j.sync_batch_no)
    AS web_job_reference_count,
  (SELECT COUNT(*) FROM sync_batch AS b
   JOIN candidate_batches AS cb ON cb.sync_batch_no = b.sync_batch_no
   WHERE b.jijia_account_id <> :legacy_account_id
      OR b.sync_job_id IS NOT NULL
      OR b.status NOT IN ('success', 'partial_failed', 'failed')
      OR b.finished_at IS NULL
      OR b.total_api_count <> 1) AS invalid_batch_count,
  (SELECT COUNT(*) FROM (
     SELECT cb.sync_batch_no
     FROM candidate_batches AS cb
     LEFT JOIN sync_api_log AS l ON l.sync_batch_no = cb.sync_batch_no
     GROUP BY cb.sync_batch_no
     HAVING COUNT(l.id) <> 1
   ) AS invalid_logs) AS invalid_log_cardinality_count,
  ((SELECT COUNT(*) FROM sync_api_log AS l
    JOIN candidate_batches AS cb ON cb.sync_batch_no = l.sync_batch_no
    WHERE l.api_code <> :api_code
       OR l.jijia_account_id <> :legacy_account_id)
   + (SELECT COUNT(*) FROM raw_api_data AS r
      JOIN candidate_batches AS cb ON cb.sync_batch_no = r.sync_batch_no
      WHERE r.api_code <> :api_code
         OR r.jijia_account_id <> :legacy_account_id)
   + (SELECT COUNT(*) FROM raw_api_data_history AS h
      JOIN candidate_batches AS cb ON cb.sync_batch_no = h.sync_batch_no
      WHERE h.api_code <> :api_code
         OR h.jijia_account_id <> :legacy_account_id)
   + (SELECT COUNT(*) FROM failed_request_log AS f
      JOIN candidate_batches AS cb ON cb.sync_batch_no = f.sync_batch_no
      WHERE f.api_code <> :api_code
         OR f.jijia_account_id <> :legacy_account_id)) AS mixed_child_count,
  (SELECT COUNT(*) FROM sync_checkpoint AS c
   JOIN candidate_batches AS cb ON cb.sync_batch_no = c.last_sync_batch_no
   WHERE c.api_code <> :api_code
      OR c.jijia_account_id <> :legacy_account_id) AS cross_api_checkpoint_count,
  (SELECT COUNT(*) FROM raw_api_data AS legacy_row
   JOIN raw_api_data AS target_row
     ON target_row.jijia_account_id = :target_account_id
    AND target_row.api_code = legacy_row.api_code
    AND target_row.record_identity = legacy_row.record_identity
   WHERE legacy_row.jijia_account_id = :legacy_account_id
     AND legacy_row.api_code = :api_code) AS raw_conflict_count,
  (SELECT COUNT(*) FROM raw_api_data_history AS legacy_row
   JOIN raw_api_data_history AS target_row
     ON target_row.jijia_account_id = :target_account_id
    AND target_row.api_code = legacy_row.api_code
    AND target_row.record_identity = legacy_row.record_identity
    AND target_row.data_hash = legacy_row.data_hash
   WHERE legacy_row.jijia_account_id = :legacy_account_id
     AND legacy_row.api_code = :api_code) AS history_conflict_count,
  (SELECT COUNT(*) FROM sync_checkpoint AS legacy_row
   JOIN sync_checkpoint AS target_row
     ON target_row.jijia_account_id = :target_account_id
    AND target_row.api_code = legacy_row.api_code
    AND target_row.checkpoint_kind = legacy_row.checkpoint_kind
   WHERE legacy_row.jijia_account_id = :legacy_account_id
     AND legacy_row.api_code = :api_code) AS checkpoint_conflict_count
"""

ATTRIBUTION_DML_SQL = {
    "history": """
UPDATE raw_api_data_history
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
""",
    "baseline": """
INSERT INTO raw_api_data_history (
  jijia_account_id, api_code, record_identity, source_primary_key,
  data_hash, raw_json, data_date, sync_batch_no, observed_at,
  created_at, updated_at
)
SELECT
  :target_account_id, r.api_code, r.record_identity, r.source_primary_key,
  r.data_hash, r.raw_json, r.data_date, r.sync_batch_no, r.last_observed_at,
  r.created_at, r.updated_at
FROM raw_api_data AS r
WHERE r.id IN :baseline_raw_ids
  AND r.jijia_account_id = :legacy_account_id
  AND r.api_code = :api_code
  AND NOT EXISTS (
    SELECT 1
    FROM raw_api_data_history AS h
    WHERE h.jijia_account_id = :target_account_id
      AND h.api_code = r.api_code
      AND h.record_identity = r.record_identity
      AND h.data_hash = r.data_hash
  )
""",
    "raw": """
UPDATE raw_api_data
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
""",
    "api_log": """
UPDATE sync_api_log
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
""",
    "failed_request": """
UPDATE failed_request_log
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
""",
    "checkpoint": """
UPDATE sync_checkpoint
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE jijia_account_id = :legacy_account_id
  AND api_code = :api_code
""",
    "batch": """
UPDATE sync_batch
SET jijia_account_id = :target_account_id,
    updated_at = updated_at
WHERE sync_batch_no IN :batch_nos
  AND jijia_account_id = :legacy_account_id
""",
}

REMAINING_LEGACY_SQL = """
SELECT
  (SELECT COUNT(*) FROM sync_api_log
   WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
  + (SELECT COUNT(*) FROM failed_request_log
     WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
  + (SELECT COUNT(*) FROM raw_api_data
     WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
  + (SELECT COUNT(*) FROM raw_api_data_history
     WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
  + (SELECT COUNT(*) FROM sync_checkpoint
     WHERE jijia_account_id = :legacy_account_id AND api_code = :api_code)
  AS remaining_legacy_count
"""

BATCH_POSTFLIGHT_SQL = """
SELECT
  (:expected_batch_count - (SELECT COUNT(*) FROM sync_batch
    WHERE sync_batch_no IN :batch_nos))
  + (SELECT COUNT(*) FROM sync_batch
     WHERE sync_batch_no IN :batch_nos
       AND (jijia_account_id <> :target_account_id
         OR sync_job_id IS NOT NULL
         OR status NOT IN ('success', 'partial_failed', 'failed')
         OR finished_at IS NULL
         OR total_api_count <> 1)) AS batch_mismatch_count,
  ((SELECT COUNT(*) FROM sync_api_log
    WHERE sync_batch_no IN :batch_nos
      AND (jijia_account_id <> :target_account_id OR api_code <> :api_code))
   + (SELECT COUNT(*) FROM failed_request_log
      WHERE sync_batch_no IN :batch_nos
        AND (jijia_account_id <> :target_account_id OR api_code <> :api_code))
   + (SELECT COUNT(*) FROM raw_api_data
      WHERE sync_batch_no IN :batch_nos
        AND (jijia_account_id <> :target_account_id OR api_code <> :api_code))
   + (SELECT COUNT(*) FROM raw_api_data_history
      WHERE sync_batch_no IN :batch_nos
        AND (jijia_account_id <> :target_account_id OR api_code <> :api_code)))
    AS child_mismatch_count,
  (SELECT COUNT(*) FROM sync_checkpoint
   WHERE last_sync_batch_no IN :batch_nos
     AND (jijia_account_id <> :target_account_id OR api_code <> :api_code))
    AS checkpoint_mismatch_count,
  (SELECT COUNT(*) FROM (
     SELECT expected_batches.sync_batch_no
     FROM sync_batch AS expected_batches
     LEFT JOIN sync_api_log AS l
       ON l.sync_batch_no = expected_batches.sync_batch_no
     WHERE expected_batches.sync_batch_no IN :batch_nos
     GROUP BY expected_batches.sync_batch_no
     HAVING COUNT(l.id) <> 1
   ) AS invalid_logs) AS invalid_log_cardinality_count
"""

BASELINE_POSTFLIGHT_SQL = """
SELECT COUNT(*)
FROM raw_api_data AS r
WHERE r.id IN :baseline_raw_ids
  AND NOT EXISTS (
    SELECT 1
    FROM raw_api_data_history AS h
    WHERE h.jijia_account_id = :target_account_id
      AND h.api_code = r.api_code
      AND h.record_identity = r.record_identity
      AND h.data_hash = r.data_hash
      AND h.raw_json = r.raw_json
      AND h.source_primary_key <=> r.source_primary_key
      AND h.data_date <=> r.data_date
      AND h.sync_batch_no = r.sync_batch_no
      AND h.observed_at = r.last_observed_at
      AND h.created_at = r.created_at
      AND h.updated_at = r.updated_at
  )
"""


@dataclass(frozen=True)
class AttributionResult:
    """提供稳定且不含账号代码、批次号或业务数据的执行结果。"""

    status: str
    code: str
    stage: str
    mode: str
    restore_required: bool
    reason_code: str | None = None
    details: dict[str, int] = field(default_factory=dict)

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "code": self.code,
            "stage": self.stage,
            "mode": self.mode,
            "restoreRequired": self.restore_required,
        }
        if self.reason_code is not None:
            payload["reasonCode"] = self.reason_code
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class AttributionPlan:
    """保存一致快照内的脱敏计数和仅供事务内部使用的行标识。"""

    target_account_id: int
    batch_nos: tuple[str, ...] = field(repr=False)
    baseline_raw_ids: tuple[int, ...] = field(repr=False)
    candidate_batch_count: int = 0
    legacy_batch_count: int = 0
    legacy_api_log_count: int = 0
    legacy_failed_request_count: int = 0
    legacy_raw_count: int = 0
    legacy_history_count: int = 0
    legacy_checkpoint_count: int = 0
    baseline_candidate_count: int = 0
    missing_batch_count: int = 0
    mock_batch_count: int = 0
    web_job_reference_count: int = 0
    invalid_batch_count: int = 0
    invalid_log_cardinality_count: int = 0
    mixed_child_count: int = 0
    cross_api_checkpoint_count: int = 0
    raw_conflict_count: int = 0
    history_conflict_count: int = 0
    checkpoint_conflict_count: int = 0

    def details(self) -> dict[str, int]:
        return {
            "candidateBatchCount": self.candidate_batch_count,
            "legacyBatchCount": self.legacy_batch_count,
            "legacyApiLogCount": self.legacy_api_log_count,
            "legacyFailedRequestCount": self.legacy_failed_request_count,
            "legacyRawCount": self.legacy_raw_count,
            "legacyHistoryCount": self.legacy_history_count,
            "legacyCheckpointCount": self.legacy_checkpoint_count,
            "baselineCandidateCount": self.baseline_candidate_count,
            "missingBatchCount": self.missing_batch_count,
            "mockBatchCount": self.mock_batch_count,
            "webJobReferenceCount": self.web_job_reference_count,
            "invalidBatchCount": self.invalid_batch_count,
            "invalidLogCardinalityCount": self.invalid_log_cardinality_count,
            "mixedChildCount": self.mixed_child_count,
            "crossApiCheckpointCount": self.cross_api_checkpoint_count,
            "rawConflictCount": self.raw_conflict_count,
            "historyConflictCount": self.history_conflict_count,
            "checkpointConflictCount": self.checkpoint_conflict_count,
        }


@dataclass(frozen=True)
class ApplyCounts:
    history_updated: int
    history_seeded: int
    raw_updated: int
    api_log_updated: int
    failed_request_updated: int
    checkpoint_updated: int
    batch_updated: int


@dataclass(frozen=True)
class PostflightSnapshot:
    remaining_legacy_count: int
    batch_mismatch_count: int
    child_mismatch_count: int
    checkpoint_mismatch_count: int
    invalid_log_cardinality_count: int
    baseline_mismatch_count: int


class _StopAttribution(Exception):
    def __init__(self, result: AttributionResult) -> None:
        self.result = result


def evaluate_plan(
    plan: AttributionPlan,
    *,
    mode: str = "dry-run",
) -> AttributionResult | None:
    """按固定优先级阻断会破坏账号、批次或唯一键边界的计划。"""
    checks = (
        (plan.candidate_batch_count != len(plan.batch_nos), "PLAN_BATCH_SET_MISMATCH"),
        (
            plan.baseline_candidate_count != len(plan.baseline_raw_ids),
            "PLAN_BASELINE_SET_MISMATCH",
        ),
        (plan.missing_batch_count, "LEGACY_BATCH_MISSING"),
        (plan.mock_batch_count, "LEGACY_MOCK_BATCH_DETECTED"),
        (plan.web_job_reference_count, "LEGACY_BATCH_WEB_JOB_REFERENCE"),
        (plan.invalid_batch_count, "LEGACY_BATCH_NOT_TERMINAL_SINGLE_API"),
        (plan.invalid_log_cardinality_count, "LEGACY_BATCH_LOG_INVALID"),
        (plan.mixed_child_count, "LEGACY_BATCH_MIXED_OR_ACCOUNT_MISMATCH"),
        (plan.cross_api_checkpoint_count, "CHECKPOINT_CROSS_API_REFERENCE"),
        (plan.raw_conflict_count, "TARGET_RAW_CONFLICT"),
        (plan.history_conflict_count, "TARGET_HISTORY_CONFLICT"),
        (plan.checkpoint_conflict_count, "TARGET_CHECKPOINT_CONFLICT"),
    )
    for failed, reason_code in checks:
        if failed:
            return AttributionResult(
                status="blocked",
                code="ATTRIBUTION_PREFLIGHT_BLOCKED",
                stage="preflight",
                mode=mode,
                restore_required=False,
                reason_code=reason_code,
                details=plan.details(),
            )
    return None


def evaluate_postflight(
    plan: AttributionPlan,
    counts: ApplyCounts,
    snapshot: PostflightSnapshot,
) -> AttributionResult | None:
    """提交前验证实际行数、账号归属、批次链和基线内容。"""
    expected = ApplyCounts(
        history_updated=plan.legacy_history_count,
        history_seeded=plan.baseline_candidate_count,
        raw_updated=plan.legacy_raw_count,
        api_log_updated=plan.legacy_api_log_count,
        failed_request_updated=plan.legacy_failed_request_count,
        checkpoint_updated=plan.legacy_checkpoint_count,
        batch_updated=plan.legacy_batch_count,
    )
    reason_code: str | None = None
    if counts != expected:
        reason_code = "DML_ROW_COUNT_MISMATCH"
    elif (
        snapshot.remaining_legacy_count
        or snapshot.batch_mismatch_count
        or snapshot.child_mismatch_count
        or snapshot.checkpoint_mismatch_count
        or snapshot.invalid_log_cardinality_count
    ):
        reason_code = "POSTFLIGHT_ACCOUNT_BATCH_MISMATCH"
    elif snapshot.baseline_mismatch_count:
        reason_code = "POSTFLIGHT_BASELINE_MISMATCH"
    if reason_code is None:
        return None
    return AttributionResult(
        status="blocked",
        code="ATTRIBUTION_POSTFLIGHT_BLOCKED",
        stage="postflight",
        mode="execute",
        restore_required=False,
        reason_code=reason_code,
        details=plan.details(),
    )


def resolve_target_account_id(
    connection: Connection,
    *,
    target_account_id: int | None,
    target_account_code: str | None,
) -> int | None:
    """按显式 ID 或 account_code 解析目标，不从运行配置猜测账号。"""
    if (target_account_id is None) == (target_account_code is None):
        raise ValueError("exactly one target account selector is required")
    if target_account_id is not None:
        if target_account_id <= 0:
            return None
        resolved = connection.execute(
            text("SELECT id FROM jijia_account WHERE id = :target_account_id"),
            {"target_account_id": target_account_id},
        ).scalar_one_or_none()
    else:
        resolved = connection.execute(
            text("SELECT id FROM jijia_account WHERE account_code = :target_account_code"),
            {"target_account_code": target_account_code},
        ).scalar_one_or_none()
    return int(resolved) if resolved is not None and int(resolved) > 0 else None


def collect_attribution_plan(
    connection: Connection,
    target_account_id: int,
) -> AttributionPlan:
    """在持锁的一致事务快照内采集计划，内部标识不会进入输出。"""
    params = {
        "api_code": API_CODE,
        "legacy_account_id": LEGACY_ACCOUNT_ID,
        "target_account_id": target_account_id,
    }
    batch_nos = tuple(
        str(value)
        for value in connection.execute(text(CANDIDATE_BATCH_SQL), params).scalars().all()
    )
    baseline_raw_ids = tuple(
        int(value)
        for value in connection.execute(text(BASELINE_RAW_IDS_SQL), params).scalars().all()
    )
    row = connection.execute(text(PLAN_SUMMARY_SQL), params).mappings().one()
    return AttributionPlan(
        target_account_id=target_account_id,
        batch_nos=batch_nos,
        baseline_raw_ids=baseline_raw_ids,
        candidate_batch_count=int(row["candidate_batch_count"] or 0),
        legacy_batch_count=int(row["legacy_batch_count"] or 0),
        legacy_api_log_count=int(row["legacy_api_log_count"] or 0),
        legacy_failed_request_count=int(row["legacy_failed_request_count"] or 0),
        legacy_raw_count=int(row["legacy_raw_count"] or 0),
        legacy_history_count=int(row["legacy_history_count"] or 0),
        legacy_checkpoint_count=int(row["legacy_checkpoint_count"] or 0),
        baseline_candidate_count=len(baseline_raw_ids),
        missing_batch_count=int(row["missing_batch_count"] or 0),
        mock_batch_count=int(row["mock_batch_count"] or 0),
        web_job_reference_count=int(row["web_job_reference_count"] or 0),
        invalid_batch_count=int(row["invalid_batch_count"] or 0),
        invalid_log_cardinality_count=int(row["invalid_log_cardinality_count"] or 0),
        mixed_child_count=int(row["mixed_child_count"] or 0),
        cross_api_checkpoint_count=int(row["cross_api_checkpoint_count"] or 0),
        raw_conflict_count=int(row["raw_conflict_count"] or 0),
        history_conflict_count=int(row["history_conflict_count"] or 0),
        checkpoint_conflict_count=int(row["checkpoint_conflict_count"] or 0),
    )


def apply_attribution(connection: Connection, plan: AttributionPlan) -> ApplyCounts:
    """按既有历史、缺失基线、当前数据、批次头的固定顺序执行 DML。"""
    params: dict[str, Any] = {
        "api_code": API_CODE,
        "legacy_account_id": LEGACY_ACCOUNT_ID,
        "target_account_id": plan.target_account_id,
    }
    history_updated = _rowcount(connection.execute(text(ATTRIBUTION_DML_SQL["history"]), params))
    history_seeded = 0
    if plan.baseline_raw_ids:
        baseline_statement = text(ATTRIBUTION_DML_SQL["baseline"]).bindparams(
            bindparam("baseline_raw_ids", expanding=True)
        )
        history_seeded = _rowcount(
            connection.execute(
                baseline_statement,
                {**params, "baseline_raw_ids": plan.baseline_raw_ids},
            )
        )
    raw_updated = _rowcount(connection.execute(text(ATTRIBUTION_DML_SQL["raw"]), params))
    api_log_updated = _rowcount(connection.execute(text(ATTRIBUTION_DML_SQL["api_log"]), params))
    failed_request_updated = _rowcount(
        connection.execute(text(ATTRIBUTION_DML_SQL["failed_request"]), params)
    )
    checkpoint_updated = _rowcount(
        connection.execute(text(ATTRIBUTION_DML_SQL["checkpoint"]), params)
    )
    batch_updated = 0
    if plan.batch_nos:
        batch_statement = text(ATTRIBUTION_DML_SQL["batch"]).bindparams(
            bindparam("batch_nos", expanding=True)
        )
        batch_updated = _rowcount(
            connection.execute(batch_statement, {**params, "batch_nos": plan.batch_nos})
        )
    return ApplyCounts(
        history_updated=history_updated,
        history_seeded=history_seeded,
        raw_updated=raw_updated,
        api_log_updated=api_log_updated,
        failed_request_updated=failed_request_updated,
        checkpoint_updated=checkpoint_updated,
        batch_updated=batch_updated,
    )


def collect_postflight_snapshot(
    connection: Connection,
    plan: AttributionPlan,
) -> PostflightSnapshot:
    """提交前验证归属结果；仅返回计数，不返回账号代码或批次号。"""
    params: dict[str, Any] = {
        "api_code": API_CODE,
        "legacy_account_id": LEGACY_ACCOUNT_ID,
        "target_account_id": plan.target_account_id,
    }
    remaining = connection.execute(text(REMAINING_LEGACY_SQL), params).scalar_one()
    batch_mismatch_count = 0
    child_mismatch_count = 0
    checkpoint_mismatch_count = 0
    invalid_log_cardinality_count = 0
    if plan.batch_nos:
        batch_statement = text(BATCH_POSTFLIGHT_SQL).bindparams(
            bindparam("batch_nos", expanding=True)
        )
        row = (
            connection.execute(
                batch_statement,
                {
                    **params,
                    "batch_nos": plan.batch_nos,
                    "expected_batch_count": len(plan.batch_nos),
                },
            )
            .mappings()
            .one()
        )
        batch_mismatch_count = int(row["batch_mismatch_count"] or 0)
        child_mismatch_count = int(row["child_mismatch_count"] or 0)
        checkpoint_mismatch_count = int(row["checkpoint_mismatch_count"] or 0)
        invalid_log_cardinality_count = int(row["invalid_log_cardinality_count"] or 0)
    baseline_mismatch_count = 0
    if plan.baseline_raw_ids:
        baseline_statement = text(BASELINE_POSTFLIGHT_SQL).bindparams(
            bindparam("baseline_raw_ids", expanding=True)
        )
        baseline_mismatch_count = int(
            connection.execute(
                baseline_statement,
                {**params, "baseline_raw_ids": plan.baseline_raw_ids},
            ).scalar_one()
            or 0
        )
    return PostflightSnapshot(
        remaining_legacy_count=int(remaining or 0),
        batch_mismatch_count=batch_mismatch_count,
        child_mismatch_count=child_mismatch_count,
        checkpoint_mismatch_count=checkpoint_mismatch_count,
        invalid_log_cardinality_count=invalid_log_cardinality_count,
        baseline_mismatch_count=baseline_mismatch_count,
    )


def run_legacy_sale_return_attribution(
    engine: Engine,
    *,
    target_account_id: int | None = None,
    target_account_code: str | None = None,
    execute: bool = False,
) -> AttributionResult:
    """使用一个连接、一个数据事务和共用 named lock 生成计划或执行归属。"""
    connection: Connection | None = None
    result: AttributionResult | None = None
    mode = "execute" if execute else "dry-run"
    try:
        connection = engine.connect()
        result = _run_on_connection(
            connection,
            target_account_id=target_account_id,
            target_account_code=target_account_code,
            execute=execute,
        )
    except Exception:
        result = AttributionResult(
            status="error",
            code="ATTRIBUTION_CONNECTION_FAILED",
            stage="connection",
            mode=mode,
            restore_required=False,
        )
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                if result is None or result.status in {"planned", "success"}:
                    result = AttributionResult(
                        status="error",
                        code="ATTRIBUTION_CONNECTION_CLOSE_FAILED",
                        stage="connection_close",
                        mode=mode,
                        restore_required=False,
                    )
    return result or AttributionResult(
        status="error",
        code="ATTRIBUTION_CONNECTION_FAILED",
        stage="connection",
        mode=mode,
        restore_required=False,
    )


def _run_on_connection(
    connection: Connection,
    *,
    target_account_id: int | None,
    target_account_code: str | None,
    execute: bool,
) -> AttributionResult:
    mode = "execute" if execute else "dry-run"
    result: AttributionResult | None = None
    lock_acquired = False
    transaction_open = False
    commit_uncertain = False
    stage = "acquire_lock"
    plan: AttributionPlan | None = None
    try:
        lock_result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 0)"),
            {"lock_name": SYNC_TASK_LOCK_NAME},
        ).scalar_one()
        if lock_result == 0:
            raise _StopAttribution(
                AttributionResult(
                    status="blocked",
                    code="ATTRIBUTION_LOCK_BUSY",
                    stage=stage,
                    mode=mode,
                    restore_required=False,
                )
            )
        if lock_result != 1:
            raise _StopAttribution(
                AttributionResult(
                    status="error",
                    code="ATTRIBUTION_LOCK_ERROR",
                    stage=stage,
                    mode=mode,
                    restore_required=False,
                )
            )
        lock_acquired = True

        stage = "verify_lock"
        owner = (
            connection.execute(
                text(
                    """
                    SELECT CONNECTION_ID() AS connection_id,
                           IS_USED_LOCK(:lock_name) AS lock_owner_id
                    """
                ),
                {"lock_name": SYNC_TASK_LOCK_NAME},
            )
            .mappings()
            .one()
        )
        if owner["connection_id"] is None or owner["lock_owner_id"] != owner["connection_id"]:
            raise _StopAttribution(
                AttributionResult(
                    status="blocked",
                    code="ATTRIBUTION_LOCK_NOT_OWNED",
                    stage=stage,
                    mode=mode,
                    restore_required=False,
                )
            )

        connection.execute(text("SET SESSION time_zone = '+00:00'"))
        connection.commit()
        transaction_open = True

        stage = "schema"
        schema_result = evaluate_target_schema(collect_target_schema_snapshot(connection))
        if schema_result.status != "pass":
            raise _StopAttribution(
                AttributionResult(
                    status="blocked",
                    code="ATTRIBUTION_SCHEMA_BLOCKED",
                    stage=stage,
                    mode=mode,
                    restore_required=False,
                    reason_code=schema_result.code,
                    details=schema_result.details,
                )
            )

        stage = "target_account"
        resolved_account_id = resolve_target_account_id(
            connection,
            target_account_id=target_account_id,
            target_account_code=target_account_code,
        )
        if resolved_account_id is None:
            raise _StopAttribution(
                AttributionResult(
                    status="blocked",
                    code="ATTRIBUTION_PREFLIGHT_BLOCKED",
                    stage=stage,
                    mode=mode,
                    restore_required=False,
                    reason_code="TARGET_ACCOUNT_NOT_FOUND",
                )
            )

        stage = "preflight"
        plan = collect_attribution_plan(connection, resolved_account_id)
        plan_result = evaluate_plan(plan, mode=mode)
        if plan_result is not None:
            raise _StopAttribution(plan_result)

        if not execute:
            connection.rollback()
            transaction_open = False
            result = AttributionResult(
                status="planned",
                code="ATTRIBUTION_PLAN_READY",
                stage="complete",
                mode=mode,
                restore_required=False,
                details=plan.details(),
            )
        else:
            stage = "apply"
            counts = apply_attribution(connection, plan)
            stage = "postflight"
            postflight_result = evaluate_postflight(
                plan,
                counts,
                collect_postflight_snapshot(connection, plan),
            )
            if postflight_result is not None:
                raise _StopAttribution(postflight_result)
            stage = "commit"
            try:
                connection.commit()
                transaction_open = False
            except Exception:
                commit_uncertain = True
                transaction_open = False
                raise
            result = AttributionResult(
                status="success",
                code="ATTRIBUTION_APPLIED",
                stage="complete",
                mode=mode,
                restore_required=False,
                details=plan.details(),
            )
    except _StopAttribution as stop:
        if transaction_open:
            try:
                connection.rollback()
                transaction_open = False
                result = stop.result
            except Exception:
                result = AttributionResult(
                    status="error",
                    code="ATTRIBUTION_ROLLBACK_FAILED",
                    stage="rollback",
                    mode=mode,
                    restore_required=(stage in {"apply", "postflight", "commit"}),
                )
        else:
            result = stop.result
    except Exception:
        rollback_failed = False
        if transaction_open:
            try:
                connection.rollback()
            except Exception:
                rollback_failed = True
        if rollback_failed:
            result = AttributionResult(
                status="error",
                code="ATTRIBUTION_ROLLBACK_FAILED",
                stage="rollback",
                mode=mode,
                restore_required=(stage in {"apply", "postflight", "commit"}),
            )
        elif commit_uncertain:
            result = AttributionResult(
                status="error",
                code="ATTRIBUTION_COMMIT_FAILED",
                stage="commit",
                mode=mode,
                restore_required=True,
            )
        else:
            result = AttributionResult(
                status="error",
                code="ATTRIBUTION_RUNTIME_FAILED",
                stage=stage,
                mode=mode,
                restore_required=False,
            )
    finally:
        if lock_acquired:
            release_failed = False
            try:
                release_result = connection.execute(
                    text("SELECT RELEASE_LOCK(:lock_name)"),
                    {"lock_name": SYNC_TASK_LOCK_NAME},
                ).scalar_one()
                release_failed = release_result != 1
            except Exception:
                release_failed = True
            if release_failed:
                result = AttributionResult(
                    status="error",
                    code="ATTRIBUTION_LOCK_RELEASE_FAILED",
                    stage="release_lock",
                    mode=mode,
                    restore_required=result.restore_required if result is not None else False,
                )
    return result or AttributionResult(
        status="error",
        code="ATTRIBUTION_RUNTIME_FAILED",
        stage=stage,
        mode=mode,
        restore_required=False,
    )


def _rowcount(result: Any) -> int:
    value = int(result.rowcount)
    return value if value >= 0 else 0
