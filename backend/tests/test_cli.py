import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import cli
from backend.app.core.errors import ApiError
from backend.app.models import Base
from backend.app.services.mail_service import FakeMailSender
from backend.tests.conftest import AuthHarness


def test_bootstrap_admin_only_creates_first_invitation(
    harness: AuthHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    fake_mail = FakeMailSender()
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    monkeypatch.setattr(cli, "get_web_settings", lambda: harness.settings)
    monkeypatch.setattr(cli, "create_mail_sender", lambda _: fake_mail)

    cli.bootstrap_admin("first-admin@example.com")
    assert fake_mail.invitations[0]["role"] == "admin"
    with pytest.raises(ApiError) as error:
        cli.bootstrap_admin("second-admin@example.com")
    assert error.value.code == "ADMIN_ALREADY_EXISTS"
    engine.dispose()
