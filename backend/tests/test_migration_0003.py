import json
import re
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from backend.app import migration_0003
from backend.app.services import migration_0003_service as service
from backend.app.services.migration_0003_service import (
    MigrationResult,
    PostflightSnapshot,
    TableStats,
    evaluate_postflight,
    load_migration_statements,
    run_migration_0003,
)
from backend.app.services.migration_preflight_service import PreflightResult

FAKE_STATEMENTS = [
    "SET SESSION time_zone = '+00:00'",
    *(f"DDL {ordinal}" for ordinal in range(2, service.EXPECTED_STATEMENT_COUNT + 1)),
]


def _target_table_engines() -> dict[str, str]:
    return {table_name: "innodb" for table_name, _column_name in service.TARGET_COLUMN_SPECS}


class FakeResult:
    def __init__(self, *, scalar=None, row=None) -> None:
        self.scalar = scalar
        self.row = row

    def scalar_one(self):
        return self.scalar

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
        fail_ddl_at: int | None = None,
        release_result=1,
        release_error: Exception | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.lock_result = lock_result
        self.owner_matches = owner_matches
        self.fail_ddl_at = fail_ddl_at
        self.release_result = release_result
        self.release_error = release_error
        self.close_error = close_error
        self.execute_calls: list[str] = []
        self.ddl_calls: list[str] = []
        self.release_calls = 0
        self.closed = False

    def execution_options(self, **_kwargs):
        return self

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
        if "RELEASE_LOCK" in sql:
            self.release_calls += 1
            if self.release_error is not None:
                raise self.release_error
            return FakeResult(scalar=self.release_result)
        raise AssertionError("unexpected query")

    def exec_driver_sql(self, statement: str):
        self.ddl_calls.append(statement)
        if self.fail_ddl_at == len(self.ddl_calls):
            raise RuntimeError("secret ddl failure")

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


def _patch_happy_path(monkeypatch, *, postflight_status: str = "pass") -> None:
    connection_ids: list[int] = []

    def collect_preflight(connection):
        connection_ids.append(id(connection))
        return object()

    def evaluate_preflight(_snapshot, *, require_lock_owned=False):
        assert require_lock_owned is True
        return PreflightResult(status="pass", code="PREFLIGHT_PASSED")

    def collect_baseline(connection):
        connection_ids.append(id(connection))
        return {}

    def collect_postflight(connection):
        connection_ids.append(id(connection))
        return object()

    def evaluate_postflight_result(_baseline, _snapshot):
        return PreflightResult(
            status=postflight_status,
            code=(
                "POSTFLIGHT_PASSED" if postflight_status == "pass" else "POSTFLIGHT_DATA_MISMATCH"
            ),
        )

    monkeypatch.setattr(service, "collect_preflight_snapshot", collect_preflight)
    monkeypatch.setattr(service, "evaluate_preflight", evaluate_preflight)
    monkeypatch.setattr(service, "collect_table_stats", collect_baseline)
    monkeypatch.setattr(service, "collect_postflight_snapshot", collect_postflight)
    monkeypatch.setattr(service, "evaluate_postflight", evaluate_postflight_result)
    monkeypatch.setattr(service, "load_migration_statements", lambda: FAKE_STATEMENTS)
    monkeypatch.setattr(service, "_test_connection_ids", connection_ids, raising=False)


