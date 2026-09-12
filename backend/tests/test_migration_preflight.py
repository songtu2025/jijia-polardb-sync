import json

import pytest

from backend.app import migration_preflight
from backend.app.services.migration_preflight_service import (
    REQUIRED_LEGACY_COLUMN_DEFAULTS,
    REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS,
    REQUIRED_LEGACY_COLUMN_SPECS,
    REQUIRED_LEGACY_COLUMNS,
    REQUIRED_LEGACY_INDEX_SPECS,
    PreflightResult,
    PreflightSnapshot,
    collect_preflight_snapshot,
    evaluate_preflight,
)


def valid_snapshot() -> PreflightSnapshot:
    return PreflightSnapshot(
        columns={table: set(columns) for table, columns in REQUIRED_LEGACY_COLUMNS.items()},
        column_specs=dict(REQUIRED_LEGACY_COLUMN_SPECS),
        column_defaults=dict(REQUIRED_LEGACY_COLUMN_DEFAULTS),
        column_extras=dict(REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS),
        index_specs=dict(REQUIRED_LEGACY_INDEX_SPECS),
        target_tables=set(),
        table_engines={table: "innodb" for table in REQUIRED_LEGACY_COLUMNS},
        duplicate_group_count=0,
        duplicate_row_count=0,
        projected_identity_null_count=0,
        checkpoint_duplicate_group_count=0,
        session_time_zone="+00:00",
        sync_lock_free=1,
        connection_id=10,
        sync_lock_owner_id=None,
    )


def test_evaluate_preflight_accepts_clean_legacy_replica() -> None:
    result = evaluate_preflight(valid_snapshot())

    assert result == PreflightResult(status="pass", code="PREFLIGHT_PASSED")


def test_evaluate_preflight_accepts_lock_owned_by_apply_connection() -> None:
    snapshot = valid_snapshot()
    snapshot.sync_lock_free = 0
    snapshot.sync_lock_owner_id = snapshot.connection_id

    result = evaluate_preflight(snapshot, require_lock_owned=True)

    assert result == PreflightResult(status="pass", code="PREFLIGHT_PASSED")


def test_evaluate_preflight_blocks_apply_connection_without_lock() -> None:
    snapshot = valid_snapshot()

    result = evaluate_preflight(snapshot, require_lock_owned=True)

    assert result.status == "blocked"
    assert result.code == "SYNC_LOCK_NOT_OWNED"


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda snapshot: snapshot.columns["raw_api_data"].add("jijia_account_id"),
            "PARTIAL_MIGRATION_DETECTED",
        ),
        (
            lambda snapshot: snapshot.index_specs.pop(("raw_api_data", "uk_raw_api_data_hash")),
            "LEGACY_SCHEMA_MISMATCH",
        ),
        (
            lambda snapshot: snapshot.column_specs.__setitem__(
                ("raw_api_data", "data_hash"),
                ("char", "NO", 32),
            ),
            "LEGACY_SCHEMA_MISMATCH",
        ),
        (
            lambda snapshot: setattr(snapshot, "duplicate_group_count", 2),
            "PROJECTED_IDENTITY_DUPLICATES",
        ),
        (
            lambda snapshot: setattr(snapshot, "session_time_zone", "SYSTEM"),
            "SESSION_NOT_UTC",
        ),
        (
            lambda snapshot: setattr(snapshot, "sync_lock_free", 0),
            "SYNC_WRITER_ACTIVE",
        ),
        (
            lambda snapshot: setattr(snapshot, "projected_identity_null_count", 1),
            "PROJECTED_IDENTITY_NULL",
        ),
        (
            lambda snapshot: setattr(
                snapshot,
                "checkpoint_duplicate_group_count",
                1,
            ),
            "CHECKPOINT_SCOPE_DUPLICATES",
        ),
    ],
)
def test_evaluate_preflight_blocks_unsafe_replica_state(
    mutate,
    expected_code: str,
) -> None:
    snapshot = valid_snapshot()
    mutate(snapshot)

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == expected_code


