from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import AppSettings


def create_db_engine(settings: AppSettings) -> Engine:
    """创建 SQLAlchemy 数据库引擎。

    `pool_pre_ping=True` 会在连接复用前做轻量探活，降低 ECS 长时间运行后
    复用失效连接的概率；`pool_recycle` 用于主动回收老连接。
    """
    return create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)


def check_db_connection(engine: Engine) -> None:
    """执行最小 SQL 验证数据库可连接。"""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
