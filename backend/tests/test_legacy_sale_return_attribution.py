import json
from dataclasses import replace

import pytest

from backend.app import legacy_sale_return_attribution
from backend.app.services import legacy_sale_return_attribution_service as service
from backend.app.services.legacy_sale_return_attribution_service import (
    ApplyCounts,
    AttributionPlan,
    AttributionResult,
    PostflightSnapshot,
    evaluate_plan,
    evaluate_postflight,
    run_legacy_sale_return_attribution,
)
from backend.app.services.migration_0003_service import (
    TARGET_COLUMN_EXTRA_FRAGMENTS,
    TARGET_COLUMN_SPECS,
    TARGET_INDEX_SPECS,
    TargetSchemaSnapshot,
)
from backend.app.services.migration_preflight_service import PreflightResult


class FakeResult:
    def __init__(self, *, scalar=None, row=None, values=None, rowcount: int = 0) -> None:
        self.scalar = scalar
        self.row = row
        self.values = values
        self.rowcount = rowcount

    def scalar_one(self):
        return self.scalar

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.values

    def mappings(self):
        return self

    def one(self):
        return self.row


class FakeConnection:
    def __init__(
        self,
        *,
        lock_result=1,
        owner_matches: bool = True,
        release_result=1,
        release_error: Exception | None = None,
        close_error: Exception | None = None,
        commit_error_at: int | None = None,
        rollback_error: Exception | None = None,
    ) -> None:
        self.lock_result = lock_result
        self.owner_matches = owner_matches
        self.release_result = release_result
        self.release_error = release_error
        self.close_error = close_error
        self.commit_error_at = commit_error_at
        self.rollback_error = rollback_error
        self.execute_calls: list[str] = []
        self.events: list[str] = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.release_calls = 0
        self.closed = False

    def execute(self, statement, _params=None):
        sql = str(statement)
        self.execute_calls.append(sql)
        if "GET_LOCK" in sql:
            return FakeResult(scalar=self.lock_result)
        if "CONNECTION_ID" in sql and "IS_USED_LOCK" in sql:
            return FakeResult(
                row={
                    "connection_id": 41,
                    "lock_owner_id": 41 if self.owner_matches else 99,
                }
            )
        if "SET SESSION time_zone" in sql:
            self.events.append("set_utc")
            return FakeResult()
        if "RELEASE_LOCK" in sql:
            self.release_calls += 1
            if self.release_error is not None:
                raise self.release_error
            return FakeResult(scalar=self.release_result)
        raise AssertionError(f"unexpected query: {sql}")

    def commit(self) -> None:
        self.commit_calls += 1
        self.events.append(f"commit_{self.commit_calls}")
        if self.commit_error_at == self.commit_calls:
            raise RuntimeError("secret commit failure")

    def rollback(self) -> None:
        self.rollback_calls += 1
        self.events.append("rollback")
        if self.rollback_error is not None:
            raise self.rollback_error

    def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class FakeEngine:
    def __init__(
        self,
        connection: FakeConnection | None = None,
        *,
        dispose_error: Exception | None = None,
    ) -> None:
        self.connection = connection or FakeConnection()
        self.connect_calls = 0
        self.disposed = False
        self.dispose_error = dispose_error

    def connect(self):
        self.connect_calls += 1
        return self.connection

    def dispose(self) -> None:
        self.disposed = True
        if self.dispose_error is not None:
            raise self.dispose_error


class QueueConnection:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return self.results.pop(0)


def _ready_plan(**changes) -> AttributionPlan:
    plan = AttributionPlan(
        target_account_id=7,
        batch_nos=("legacy-batch-1",),
        baseline_raw_ids=(31,),
        candidate_batch_count=1,
        legacy_batch_count=1,
        legacy_api_log_count=1,
        legacy_failed_request_count=0,
        legacy_raw_count=1,
        legacy_history_count=0,
        legacy_checkpoint_count=1,
        baseline_candidate_count=1,
        missing_batch_count=0,
        mock_batch_count=0,
        web_job_reference_count=0,
        invalid_batch_count=0,
        invalid_log_cardinality_count=0,
        mixed_child_count=0,
        cross_api_checkpoint_count=0,
        raw_conflict_count=0,
        history_conflict_count=0,
        checkpoint_conflict_count=0,
    )
    return replace(plan, **changes)


