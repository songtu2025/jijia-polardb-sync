from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_SQL_PATH = (
    PROJECT_ROOT / "sql" / "migrations" / "0003_sync_scope_and_history_preflight.sql"
)

REQUIRED_LEGACY_COLUMN_SPECS = {
    ("sync_batch", "id"): ("bigint unsigned", "NO", None),
    ("sync_batch", "sync_batch_no"): ("varchar", "NO", 64),
    ("sync_batch", "status"): ("varchar", "NO", 30),
    ("sync_batch", "started_at"): ("datetime", "NO", None),
    ("sync_batch", "finished_at"): ("datetime", "YES", None),
    ("sync_batch", "total_api_count"): ("int", "NO", None),
    ("sync_batch", "success_api_count"): ("int", "NO", None),
    ("sync_batch", "failed_api_count"): ("int", "NO", None),
    ("sync_batch", "message"): ("varchar", "YES", 1000),
    ("sync_batch", "created_at"): ("timestamp", "NO", None),
    ("sync_batch", "updated_at"): ("timestamp", "NO", None),
    ("sync_api_log", "id"): ("bigint unsigned", "NO", None),
    ("sync_api_log", "sync_batch_no"): ("varchar", "NO", 64),
    ("sync_api_log", "api_code"): ("varchar", "NO", 100),
    ("sync_api_log", "status"): ("varchar", "NO", 30),
    ("sync_api_log", "request_count"): ("int", "NO", None),
    ("sync_api_log", "success_count"): ("int", "NO", None),
    ("sync_api_log", "failed_count"): ("int", "NO", None),
    ("sync_api_log", "started_at"): ("datetime", "NO", None),
    ("sync_api_log", "finished_at"): ("datetime", "YES", None),
    ("sync_api_log", "error_message"): ("text", "YES", None),
    ("sync_api_log", "created_at"): ("timestamp", "NO", None),
    ("sync_api_log", "updated_at"): ("timestamp", "NO", None),
    ("failed_request_log", "id"): ("bigint unsigned", "NO", None),
    ("failed_request_log", "sync_batch_no"): ("varchar", "YES", 64),
    ("failed_request_log", "api_code"): ("varchar", "NO", 100),
    ("failed_request_log", "request_url"): ("varchar", "YES", 1000),
    ("failed_request_log", "request_method"): ("varchar", "NO", 20),
    ("failed_request_log", "request_params"): ("json", "YES", None),
    ("failed_request_log", "response_status_code"): ("int", "YES", None),
    ("failed_request_log", "response_body"): ("mediumtext", "YES", None),
    ("failed_request_log", "error_message"): ("text", "YES", None),
    ("failed_request_log", "retry_count"): ("int", "NO", None),
    ("failed_request_log", "created_at"): ("timestamp", "NO", None),
    ("failed_request_log", "updated_at"): ("timestamp", "NO", None),
    ("raw_api_data", "id"): ("bigint unsigned", "NO", None),
    ("raw_api_data", "api_code"): ("varchar", "NO", 100),
    ("raw_api_data", "source_primary_key"): ("varchar", "YES", 255),
    ("raw_api_data", "data_hash"): ("char", "NO", 64),
    ("raw_api_data", "raw_json"): ("json", "NO", None),
    ("raw_api_data", "data_date"): ("date", "YES", None),
    ("raw_api_data", "sync_batch_no"): ("varchar", "NO", 64),
    ("raw_api_data", "created_at"): ("timestamp", "NO", None),
    ("raw_api_data", "updated_at"): ("timestamp", "NO", None),
    ("sync_checkpoint", "id"): ("bigint unsigned", "NO", None),
    ("sync_checkpoint", "api_code"): ("varchar", "NO", 100),
    ("sync_checkpoint", "checkpoint_value"): ("varchar", "YES", 255),
    ("sync_checkpoint", "checkpoint_time"): ("datetime", "YES", None),
    ("sync_checkpoint", "last_sync_batch_no"): ("varchar", "YES", 64),
    ("sync_checkpoint", "created_at"): ("timestamp", "NO", None),
    ("sync_checkpoint", "updated_at"): ("timestamp", "NO", None),
}
REQUIRED_LEGACY_COLUMN_DEFAULTS = dict.fromkeys(REQUIRED_LEGACY_COLUMN_SPECS)
REQUIRED_LEGACY_COLUMN_DEFAULTS.update(
    {
        ("sync_batch", "status"): "running",
        ("sync_batch", "total_api_count"): "0",
        ("sync_batch", "success_api_count"): "0",
        ("sync_batch", "failed_api_count"): "0",
        ("sync_batch", "created_at"): "current_timestamp",
        ("sync_batch", "updated_at"): "current_timestamp",
        ("sync_api_log", "request_count"): "0",
        ("sync_api_log", "success_count"): "0",
        ("sync_api_log", "failed_count"): "0",
        ("sync_api_log", "created_at"): "current_timestamp",
        ("sync_api_log", "updated_at"): "current_timestamp",
        ("failed_request_log", "request_method"): "post",
        ("failed_request_log", "retry_count"): "0",
        ("failed_request_log", "created_at"): "current_timestamp",
        ("failed_request_log", "updated_at"): "current_timestamp",
        ("raw_api_data", "created_at"): "current_timestamp",
        ("raw_api_data", "updated_at"): "current_timestamp",
        ("sync_checkpoint", "created_at"): "current_timestamp",
        ("sync_checkpoint", "updated_at"): "current_timestamp",
    }
)
REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS = {
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
}
REQUIRED_LEGACY_COLUMNS = {
    table_name: {
        column_name
        for current_table_name, column_name in REQUIRED_LEGACY_COLUMN_SPECS
        if current_table_name == table_name
    }
    for table_name in (
        "sync_batch",
        "sync_api_log",
        "failed_request_log",
        "raw_api_data",
        "sync_checkpoint",
    )
}
REQUIRED_LEGACY_TABLE_ENGINES = dict.fromkeys(REQUIRED_LEGACY_COLUMNS, "innodb")
REQUIRED_LEGACY_INDEX_SPECS = {
    ("sync_batch", "PRIMARY"): (0, ("id",)),
    ("sync_batch", "uk_sync_batch_no"): (0, ("sync_batch_no",)),
    ("sync_batch", "idx_sync_batch_status_started_at"): (
        1,
        ("status", "started_at"),
    ),
    ("sync_api_log", "PRIMARY"): (0, ("id",)),
    ("sync_api_log", "idx_sync_api_log_batch"): (1, ("sync_batch_no",)),
    ("sync_api_log", "idx_sync_api_log_api_status"): (
        1,
        ("api_code", "status"),
    ),
    ("failed_request_log", "PRIMARY"): (0, ("id",)),
    ("failed_request_log", "idx_failed_request_batch"): (1, ("sync_batch_no",)),
    ("failed_request_log", "idx_failed_request_api_created_at"): (
        1,
        ("api_code", "created_at"),
    ),
    ("raw_api_data", "PRIMARY"): (0, ("id",)),
    ("raw_api_data", "idx_raw_api_data_date"): (1, ("api_code", "data_date")),
    ("raw_api_data", "idx_raw_api_batch"): (1, ("sync_batch_no",)),
    ("raw_api_data", "uk_raw_api_primary_key"): (
        0,
        ("api_code", "source_primary_key"),
    ),
    ("raw_api_data", "uk_raw_api_data_hash"): (
        0,
        ("api_code", "data_hash"),
    ),
    ("sync_checkpoint", "PRIMARY"): (0, ("id",)),
    ("sync_checkpoint", "uk_sync_checkpoint_api_code"): (0, ("api_code",)),
}
TARGET_COLUMNS = {
    "sync_batch": {"jijia_account_id", "sync_job_id"},
    "sync_api_log": {"jijia_account_id"},
    "failed_request_log": {"jijia_account_id"},
    "raw_api_data": {
        "jijia_account_id",
        "record_identity",
        "first_observed_at",
        "last_observed_at",
        "observation_count",
    },
    "sync_checkpoint": {"jijia_account_id", "checkpoint_kind"},
}
TARGET_TABLES = {"raw_api_data_history"}


