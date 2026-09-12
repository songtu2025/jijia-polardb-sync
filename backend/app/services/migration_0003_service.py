from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.sync_lock import SYNC_TASK_LOCK_NAME
from backend.app.services._migration_schema import (
    bounded_character_length,
    build_index_specs,
    normalize_column_data_type,
    normalize_column_default,
    read_information_schema_columns,
    read_information_schema_indexes,
    read_information_schema_tables,
)
from backend.app.services.migration_preflight_service import (
    PreflightResult,
    collect_preflight_snapshot,
    evaluate_preflight,
)
from backend.app.services.migration_sql_service import load_sql_statements

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_SQL_PATH = PROJECT_ROOT / "sql" / "migrations" / "0003_sync_scope_and_history.sql"
EXPECTED_STATEMENT_COUNT = 20
LEGACY_TABLES = (
    "sync_batch",
    "sync_api_log",
    "failed_request_log",
    "raw_api_data",
    "sync_checkpoint",
)

TARGET_COLUMN_SPECS = {
    ("sync_batch", "id"): ("bigint unsigned", "NO", None, None),
    ("sync_batch", "sync_batch_no"): ("varchar", "NO", 64, None),
    ("sync_batch", "jijia_account_id"): ("int", "NO", None, "0"),
    ("sync_batch", "sync_job_id"): ("int", "YES", None, None),
    ("sync_batch", "status"): ("varchar", "NO", 30, "running"),
    ("sync_batch", "started_at"): ("datetime", "NO", None, None),
    ("sync_batch", "finished_at"): ("datetime", "YES", None, None),
    ("sync_batch", "total_api_count"): ("int", "NO", None, "0"),
    ("sync_batch", "success_api_count"): ("int", "NO", None, "0"),
    ("sync_batch", "failed_api_count"): ("int", "NO", None, "0"),
    ("sync_batch", "message"): ("varchar", "YES", 1000, None),
    ("sync_batch", "created_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("sync_batch", "updated_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("sync_api_log", "id"): ("bigint unsigned", "NO", None, None),
    ("sync_api_log", "sync_batch_no"): ("varchar", "NO", 64, None),
    ("sync_api_log", "jijia_account_id"): ("int", "NO", None, "0"),
    ("sync_api_log", "api_code"): ("varchar", "NO", 100, None),
    ("sync_api_log", "status"): ("varchar", "NO", 30, None),
    ("sync_api_log", "request_count"): ("int", "NO", None, "0"),
    ("sync_api_log", "success_count"): ("int", "NO", None, "0"),
    ("sync_api_log", "failed_count"): ("int", "NO", None, "0"),
    ("sync_api_log", "started_at"): ("datetime", "NO", None, None),
    ("sync_api_log", "finished_at"): ("datetime", "YES", None, None),
    ("sync_api_log", "error_message"): ("text", "YES", None, None),
    ("sync_api_log", "created_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("sync_api_log", "updated_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("failed_request_log", "id"): ("bigint unsigned", "NO", None, None),
    ("failed_request_log", "sync_batch_no"): ("varchar", "YES", 64, None),
    ("failed_request_log", "jijia_account_id"): ("int", "NO", None, "0"),
    ("failed_request_log", "api_code"): ("varchar", "NO", 100, None),
    ("failed_request_log", "request_url"): ("varchar", "YES", 1000, None),
    ("failed_request_log", "request_method"): ("varchar", "NO", 20, "post"),
    ("failed_request_log", "request_params"): ("json", "YES", None, None),
    ("failed_request_log", "response_status_code"): ("int", "YES", None, None),
    ("failed_request_log", "response_body"): ("mediumtext", "YES", None, None),
    ("failed_request_log", "error_message"): ("text", "YES", None, None),
    ("failed_request_log", "retry_count"): ("int", "NO", None, "0"),
    ("failed_request_log", "created_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
    ("failed_request_log", "updated_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
    ("raw_api_data", "id"): ("bigint unsigned", "NO", None, None),
    ("raw_api_data", "jijia_account_id"): ("int", "NO", None, "0"),
    ("raw_api_data", "api_code"): ("varchar", "NO", 100, None),
    ("raw_api_data", "source_primary_key"): ("varchar", "YES", 255, None),
    ("raw_api_data", "record_identity"): ("char", "NO", 64, None),
    ("raw_api_data", "data_hash"): ("char", "NO", 64, None),
    ("raw_api_data", "raw_json"): ("json", "NO", None, None),
    ("raw_api_data", "data_date"): ("date", "YES", None, None),
    ("raw_api_data", "sync_batch_no"): ("varchar", "NO", 64, None),
    ("raw_api_data", "first_observed_at"): (
        "datetime",
        "NO",
        None,
        "current_timestamp",
    ),
    ("raw_api_data", "last_observed_at"): (
        "datetime",
        "NO",
        None,
        "current_timestamp",
    ),
    ("raw_api_data", "observation_count"): (
        "bigint unsigned",
        "NO",
        None,
        "1",
    ),
    ("raw_api_data", "created_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("raw_api_data", "updated_at"): ("timestamp", "NO", None, "current_timestamp"),
    ("sync_checkpoint", "id"): ("bigint unsigned", "NO", None, None),
    ("sync_checkpoint", "jijia_account_id"): ("int", "NO", None, "0"),
    ("sync_checkpoint", "api_code"): ("varchar", "NO", 100, None),
    ("sync_checkpoint", "checkpoint_kind"): (
        "varchar",
        "NO",
        32,
        "date_window",
    ),
    ("sync_checkpoint", "checkpoint_value"): ("json", "YES", None, None),
    ("sync_checkpoint", "checkpoint_time"): ("datetime", "YES", None, None),
    ("sync_checkpoint", "last_sync_batch_no"): ("varchar", "YES", 64, None),
    ("sync_checkpoint", "created_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
    ("sync_checkpoint", "updated_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
    ("raw_api_data_history", "id"): (
        "bigint unsigned",
        "NO",
        None,
        None,
    ),
    ("raw_api_data_history", "jijia_account_id"): ("int", "NO", None, "0"),
    ("raw_api_data_history", "api_code"): ("varchar", "NO", 100, None),
    ("raw_api_data_history", "record_identity"): ("char", "NO", 64, None),
    ("raw_api_data_history", "source_primary_key"): (
        "varchar",
        "YES",
        255,
        None,
    ),
    ("raw_api_data_history", "data_hash"): ("char", "NO", 64, None),
    ("raw_api_data_history", "raw_json"): ("json", "NO", None, None),
    ("raw_api_data_history", "data_date"): ("date", "YES", None, None),
    ("raw_api_data_history", "sync_batch_no"): (
        "varchar",
        "NO",
        64,
        None,
    ),
    ("raw_api_data_history", "observed_at"): ("datetime", "NO", None, None),
    ("raw_api_data_history", "created_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
    ("raw_api_data_history", "updated_at"): (
        "timestamp",
        "NO",
        None,
        "current_timestamp",
    ),
}
TARGET_TABLE_ENGINES = dict.fromkeys(
    (
        "sync_batch",
        "sync_api_log",
        "failed_request_log",
        "raw_api_data",
        "sync_checkpoint",
        "raw_api_data_history",
    ),
    "innodb",
)

TARGET_COLUMN_EXTRA_FRAGMENTS = {
    **{
        (table_name, column_name): fragment
        for table_name in (
            "sync_batch",
            "sync_api_log",
            "failed_request_log",
            "raw_api_data",
            "sync_checkpoint",
        )
        for column_name, fragment in (
            ("id", "auto_increment"),
            ("updated_at", "on update current_timestamp"),
        )
    },
    ("raw_api_data_history", "id"): "auto_increment",
    ("raw_api_data_history", "updated_at"): "on update current_timestamp",
}

TARGET_INDEX_SPECS = {
    ("sync_batch", "PRIMARY"): (0, ("id",)),
    ("sync_batch", "uk_sync_batch_no"): (0, ("sync_batch_no",)),
    ("sync_batch", "uk_sync_batch_job"): (0, ("sync_job_id",)),
    ("sync_batch", "idx_sync_batch_account_status"): (
        1,
        ("jijia_account_id", "status", "started_at"),
    ),
    ("sync_api_log", "idx_sync_api_log_account_api_status"): (
        1,
        ("jijia_account_id", "api_code", "status"),
    ),
    ("sync_api_log", "PRIMARY"): (0, ("id",)),
    ("sync_api_log", "idx_sync_api_log_batch"): (1, ("sync_batch_no",)),
    ("failed_request_log", "PRIMARY"): (0, ("id",)),
    ("failed_request_log", "idx_failed_request_account_api_created_at"): (
        1,
        ("jijia_account_id", "api_code", "created_at"),
    ),
    ("failed_request_log", "idx_failed_request_batch"): (1, ("sync_batch_no",)),
    ("raw_api_data", "PRIMARY"): (0, ("id",)),
    ("raw_api_data", "uk_raw_account_api_identity"): (
        0,
        ("jijia_account_id", "api_code", "record_identity"),
    ),
    ("raw_api_data", "idx_raw_account_api_hash"): (
        1,
        ("jijia_account_id", "api_code", "data_hash"),
    ),
    ("raw_api_data", "idx_raw_account_api_source_pk"): (
        1,
        ("jijia_account_id", "api_code", "source_primary_key"),
    ),
    ("raw_api_data", "idx_raw_api_data_date"): (
        1,
        ("jijia_account_id", "api_code", "data_date"),
    ),
    ("raw_api_data", "idx_raw_api_batch"): (1, ("sync_batch_no",)),
    ("sync_checkpoint", "PRIMARY"): (0, ("id",)),
    ("sync_checkpoint", "uk_sync_checkpoint_scope"): (
        0,
        ("jijia_account_id", "api_code", "checkpoint_kind"),
    ),
    ("raw_api_data_history", "uk_raw_history_version"): (
        0,
        ("jijia_account_id", "api_code", "record_identity", "data_hash"),
    ),
    ("raw_api_data_history", "PRIMARY"): (0, ("id",)),
    ("raw_api_data_history", "idx_raw_history_account_record"): (
        1,
        ("jijia_account_id", "api_code", "record_identity", "observed_at"),
    ),
    ("raw_api_data_history", "idx_raw_history_date"): (
        1,
        ("jijia_account_id", "api_code", "data_date"),
    ),
    ("raw_api_data_history", "idx_raw_history_batch"): (1, ("sync_batch_no",)),
}

POST_0003_INDEX_SPECS = {
    ("raw_api_data", "idx_raw_created"): (1, ("created_at", "id")),
    ("raw_api_data", "idx_raw_account_api_created"): (
        1,
        ("jijia_account_id", "api_code", "created_at", "id"),
    ),
    ("raw_api_data", "idx_raw_last_observed"): (1, ("last_observed_at",)),
    ("raw_api_data", "idx_raw_account_last_observed"): (
        1,
        ("jijia_account_id", "last_observed_at"),
    ),
}
CURRENT_INDEX_SPECS = {**TARGET_INDEX_SPECS, **POST_0003_INDEX_SPECS}

LEGACY_INDEXES = {
    ("sync_batch", "idx_sync_batch_status_started_at"),
    ("sync_api_log", "idx_sync_api_log_api_status"),
    ("failed_request_log", "idx_failed_request_api_created_at"),
    ("raw_api_data", "uk_raw_api_primary_key"),
    ("raw_api_data", "uk_raw_api_data_hash"),
    ("sync_checkpoint", "uk_sync_checkpoint_api_code"),
}


@dataclass(frozen=True)
class MigrationResult:
    """返回不含 SQL、异常文本和业务身份的稳定迁移状态。"""

    status: str
    code: str
    stage: str
    ordinal: int
    restore_required: bool
    reason_code: str | None = None

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "code": self.code,
            "stage": self.stage,
            "ordinal": self.ordinal,
            "restoreRequired": self.restore_required,
        }
        if self.reason_code is not None:
            payload["reasonCode"] = self.reason_code
        return payload


@dataclass(frozen=True)
class TableStats:
    row_count: int
    id_sum: int
    min_id: int | None
    max_id: int | None
    min_created_at: datetime | None = None
    max_created_at: datetime | None = None
    min_updated_at: datetime | None = None
    max_updated_at: datetime | None = None


@dataclass
class TargetSchemaSnapshot:
    """保存 0003 目标结构，不执行任何业务表聚合。"""

    column_specs: dict[tuple[str, str], tuple[str, str, int | None, str | None]]
    column_extras: dict[tuple[str, str], str]
    index_specs: dict[tuple[str, str], tuple[int, tuple[str, ...]]]
    table_engines: dict[str, str]


@dataclass
class PostflightSnapshot(TargetSchemaSnapshot):
    table_stats: dict[str, TableStats]
    raw_violation_count: int
    legacy_scope_violation_count: int
    history_row_count: int


class _StopMigration(Exception):
    """仅用于结束当前受控流程，不携带数据库异常或 SQL。"""

    def __init__(self, result: MigrationResult) -> None:
        self.result = result


def run_migration_0003(engine: Engine) -> MigrationResult:
    """用一个数据库连接串行执行受控 0003，并始终关闭连接。"""
    connection: Connection | None = None
    result: MigrationResult | None = None
    try:
        connection = engine.connect()
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        result = _run_on_connection(connection)
    except Exception:
        result = MigrationResult(
            status="error",
            code="MIGRATION_CONNECTION_FAILED",
            stage="connection",
            ordinal=0,
            restore_required=False,
        )
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                if result is None or result.status == "success":
                    result = MigrationResult(
                        status="error",
                        code="MIGRATION_CONNECTION_CLOSE_FAILED",
                        stage="connection_close",
                        ordinal=result.ordinal if result is not None else 0,
                        restore_required=False,
                    )
    return result or MigrationResult(
        status="error",
        code="MIGRATION_CONNECTION_FAILED",
        stage="connection",
        ordinal=0,
        restore_required=False,
    )


def _run_on_connection(connection: Connection) -> MigrationResult:
    statements: list[str] = []
    result: MigrationResult | None = None
    lock_acquired = False
    ddl_started = False
    ordinal = 0
    stage = "acquire_lock"
    try:
        lock_result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 0)"),
            {"lock_name": SYNC_TASK_LOCK_NAME},
        ).scalar_one()
        if lock_result == 0:
            raise _StopMigration(
                MigrationResult(
                    status="blocked",
                    code="MIGRATION_LOCK_BUSY",
                    stage=stage,
                    ordinal=0,
                    restore_required=False,
                )
            )
        if lock_result != 1:
            raise _StopMigration(
                MigrationResult(
                    status="error",
                    code="MIGRATION_LOCK_ERROR",
                    stage=stage,
                    ordinal=0,
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
            raise _StopMigration(
                MigrationResult(
                    status="blocked",
                    code="MIGRATION_LOCK_NOT_OWNED",
                    stage=stage,
                    ordinal=0,
                    restore_required=False,
                )
            )

        stage = "preflight"
        preflight = evaluate_preflight(
            collect_preflight_snapshot(connection),
            require_lock_owned=True,
        )
        if preflight.status != "pass":
            raise _StopMigration(_blocked_result("MIGRATION_PREFLIGHT_BLOCKED", stage, preflight))

        stage = "baseline"
        baseline = collect_table_stats(connection)
        statements = load_migration_statements()

        stage = "apply"
        for statement in statements:
            ordinal += 1
            if not statement.lstrip().upper().startswith("SET SESSION"):
                ddl_started = True
            connection.exec_driver_sql(statement)

        stage = "postflight"
        postflight = evaluate_postflight(
            baseline,
            collect_postflight_snapshot(connection),
        )
        if postflight.status != "pass":
            raise _StopMigration(
                _blocked_result(
                    "MIGRATION_POSTFLIGHT_BLOCKED",
                    stage,
                    postflight,
                    ordinal=len(statements),
                    restore_required=True,
                    status="error",
                )
            )

        result = MigrationResult(
            status="success",
            code="MIGRATION_APPLIED",
            stage="complete",
            ordinal=len(statements),
            restore_required=False,
        )
    except _StopMigration as stop:
        result = stop.result
    except Exception:
        if stage == "apply":
            result = MigrationResult(
                status="error",
                code=("MIGRATION_DDL_FAILED" if ddl_started else "MIGRATION_SESSION_SETUP_FAILED"),
                stage=stage,
                ordinal=ordinal,
                restore_required=ddl_started,
            )
        else:
            result = MigrationResult(
                status="error",
                code="MIGRATION_RUNTIME_FAILED",
                stage=stage,
                ordinal=ordinal,
                restore_required=ddl_started,
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
                result = MigrationResult(
                    status="error",
                    code="MIGRATION_LOCK_RELEASE_FAILED",
                    stage="release_lock",
                    ordinal=ordinal,
                    restore_required=ddl_started,
                )
    return result or MigrationResult(
        status="error",
        code="MIGRATION_RUNTIME_FAILED",
        stage=stage,
        ordinal=ordinal,
        restore_required=ddl_started,
    )


def collect_table_stats(connection: Connection) -> dict[str, TableStats]:
    """采集不含业务值的表级摘要，用于升级前后数据保全比较。"""
    rows = connection.execute(text(_table_stats_sql())).mappings()
    return {
        str(row["table_name"]): TableStats(
            row_count=int(row["row_count"] or 0),
            id_sum=int(row["id_sum"] or 0),
            min_id=int(row["min_id"]) if row["min_id"] is not None else None,
            max_id=int(row["max_id"]) if row["max_id"] is not None else None,
            min_created_at=row["min_created_at"],
            max_created_at=row["max_created_at"],
            min_updated_at=row["min_updated_at"],
            max_updated_at=row["max_updated_at"],
        )
        for row in rows
    }


def collect_target_schema_snapshot(connection: Connection) -> TargetSchemaSnapshot:
    """只读取 0003 目标列和索引结构，不扫描业务表。"""
    target_tables = (*LEGACY_TABLES, "raw_api_data_history")
    column_rows = read_information_schema_columns(
        connection,
        target_tables,
    )
    column_specs = {
        (str(row["table_name"]), str(row["column_name"])): (
            normalize_column_data_type(row),
            str(row["is_nullable"]).upper(),
            bounded_character_length(row),
            normalize_column_default(row["column_default"]),
        )
        for row in column_rows
    }
    column_extras = {
        (str(row["table_name"]), str(row["column_name"])): str(row["extra"] or "").lower()
        for row in column_rows
    }
    index_rows = read_information_schema_indexes(
        connection,
        target_tables,
    )
    index_specs = build_index_specs(index_rows)
    table_rows = read_information_schema_tables(
        connection,
        target_tables,
    )
    table_engines = {str(row["table_name"]): str(row["engine"] or "").lower() for row in table_rows}
    return TargetSchemaSnapshot(
        column_specs=column_specs,
        column_extras=column_extras,
        index_specs=index_specs,
        table_engines=table_engines,
    )


def collect_postflight_snapshot(connection: Connection) -> PostflightSnapshot:
    """采集升级后的结构和脱敏数据完整性事实。"""
    target_schema = collect_target_schema_snapshot(connection)
    raw_violations = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM raw_api_data
            WHERE jijia_account_id <> 0
               OR record_identity IS NULL
               OR first_observed_at IS NULL
               OR last_observed_at IS NULL
               OR observation_count IS NULL
               OR first_observed_at <> created_at
               OR last_observed_at <> updated_at
               OR observation_count <> 1
               OR BINARY record_identity <> BINARY SHA2(
                    CASE
                      WHEN source_primary_key IS NOT NULL
                           AND TRIM(source_primary_key) <> ''
                        THEN CONCAT('pk:', TRIM(source_primary_key))
                      ELSE CONCAT('hash:', data_hash)
                    END,
                    256
                  )
            """
        )
    ).scalar_one()
    legacy_scope_violations = connection.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM sync_batch
               WHERE jijia_account_id <> 0 OR sync_job_id IS NOT NULL)
              + (SELECT COUNT(*) FROM sync_api_log WHERE jijia_account_id <> 0)
              + (SELECT COUNT(*) FROM failed_request_log WHERE jijia_account_id <> 0)
              + (SELECT COUNT(*) FROM sync_checkpoint
                 WHERE jijia_account_id <> 0 OR checkpoint_kind <> 'date_window')
            """
        )
    ).scalar_one()
    history_row_count = connection.execute(
        text("SELECT COUNT(*) FROM raw_api_data_history")
    ).scalar_one()
    return PostflightSnapshot(
        column_specs=target_schema.column_specs,
        column_extras=target_schema.column_extras,
        index_specs=target_schema.index_specs,
        table_engines=target_schema.table_engines,
        table_stats=collect_table_stats(connection),
        raw_violation_count=int(raw_violations or 0),
        legacy_scope_violation_count=int(legacy_scope_violations or 0),
        history_row_count=int(history_row_count or 0),
    )


def evaluate_target_schema(snapshot: TargetSchemaSnapshot) -> PreflightResult:
    """按同一份 0003 目标契约验证列、索引和已移除 legacy 索引。"""
    return _evaluate_schema(snapshot, allow_extra_non_unique_indexes=False)


def evaluate_runtime_schema(snapshot: TargetSchemaSnapshot) -> PreflightResult:
    """验证运行时语义兼容性，额外普通索引只作为结构漂移警告。"""
    return _evaluate_schema(snapshot, allow_extra_non_unique_indexes=True)


def _evaluate_schema(
    snapshot: TargetSchemaSnapshot,
    *,
    allow_extra_non_unique_indexes: bool,
) -> PreflightResult:
    unexpected_column_count = len(set(snapshot.column_specs) - set(TARGET_COLUMN_SPECS))
    invalid_column_count = sum(
        snapshot.column_specs.get(key) != expected for key, expected in TARGET_COLUMN_SPECS.items()
    )
    invalid_extra_count = sum(
        fragment not in snapshot.column_extras.get(key, "")
        for key, fragment in TARGET_COLUMN_EXTRA_FRAGMENTS.items()
    )
    invalid_index_count = sum(
        snapshot.index_specs.get(key) != expected for key, expected in TARGET_INDEX_SPECS.items()
    )
    invalid_index_count += sum(
        key in snapshot.index_specs and snapshot.index_specs[key] != expected
        for key, expected in POST_0003_INDEX_SPECS.items()
    )
    invalid_table_engine_count = sum(
        snapshot.table_engines.get(table_name) != expected
        for table_name, expected in TARGET_TABLE_ENGINES.items()
    )
    unexpected_indexes = set(snapshot.index_specs) - set(CURRENT_INDEX_SPECS) - LEGACY_INDEXES
    legacy_indexes = set(snapshot.index_specs) & LEGACY_INDEXES
    unexpected_unique_index_count = sum(
        snapshot.index_specs[key][0] == 0 for key in unexpected_indexes
    )
    unexpected_non_unique_index_count = len(unexpected_indexes) - unexpected_unique_index_count
    legacy_unique_index_count = sum(snapshot.index_specs[key][0] == 0 for key in legacy_indexes)
    legacy_non_unique_index_count = len(legacy_indexes) - legacy_unique_index_count
    blocking_unexpected_index_count = unexpected_unique_index_count
    blocking_legacy_index_count = legacy_unique_index_count
    if not allow_extra_non_unique_indexes:
        blocking_unexpected_index_count += unexpected_non_unique_index_count
        blocking_legacy_index_count += legacy_non_unique_index_count
    if (
        invalid_column_count
        or invalid_extra_count
        or invalid_index_count
        or invalid_table_engine_count
        or unexpected_column_count
        or blocking_unexpected_index_count
        or blocking_legacy_index_count
    ):
        return PreflightResult(
            status="blocked",
            code="POSTFLIGHT_SCHEMA_MISMATCH",
            details={
                "invalidColumnCount": invalid_column_count,
                "invalidExtraCount": invalid_extra_count,
                "invalidIndexCount": invalid_index_count,
                "invalidTableEngineCount": invalid_table_engine_count,
                "unexpectedColumnCount": unexpected_column_count,
                "unexpectedIndexCount": len(unexpected_indexes),
                "legacyIndexCount": len(legacy_indexes),
                "unexpectedUniqueIndexCount": unexpected_unique_index_count,
                "unexpectedNonUniqueIndexCount": unexpected_non_unique_index_count,
                "legacyUniqueIndexCount": legacy_unique_index_count,
                "legacyNonUniqueIndexCount": legacy_non_unique_index_count,
            },
        )
    warning_details = {
        key: value
        for key, value in (
            ("unexpectedNonUniqueIndexCount", unexpected_non_unique_index_count),
            ("legacyNonUniqueIndexCount", legacy_non_unique_index_count),
        )
        if value
    }
    return PreflightResult(
        status="pass",
        code="TARGET_SCHEMA_READY",
        details=warning_details,
    )


def evaluate_postflight(
    baseline: dict[str, TableStats],
    snapshot: PostflightSnapshot,
) -> PreflightResult:
    """验证升级后的结构、行摘要和 legacy 数据边界。"""
    schema_result = evaluate_target_schema(snapshot)
    if schema_result.status != "pass":
        return schema_result
    changed_table_count = sum(
        snapshot.table_stats.get(table) != stats for table, stats in baseline.items()
    )
    if (
        changed_table_count
        or snapshot.raw_violation_count
        or snapshot.legacy_scope_violation_count
        or snapshot.history_row_count
    ):
        return PreflightResult(
            status="blocked",
            code="POSTFLIGHT_DATA_MISMATCH",
            details={
                "changedTableCount": changed_table_count,
                "rawViolationCount": snapshot.raw_violation_count,
                "legacyScopeViolationCount": snapshot.legacy_scope_violation_count,
                "historyRowCount": snapshot.history_row_count,
            },
        )
    return PreflightResult(status="pass", code="POSTFLIGHT_PASSED")


def load_migration_statements() -> list[str]:
    """按当前受控 SQL 文件拆分语句；不实现通用 SQL 解析。"""
    return load_sql_statements(MIGRATION_SQL_PATH, EXPECTED_STATEMENT_COUNT)


def _blocked_result(
    code: str,
    stage: str,
    reason: PreflightResult,
    *,
    ordinal: int = 0,
    restore_required: bool = False,
    status: str = "blocked",
) -> MigrationResult:
    return MigrationResult(
        status=status,
        code=code,
        stage=stage,
        ordinal=ordinal,
        restore_required=restore_required,
        reason_code=reason.code,
    )


def _table_stats_sql() -> str:
    selects = [
        (
            f"SELECT '{table}' AS table_name, COUNT(*) AS row_count, "
            f"COALESCE(SUM(id), 0) AS id_sum, MIN(id) AS min_id, MAX(id) AS max_id, "
            f"MIN(created_at) AS min_created_at, MAX(created_at) AS max_created_at, "
            f"MIN(updated_at) AS min_updated_at, MAX(updated_at) AS max_updated_at "
            f"FROM {table}"
        )
        for table in LEGACY_TABLES
    ]
    return "\nUNION ALL\n".join(selects)