def test_runner_uses_one_owned_connection_for_full_flow(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine()

    result = run_migration_0003(engine)

    assert result == MigrationResult(
        status="success",
        code="MIGRATION_APPLIED",
        stage="complete",
        ordinal=service.EXPECTED_STATEMENT_COUNT,
        restore_required=False,
    )
    assert engine.connect_calls == 1
    assert engine.connection.ddl_calls == FAKE_STATEMENTS
    assert engine.connection.release_calls == 1
    assert engine.connection.closed is True
    assert set(service._test_connection_ids) == {id(engine.connection)}


def test_runner_blocks_when_lock_is_busy(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(lock_result=0))

    result = run_migration_0003(engine)

    assert result.code == "MIGRATION_LOCK_BUSY"
    assert result.status == "blocked"
    assert engine.connection.ddl_calls == []
    assert engine.connection.release_calls == 0


def test_runner_reports_lock_error_without_running_ddl(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(lock_result=None))

    result = run_migration_0003(engine)

    assert result.code == "MIGRATION_LOCK_ERROR"
    assert result.status == "error"
    assert engine.connection.ddl_calls == []
    assert engine.connection.release_calls == 0


def test_runner_blocks_when_lock_owner_is_not_current_connection(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(owner_matches=False))

    result = run_migration_0003(engine)

    assert result.code == "MIGRATION_LOCK_NOT_OWNED"
    assert engine.connection.ddl_calls == []
    assert engine.connection.release_calls == 1


def test_runner_stops_when_apply_preflight_is_blocked(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    monkeypatch.setattr(
        service,
        "evaluate_preflight",
        lambda _snapshot, require_lock_owned=False: PreflightResult(
            status="blocked",
            code="PROJECTED_IDENTITY_NULL",
        ),
    )
    engine = FakeEngine()

    result = run_migration_0003(engine)

    assert result.code == "MIGRATION_PREFLIGHT_BLOCKED"
    assert result.reason_code == "PROJECTED_IDENTITY_NULL"
    assert result.restore_required is False
    assert engine.connection.ddl_calls == []
    assert engine.connection.release_calls == 1


def test_runner_session_setup_failure_does_not_require_restore(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(fail_ddl_at=1))

    result = run_migration_0003(engine)

    assert result.payload() == {
        "status": "error",
        "code": "MIGRATION_SESSION_SETUP_FAILED",
        "stage": "apply",
        "ordinal": 1,
        "restoreRequired": False,
    }
    assert engine.connection.ddl_calls == [FAKE_STATEMENTS[0]]
    assert engine.connection.release_calls == 1


@pytest.mark.parametrize("fail_at", range(2, service.EXPECTED_STATEMENT_COUNT + 1))
def test_runner_stops_at_each_failed_ddl_and_requires_restore(monkeypatch, fail_at) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(fail_ddl_at=fail_at))

    result = run_migration_0003(engine)

    assert result.payload() == {
        "status": "error",
        "code": "MIGRATION_DDL_FAILED",
        "stage": "apply",
        "ordinal": fail_at,
        "restoreRequired": True,
    }
    assert len(engine.connection.ddl_calls) == fail_at
    assert engine.connection.release_calls == 1


def test_runner_requires_restore_when_postflight_is_blocked(monkeypatch) -> None:
    _patch_happy_path(monkeypatch, postflight_status="blocked")
    engine = FakeEngine()

    result = run_migration_0003(engine)

    assert result.code == "MIGRATION_POSTFLIGHT_BLOCKED"
    assert result.status == "error"
    assert result.reason_code == "POSTFLIGHT_DATA_MISMATCH"
    assert result.restore_required is True
    assert result.ordinal == service.EXPECTED_STATEMENT_COUNT
    assert engine.connection.release_calls == 1


@pytest.mark.parametrize(
    "connection",
    [
        FakeConnection(release_result=0),
        FakeConnection(release_error=RuntimeError("secret release error")),
    ],
)
def test_runner_never_reports_success_when_release_fails(monkeypatch, connection) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(connection)

    result = run_migration_0003(engine)

    assert result.status == "error"
    assert result.code == "MIGRATION_LOCK_RELEASE_FAILED"
    assert result.stage == "release_lock"
    assert connection.release_calls == 1


def test_runner_never_reports_success_when_connection_close_fails(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    engine = FakeEngine(FakeConnection(close_error=RuntimeError("secret close error")))

    result = run_migration_0003(engine)

    assert result.status == "error"
    assert result.code == "MIGRATION_CONNECTION_CLOSE_FAILED"


def test_postflight_blocks_schema_and_data_differences() -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    clean = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, clean).code == "POSTFLIGHT_PASSED"
    invalid_schema = replace(clean, column_specs={})
    assert evaluate_postflight(baseline, invalid_schema).code == "POSTFLIGHT_SCHEMA_MISMATCH"
    invalid_data = replace(clean, raw_violation_count=1)
    assert evaluate_postflight(baseline, invalid_data).code == "POSTFLIGHT_DATA_MISMATCH"


@pytest.mark.parametrize("table_name", list(_target_table_engines()))
def test_postflight_blocks_each_non_innodb_target_table(table_name: str) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    table_engines = _target_table_engines()
    table_engines[table_name] = "myisam"
    snapshot = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=table_engines,
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    result = evaluate_postflight(baseline, snapshot)

    assert result.code == "POSTFLIGHT_SCHEMA_MISMATCH"
    assert result.details["invalidTableEngineCount"] == 1


def test_postflight_compares_legacy_time_boundaries() -> None:
    created_at = datetime(2026, 8, 25, 8, 0, 0)
    updated_at = datetime(2026, 8, 26, 8, 0, 0)
    baseline_stats = TableStats(
        1,
        1,
        1,
        1,
        min_created_at=created_at,
        max_created_at=created_at,
        min_updated_at=updated_at,
        max_updated_at=updated_at,
    )
    baseline = {"raw_api_data": baseline_stats}
    clean = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, clean).code == "POSTFLIGHT_PASSED"
    for field_name in (
        "min_created_at",
        "max_created_at",
        "min_updated_at",
        "max_updated_at",
    ):
        changed_stats = replace(
            baseline_stats,
            **{field_name: getattr(baseline_stats, field_name) + timedelta(seconds=1)},
        )
        changed = replace(clean, table_stats={"raw_api_data": changed_stats})

        result = evaluate_postflight(baseline, changed)

        assert result.code == "POSTFLIGHT_DATA_MISMATCH"
        assert result.details["changedTableCount"] == 1