@dataclass
class PreflightSnapshot:
    """保存一次只读副本检查所需的脱敏事实。"""

    columns: dict[str, set[str]]
    column_specs: dict[tuple[str, str], tuple[str, str, int | None]]
    column_defaults: dict[tuple[str, str], str | None]
    column_extras: dict[tuple[str, str], str]
    index_specs: dict[tuple[str, str], tuple[int, tuple[str, ...]]]
    target_tables: set[str]
    table_engines: dict[str, str]
    duplicate_group_count: int
    duplicate_row_count: int
    projected_identity_null_count: int
    checkpoint_duplicate_group_count: int
    session_time_zone: str | None
    sync_lock_free: int | None
    connection_id: int | None
    sync_lock_owner_id: int | None


@dataclass(frozen=True)
class PreflightResult:
    """提供机器可判定的预检结果，不包含连接串或业务身份。"""

    status: str
    code: str
    details: dict[str, int] = field(default_factory=dict)

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status, "code": self.code}
        if self.details:
            payload["details"] = self.details
        return payload


def evaluate_preflight(
    snapshot: PreflightSnapshot,
    *,
    require_lock_owned: bool = False,
) -> PreflightResult:
    """按固定优先级判断副本是否具备执行 0003 的前置条件。"""
    target_column_count = sum(
        len(snapshot.columns.get(table, set()) & target_columns)
        for table, target_columns in TARGET_COLUMNS.items()
    )
    target_table_count = len(snapshot.target_tables & TARGET_TABLES)
    if target_column_count or target_table_count:
        return PreflightResult(
            status="blocked",
            code="PARTIAL_MIGRATION_DETECTED",
            details={
                "targetColumnCount": target_column_count,
                "targetTableCount": target_table_count,
            },
        )

    missing_column_count = sum(
        len(required - snapshot.columns.get(table, set()))
        for table, required in REQUIRED_LEGACY_COLUMNS.items()
    )
    invalid_column_spec_count = sum(
        snapshot.column_specs.get(key) != expected
        for key, expected in REQUIRED_LEGACY_COLUMN_SPECS.items()
    )
    invalid_column_default_count = sum(
        snapshot.column_defaults.get(key) != expected
        for key, expected in REQUIRED_LEGACY_COLUMN_DEFAULTS.items()
    )
    invalid_column_extra_count = sum(
        fragment not in snapshot.column_extras.get(key, "")
        for key, fragment in REQUIRED_LEGACY_COLUMN_EXTRA_FRAGMENTS.items()
    )
    invalid_index_spec_count = sum(
        snapshot.index_specs.get(key) != expected
        for key, expected in REQUIRED_LEGACY_INDEX_SPECS.items()
    )
    invalid_table_engine_count = sum(
        snapshot.table_engines.get(table_name) != expected
        for table_name, expected in REQUIRED_LEGACY_TABLE_ENGINES.items()
    )
    unexpected_column_count = sum(
        len(snapshot.columns.get(table, set()) - required)
        for table, required in REQUIRED_LEGACY_COLUMNS.items()
    )
    unexpected_index_count = len(set(snapshot.index_specs) - set(REQUIRED_LEGACY_INDEX_SPECS))
    if (
        missing_column_count
        or invalid_column_spec_count
        or invalid_column_default_count
        or invalid_column_extra_count
        or invalid_index_spec_count
        or invalid_table_engine_count
        or unexpected_column_count
        or unexpected_index_count
    ):
        return PreflightResult(
            status="blocked",
            code="LEGACY_SCHEMA_MISMATCH",
            details={
                "missingColumnCount": missing_column_count,
                "invalidColumnSpecCount": invalid_column_spec_count,
                "invalidColumnDefaultCount": invalid_column_default_count,
                "invalidColumnExtraCount": invalid_column_extra_count,
                "invalidIndexSpecCount": invalid_index_spec_count,
                "invalidTableEngineCount": invalid_table_engine_count,
                "unexpectedColumnCount": unexpected_column_count,
                "unexpectedIndexCount": unexpected_index_count,
            },
        )

    if snapshot.session_time_zone != "+00:00":
        return PreflightResult(status="blocked", code="SESSION_NOT_UTC")
    if require_lock_owned:
        if snapshot.connection_id is None or snapshot.sync_lock_owner_id != snapshot.connection_id:
            return PreflightResult(status="blocked", code="SYNC_LOCK_NOT_OWNED")
    elif snapshot.sync_lock_free != 1:
        return PreflightResult(status="blocked", code="SYNC_WRITER_ACTIVE")
    if snapshot.projected_identity_null_count:
        return PreflightResult(
            status="blocked",
            code="PROJECTED_IDENTITY_NULL",
            details={"projectedIdentityNullCount": snapshot.projected_identity_null_count},
        )
    if snapshot.checkpoint_duplicate_group_count:
        return PreflightResult(
            status="blocked",
            code="CHECKPOINT_SCOPE_DUPLICATES",
            details={"checkpointDuplicateGroupCount": (snapshot.checkpoint_duplicate_group_count)},
        )
    if snapshot.duplicate_group_count:
        return PreflightResult(
            status="blocked",
            code="PROJECTED_IDENTITY_DUPLICATES",
            details={
                "duplicateGroupCount": snapshot.duplicate_group_count,
                "duplicateRowCount": snapshot.duplicate_row_count,
            },
        )
    return PreflightResult(status="pass", code="PREFLIGHT_PASSED")


