from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, insert, select
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from backend.app.models.sync_records import (
    raw_api_data_stat_table,
    raw_api_data_table,
    sync_records_metadata,
)
from backend.app.services.migration_0007_service import (
    rebuild_raw_api_data_stats,
    run_migration_0007,
    stats_match_raw_data,
)

ROOT = Path(__file__).resolve().parents[2]


def _raw_row(account_id: int, api_code: str, identity: str) -> dict[str, object]:
    now = datetime(2026, 9, 4, 8, 0, 0)
    return {
        "jijia_account_id": account_id,
        "api_code": api_code,
        "source_primary_key": identity,
        "record_identity": identity,
        "data_hash": identity,
        "raw_json": {"id": identity},
        "data_date": None,
        "sync_batch_no": "batch-stat-test",
        "first_observed_at": now,
        "last_observed_at": now,
        "observation_count": 1,
        "created_at": now,
        "updated_at": now,
    }


def test_backfill_rebuilds_exact_account_api_counts() -> None:
    engine = create_engine("sqlite+pysqlite://")
    sync_records_metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(raw_api_data_table),
            [
                _raw_row(1, "api-a", "a-1"),
                _raw_row(1, "api-a", "a-2"),
                _raw_row(1, "api-b", "b-1"),
                _raw_row(2, "api-a", "a-3"),
            ],
        )
        connection.execute(
            insert(raw_api_data_stat_table),
            {"jijia_account_id": 99, "api_code": "stale", "record_count": 8},
        )
        rebuild_raw_api_data_stats(connection)
        assert stats_match_raw_data(connection)

    with engine.connect() as connection:
        counts = {
            (row.jijia_account_id, row.api_code): row.record_count
            for row in connection.execute(select(raw_api_data_stat_table))
        }
    assert counts == {(1, "api-a"): 2, (1, "api-b"): 1, (2, "api-a"): 1}


def test_schema_and_manual_migration_contract() -> None:
    init_sql = (ROOT / "sql" / "init_tables.sql").read_text(encoding="utf-8")
    upgrade_sql = (ROOT / "sql" / "migrations" / "0007_raw_api_data_stat.sql").read_text(
        encoding="utf-8"
    )
    down_sql = (ROOT / "sql" / "migrations" / "0007_raw_api_data_stat_down.sql").read_text(
        encoding="utf-8"
    )
    compiled = str(CreateTable(raw_api_data_stat_table).compile(dialect=mysql.dialect()))

    for sql in (init_sql, upgrade_sql, compiled):
        assert "raw_api_data_stat" in sql
        assert "jijia_account_id" in sql
        assert "api_code" in sql
        assert "record_count" in sql
    assert "PRIMARY KEY (jijia_account_id, api_code)" in init_sql
    assert "START TRANSACTION" in upgrade_sql
    assert "GROUP BY jijia_account_id, api_code" in upgrade_sql
    assert "DROP TABLE raw_api_data_stat" in down_sql


def test_controlled_migration_rejects_non_mysql_engine() -> None:
    engine = create_engine("sqlite+pysqlite://")

    result = run_migration_0007(engine)

    assert result.status == "blocked"
    assert result.code == "MIGRATION_DIALECT_UNSUPPORTED"