@pytest.mark.parametrize(
    "mutation",
    [
        "unexpected_column",
        "unexpected_index",
    ],
)
def test_preflight_blocks_schema_drift_before_ddl(mutation: str) -> None:
    snapshot = valid_snapshot()
    if mutation == "unexpected_column":
        snapshot.columns["raw_api_data"].add("legacy_extra")
        snapshot.column_specs[("raw_api_data", "legacy_extra")] = (
            "varchar",
            "YES",
            32,
        )
        snapshot.column_defaults[("raw_api_data", "legacy_extra")] = None
    else:
        snapshot.index_specs[("raw_api_data", "idx_legacy_extra")] = (
            1,
            ("api_code",),
        )

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


def test_preflight_blocks_legacy_default_drift_before_ddl() -> None:
    snapshot = valid_snapshot()
    snapshot.column_defaults[("sync_batch", "status")] = "queued"

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


@pytest.mark.parametrize("table_name", list(REQUIRED_LEGACY_COLUMNS))
def test_preflight_blocks_each_non_innodb_legacy_table(table_name: str) -> None:
    snapshot = valid_snapshot()
    snapshot.table_engines[table_name] = "myisam"

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"
    assert result.details["invalidTableEngineCount"] == 1


@pytest.mark.parametrize("column_key", list(REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS))
def test_preflight_blocks_missing_runtime_extra_before_ddl(
    column_key: tuple[str, str],
) -> None:
    snapshot = valid_snapshot()
    snapshot.column_extras[column_key] = ""

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    ("table_name", "column_name"),
    [
        ("sync_batch", "sync_batch_no"),
        ("sync_api_log", "sync_batch_no"),
        ("raw_api_data", "raw_json"),
        ("sync_checkpoint", "last_sync_batch_no"),
        ("failed_request_log", "request_method"),
    ],
)
def test_preflight_blocks_each_missing_runtime_column(
    table_name: str,
    column_name: str,
) -> None:
    snapshot = valid_snapshot()
    snapshot.columns[table_name].remove(column_name)

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    ("column_key", "invalid_spec"),
    [
        (("sync_batch", "sync_batch_no"), ("varchar", "NO", 32)),
        (("raw_api_data", "source_primary_key"), ("varchar", "YES", 100)),
        (("sync_api_log", "sync_batch_no"), ("varchar", "YES", 64)),
        (("failed_request_log", "request_method"), ("varchar", "YES", 20)),
    ],
)
def test_preflight_blocks_invalid_runtime_length_or_nullable(
    column_key: tuple[str, str],
    invalid_spec: tuple[str, str, int | None],
) -> None:
    snapshot = valid_snapshot()
    snapshot.column_specs[column_key] = invalid_spec

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "column_key",
    [key for key, spec in REQUIRED_LEGACY_COLUMN_SPECS.items() if spec[0] == "bigint unsigned"],
)
def test_preflight_blocks_each_signed_bigint(column_key: tuple[str, str]) -> None:
    snapshot = valid_snapshot()
    _data_type, is_nullable, maximum_length = snapshot.column_specs[column_key]
    snapshot.column_specs[column_key] = ("bigint", is_nullable, maximum_length)

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


@pytest.mark.parametrize("index_key", list(REQUIRED_LEGACY_INDEX_SPECS))
def test_preflight_blocks_each_missing_legacy_index(
    index_key: tuple[str, str],
) -> None:
    snapshot = valid_snapshot()
    snapshot.index_specs.pop(index_key)

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"


class FakeEngine:
    def __init__(self, dispose_error: Exception | None = None) -> None:
        self.disposed = False
        self.dispose_error = dispose_error

    def dispose(self) -> None:
        self.disposed = True
        if self.dispose_error is not None:
            raise self.dispose_error


class FakeResult:
    def __init__(self, rows=None, scalar=None) -> None:
        self.rows = rows or []
        self.scalar = scalar
        self._iterated = False

    def mappings(self):
        return self

    def __iter__(self):
        if self._iterated:
            raise AssertionError("MappingResult 不得被二次迭代")
        self._iterated = True
        return iter(self.rows)

    def one(self):
        return self.rows[0]

    def scalar_one(self):
        return self.scalar


