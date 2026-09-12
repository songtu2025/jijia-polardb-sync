from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateTable

from app.sale_return_projection import main as projection_main
from app.sale_return_projection import project_sale_return_orders
from app.sync_engine import SyncEngine
from backend.app.models.sync_records import sale_return_order_table

ROOT = Path(__file__).resolve().parents[2]


class RecordingConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | list[dict[str, Any]]]] = []

    def execute(self, statement: Any, params: Any = None) -> Any:
        self.calls.append((str(statement), params))
        return SimpleNamespace(
            rowcount=1,
            mappings=lambda: SimpleNamespace(all=lambda: []),
        )


def test_projection_sql_uses_current_raw_snapshot_and_official_fields() -> None:
    connection = RecordingConnection()

    projected = project_sale_return_orders(
        cast(Connection, connection),
        ["a" * 64],
    )

    assert projected == 1
    sql, params = connection.calls[0]
    assert "INSERT INTO sale_return_order" in sql
    assert "FROM raw_api_data AS raw" in sql
    assert "$.returnDateTime" in sql
    assert "$.orderId" in sql
    assert "$.sku" in sql
    assert "$.status" in sql
    assert "customerComments" not in sql
    assert params == {"api_code": "sale_return_order_page", "record_identities": ["a" * 64]}


def test_account_scope_projection_requires_explicit_account_before_database(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.config.load_settings",
        lambda: SimpleNamespace(sync_lock_scope="account"),
    )
    monkeypatch.setattr(
        "app.db.create_db_engine",
        lambda _settings: (_ for _ in ()).throw(AssertionError("不能创建数据库引擎")),
    )

    try:
        projection_main([])
    except SystemExit as error:
        assert "--account-id" in str(error)
    else:
        raise AssertionError("账号锁模式缺少账号时必须拒绝")


def test_account_scope_projection_uses_account_lock(monkeypatch) -> None:
    lock_calls: list[dict[str, Any]] = []

    @contextmanager
    def fake_lock(_engine, **kwargs):
        lock_calls.append(kwargs)
        yield

    monkeypatch.setattr(
        "app.config.load_settings",
        lambda: SimpleNamespace(sync_lock_scope="account"),
    )
    monkeypatch.setattr(
        "app.db.create_db_engine",
        lambda _settings: SimpleNamespace(dispose=lambda: None),
    )
    monkeypatch.setattr("app.sync_lock.sync_task_lock", fake_lock)
    monkeypatch.setattr("app.sale_return_projection.project_existing", lambda _engine, _id: 0)

    assert projection_main(["--account-id", "7"]) == 0
    assert lock_calls == [{"scope": "account", "account_id": 7}]


def test_sync_engine_projects_sale_return_rows_after_raw_upsert(monkeypatch) -> None:
    connection = RecordingConnection()
    projected: list[list[str]] = []
    monkeypatch.setattr(
        "app.sync_engine.project_sale_return_orders",
        lambda _connection, identities: projected.append(list(identities)),
    )
    engine = SyncEngine(
        [],
        sync_context=SimpleNamespace(jijia_account_id=7),
    )

    engine._insert_raw_items(
        connection,
        {
            "api_code": "sale_return_order_page",
            "storage_mode": "history_on_change",
            "primary_key": {"field": "id"},
            "date_field": "returnDateTime",
        },
        [{"id": 9, "returnDateTime": "2021-08-01 09:30:00"}],
        "sync-test",
    )

    statements = [statement for statement, _ in connection.calls]
    assert sum("INSERT INTO raw_api_data_history" in statement for statement in statements) == 1
    assert sum("INSERT INTO raw_api_data (" in statement for statement in statements) == 1
    assert sum("INSERT INTO raw_api_data_stat" in statement for statement in statements) == 1
    assert len(projected) == 1
    assert len(projected[0][0]) == 64


def test_schema_contract_is_present_in_init_and_upgrade_sql() -> None:
    init_sql = (ROOT / "sql" / "init_tables.sql").read_text(encoding="utf-8")
    upgrade_sql = (ROOT / "sql" / "migrations" / "0004_sale_return_order_projection.sql").read_text(
        encoding="utf-8"
    )
    down_sql = (
        ROOT / "sql" / "migrations" / "0004_sale_return_order_projection_down.sql"
    ).read_text(encoding="utf-8")
    compiled = str(CreateTable(sale_return_order_table).compile(dialect=mysql.dialect()))

    for sql in (init_sql, upgrade_sql):
        assert "sale_return_order" in sql
        assert "uk_sale_return_account_source" in sql
        assert "idx_sale_return_account_status_date" in sql
    assert "sale_return_order" in compiled
    assert "uk_sale_return_account_source" in compiled
    assert "idx_sale_return_account_status_date" in {
        index.name for index in sale_return_order_table.indexes
    }
    assert "DROP TABLE sale_return_order" in down_sql


def test_sale_return_created_index_contract() -> None:
    init_sql = (ROOT / "sql" / "init_tables.sql").read_text(encoding="utf-8")
    upgrade_sql = (ROOT / "sql" / "migrations" / "0006_sale_return_created_index.sql").read_text(
        encoding="utf-8"
    )
    down_sql = (ROOT / "sql" / "migrations" / "0006_sale_return_created_index_down.sql").read_text(
        encoding="utf-8"
    )

    assert "idx_sale_return_created (created_at, id)" in init_sql
    assert "ADD KEY idx_sale_return_created (created_at, id)" in upgrade_sql
    assert "idx_sale_return_created" in {index.name for index in sale_return_order_table.indexes}
    assert "DROP INDEX idx_sale_return_created" in down_sql
