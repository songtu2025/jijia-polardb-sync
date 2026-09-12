from pathlib import Path

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.engine import Connection, Engine

from app.sync_lock import SYNC_TASK_LOCK_NAME
from backend.app.models.sync_records import raw_api_data_stat_table, raw_api_data_table
from backend.app.services.migration_0003_service import MigrationResult
from backend.app.services.migration_sql_service import load_sql_statements

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_SQL_PATH = PROJECT_ROOT / "sql" / "migrations" / "0007_raw_api_data_stat.sql"
EXPECTED_STATEMENT_COUNT = 6


def load_migration_statements() -> list[str]:
    """加载统计表的手工迁移脚本并校验其完整性。"""
    return load_sql_statements(MIGRATION_SQL_PATH, EXPECTED_STATEMENT_COUNT)


def rebuild_raw_api_data_stats(connection: Connection) -> None:
    """在当前事务中用 raw 快照重建精确统计。"""
    grouped_counts = select(
        raw_api_data_table.c.jijia_account_id,
        raw_api_data_table.c.api_code,
        func.count(raw_api_data_table.c.id),
    ).group_by(
        raw_api_data_table.c.jijia_account_id,
        raw_api_data_table.c.api_code,
    )
    connection.execute(delete(raw_api_data_stat_table))
    connection.execute(
        insert(raw_api_data_stat_table).from_select(
            ["jijia_account_id", "api_code", "record_count"],
            grouped_counts,
        )
    )


def stats_match_raw_data(connection: Connection) -> bool:
    """只比较账号/API 计数，不读取 raw_json 或业务主键。"""
    raw_counts = {
        (int(row["jijia_account_id"]), str(row["api_code"])): int(row["record_count"])
        for row in connection.execute(
            select(
                raw_api_data_table.c.jijia_account_id,
                raw_api_data_table.c.api_code,
                func.count(raw_api_data_table.c.id).label("record_count"),
            ).group_by(
                raw_api_data_table.c.jijia_account_id,
                raw_api_data_table.c.api_code,
            )
        ).mappings()
    }
    stat_counts = {
        (int(row["jijia_account_id"]), str(row["api_code"])): int(row["record_count"])
        for row in connection.execute(select(raw_api_data_stat_table)).mappings()
    }
    return raw_counts == stat_counts


def run_migration_0007(engine: Engine) -> MigrationResult:
    """持有同步锁后建表、原子回填并验证统计一致性。"""
    connection: Connection | None = None
    result: MigrationResult | None = None
    lock_acquired = False
    stage = "connection"
    ordinal = 0
    try:
        connection = engine.connect()
        if connection.dialect.name != "mysql":
            return MigrationResult(
                status="blocked",
                code="MIGRATION_DIALECT_UNSUPPORTED",
                stage=stage,
                ordinal=ordinal,
                restore_required=False,
            )

        stage = "session"
        connection.exec_driver_sql("SET SESSION time_zone = '+00:00'")
        connection.commit()

        stage = "acquire_lock"
        lock_result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 0)"),
            {"lock_name": SYNC_TASK_LOCK_NAME},
        ).scalar_one()
        if lock_result != 1:
            return MigrationResult(
                status="blocked" if lock_result == 0 else "error",
                code="MIGRATION_LOCK_BUSY" if lock_result == 0 else "MIGRATION_LOCK_ERROR",
                stage=stage,
                ordinal=ordinal,
                restore_required=False,
            )
        lock_acquired = True
        connection.commit()

        stage = "create_table"
        schema_statement = load_migration_statements()[1]
        connection.exec_driver_sql(schema_statement)
        ordinal = 1
        connection.commit()

        stage = "backfill"
        with connection.begin():
            rebuild_raw_api_data_stats(connection)
        ordinal = 2

        stage = "postflight"
        if not stats_match_raw_data(connection):
            result = MigrationResult(
                status="error",
                code="MIGRATION_POSTFLIGHT_BLOCKED",
                stage=stage,
                ordinal=ordinal,
                restore_required=False,
                reason_code="RAW_DATA_STAT_MISMATCH",
            )
        else:
            result = MigrationResult(
                status="success",
                code="MIGRATION_0007_APPLIED",
                stage="complete",
                ordinal=ordinal,
                restore_required=False,
            )
    except Exception:
        if connection is not None:
            connection.rollback()
        result = MigrationResult(
            status="error",
            code="MIGRATION_RUNTIME_FAILED",
            stage=stage,
            ordinal=ordinal,
            restore_required=False,
        )
    finally:
        if connection is not None:
            if lock_acquired:
                try:
                    released = connection.execute(
                        text("SELECT RELEASE_LOCK(:lock_name)"),
                        {"lock_name": SYNC_TASK_LOCK_NAME},
                    ).scalar_one()
                    connection.commit()
                    if released != 1:
                        result = MigrationResult(
                            status="error",
                            code="MIGRATION_LOCK_RELEASE_FAILED",
                            stage="release_lock",
                            ordinal=ordinal,
                            restore_required=False,
                        )
                except Exception:
                    result = MigrationResult(
                        status="error",
                        code="MIGRATION_LOCK_RELEASE_FAILED",
                        stage="release_lock",
                        ordinal=ordinal,
                        restore_required=False,
                    )
            connection.close()
    return result or MigrationResult(
        status="error",
        code="MIGRATION_RUNTIME_FAILED",
        stage=stage,
        ordinal=ordinal,
        restore_required=False,
    )