def _expected_counts(plan: AttributionPlan) -> ApplyCounts:
    return ApplyCounts(
        history_updated=plan.legacy_history_count,
        history_seeded=plan.baseline_candidate_count,
        raw_updated=plan.legacy_raw_count,
        api_log_updated=plan.legacy_api_log_count,
        failed_request_updated=plan.legacy_failed_request_count,
        checkpoint_updated=plan.legacy_checkpoint_count,
        batch_updated=plan.legacy_batch_count,
    )


def _clean_postflight() -> PostflightSnapshot:
    return PostflightSnapshot(
        remaining_legacy_count=0,
        batch_mismatch_count=0,
        child_mismatch_count=0,
        checkpoint_mismatch_count=0,
        invalid_log_cardinality_count=0,
        baseline_mismatch_count=0,
    )


def _patch_ready_runner(monkeypatch, *, postflight=None) -> list[str]:
    events: list[str] = []
    ready_plan = _ready_plan()
    monkeypatch.setattr(service, "collect_target_schema_snapshot", lambda connection: object())
    monkeypatch.setattr(
        service,
        "evaluate_target_schema",
        lambda _snapshot: PreflightResult(status="pass", code="TARGET_SCHEMA_READY"),
    )
    monkeypatch.setattr(
        service,
        "resolve_target_account_id",
        lambda connection, **_kwargs: 7,
    )
    monkeypatch.setattr(
        service,
        "collect_attribution_plan",
        lambda connection, target_account_id: ready_plan,
    )

    def apply_attribution(connection, received_plan):
        assert received_plan is ready_plan
        events.append("apply")
        return _expected_counts(ready_plan)

    def collect_postflight(connection, received_plan):
        assert received_plan is ready_plan
        events.append("postflight")
        return postflight or _clean_postflight()

    monkeypatch.setattr(service, "apply_attribution", apply_attribution)
    monkeypatch.setattr(service, "collect_postflight_snapshot", collect_postflight)
    return events


@pytest.mark.parametrize(
    ("field_name", "reason_code"),
    [
        ("missing_batch_count", "LEGACY_BATCH_MISSING"),
        ("mock_batch_count", "LEGACY_MOCK_BATCH_DETECTED"),
        ("web_job_reference_count", "LEGACY_BATCH_WEB_JOB_REFERENCE"),
        ("invalid_batch_count", "LEGACY_BATCH_NOT_TERMINAL_SINGLE_API"),
        ("invalid_log_cardinality_count", "LEGACY_BATCH_LOG_INVALID"),
        ("mixed_child_count", "LEGACY_BATCH_MIXED_OR_ACCOUNT_MISMATCH"),
        ("cross_api_checkpoint_count", "CHECKPOINT_CROSS_API_REFERENCE"),
        ("raw_conflict_count", "TARGET_RAW_CONFLICT"),
        ("history_conflict_count", "TARGET_HISTORY_CONFLICT"),
        ("checkpoint_conflict_count", "TARGET_CHECKPOINT_CONFLICT"),
    ],
)
def test_plan_blocks_each_integrity_violation(field_name, reason_code) -> None:
    result = evaluate_plan(_ready_plan(**{field_name: 1}))

    assert result is not None
    assert result.status == "blocked"
    assert result.reason_code == reason_code


def test_plan_accepts_strict_single_api_scope() -> None:
    assert evaluate_plan(_ready_plan()) is None


def test_single_api_mock_batch_is_still_blocked() -> None:
    result = evaluate_plan(_ready_plan(mock_batch_count=1))

    assert result is not None
    assert result.reason_code == "LEGACY_MOCK_BATCH_DETECTED"


