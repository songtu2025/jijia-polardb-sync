from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_0001_upgrade_and_downgrade_on_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sync_batch (id INTEGER PRIMARY KEY)"))

    config = Config("backend/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert {"app_user", "auth_action_token", "user_session"}.issubset(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("user_session")} >= {
        "session_hash",
        "csrf_hash",
        "expires_at",
        "idle_expires_at",
    }

    command.downgrade(config, "base")
    remaining_tables = inspect(engine).get_table_names()
    assert "app_user" not in remaining_tables
    assert "sync_batch" in remaining_tables
    engine.dispose()