def test_collect_table_stats_keeps_empty_and_non_empty_time_boundaries() -> None:
    created_at = datetime(2026, 8, 25, 8, 0, 0)
    updated_at = datetime(2026, 8, 26, 8, 0, 0)
    rows = [
        {
            "table_name": "raw_api_data",
            "row_count": 1,
            "id_sum": 7,
            "min_id": 7,
            "max_id": 7,
            "min_created_at": created_at,
            "max_created_at": created_at,
            "min_updated_at": updated_at,
            "max_updated_at": updated_at,
        },
        {
            "table_name": "sync_checkpoint",
            "row_count": 0,
            "id_sum": 0,
            "min_id": None,
            "max_id": None,
            "min_created_at": None,
            "max_created_at": None,
            "min_updated_at": None,
            "max_updated_at": None,
        },
    ]

    class StatsConnection:
        def __init__(self) -> None:
            self.sql = ""

        def execute(self, statement):
            self.sql = str(statement)
            return FakeStatsResult(rows)

    class FakeStatsResult:
        def __init__(self, result_rows) -> None:
            self.result_rows = result_rows

        def mappings(self):
            return self.result_rows

    connection = StatsConnection()

    stats = service.collect_table_stats(connection)

    assert stats["raw_api_data"] == TableStats(
        1,
        7,
        7,
        7,
        min_created_at=created_at,
        max_created_at=created_at,
        min_updated_at=updated_at,
        max_updated_at=updated_at,
    )
    assert stats["sync_checkpoint"] == TableStats(0, 0, None, None)
    for alias in (
        "min_created_at",
        "max_created_at",
        "min_updated_at",
        "max_updated_at",
    ):
        assert alias in connection.sql


def test_target_schema_blocks_unexpected_columns_and_indexes() -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    column_specs = dict(service.TARGET_COLUMN_SPECS)
    column_specs[("raw_api_data", "unexpected_column")] = (
        "varchar",
        "YES",
        10,
        None,
    )
    index_specs = dict(service.TARGET_INDEX_SPECS)
    index_specs[("raw_api_data", "idx_unexpected")] = (
        1,
        ("unexpected_column",),
    )
    snapshot = PostflightSnapshot(
        column_specs=column_specs,
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=index_specs,
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    result = evaluate_postflight(baseline, snapshot)

    assert result.code == "POSTFLIGHT_SCHEMA_MISMATCH"
    assert result.details["unexpectedColumnCount"] == 1
    assert result.details["unexpectedIndexCount"] == 1


def test_target_schema_counts_legacy_index_separately_from_unexpected() -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    index_specs = dict(service.TARGET_INDEX_SPECS)
    legacy_index = next(iter(service.LEGACY_INDEXES))
    index_specs[legacy_index] = (1, ("legacy_column",))
    snapshot = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=index_specs,
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    result = evaluate_postflight(baseline, snapshot)

    assert result.code == "POSTFLIGHT_SCHEMA_MISMATCH"
    assert result.details["legacyIndexCount"] == 1
    assert result.details["unexpectedIndexCount"] == 0


@pytest.mark.parametrize(
    "column_key",
    [
        ("sync_batch", "sync_batch_no"),
        ("sync_api_log", "sync_batch_no"),
        ("raw_api_data", "raw_json"),
        ("sync_checkpoint", "last_sync_batch_no"),
        ("failed_request_log", "request_method"),
    ],
)
def test_postflight_blocks_each_missing_runtime_column(column_key) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    column_specs = dict(service.TARGET_COLUMN_SPECS)
    column_specs.pop(column_key)
    snapshot = PostflightSnapshot(
        column_specs=column_specs,
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, snapshot).code == "POSTFLIGHT_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    ("column_key", "invalid_spec"),
    [
        (("sync_batch", "sync_batch_no"), ("varchar", "NO", 32, None)),
        (("raw_api_data", "source_primary_key"), ("varchar", "YES", 100, None)),
        (("sync_api_log", "sync_batch_no"), ("varchar", "YES", 64, None)),
        (("failed_request_log", "request_method"), ("varchar", "YES", 20, "post")),
    ],
)
def test_postflight_blocks_invalid_runtime_length_or_nullable(
    column_key,
    invalid_spec,
) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    column_specs = dict(service.TARGET_COLUMN_SPECS)
    column_specs[column_key] = invalid_spec
    snapshot = PostflightSnapshot(
        column_specs=column_specs,
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, snapshot).code == "POSTFLIGHT_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "column_key",
    [key for key, spec in service.TARGET_COLUMN_SPECS.items() if spec[0] == "bigint unsigned"],
)
def test_postflight_blocks_each_signed_bigint(column_key) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    column_specs = dict(service.TARGET_COLUMN_SPECS)
    _data_type, is_nullable, maximum_length, default = column_specs[column_key]
    column_specs[column_key] = ("bigint", is_nullable, maximum_length, default)
    snapshot = PostflightSnapshot(
        column_specs=column_specs,
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, snapshot).code == "POSTFLIGHT_SCHEMA_MISMATCH"