class FakeMysqlConnection:
    class Dialect:
        name = "mysql"

    dialect = Dialect()

    def __init__(self, *, myisam_table: str | None = None) -> None:
        self.calls = []
        self.myisam_table = myisam_table

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if "information_schema.columns" in sql:
            rows = []
            for table, columns in REQUIRED_LEGACY_COLUMNS.items():
                for column in columns:
                    normalized_type, is_nullable, maximum_length = REQUIRED_LEGACY_COLUMN_SPECS[
                        (table, column)
                    ]
                    column_key = (table, column)
                    rows.append(
                        {
                            "table_name": table,
                            "column_name": column,
                            "data_type": normalized_type.split()[0],
                            "column_type": normalized_type,
                            "is_nullable": is_nullable,
                            "character_maximum_length": maximum_length,
                            "column_default": REQUIRED_LEGACY_COLUMN_DEFAULTS[column_key],
                            "extra": REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS.get(column_key, ""),
                        }
                    )
            return FakeResult(rows)
        if "information_schema.statistics" in sql:
            rows = []
            for (table, index), (non_unique, columns) in REQUIRED_LEGACY_INDEX_SPECS.items():
                rows.extend(
                    {
                        "table_name": table,
                        "index_name": index,
                        "non_unique": non_unique,
                        "seq_in_index": position,
                        "column_name": column,
                    }
                    for position, column in enumerate(columns, start=1)
                )
            return FakeResult(rows)
        if "information_schema.tables" in sql:
            return FakeResult(
                [
                    {
                        "table_name": table,
                        "engine": ("MyISAM" if table == self.myisam_table else "InnoDB"),
                    }
                    for table in REQUIRED_LEGACY_COLUMNS
                ]
            )
        if "IS_FREE_LOCK" in sql:
            return FakeResult(
                [
                    {
                        "session_time_zone": "+00:00",
                        "sync_lock_free": 1,
                        "connection_id": 10,
                        "sync_lock_owner_id": None,
                    }
                ]
            )
        if "projected_identity_null_count" in sql:
            return FakeResult(scalar=0)
        if "checkpoint_duplicate_group_count" in sql:
            return FakeResult(scalar=0)
        if "AS duplicate_group_count" in sql:
            return FakeResult([{"duplicate_group_count": 0, "duplicate_row_count": 0}])
        raise AssertionError(f"unexpected SQL: {sql}")


def test_collect_preflight_snapshot_executes_read_only_mysql_checks() -> None:
    connection = FakeMysqlConnection()

    snapshot = collect_preflight_snapshot(connection)
    result = evaluate_preflight(snapshot)

    assert result == PreflightResult(status="pass", code="PREFLIGHT_PASSED")
    assert all(
        snapshot.column_specs[key] == expected
        for key, expected in REQUIRED_LEGACY_COLUMN_SPECS.items()
    )
    assert snapshot.column_defaults == REQUIRED_LEGACY_COLUMN_DEFAULTS
    assert all(
        fragment in snapshot.column_extras[key]
        for key, fragment in REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS.items()
    )
    assert snapshot.index_specs == REQUIRED_LEGACY_INDEX_SPECS
    assert snapshot.table_engines == {table: "innodb" for table in REQUIRED_LEGACY_COLUMNS}
    assert snapshot.projected_identity_null_count == 0
    assert snapshot.checkpoint_duplicate_group_count == 0
    column_query = next(sql for sql, _params in connection.calls if "columns" in sql)
    assert "TABLE_NAME AS table_name" in column_query
    assert "COLUMN_NAME AS column_name" in column_query
    assert "COLUMN_TYPE AS column_type" in column_query
    index_query = next(sql for sql, _params in connection.calls if "statistics" in sql)
    assert "INDEX_NAME AS index_name" in index_query
    table_query = next(sql for sql, _params in connection.calls if "tables" in sql)
    assert "ENGINE AS engine" in table_query
    assert len(connection.calls) == 7
    assert all(
        not any(
            keyword in sql.upper()
            for keyword in ("ALTER TABLE", "INSERT INTO", "UPDATE ", "DELETE FROM")
        )
        for sql, _params in connection.calls
    )


