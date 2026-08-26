import pytest
from pydantic import ValidationError

from backend.app.core.config import WebSettings
from backend.app.services.mail_service import (
    ConsoleMailSender,
    FakeMailSender,
    SmtpMailSender,
    create_mail_sender,
)


def test_fake_and_console_mail_adapters(capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeMailSender()
    fake.send_invitation("user@example.com", "viewer", "http://example/register#token=secret")
    assert fake.invitations[0]["email"] == "user@example.com"

    console = ConsoleMailSender()
    console.send_invitation("user@example.com", "viewer", "http://example/register#token=secret")
    captured = capsys.readouterr()
    assert "邀请链接" in captured.out
    assert captured.err == ""


def test_mail_sender_factory_supports_all_adapters() -> None:
    assert isinstance(
        create_mail_sender(WebSettings(_env_file=None, mail_provider="console")),
        ConsoleMailSender,
    )
    assert isinstance(
        create_mail_sender(WebSettings(_env_file=None, mail_provider="fake")),
        FakeMailSender,
    )
    assert isinstance(
        create_mail_sender(WebSettings(_env_file=None, mail_provider="smtp")),
        SmtpMailSender,
    )


def test_production_rejects_console_mail_and_insecure_cookie() -> None:
    with pytest.raises(ValidationError):
        WebSettings(_env_file=None, app_env="production", mail_provider="console")
    with pytest.raises(ValidationError):
        WebSettings(
            _env_file=None,
            app_env="production",
            mail_provider="smtp",
            session_cookie_secure=False,
        )