def test_migration_sql_has_fixed_order_and_no_legacy_seed() -> None:
    statements = load_migration_statements()
    normalized = "\n".join(statements).upper()
    ordered_statements = [
        re.sub(
            r"\s+",
            " ",
            re.sub(r"^\s*--[^\n]*(?:\n|$)", "", statement, flags=re.MULTILINE),
        )
        .strip()
        .upper()
        for statement in statements
    ]
    ordered_prefixes = [
        "SET SESSION TIME_ZONE",
        "ALTER TABLE SYNC_BATCH ADD COLUMN",
        "ALTER TABLE SYNC_API_LOG ADD COLUMN",
        "ALTER TABLE FAILED_REQUEST_LOG ADD COLUMN",
        "ALTER TABLE RAW_API_DATA ADD COLUMN",
        "ALTER TABLE SYNC_CHECKPOINT ADD COLUMN",
        "UPDATE SYNC_BATCH SET",
        "UPDATE SYNC_API_LOG SET",
        "UPDATE FAILED_REQUEST_LOG SET",
        "UPDATE RAW_API_DATA SET",
        "UPDATE SYNC_CHECKPOINT SET",
        "ALTER TABLE SYNC_CHECKPOINT ADD COLUMN CHECKPOINT_VALUE_JSON",
        "UPDATE SYNC_CHECKPOINT SET",
        "ALTER TABLE SYNC_CHECKPOINT DROP COLUMN CHECKPOINT_VALUE",
        "ALTER TABLE RAW_API_DATA DROP INDEX",
        "ALTER TABLE SYNC_BATCH DROP INDEX",
        "ALTER TABLE SYNC_API_LOG DROP INDEX",
        "ALTER TABLE FAILED_REQUEST_LOG DROP INDEX",
        "ALTER TABLE SYNC_CHECKPOINT DROP INDEX",
        "CREATE TABLE IF NOT EXISTS RAW_API_DATA_HISTORY",
    ]

    assert len(statements) == service.EXPECTED_STATEMENT_COUNT
    assert all(
        statement.startswith(prefix)
        for statement, prefix in zip(ordered_statements, ordered_prefixes, strict=True)
    )
    assert "INSERT INTO RAW_API_DATA_HISTORY" not in normalized
    assert "UPDATE JIJIA_ACCOUNT" not in normalized
    updates = [statement for statement in ordered_statements if statement.startswith("UPDATE ")]
    assert len(updates) == 6
    assert all("UPDATED_AT = UPDATED_AT" in statement for statement in updates)