def collect_preflight_snapshot(connection: Connection) -> PreflightSnapshot:
    """只读取 MySQL 元数据和冲突汇总，不返回业务记录。"""
    if connection.dialect.name != "mysql":
        raise RuntimeError("0003 preflight requires MySQL")

    legacy_tables = tuple(REQUIRED_LEGACY_COLUMNS)
    column_rows = read_information_schema_columns(
        connection,
        legacy_tables,
    )
    columns = _group_names(column_rows, "column_name")
    column_specs = {
        (str(row["table_name"]), str(row["column_name"])): (
            normalize_column_data_type(row),
            str(row["is_nullable"]).upper(),
            bounded_character_length(row),
        )
        for row in column_rows
    }
    column_defaults = {
        (str(row["table_name"]), str(row["column_name"])): normalize_column_default(
            row["column_default"]
        )
        for row in column_rows
    }
    column_extras = {
        (str(row["table_name"]), str(row["column_name"])): str(row["extra"] or "").lower()
        for row in column_rows
    }

    index_rows = read_information_schema_indexes(
        connection,
        legacy_tables,
    )
    index_specs = build_index_specs(index_rows)

    table_rows = read_information_schema_tables(
        connection,
        (*legacy_tables, "raw_api_data_history"),
    )
    target_tables = {str(row["table_name"]) for row in table_rows}
    table_engines = {str(row["table_name"]): str(row["engine"] or "").lower() for row in table_rows}

    state = (
        connection.execute(
            text(
                """
            SELECT
              @@SESSION.time_zone AS session_time_zone,
              IS_FREE_LOCK(:lock_name) AS sync_lock_free,
              CONNECTION_ID() AS connection_id,
              IS_USED_LOCK(:lock_name) AS sync_lock_owner_id
            """
            ),
            {"lock_name": SYNC_TASK_LOCK_NAME},
        )
        .mappings()
        .one()
    )
    duplicate_summary = connection.execute(text(_duplicate_summary_sql())).mappings().one()
    projected_identity_null_count = connection.execute(
        text(
            f"""
            SELECT COUNT(*) AS projected_identity_null_count
            FROM raw_api_data
            WHERE {_projected_identity_sql()} IS NULL
            """
        )
    ).scalar_one()
    checkpoint_duplicate_group_count = connection.execute(
        text(
            """
            SELECT COUNT(*) AS checkpoint_duplicate_group_count
            FROM (
              SELECT api_code
              FROM sync_checkpoint
              GROUP BY api_code
              HAVING COUNT(*) > 1
            ) AS duplicate_checkpoints
            """
        )
    ).scalar_one()

    return PreflightSnapshot(
        columns=columns,
        column_specs=column_specs,
        column_defaults=column_defaults,
        column_extras=column_extras,
        index_specs=index_specs,
        target_tables=target_tables,
        table_engines=table_engines,
        duplicate_group_count=int(duplicate_summary["duplicate_group_count"] or 0),
        duplicate_row_count=int(duplicate_summary["duplicate_row_count"] or 0),
        projected_identity_null_count=int(projected_identity_null_count or 0),
        checkpoint_duplicate_group_count=int(checkpoint_duplicate_group_count or 0),
        session_time_zone=state["session_time_zone"],
        sync_lock_free=state["sync_lock_free"],
        connection_id=(int(state["connection_id"]) if state["connection_id"] is not None else None),
        sync_lock_owner_id=(
            int(state["sync_lock_owner_id"]) if state["sync_lock_owner_id"] is not None else None
        ),
    )


def run_preflight(engine: Engine) -> PreflightResult:
    """使用短连接执行纯只读检查，并返回稳定结果。"""
    with engine.connect() as connection:
        return evaluate_preflight(collect_preflight_snapshot(connection))


def _group_names(rows: Any, name_field: str) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for row in rows:
        grouped.setdefault(str(row["table_name"]), set()).add(str(row[name_field]))
    return grouped


def _projected_identity_sql() -> str:
    return """SHA2(
      CASE
        WHEN source_primary_key IS NOT NULL AND TRIM(source_primary_key) <> ''
          THEN CONCAT('pk:', TRIM(source_primary_key))
        ELSE CONCAT('hash:', data_hash)
      END,
      256
    )"""


def _duplicate_summary_sql() -> str:
    preflight_sql = PREFLIGHT_SQL_PATH.read_text(encoding="utf-8").strip()
    preflight_sql = preflight_sql.removesuffix(";")
    return f"""
        SELECT
          COUNT(*) AS duplicate_group_count,
          COALESCE(SUM(duplicate_count - 1), 0) AS duplicate_row_count
        FROM (
          {preflight_sql}
        ) AS projected_duplicates
    """