def test_empty_plan_is_idempotent() -> None:
    plan = _ready_plan(
        batch_nos=(),
        baseline_raw_ids=(),
        candidate_batch_count=0,
        legacy_batch_count=0,
        legacy_api_log_count=0,
        legacy_raw_count=0,
        legacy_checkpoint_count=0,
        baseline_candidate_count=0,
    )

    assert evaluate_plan(plan) is None
    assert evaluate_postflight(plan, _expected_counts(plan), _clean_postflight()) is None


def test_postflight_requires_exact_row_counts_and_consistency() -> None:
    plan = _ready_plan()
    counts = _expected_counts(plan)

    assert evaluate_postflight(plan, counts, _clean_postflight()) is None

    wrong_counts = replace(counts, history_seeded=0)
    count_result = evaluate_postflight(plan, wrong_counts, _clean_postflight())
    mismatch_result = evaluate_postflight(
        plan,
        counts,
        replace(_clean_postflight(), child_mismatch_count=1),
    )

    assert count_result is not None
    assert count_result.reason_code == "DML_ROW_COUNT_MISMATCH"
    assert mismatch_result is not None
    assert mismatch_result.reason_code == "POSTFLIGHT_ACCOUNT_BATCH_MISMATCH"


def test_dry_run_uses_one_locked_connection_and_never_applies(monkeypatch) -> None:
    events = _patch_ready_runner(monkeypatch)
    engine = FakeEngine()

    result = run_legacy_sale_return_attribution(
        engine,
        target_account_id=7,
        execute=False,
    )

    assert result.status == "planned"
    assert result.code == "ATTRIBUTION_PLAN_READY"
    assert engine.connect_calls == 1
    assert engine.connection.commit_calls == 1
    assert engine.connection.rollback_calls == 1
    assert engine.connection.release_calls == 1
    assert engine.connection.closed is True
    assert events == []