def test_postflight_contract_covers_full_history_table_shape() -> None:
    history_columns = {
        column_name
        for table_name, column_name in service.TARGET_COLUMN_SPECS
        if table_name == "raw_api_data_history"
    }
    history_indexes = {
        index_name
        for table_name, index_name in service.TARGET_INDEX_SPECS
        if table_name == "raw_api_data_history"
    }

    assert history_columns == {
        "id",
        "jijia_account_id",
        "api_code",
        "record_identity",
        "source_primary_key",
        "data_hash",
        "raw_json",
        "data_date",
        "sync_batch_no",
        "observed_at",
        "created_at",
        "updated_at",
    }
    assert history_indexes == {
        "PRIMARY",
        "uk_raw_history_version",
        "idx_raw_history_account_record",
        "idx_raw_history_date",
        "idx_raw_history_batch",
    }
    history_extras = {
        key: fragment
        for key, fragment in service.TARGET_COLUMN_EXTRA_FRAGMENTS.items()
        if key[0] == "raw_api_data_history"
    }
    assert history_extras == {
        ("raw_api_data_history", "id"): "auto_increment",
        ("raw_api_data_history", "updated_at"): "on update current_timestamp",
    }


def test_postflight_contract_covers_existing_core_runtime_extras() -> None:
    for table_name in (
        "sync_batch",
        "sync_api_log",
        "failed_request_log",
        "raw_api_data",
        "sync_checkpoint",
    ):
        assert service.TARGET_COLUMN_EXTRA_FRAGMENTS[(table_name, "id")] == "auto_increment"
        assert (
            service.TARGET_COLUMN_EXTRA_FRAGMENTS[(table_name, "updated_at")]
            == "on update current_timestamp"
        )


@pytest.mark.parametrize(
    "index_key",
    list(service.TARGET_INDEX_SPECS),
)
def test_postflight_blocks_each_missing_required_index(index_key) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    index_specs = dict(service.TARGET_INDEX_SPECS)
    index_specs.pop(index_key)
    snapshot = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
        index_specs=index_specs,
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, snapshot).code == "POSTFLIGHT_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "extra_key",
    list(service.TARGET_COLUMN_EXTRA_FRAGMENTS),
)
def test_postflight_blocks_each_missing_history_extra(extra_key) -> None:
    baseline = {"raw_api_data": TableStats(1, 1, 1, 1)}
    column_extras = dict(service.TARGET_COLUMN_EXTRA_FRAGMENTS)
    column_extras.pop(extra_key)
    snapshot = PostflightSnapshot(
        column_specs=dict(service.TARGET_COLUMN_SPECS),
        column_extras=column_extras,
        index_specs=dict(service.TARGET_INDEX_SPECS),
        table_engines=_target_table_engines(),
        table_stats=dict(baseline),
        raw_violation_count=0,
        legacy_scope_violation_count=0,
        history_row_count=0,
    )

    assert evaluate_postflight(baseline, snapshot).code == "POSTFLIGHT_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--confirm-isolated-replica"],
        ["--confirm-snapshot-ready"],
    ],
)
def test_cli_does_not_load_engine_before_both_confirmations(argv) -> None:
    factory_called = False

    def engine_factory():
        nonlocal factory_called
        factory_called = True
        return FakeEngine()

    with pytest.raises(SystemExit) as error:
        migration_0003.main(argv, engine_factory=engine_factory)

    assert error.value.code == 2
    assert factory_called is False


def test_cli_outputs_only_stable_json_and_disposes_engine(capsys) -> None:
    engine = FakeEngine()
    result = MigrationResult(
        status="error",
        code="MIGRATION_DDL_FAILED",
        stage="apply",
        ordinal=4,
        restore_required=True,
    )

    exit_code = migration_0003.main(
        ["--confirm-isolated-replica", "--confirm-snapshot-ready"],
        engine_factory=lambda: engine,
        runner=lambda _engine: result,
    )

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out) == result.payload()
    assert engine.disposed is True


def test_cli_redacts_runner_and_dispose_errors(capsys) -> None:
    secret = "mysql://user:secret@example.invalid/database"
    engine = FakeEngine(dispose_error=RuntimeError(secret))

    exit_code = migration_0003.main(
        ["--confirm-isolated-replica", "--confirm-snapshot-ready"],
        engine_factory=lambda: engine,
        runner=lambda _engine: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 1
    assert payload["code"] == "MIGRATION_ENGINE_DISPOSE_FAILED"
    assert "secret" not in output
    assert "mysql://" not in output


def test_default_engine_factory_uses_migration_database_settings(monkeypatch) -> None:
    settings = object()
    engine = object()
    monkeypatch.setattr(migration_0003, "load_migration_settings", lambda: settings)
    monkeypatch.setattr(
        migration_0003,
        "create_db_engine",
        lambda received: engine if received is settings else pytest.fail("使用了运行时数据库配置"),
    )

    assert migration_0003._project_engine() is engine
