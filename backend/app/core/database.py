from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings
from app.db import create_db_engine

engine = create_db_engine(load_settings())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """为单个 HTTP 请求提供数据库会话。"""
    with SessionLocal() as session:
        yield session