def test_execute_blocks_non_innodb_schema_before_dml(monkeypatch) -> None:
    table_engines = {table_name: "innodb" for table_name, _column_name in TARGET_COLUMN_SPECS}
    table_engines["raw_api_data"] = "myisam"
    snapshot = TargetSchemaSnapshot(
        column_specs=dict(TARGET_COLUMN_SPECS),
        column_extras=dict(TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(TARGET_INDEX_SPECS),
        table_engines=table_engines,
    )
    monkeypatch.setattr(
        service,
        "collect_target_schema_snapshot",
        lambda _connection: snapshot,
    )
    apply_calls: list[object] = []
    monkeypatch.setattr(
        service,
        "apply_attribution",
        lambda *_args: apply_calls.append(object()),
    )
    engine = FakeEngine()

    result = run_legacy_sale_return_attribution(
        engine,
        target_account_id=7,
        execute=True,
    )

    assert result.status == "blocked"
    assert result.code == "ATTRIBUTION_SCHEMA_BLOCKED"
    assert result.reason_code == "POSTFLIGHT_SCHEMA_MISMATCH"
    assert apply_calls == []
    assert engine.connection.rollback_calls == 1


def test_execute_runs_postflight_before_commit(monkeypatch) -> None:
    events = _patch_ready_runner(monkeypatch)
    engine = FakeEngine()

    result = run_legacy_sale_return_attribution(
        engine,
        target_account_code="account-a",
        execute=True,
    )

    assert result.status == "success"
    assert result.code == "ATTRIBUTION_APPLIED"
    assert events == ["apply", "postflight"]
    assert engine.connection.events == ["set_utc", "commit_1", "commit_2"]
    assert engine.connection.rollback_calls == 0
    assert engine.connection.release_calls == 1


def test_execute_rolls_back_when_postflight_blocks(monkeypatch) -> None:
    events = _patch_ready_runner(
        monkeypatch,
        postflight=replace(_clean_postflight(), checkpoint_mismatch_count=1),
    )
    engine = FakeEngine()

    result = run_legacy_sale_return_attribution(
        engine,
        target_account_id=7,
        execute=True,
    )

    assert result.status == "blocked"
    assert result.code == "ATTRIBUTION_POSTFLIGHT_BLOCKED"
    assert events == ["apply", "postflight"]
    assert engine.connection.commit_calls == 1
    assert engine.connection.rollback_calls == 1


def test_runner_blocks_lock_and_target_failures_before_dml(monkeypatch) -> None:
    _patch_ready_runner(monkeypatch)
    busy_engine = FakeEngine(FakeConnection(lock_result=0))

    busy = run_legacy_sale_return_attribution(
        busy_engine,
        target_account_id=7,
        execute=True,
    )

    assert busy.code == "ATTRIBUTION_LOCK_BUSY"
    assert busy_engine.connection.commit_calls == 0
    assert busy_engine.connection.release_calls == 0

    monkeypatch.setattr(
        service,
        "resolve_target_account_id",
        lambda connection, **_kwargs: None,
    )
    missing_engine = FakeEngine()
    missing = run_legacy_sale_return_attribution(
        missing_engine,
        target_account_id=999,
        execute=True,
    )

    assert missing.status == "blocked"
    assert missing.reason_code == "TARGET_ACCOUNT_NOT_FOUND"
    assert missing_engine.connection.rollback_calls == 1


def test_runner_blocks_when_named_lock_owner_is_different(monkeypatch) -> None:
    _patch_ready_runner(monkeypatch)
    engine = FakeEngine(FakeConnection(owner_matches=False))

    result = run_legacy_sale_return_attribution(
        engine,
        target_account_id=7,
        execute=True,
    )

    assert result.status == "blocked"
    assert result.code == "ATTRIBUTION_LOCK_NOT_OWNED"
    assert engine.connection.commit_calls == 0
    assert engine.connection.release_calls == 1


def test_release_and_commit_errors_never_report_success(monkeypatch) -> None:
    _patch_ready_runner(monkeypatch)
    release_engine = FakeEngine(FakeConnection(release_result=0))
    release_result = run_legacy_sale_return_attribution(
        release_engine,
        target_account_id=7,
        execute=True,
    )

    assert release_result.status == "error"
    assert release_result.code == "ATTRIBUTION_LOCK_RELEASE_FAILED"

    commit_engine = FakeEngine(FakeConnection(commit_error_at=2))
    commit_result = run_legacy_sale_return_attribution(
        commit_engine,
        target_account_id=7,
        execute=True,
    )

    assert commit_result.status == "error"
    assert commit_result.code == "ATTRIBUTION_COMMIT_FAILED"
    assert commit_result.restore_required is True


def test_rollback_and_close_errors_never_report_success(monkeypatch) -> None:
    _patch_ready_runner(
        monkeypatch,
        postflight=replace(_clean_postflight(), child_mismatch_count=1),
    )
    rollback_engine = FakeEngine(
        FakeConnection(rollback_error=RuntimeError("secret rollback failure"))
    )

    rollback_result = run_legacy_sale_return_attribution(
        rollback_engine,
        target_account_id=7,
        execute=True,
    )

    assert rollback_result.status == "error"
    assert rollback_result.code == "ATTRIBUTION_ROLLBACK_FAILED"

    _patch_ready_runner(monkeypatch)
    close_engine = FakeEngine(FakeConnection(close_error=RuntimeError("secret close failure")))
    close_result = run_legacy_sale_return_attribution(
        close_engine,
        target_account_id=7,
        execute=True,
    )

    assert close_result.status == "error"
    assert close_result.code == "ATTRIBUTION_CONNECTION_CLOSE_FAILED"


def test_runner_second_execute_with_empty_plan_is_idempotent(monkeypatch) -> None:
    class StatefulAttributionFake:
        def __init__(self) -> None:
            self.migrated = False
            self.apply_counts: list[ApplyCounts] = []
            self.postflight_calls = 0

        def collect(self, _connection, _target_account_id):
            if not self.migrated:
                return _ready_plan()
            return _ready_plan(
                batch_nos=(),
                baseline_raw_ids=(),
                candidate_batch_count=0,
                legacy_batch_count=0,
                legacy_api_log_count=0,
                legacy_raw_count=0,
                legacy_checkpoint_count=0,
                baseline_candidate_count=0,
            )

        def apply(self, _connection, plan):
            counts = _expected_counts(plan)
            self.apply_counts.append(counts)
            self.migrated = True
            return counts

        def postflight(self, _connection, _plan):
            self.postflight_calls += 1
            return _clean_postflight()

    stateful_fake = StatefulAttributionFake()
    monkeypatch.setattr(service, "collect_target_schema_snapshot", lambda _connection: object())
    monkeypatch.setattr(
        service,
        "evaluate_target_schema",
        lambda _snapshot: PreflightResult(status="pass", code="TARGET_SCHEMA_READY"),
    )
    monkeypatch.setattr(
        service,
        "resolve_target_account_id",
        lambda _connection, **_kwargs: 7,
    )
    monkeypatch.setattr(service, "collect_attribution_plan", stateful_fake.collect)
    monkeypatch.setattr(service, "apply_attribution", stateful_fake.apply)
    monkeypatch.setattr(service, "collect_postflight_snapshot", stateful_fake.postflight)
    first_engine = FakeEngine()
    first_result = run_legacy_sale_return_attribution(
        first_engine,
        target_account_id=7,
        execute=True,
    )
    second_engine = FakeEngine()

    second_result = run_legacy_sale_return_attribution(
        second_engine,
        target_account_id=7,
        execute=True,
    )

    assert first_result.status == "success"
    assert first_engine.connection.commit_calls == 2
    assert second_result.status == "success"
    assert second_result.code == "ATTRIBUTION_APPLIED"
    assert second_result.details["candidateBatchCount"] == 0
    assert stateful_fake.apply_counts == [
        _expected_counts(_ready_plan()),
        ApplyCounts(0, 0, 0, 0, 0, 0, 0),
    ]
    assert stateful_fake.postflight_calls == 2
    assert second_engine.connection.commit_calls == 2
    assert second_engine.connection.rollback_calls == 0


def test_dml_contract_preserves_content_timestamps_and_order() -> None:
    statements = service.ATTRIBUTION_DML_SQL

    assert list(statements) == [
        "history",
        "baseline",
        "raw",
        "api_log",
        "failed_request",
        "checkpoint",
        "batch",
    ]
    for name in ("history", "raw", "api_log", "failed_request", "checkpoint", "batch"):
        assert "updated_at = updated_at" in statements[name]

    baseline = statements["baseline"]
    for field in (
        "record_identity",
        "data_hash",
        "raw_json",
        "sync_batch_no",
        "last_observed_at",
        "created_at",
        "updated_at",
    ):
        assert field in baseline
    assert "NOT EXISTS" in baseline
    assert "r.id IN" in baseline


def test_each_update_has_exact_account_api_or_captured_batch_scope() -> None:
    statements = service.ATTRIBUTION_DML_SQL
    for name in ("history", "raw", "api_log", "failed_request", "checkpoint"):
        normalized = " ".join(statements[name].split())
        assert "WHERE jijia_account_id = :legacy_account_id" in normalized
        assert "AND api_code = :api_code" in normalized

    batch = " ".join(statements["batch"].split())
    assert "WHERE sync_batch_no IN :batch_nos" in batch
    assert "AND jijia_account_id = :legacy_account_id" in batch

    baseline = " ".join(statements["baseline"].split())
    assert "WHERE r.id IN :baseline_raw_ids" in baseline
    assert "AND r.jijia_account_id = :legacy_account_id" in baseline
    assert "AND r.api_code = :api_code" in baseline
    assert "h.jijia_account_id = :target_account_id" in baseline
    assert "NOT EXISTS" in baseline


def test_apply_executes_fixed_order_with_exact_plan_sets() -> None:
    plan = _ready_plan(
        legacy_history_count=1,
        legacy_failed_request_count=1,
    )
    connection = QueueConnection([FakeResult(rowcount=1) for _ in range(7)])

    counts = service.apply_attribution(connection, plan)

    assert counts == _expected_counts(plan)
    assert len(connection.calls) == 7
    assert "UPDATE raw_api_data_history" in connection.calls[0][0]
    assert "INSERT INTO raw_api_data_history" in connection.calls[1][0]
    assert "UPDATE raw_api_data" in connection.calls[2][0]
    assert "UPDATE sync_api_log" in connection.calls[3][0]
    assert "UPDATE failed_request_log" in connection.calls[4][0]
    assert "UPDATE sync_checkpoint" in connection.calls[5][0]
    assert "UPDATE sync_batch" in connection.calls[6][0]
    assert connection.calls[1][1]["baseline_raw_ids"] == (31,)
    assert connection.calls[6][1]["batch_nos"] == ("legacy-batch-1",)
    assert all(call[1]["target_account_id"] == 7 for call in connection.calls)


def test_collect_plan_keeps_internal_ids_out_of_public_details() -> None:
    summary = {
        "candidate_batch_count": 1,
        "legacy_batch_count": 1,
        "legacy_api_log_count": 1,
        "legacy_failed_request_count": 0,
        "legacy_raw_count": 1,
        "legacy_history_count": 0,
        "legacy_checkpoint_count": 1,
        "missing_batch_count": 0,
        "mock_batch_count": 0,
        "web_job_reference_count": 1,
        "invalid_batch_count": 0,
        "invalid_log_cardinality_count": 0,
        "mixed_child_count": 0,
        "cross_api_checkpoint_count": 0,
        "raw_conflict_count": 0,
        "history_conflict_count": 0,
        "checkpoint_conflict_count": 0,
    }
    connection = QueueConnection(
        [
            FakeResult(values=["private-batch-no"]),
            FakeResult(values=[31]),
            FakeResult(row=summary),
        ]
    )

    plan = service.collect_attribution_plan(connection, 7)

    assert plan.batch_nos == ("private-batch-no",)
    assert plan.baseline_raw_ids == (31,)
    output = json.dumps(plan.details())
    assert "private-batch-no" not in output
    assert "target_account_id" not in output
    assert plan.details()["webJobReferenceCount"] == 1


def test_postflight_checks_captured_batches_and_baseline_rows() -> None:
    connection = QueueConnection(
        [
            FakeResult(scalar=0),
            FakeResult(
                row={
                    "batch_mismatch_count": 0,
                    "child_mismatch_count": 0,
                    "checkpoint_mismatch_count": 0,
                    "invalid_log_cardinality_count": 0,
                }
            ),
            FakeResult(scalar=0),
        ]
    )

    snapshot = service.collect_postflight_snapshot(connection, _ready_plan())

    assert snapshot == _clean_postflight()
    assert connection.calls[1][1]["batch_nos"] == ("legacy-batch-1",)
    assert connection.calls[2][1]["baseline_raw_ids"] == (31,)


@pytest.mark.parametrize(
    ("account_id", "account_code", "expected_param"),
    [
        (7, None, {"target_account_id": 7}),
        (None, "account-a", {"target_account_code": "account-a"}),
    ],
)
def test_target_account_is_resolved_only_from_explicit_selector(
    account_id,
    account_code,
    expected_param,
) -> None:
    connection = QueueConnection([FakeResult(scalar=7)])

    resolved = service.resolve_target_account_id(
        connection,
        target_account_id=account_id,
        target_account_code=account_code,
    )

    assert resolved == 7
    assert connection.calls[0][1] == expected_param


def test_plan_sql_enforces_single_api_batch_and_checkpoint_boundaries() -> None:
    normalized = " ".join(service.PLAN_SUMMARY_SQL.split())

    assert "b.sync_job_id IS NOT NULL" in normalized
    assert "b.finished_at IS NULL" in normalized
    assert "b.total_api_count <> 1" in normalized
    assert "COUNT(l.id) <> 1" in normalized
    assert "api_code <> :api_code" in normalized
    assert "last_sync_batch_no" in normalized
    assert "jijia_account_id <> :legacy_account_id" in normalized
    assert "BINARY b.message = BINARY 'mock sync finished'" in normalized


def test_plan_sql_scopes_web_job_references_to_candidate_batches() -> None:
    normalized = " ".join(service.PLAN_SUMMARY_SQL.split())

    assert (
        "FROM sync_job AS j JOIN candidate_batches AS cb ON cb.sync_batch_no = j.sync_batch_no"
    ) in normalized
    assert ") AS web_job_reference_count" in normalized


def test_nullable_batch_references_are_allowed_but_non_null_references_are_checked() -> None:
    candidate_sql = " ".join(service.CANDIDATE_BATCH_BODY.split())
    summary_sql = " ".join(service.PLAN_SUMMARY_SQL.split())

    assert "failed_request_log" in candidate_sql
    assert "sync_batch_no IS NOT NULL" in candidate_sql
    assert "last_sync_batch_no IS NOT NULL" in candidate_sql
    assert "null_failed_batch_count" not in summary_sql
    assert "null_checkpoint_batch_count" not in summary_sql


def test_baseline_candidates_exclude_existing_legacy_and_target_versions() -> None:
    normalized = " ".join(service.BASELINE_RAW_IDS_SQL.split())

    assert normalized.count("NOT EXISTS") == 2
    assert "h.jijia_account_id = :legacy_account_id" in normalized
    assert "h.jijia_account_id = :target_account_id" in normalized
    assert normalized.count("h.data_hash = r.data_hash") == 2


@pytest.mark.parametrize(
    "argv",
    [
        ["--target-account-id", "7", "--execute"],
        [
            "--target-account-code",
            "account-a",
            "--execute",
            "--confirm-writers-stopped",
        ],
        [
            "--target-account-code",
            "account-a",
            "--execute",
            "--confirm-snapshot-ready",
        ],
    ],
)
def test_cli_does_not_load_engine_before_execute_confirmations(argv) -> None:
    factory_called = False

    def engine_factory():
        nonlocal factory_called
        factory_called = True
        return FakeEngine()

    with pytest.raises(SystemExit) as error:
        legacy_sale_return_attribution.main(argv, engine_factory=engine_factory)

    assert error.value.code == 2
    assert factory_called is False


def test_cli_default_is_dry_run_and_outputs_redacted_json(capsys) -> None:
    engine = FakeEngine()
    received: dict[str, object] = {}

    def runner(_engine, **kwargs):
        received.update(kwargs)
        return AttributionResult(
            status="planned",
            code="ATTRIBUTION_PLAN_READY",
            stage="complete",
            mode="dry-run",
            restore_required=False,
            details={"legacyRawCount": 3},
        )

    exit_code = legacy_sale_return_attribution.main(
        ["--target-account-code", "secret-account-code"],
        engine_factory=lambda: engine,
        runner=runner,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert json.loads(output)["code"] == "ATTRIBUTION_PLAN_READY"
    assert "secret-account-code" not in output
    assert received == {
        "target_account_id": None,
        "target_account_code": "secret-account-code",
        "execute": False,
    }
    assert engine.disposed is True


def test_cli_redacts_runtime_and_dispose_errors(capsys) -> None:
    secret = "mysql://user:secret@example.invalid/database"
    engine = FakeEngine(dispose_error=RuntimeError(secret))

    exit_code = legacy_sale_return_attribution.main(
        ["--target-account-id", "7"],
        engine_factory=lambda: engine,
        runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert json.loads(output)["code"] == "ATTRIBUTION_ENGINE_DISPOSE_FAILED"
    assert "secret" not in output
    assert "mysql://" not in output


def test_default_engine_factory_uses_migration_settings(monkeypatch) -> None:
    settings = object()
    engine = object()
    monkeypatch.setattr(
        legacy_sale_return_attribution,
        "load_migration_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        legacy_sale_return_attribution,
        "create_db_engine",
        lambda received: engine if received is settings else pytest.fail("使用了运行时数据库配置"),
    )

    assert legacy_sale_return_attribution._project_engine() is engine