@pytest.mark.parametrize("table_name", list(REQUIRED_LEGACY_COLUMNS))
def test_collect_preflight_snapshot_blocks_each_non_innodb_table(
    table_name: str,
) -> None:
    snapshot = collect_preflight_snapshot(FakeMysqlConnection(myisam_table=table_name))

    result = evaluate_preflight(snapshot)

    assert result.status == "blocked"
    assert result.code == "LEGACY_SCHEMA_MISMATCH"
    assert result.details == {
        "missingColumnCount": 0,
        "invalidColumnSpecCount": 0,
        "invalidColumnDefaultCount": 0,
        "invalidColumnExtraCount": 0,
        "invalidIndexSpecCount": 0,
        "invalidTableEngineCount": 1,
        "unexpectedColumnCount": 0,
        "unexpectedIndexCount": 0,
    }


def test_main_returns_zero_for_passed_preflight(capsys) -> None:
    exit_code = migration_preflight.main(
        ["--confirm-isolated-replica"],
        engine_factory=FakeEngine,
        runner=lambda _engine: PreflightResult(
            status="pass",
            code="PREFLIGHT_PASSED",
        ),
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "pass",
        "code": "PREFLIGHT_PASSED",
    }


def test_main_outputs_json_and_stable_exit_codes(capsys) -> None:
    engine = FakeEngine()
    exit_code = migration_preflight.main(
        ["--confirm-isolated-replica"],
        engine_factory=lambda: engine,
        runner=lambda _engine: PreflightResult(
            status="blocked",
            code="LEGACY_SCHEMA_MISMATCH",
            details={"missingColumnCount": 1},
        ),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload == {
        "status": "blocked",
        "code": "LEGACY_SCHEMA_MISMATCH",
        "details": {"missingColumnCount": 1},
    }
    assert engine.disposed is True


def test_main_redacts_runtime_error(capsys) -> None:
    secret = "mysql://user:secret@example.invalid/database"

    def fail_runner(_engine):
        raise RuntimeError(secret)

    exit_code = migration_preflight.main(
        ["--confirm-isolated-replica"],
        engine_factory=FakeEngine,
        runner=fail_runner,
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 1
    assert payload == {
        "status": "error",
        "code": "PREFLIGHT_RUNTIME_ERROR",
        "errorType": "RuntimeError",
    }
    assert "secret" not in output
    assert "mysql://" not in output


def test_main_redacts_dispose_error_and_only_outputs_error_json(capsys) -> None:
    secret = "mysql://user:secret@example.invalid/database"
    engine = FakeEngine(dispose_error=RuntimeError(secret))

    exit_code = migration_preflight.main(
        ["--confirm-isolated-replica"],
        engine_factory=lambda: engine,
        runner=lambda _engine: PreflightResult(
            status="pass",
            code="PREFLIGHT_PASSED",
        ),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert json.loads(captured.out) == {
        "status": "error",
        "code": "PREFLIGHT_RUNTIME_ERROR",
        "errorType": "RuntimeError",
    }
    assert captured.err == ""
    assert "secret" not in captured.out
    assert "mysql://" not in captured.out


def test_main_requires_explicit_replica_confirmation() -> None:
    factory_called = False

    def engine_factory():
        nonlocal factory_called
        factory_called = True
        return FakeEngine()

    with pytest.raises(SystemExit) as error:
        migration_preflight.main([], engine_factory=engine_factory)

    assert error.value.code == 2
    assert factory_called is False


def test_default_engine_factory_uses_migration_database_settings(monkeypatch) -> None:
    settings = object()
    engine = object()
    monkeypatch.setattr(migration_preflight, "load_migration_settings", lambda: settings)
    monkeypatch.setattr(
        migration_preflight,
        "create_db_engine",
        lambda received: engine if received is settings else pytest.fail("使用了运行时数据库配置"),
    )

    assert migration_preflight._project_engine() is engine
