from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.deps import get_mail_sender
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.main import create_app
from backend.app.models import Base
from backend.app.services.mail_service import FakeMailSender


@dataclass
class AuthHarness:
    """集中提供 API 客户端、测试数据库和假邮件。"""

    app: FastAPI
    client: TestClient
    session_factory: sessionmaker[Session]
    settings: WebSettings
    mail_sender: FakeMailSender


@pytest.fixture
def harness() -> Generator[AuthHarness, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = WebSettings(
        _env_file=None,
        app_env="test",
        public_web_url="http://testserver",
        session_cookie_name="jijia_session",
        session_cookie_secure=False,
        invitation_ttl_hours=24,
        password_min_length=12,
        login_max_failures=3,
        login_lock_minutes=15,
        mail_provider="fake",
    )
    mail_sender = FakeMailSender()
    app = create_app(validate_settings=False)

    def override_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_web_settings] = lambda: settings
    app.dependency_overrides[get_mail_sender] = lambda: mail_sender
    with TestClient(app) as client:
        yield AuthHarness(app, client, session_factory, settings, mail_sender)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
