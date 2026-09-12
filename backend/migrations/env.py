from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import load_migration_settings
from app.db import configure_engine_session_timezone, set_connection_session_utc
from backend.app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """优先使用测试显式传入的 URL，否则复用现有项目数据库配置。"""
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return load_migration_settings().database_url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """生成迁移 SQL，不建立数据库连接。"""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在单一连接中执行迁移。"""
    external_connection = config.attributes.get("connection")
    if external_connection is not None:
        set_connection_session_utc(external_connection)
        context.configure(connection=external_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    configure_engine_session_timezone(connectable)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
