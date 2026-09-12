from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier, Event, Lock
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from backend.app.api.deps import get_mail_sender
from backend.app.api.v1.auth import delete_session_cookies
from backend.app.api.v1.users import update_user
from backend.app.core.config import WebSettings
from backend.app.core.errors import ApiError
from backend.app.core.security import DUMMY_PASSWORD_HASH, hash_token, utc_now
from backend.app.models.audit_log import AuditLog
from backend.app.models.auth_action_token import AuthActionToken
from backend.app.models.base import Base
from backend.app.models.user import AppUser, UserRole, UserStatus
from backend.app.models.user_session import UserSession
from backend.app.schemas.user import UserUpdateRequest
from backend.app.services.auth_service import (
    authenticate_user,
    create_invitation,
    resend_invitation,
    revoke_invitation,
    validate_invitation,
)
from backend.app.services.auth_service import (
    register_user as register_user_service,
)
from backend.tests.conftest import AuthHarness

VALID_PASSWORD = "correct-password-123"


def test_logout_cookie_deletion_reuses_security_attributes() -> None:
    response = Response()
    settings = WebSettings.model_validate(
        {
            "app_env": "test",
            "session_cookie_name": "__Host-jijia_session",
            "session_cookie_secure": True,
        }
    )

    delete_session_cookies(response, settings)

    cookies = [
        value.decode("latin-1")
        for name, value in response.raw_headers
        if name.lower() == b"set-cookie"
    ]
    session_cookie = next(value for value in cookies if value.startswith("__Host-jijia_session="))
    csrf_cookie = next(value for value in cookies if value.startswith("__Host-jijia_session_csrf="))
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    for cookie in cookies:
        assert "Max-Age=0" in cookie
        assert "Path=/" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" in cookie


def token_from_latest_mail(harness: AuthHarness) -> str:
    url = harness.mail_sender.invitations[-1]["url"]
    return parse_qs(urlparse(url).fragment)["token"][0]


def token_from_latest_password_reset(harness: AuthHarness) -> str:
    url = harness.mail_sender.password_resets[-1]["url"]
    return parse_qs(urlparse(url).fragment)["token"][0]


def create_pending_invitation(harness: AuthHarness, email: str, role: UserRole) -> str:
    with harness.session_factory() as db:
        create_invitation(
            db,
            email,
            role,
            created_by=None,
            settings=harness.settings,
            mail_sender=harness.mail_sender,
            request_id=None,
        )
    return token_from_latest_mail(harness)


def register_user(
    harness: AuthHarness,
    email: str,
    role: UserRole,
    client: TestClient | None = None,
) -> tuple[TestClient, dict[str, Any], str]:
    target_client = client or harness.client
    token = create_pending_invitation(harness, email, role)
    response = target_client.post(
        "/api/v1/auth/register",
        json={
            "token": token,
            "display_name": email.split("@")[0],
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 200
    return target_client, response.json()["data"], token


def test_password_policy_is_public(harness: AuthHarness) -> None:
    response = harness.client.get("/api/v1/auth/password-policy")

    assert response.status_code == 200
    assert response.json()["data"] == {"minimumLength": harness.settings.password_min_length}


@pytest.mark.parametrize("role", list(UserRole))
def test_all_roles_can_change_own_password_and_revoke_sessions(
    harness: AuthHarness,
    role: UserRole,
) -> None:
    client, data, _ = register_user(harness, f"change-{role.value}@example.com", role)
    with TestClient(harness.app) as other_client:
        second_login = other_client.post(
            "/api/v1/auth/login",
            json={"email": data["user"]["email"], "password": VALID_PASSWORD},
        )
        assert second_login.status_code == 200

        changed = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": VALID_PASSWORD,
                "new_password": "changed-password-456",
            },
            headers={"X-CSRF-Token": data["csrfToken"]},
        )

        assert changed.status_code == 200
        assert changed.json()["data"] == {"passwordChanged": True}
        assert client.get("/api/v1/auth/session").status_code == 401
        assert other_client.get("/api/v1/auth/session").status_code == 401

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": data["user"]["email"], "password": VALID_PASSWORD},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": data["user"]["email"], "password": "changed-password-456"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    with harness.session_factory() as db:
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.actor_user_id == data["user"]["id"],
                AuditLog.action == "auth.password.change",
            )
        )


def test_password_change_validates_csrf_current_and_new_password(harness: AuthHarness) -> None:
    client, data, _ = register_user(harness, "change-validation@example.com", UserRole.VIEWER)
    payload = {
        "current_password": VALID_PASSWORD,
        "new_password": "changed-password-456",
    }

    assert client.post("/api/v1/auth/password/change", json=payload).status_code == 403
    headers = {"X-CSRF-Token": data["csrfToken"]}
    wrong_current = client.post(
        "/api/v1/auth/password/change",
        json={**payload, "current_password": "wrong-password"},
        headers=headers,
    )
    unchanged = client.post(
        "/api/v1/auth/password/change",
        json={**payload, "new_password": VALID_PASSWORD},
        headers=headers,
    )
    too_short = client.post(
        "/api/v1/auth/password/change",
        json={**payload, "new_password": "short"},
        headers=headers,
    )

    assert wrong_current.status_code == 400
    assert wrong_current.json()["error"]["code"] == "CURRENT_PASSWORD_INVALID"
    assert unchanged.status_code == 422
    assert unchanged.json()["error"]["code"] == "PASSWORD_UNCHANGED"
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "PASSWORD_TOO_SHORT"
    assert client.get("/api/v1/auth/session").status_code == 200


def test_password_reset_request_is_generic_and_replaces_old_token(
    harness: AuthHarness,
) -> None:
    _, data, _ = register_user(harness, "reset-request@example.com", UserRole.OPERATOR)

    first = harness.client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "RESET-REQUEST@example.com"},
    )
    first_token = token_from_latest_password_reset(harness)
    second = harness.client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": data["user"]["email"]},
    )
    latest_token = token_from_latest_password_reset(harness)
    unknown = harness.client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )

    assert first.status_code == second.status_code == unknown.status_code == 200
    assert (
        first.json()["data"]
        == second.json()["data"]
        == unknown.json()["data"]
        == {"accepted": True}
    )
    assert len(harness.mail_sender.password_resets) == 2
    assert "/reset-password#token=" in harness.mail_sender.password_resets[-1]["url"]
    assert first_token != latest_token
    invalid = harness.client.post(
        "/api/v1/auth/password-reset/validate",
        json={"token": first_token},
    )
    valid = harness.client.post(
        "/api/v1/auth/password-reset/validate",
        json={"token": latest_token},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "PASSWORD_RESET_INVALID"
    assert valid.status_code == 200
    assert valid.json()["data"] == {"valid": True}
    with harness.session_factory() as db:
        latest = db.scalar(
            select(AuthActionToken).where(AuthActionToken.token_hash == hash_token(latest_token))
        )
        assert latest is not None
        assert latest.token_hash != latest_token
        assert latest.expires_at <= utc_now() + timedelta(minutes=31)


def test_password_reset_completes_once_unlocks_and_revokes_sessions(
    harness: AuthHarness,
) -> None:
    client, data, _ = register_user(harness, "reset-complete@example.com", UserRole.VIEWER)
    request_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": data["user"]["email"]},
    )
    assert request_response.status_code == 200
    token = token_from_latest_password_reset(harness)
    with harness.session_factory() as db:
        user = db.get(AppUser, data["user"]["id"])
        assert user is not None
        user.failed_login_count = harness.settings.login_max_failures
        user.locked_until = utc_now() + timedelta(minutes=15)
        db.commit()

    completed = client.post(
        "/api/v1/auth/password-reset/complete",
        json={"token": token, "new_password": "reset-password-789"},
    )

    assert completed.status_code == 200
    assert completed.json()["data"] == {"passwordReset": True}
    assert client.get("/api/v1/auth/session").status_code == 401
    reused = client.post(
        "/api/v1/auth/password-reset/complete",
        json={"token": token, "new_password": "another-password-789"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "PASSWORD_RESET_INVALID"
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": data["user"]["email"], "password": VALID_PASSWORD},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": data["user"]["email"], "password": "reset-password-789"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    with harness.session_factory() as db:
        user = db.get(AppUser, data["user"]["id"])
        assert user is not None
        assert user.failed_login_count == 0
        assert user.locked_until is None
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "auth.password.reset",
            )
        )


def test_password_reset_rejects_same_password_without_consuming_token(
    harness: AuthHarness,
) -> None:
    _, data, _ = register_user(harness, "reset-same@example.com", UserRole.VIEWER)
    harness.client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": data["user"]["email"]},
    )
    token = token_from_latest_password_reset(harness)

    unchanged = harness.client.post(
        "/api/v1/auth/password-reset/complete",
        json={"token": token, "new_password": VALID_PASSWORD},
    )

    assert unchanged.status_code == 422
    assert unchanged.json()["error"]["code"] == "PASSWORD_UNCHANGED"
    valid = harness.client.post(
        "/api/v1/auth/password-reset/validate",
        json={"token": token},
    )
    assert valid.status_code == 200


def test_password_reset_mail_failure_keeps_generic_response_and_rolls_back(
    harness: AuthHarness,
) -> None:
    _, data, _ = register_user(harness, "reset-mail-failure@example.com", UserRole.VIEWER)

    class FailingMailSender:
        def send_invitation(self, _email: str, _role: str, _url: str) -> None:
            raise AssertionError("本测试不发送邀请")

        def send_password_reset(self, _email: str, _url: str) -> None:
            raise RuntimeError("synthetic mail failure")

    original_override = harness.app.dependency_overrides[get_mail_sender]
    harness.app.dependency_overrides[get_mail_sender] = lambda: FailingMailSender()
    try:
        response = harness.client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": data["user"]["email"]},
        )
    finally:
        harness.app.dependency_overrides[get_mail_sender] = original_override

    assert response.status_code == 200
    assert response.json()["data"] == {"accepted": True}
    with harness.session_factory() as db:
        assert not db.scalars(
            select(AuthActionToken).where(
                AuthActionToken.user_id == data["user"]["id"],
                AuthActionToken.purpose == "password_reset",
            )
        ).all()


def mysql_sql(statement: Any) -> str:
    """使用 MySQL 方言验证锁定读契约，不连接真实数据库。"""
    return str(
        statement.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()


class MysqlInvitationLockScope:
    """为同一用户提供独立的用户锁和多邀请行锁。"""

    def __init__(self) -> None:
        self.user_lock = Lock()
        self.invitation_locks: dict[int, Lock] = {}
        self.guard = Lock()

    def invitation_lock(self, invitation_id: int) -> Lock:
        with self.guard:
            return self.invitation_locks.setdefault(invitation_id, Lock())


class MysqlInvitationRaceSession:
    """用多资源进程锁为两个 SQLite Session 模拟 MySQL 锁序。"""

    def __init__(
        self,
        db: Session,
        lock_scope: MysqlInvitationLockScope,
        waiting: Event,
        operation_ready: Event,
        release_operation: Event,
        pause_after: str,
    ) -> None:
        self.db = db
        self.lock_scope = lock_scope
        self.waiting = waiting
        self.operation_ready = operation_ready
        self.release_operation = release_operation
        self.pause_after = pause_after
        self.owned_locks: list[tuple[str, Lock]] = []
        self.lock_sequence: list[str] = []
        self.statements: list[Any] = []

    def _acquire_lock(self, name: str, lock: Lock) -> bool:
        if any(owned_name == name for owned_name, _owned in self.owned_locks):
            return False
        if not lock.acquire(blocking=False):
            self.waiting.set()
            lock.acquire()
        if not self.owned_locks:
            # MySQL 锁定读读取最新提交值，重开 SQLite 快照模拟该语义。
            self.db.rollback()
        self.owned_locks.append((name, lock))
        self.lock_sequence.append(name)
        return True

    def scalar(self, statement: Any) -> Any:
        self.statements.append(statement)
        compiled = mysql_sql(statement)
        is_user_lock = (
            getattr(statement, "_for_update_arg", None) is not None and "FROM APP_USER" in compiled
        )
        acquired = self._acquire_lock("user", self.lock_scope.user_lock) if is_user_lock else False
        result = self.db.scalar(statement)
        if acquired and self.pause_after == "user":
            self.operation_ready.set()
            assert self.release_operation.wait(timeout=5)
        return result

    def scalars(self, statement: Any) -> Any:
        self.statements.append(statement)
        locked = getattr(statement, "_for_update_arg", None) is not None
        rows = list(self.db.scalars(statement).all())
        if locked:
            assert self.lock_sequence and self.lock_sequence[0] == "user"
            for row in sorted(rows, key=lambda item: item.id):
                self._acquire_lock(
                    f"invitation:{row.id}",
                    self.lock_scope.invitation_lock(row.id),
                )
            if self.pause_after == "invitations":
                self.operation_ready.set()
                assert self.release_operation.wait(timeout=5)
        return SimpleNamespace(all=lambda: rows)

    def execute(self, statement: Any) -> Any:
        self.statements.append(statement)
        is_token_update = mysql_sql(statement).lstrip().startswith("UPDATE AUTH_ACTION_TOKEN")
        if is_token_update:
            assert self.lock_sequence and self.lock_sequence[0] == "user"
            assert any(name.startswith("invitation:") for name in self.lock_sequence)
        result = self.db.execute(statement)
        if is_token_update and self.pause_after == "update":
            self.operation_ready.set()
            assert self.release_operation.wait(timeout=5)
        return result

    def get(self, model: Any, identity: int) -> Any:
        return self.db.get(model, identity)

    def add(self, instance: Any) -> None:
        self.db.add(instance)

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        try:
            self.db.commit()
        finally:
            self._release()

    def rollback(self) -> None:
        try:
            self.db.rollback()
        finally:
            self._release()

    def refresh(self, instance: Any) -> None:
        self.db.refresh(instance)

    def close(self) -> None:
        try:
            self.db.close()
        finally:
            self._release()

    def _release(self) -> None:
        while self.owned_locks:
            _name, lock = self.owned_locks.pop()
            lock.release()


def create_invitation_race_database(
    tmp_path: Path,
    database_name: str,
) -> tuple[Any, Any, int, int, str]:
    """创建同一用户含两条邀请的隔离 SQLite 竞态模型。"""
    engine = create_engine(f"sqlite:///{(tmp_path / database_name).as_posix()}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    raw_token = f"{database_name}-invitation-token"
    with session_factory() as db:
        user = AppUser(
            email=f"{database_name}@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.INVITED,
            failed_login_count=0,
        )
        db.add(user)
        db.flush()
        db.add(
            AuthActionToken(
                user_id=user.id,
                email=user.email,
                purpose="invitation",
                token_hash=hash_token(f"{database_name}-older-token"),
                expires_at=utc_now() + timedelta(hours=1),
                created_by=user.id,
            )
        )
        db.flush()
        invitation = AuthActionToken(
            user_id=user.id,
            email=user.email,
            purpose="invitation",
            token_hash=hash_token(raw_token),
            expires_at=utc_now() + timedelta(hours=1),
            created_by=user.id,
        )
        db.add(invitation)
        db.commit()
        return engine, session_factory, invitation.id, user.id, raw_token


def test_authenticate_user_locks_normalized_email_and_hides_unknown_user(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CapturingSession:
        statement: Any = None

        def scalar(self, statement: Any) -> None:
            self.statement = statement
            return None

    session = CapturingSession()
    verify_password = Mock(return_value=False)
    monkeypatch.setattr(
        "backend.app.services.auth_service.verify_password",
        verify_password,
    )

    with pytest.raises(ApiError) as error:
        authenticate_user(
            cast(Session, session),
            " Unknown@Example.com ",
            "wrong-password",
            harness.settings,
            None,
            "request-unknown-login",
        )

    assert error.value.status_code == 401
    assert error.value.code == "LOGIN_FAILED"
    compiled = mysql_sql(session.statement)
    assert "FOR UPDATE" in compiled
    assert "unknown@example.com" in compiled.lower()
    verify_password.assert_called_once_with("wrong-password", DUMMY_PASSWORD_HASH)


def test_concurrent_invalid_logins_reach_lock_threshold(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """并发失败登录必须串行累加，不能用旧计数覆盖新计数。"""
    user = AppUser(
        id=1,
        email="locked@example.com",
        password_hash="synthetic-hash",
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    row_lock = Lock()
    start = Barrier(harness.settings.login_max_failures)

    class LockingSession:
        owns_lock = False

        def scalar(self, statement: Any) -> AppUser:
            if "FOR UPDATE" not in mysql_sql(statement):
                raise AssertionError("登录查询必须使用锁定读")
            row_lock.acquire()
            self.owns_lock = True
            return user

        def commit(self) -> None:
            self.close()

        def add(self, _instance: Any) -> None:
            return None

        def close(self) -> None:
            if self.owns_lock:
                self.owns_lock = False
                row_lock.release()

    monkeypatch.setattr(
        "backend.app.services.auth_service.verify_password",
        lambda _password, _password_hash: False,
    )

    def fail_login() -> str:
        session = LockingSession()
        start.wait()
        try:
            authenticate_user(
                cast(Session, session),
                user.email,
                "wrong-password",
                harness.settings,
                None,
                "request-failed-login",
            )
        except ApiError as error:
            return error.code
        finally:
            session.close()
        raise AssertionError("错误密码不应登录成功")

    with ThreadPoolExecutor(max_workers=harness.settings.login_max_failures) as executor:
        results = [
            future.result(timeout=5)
            for future in [
                executor.submit(fail_login) for _ in range(harness.settings.login_max_failures)
            ]
        ]

    assert results == ["LOGIN_FAILED"] * harness.settings.login_max_failures
    assert user.failed_login_count == harness.settings.login_max_failures
    assert user.locked_until is not None


def test_invitation_register_session_and_sensitive_values(harness: AuthHarness) -> None:
    client, data, raw_invitation = register_user(harness, "Admin@Example.com", UserRole.ADMIN)
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["role"] == "admin"

    session_response = client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["data"]["csrfToken"] == data["csrfToken"]

    raw_session = client.cookies.get("jijia_session")
    raw_csrf = client.cookies.get("jijia_session_csrf")
    with harness.session_factory() as db:
        user = db.scalar(select(AppUser).where(AppUser.email == "admin@example.com"))
        invitation = db.scalar(select(AuthActionToken))
        session = db.scalar(select(UserSession))
        assert user is not None and user.password_hash != VALID_PASSWORD
        assert invitation is not None and invitation.token_hash != raw_invitation
        assert session is not None and session.session_hash != raw_session
        assert session.csrf_hash != raw_csrf
        assert len(invitation.token_hash) == 64
        assert len(session.session_hash) == 64
        assert len(session.csrf_hash) == 64


def test_session_recovery_keeps_csrf_valid_in_other_tab(harness: AuthHarness) -> None:
    first_tab, data, _ = register_user(harness, "tabs@example.com", UserRole.OPERATOR)
    second_tab = TestClient(harness.app)
    second_tab.cookies.update(first_tab.cookies)

    with second_tab:
        restored = second_tab.get("/api/v1/auth/session")
        assert restored.status_code == 200
        assert restored.json()["data"]["csrfToken"] == data["csrfToken"]

    logout = first_tab.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": data["csrfToken"]},
    )
    assert logout.status_code == 200


def test_recent_session_auth_reads_once_without_commit(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """近期会话只读取一次会话与用户，不写入活动时间。"""
    client, _, _ = register_user(harness, "recent@example.com", UserRole.ADMIN)
    engine = harness.session_factory.kw["bind"]
    statements: list[str] = []

    def capture_statement(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        statements.append(statement.upper())

    def reject_commit(_db: Session) -> None:
        raise AssertionError("近期会话请求不应提交写事务")

    event.listen(engine, "before_cursor_execute", capture_statement)
    monkeypatch.setattr(Session, "commit", reject_commit)
    try:
        response = client.get("/api/v1/auth/me")
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)

    assert response.status_code == 200
    auth_reads = [
        statement
        for statement in statements
        if "FROM USER_SESSION" in statement or "JOIN APP_USER" in statement
    ]
    assert len(auth_reads) == 1
    assert "JOIN APP_USER" in auth_reads[0]


def test_session_activity_touch_does_not_flush_loaded_session(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """重复认证请求不得走会触发 MySQL 陈旧行检查的 ORM 实例更新。"""
    client, _, _ = register_user(harness, "race@example.com", UserRole.ADMIN)
    previous_seen_at = utc_now() - timedelta(minutes=10)
    with harness.session_factory() as db:
        session = db.scalar(select(UserSession))
        assert session is not None
        session.last_seen_at = previous_seen_at
        db.commit()
    original_commit = Session.commit
    commit_count = 0

    def reject_user_session_orm_update(db: Session) -> None:
        nonlocal commit_count
        if any(isinstance(instance, UserSession) for instance in db.dirty):
            raise StaleDataError("synthetic concurrent session update")
        commit_count += 1
        original_commit(db)

    monkeypatch.setattr(Session, "commit", reject_user_session_orm_update)

    responses = [client.get("/api/v1/users") for _ in range(2)]

    assert [response.status_code for response in responses] == [200, 200]
    assert commit_count == 1
    with harness.session_factory() as db:
        session = db.scalar(select(UserSession))
        assert session is not None
        assert session.last_seen_at > previous_seen_at


def test_session_activity_touch_keeps_newer_out_of_order_update(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """较旧请求晚提交时不得让会话活动时间倒退。"""
    client, _, _ = register_user(harness, "order@example.com", UserRole.ADMIN)
    newer_seen_at = utc_now() + timedelta(minutes=2)
    older_seen_at = newer_seen_at - timedelta(minutes=1)
    moments = iter((newer_seen_at, older_seen_at))
    monkeypatch.setattr("backend.app.api.deps.utc_now", lambda: next(moments))

    responses = [client.get("/api/v1/users") for _ in range(2)]

    assert [response.status_code for response in responses] == [200, 200]
    with harness.session_factory() as db:
        session = db.scalar(select(UserSession))
        assert session is not None
        assert session.last_seen_at == newer_seen_at
        assert session.idle_expires_at == min(
            newer_seen_at + timedelta(minutes=harness.settings.session_idle_minutes),
            session.expires_at,
        )


def test_expired_revoked_and_used_invitations_are_rejected(harness: AuthHarness) -> None:
    expired_token = create_pending_invitation(harness, "expired@example.com", UserRole.VIEWER)
    with harness.session_factory() as db:
        invitation = db.scalar(
            select(AuthActionToken).where(AuthActionToken.email == "expired@example.com")
        )
        assert invitation is not None
        invitation.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()
    response = harness.client.post(
        "/api/v1/auth/invitations/validate", json={"token": expired_token}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVITATION_EXPIRED"

    revoked_token = create_pending_invitation(harness, "revoked@example.com", UserRole.OPERATOR)
    with harness.session_factory() as db:
        invitation = db.scalar(
            select(AuthActionToken).where(AuthActionToken.email == "revoked@example.com")
        )
        assert invitation is not None
        invitation.revoked_at = utc_now()
        db.commit()
    response = harness.client.post(
        "/api/v1/auth/invitations/validate", json={"token": revoked_token}
    )
    assert response.json()["error"]["code"] == "INVITATION_REVOKED"

    _, _, used_token = register_user(harness, "used@example.com", UserRole.VIEWER)
    response = harness.client.post("/api/v1/auth/invitations/validate", json={"token": used_token})
    assert response.json()["error"]["code"] == "INVITATION_USED"


def test_revoke_invitation_uses_mysql_current_locking_read() -> None:
    invitation = AuthActionToken(
        id=17,
        user_id=9,
        email="used-invitation@example.com",
        purpose="invitation",
        token_hash="b" * 64,
        expires_at=utc_now() + timedelta(hours=1),
        used_at=utc_now(),
    )
    user = AppUser(
        id=invitation.user_id,
        email=invitation.email,
        role=UserRole.VIEWER,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )

    class ScalarRows:
        def all(self) -> list[AuthActionToken]:
            return [invitation]

    class CapturingSession:
        statements: list[Any] = []
        lock_sequence: list[str] = []

        def scalar(self, statement: Any) -> int | AppUser:
            self.statements.append(statement)
            compiled = mysql_sql(statement)
            if "FROM APP_USER" in compiled:
                self.lock_sequence.append("user")
                return user
            return invitation.user_id

        def scalars(self, statement: Any) -> ScalarRows:
            self.statements.append(statement)
            self.lock_sequence.append("invitations")
            return ScalarRows()

    session = CapturingSession()
    with pytest.raises(ApiError) as error:
        revoke_invitation(
            cast(Session, session),
            invitation.id,
            actor_id=3,
            request_id="request-revoke-lock",
        )

    assert error.value.status_code == 409
    assert error.value.code == "INVITATION_USED"
    discovery_sql, user_sql, invitations_sql = map(mysql_sql, session.statements)
    assert "FOR UPDATE" not in discovery_sql
    assert "AUTH_ACTION_TOKEN.ID = 17" in discovery_sql
    assert "AUTH_ACTION_TOKEN.PURPOSE = 'INVITATION'" in discovery_sql
    assert "FROM APP_USER" in user_sql and "FOR UPDATE" in user_sql
    assert "FOR UPDATE" in invitations_sql
    assert "ORDER BY AUTH_ACTION_TOKEN.ID" in invitations_sql
    assert session.lock_sequence == ["user", "invitations"]


def test_revoke_invitation_preserves_used_and_revoked_semantics(
    harness: AuthHarness,
) -> None:
    create_pending_invitation(harness, "used-revoke@example.com", UserRole.VIEWER)
    with harness.session_factory() as db:
        used = db.scalar(
            select(AuthActionToken).where(AuthActionToken.email == "used-revoke@example.com")
        )
        assert used is not None
        used.used_at = utc_now()
        db.commit()
        used_id = used.id
        actor_id = used.user_id

    with harness.session_factory() as db:
        with pytest.raises(ApiError) as error:
            revoke_invitation(db, used_id, actor_id, "request-used-revoke")
        assert error.value.status_code == 409
        assert error.value.code == "INVITATION_USED"
        db.rollback()
    with harness.session_factory() as db:
        assert (
            db.scalar(select(AuditLog).where(AuditLog.request_id == "request-used-revoke")) is None
        )

    create_pending_invitation(harness, "revoked-again@example.com", UserRole.VIEWER)
    revoked_at = utc_now()
    with harness.session_factory() as db:
        revoked = db.scalar(
            select(AuthActionToken).where(AuthActionToken.email == "revoked-again@example.com")
        )
        assert revoked is not None
        revoked.revoked_at = revoked_at
        db.commit()
        revoked_id = revoked.id
        actor_id = revoked.user_id

    with harness.session_factory() as db:
        result = revoke_invitation(db, revoked_id, actor_id, "request-revoked-again")
        assert result.revoked_at == revoked_at
    with harness.session_factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.request_id == "request-revoked-again"))
        assert audit is not None and audit.result == "success"


def test_registration_lock_wins_over_concurrent_revoke(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine, session_factory, invitation_id, actor_id, raw_token = create_invitation_race_database(
        tmp_path, "register-first"
    )
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password",
        lambda _password: "synthetic-password-hash",
    )
    lock_scope = MysqlInvitationLockScope()
    registration_waiting = Event()
    registration_consumed = Event()
    release_registration = Event()
    revoke_waiting = Event()

    def register_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            registration_waiting,
            registration_consumed,
            release_registration,
            "update",
        )
        try:
            register_user_service(
                cast(Session, session),
                raw_token,
                "registered user",
                VALID_PASSWORD,
                harness.settings,
                None,
            )
        finally:
            session.close()

    def revoke_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            revoke_waiting,
            Event(),
            Event(),
            "none",
        )
        try:
            revoke_invitation(
                cast(Session, session),
                invitation_id,
                actor_id,
                "request-register-first-revoke",
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            registration = executor.submit(register_once)
            assert registration_consumed.wait(timeout=5)
            revocation = executor.submit(revoke_once)
            try:
                assert revoke_waiting.wait(timeout=5)
            finally:
                release_registration.set()
            registration.result(timeout=5)
            with pytest.raises(ApiError) as error:
                revocation.result(timeout=5)
            assert error.value.status_code == 409
            assert error.value.code == "INVITATION_USED"

        with session_factory() as db:
            invitation = db.get(AuthActionToken, invitation_id)
            user = db.get(AppUser, actor_id)
            sessions = db.scalars(select(UserSession)).all()
            revoke_audits = db.scalars(
                select(AuditLog).where(
                    AuditLog.action == "invitation.revoke",
                    AuditLog.result == "success",
                )
            ).all()
            assert invitation is not None
            assert invitation.used_at is not None
            assert invitation.revoked_at is None
            assert not (invitation.used_at is not None and invitation.revoked_at is not None)
            assert user is not None and user.status == UserStatus.ACTIVE
            assert len(sessions) == 1
            assert revoke_audits == []
    finally:
        release_registration.set()
        engine.dispose()


def test_revoke_lock_wins_over_concurrent_registration(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine, session_factory, invitation_id, actor_id, raw_token = create_invitation_race_database(
        tmp_path, "revoke-first"
    )
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password",
        lambda _password: "synthetic-password-hash",
    )
    lock_scope = MysqlInvitationLockScope()
    revoke_waiting = Event()
    revoke_read = Event()
    release_revoke = Event()
    registration_waiting = Event()

    def revoke_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            revoke_waiting,
            revoke_read,
            release_revoke,
            "invitations",
        )
        try:
            revoke_invitation(
                cast(Session, session),
                invitation_id,
                actor_id,
                "request-revoke-first",
            )
        finally:
            session.close()

    def register_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            registration_waiting,
            Event(),
            Event(),
            "none",
        )
        try:
            register_user_service(
                cast(Session, session),
                raw_token,
                "registered user",
                VALID_PASSWORD,
                harness.settings,
                None,
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            revocation = executor.submit(revoke_once)
            assert revoke_read.wait(timeout=5)
            registration = executor.submit(register_once)
            try:
                assert registration_waiting.wait(timeout=5)
            finally:
                release_revoke.set()
            revocation.result(timeout=5)
            with pytest.raises(ApiError) as error:
                registration.result(timeout=5)
            assert error.value.status_code == 400
            assert error.value.code == "INVITATION_REVOKED"

        with session_factory() as db:
            invitation = db.get(AuthActionToken, invitation_id)
            user = db.get(AppUser, actor_id)
            sessions = db.scalars(select(UserSession)).all()
            revoke_audits = db.scalars(
                select(AuditLog).where(
                    AuditLog.action == "invitation.revoke",
                    AuditLog.result == "success",
                )
            ).all()
            assert invitation is not None
            assert invitation.used_at is None
            assert invitation.revoked_at is not None
            assert not (invitation.used_at is not None and invitation.revoked_at is not None)
            assert user is not None and user.status == UserStatus.INVITED
            assert sessions == []
            assert len(revoke_audits) == 1
    finally:
        release_revoke.set()
        engine.dispose()


def test_registration_lock_wins_over_concurrent_resend(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine, session_factory, invitation_id, actor_id, raw_token = create_invitation_race_database(
        tmp_path, "register-first-resend"
    )
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password",
        lambda _password: "synthetic-password-hash",
    )
    lock_scope = MysqlInvitationLockScope()
    registration_consumed = Event()
    release_registration = Event()
    resend_waiting = Event()
    sessions: dict[str, MysqlInvitationRaceSession] = {}

    def register_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            Event(),
            registration_consumed,
            release_registration,
            "update",
        )
        sessions["register"] = session
        try:
            register_user_service(
                cast(Session, session),
                raw_token,
                "registered user",
                VALID_PASSWORD,
                harness.settings,
                None,
            )
        finally:
            session.close()

    def resend_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            resend_waiting,
            Event(),
            Event(),
            "none",
        )
        sessions["resend"] = session
        try:
            resend_invitation(
                cast(Session, session),
                invitation_id,
                actor_id,
                harness.settings,
                harness.mail_sender,
                "request-register-first-resend",
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            registration = executor.submit(register_once)
            assert registration_consumed.wait(timeout=5)
            registration_locks = sessions["register"].lock_sequence
            assert registration_locks[0] == "user"
            assert len([name for name in registration_locks if name.startswith("invitation:")]) == 2
            resend = executor.submit(resend_once)
            try:
                assert resend_waiting.wait(timeout=5)
                assert sessions["resend"].lock_sequence == []
            finally:
                release_registration.set()
            registration.result(timeout=5)
            with pytest.raises(ApiError) as error:
                resend.result(timeout=5)
            assert error.value.status_code == 409
            assert error.value.code == "INVITATION_NOT_PENDING"

        discovery_sql, user_sql, invitations_sql, consume_sql = map(
            mysql_sql,
            sessions["register"].statements,
        )
        assert "FOR UPDATE" not in discovery_sql
        assert "FROM APP_USER" in user_sql and "FOR UPDATE" in user_sql
        assert "ORDER BY AUTH_ACTION_TOKEN.ID" in invitations_sql
        assert "FOR UPDATE" in invitations_sql
        assert consume_sql.lstrip().startswith("UPDATE AUTH_ACTION_TOKEN")
        assert "AUTH_ACTION_TOKEN.ID =" in consume_sql
        assert "AUTH_ACTION_TOKEN.TOKEN_HASH =" in consume_sql
        assert "AUTH_ACTION_TOKEN.USED_AT IS NULL" in consume_sql
        assert "AUTH_ACTION_TOKEN.REVOKED_AT IS NULL" in consume_sql

        with session_factory() as db:
            invitations = db.scalars(
                select(AuthActionToken)
                .where(AuthActionToken.user_id == actor_id)
                .order_by(AuthActionToken.id)
            ).all()
            sessions_rows = db.scalars(select(UserSession)).all()
            resend_audits = db.scalars(
                select(AuditLog).where(AuditLog.action == "invitation.resend")
            ).all()
            assert len(invitations) == 2
            assert invitations[-1].used_at is not None
            assert invitations[-1].revoked_at is None
            assert invitations[0].revoked_at is not None
            assert len(sessions_rows) == 1
            assert resend_audits == []
            assert harness.mail_sender.invitations == []
    finally:
        release_registration.set()
        engine.dispose()


def test_resend_lock_wins_over_concurrent_registration(
    harness: AuthHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine, session_factory, invitation_id, actor_id, raw_token = create_invitation_race_database(
        tmp_path, "resend-first-register"
    )
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password",
        lambda _password: "synthetic-password-hash",
    )
    lock_scope = MysqlInvitationLockScope()
    resend_locked = Event()
    release_resend = Event()
    registration_waiting = Event()
    sessions: dict[str, MysqlInvitationRaceSession] = {}

    def resend_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            Event(),
            resend_locked,
            release_resend,
            "invitations",
        )
        sessions["resend"] = session
        try:
            resend_invitation(
                cast(Session, session),
                invitation_id,
                actor_id,
                harness.settings,
                harness.mail_sender,
                "request-resend-first",
            )
        finally:
            session.close()

    def register_once() -> None:
        session = MysqlInvitationRaceSession(
            session_factory(),
            lock_scope,
            registration_waiting,
            Event(),
            Event(),
            "none",
        )
        sessions["register"] = session
        try:
            register_user_service(
                cast(Session, session),
                raw_token,
                "registered user",
                VALID_PASSWORD,
                harness.settings,
                None,
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            resend = executor.submit(resend_once)
            assert resend_locked.wait(timeout=5)
            resend_locks = sessions["resend"].lock_sequence
            assert resend_locks[0] == "user"
            assert len([name for name in resend_locks if name.startswith("invitation:")]) == 2
            registration = executor.submit(register_once)
            try:
                assert registration_waiting.wait(timeout=5)
                assert sessions["register"].lock_sequence == []
            finally:
                release_resend.set()
            resend.result(timeout=5)
            with pytest.raises(ApiError) as error:
                registration.result(timeout=5)
            assert error.value.status_code == 400
            assert error.value.code == "INVITATION_REVOKED"

        with session_factory() as db:
            invitations = db.scalars(
                select(AuthActionToken)
                .where(AuthActionToken.user_id == actor_id)
                .order_by(AuthActionToken.id)
            ).all()
            sessions_rows = db.scalars(select(UserSession)).all()
            resend_audits = db.scalars(
                select(AuditLog).where(AuditLog.action == "invitation.resend")
            ).all()
            active = [
                item for item in invitations if item.used_at is None and item.revoked_at is None
            ]
            assert len(invitations) == 3
            assert invitations[1].revoked_at is not None
            assert invitations[1].used_at is None
            assert len(active) == 1 and active[0].id == invitations[-1].id
            assert sessions_rows == []
            assert len(resend_audits) == 1
            assert len(harness.mail_sender.invitations) == 1
    finally:
        release_resend.set()
        engine.dispose()


def test_login_lock_session_expiry_and_logout_csrf(harness: AuthHarness) -> None:
    client, data, _ = register_user(harness, "user@example.com", UserRole.OPERATOR)
    csrf_token = data["csrfToken"]

    missing_csrf = client.post("/api/v1/auth/logout")
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_INVALID"

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 401

    for _ in range(harness.settings.login_max_failures):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
    locked = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": VALID_PASSWORD},
    )
    assert locked.status_code == 423

    with harness.session_factory() as db:
        user = db.scalar(select(AppUser).where(AppUser.email == "user@example.com"))
        assert user is not None
        user.locked_until = None
        user.failed_login_count = 0
        db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": VALID_PASSWORD},
    )
    assert login.status_code == 200
    with harness.session_factory() as db:
        session = db.scalar(select(UserSession).order_by(UserSession.id.desc()).limit(1))
        assert session is not None
        session.idle_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401


def test_admin_can_invite_and_viewer_cannot_manage_members(harness: AuthHarness) -> None:
    admin_client, admin_data, _ = register_user(harness, "admin@example.com", UserRole.ADMIN)
    admin_csrf = admin_data["csrfToken"]

    invite = admin_client.post(
        "/api/v1/invitations",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert invite.status_code == 200
    assert invite.json()["data"]["role"] == "viewer"
    assert admin_client.get("/api/v1/users").status_code == 200

    with TestClient(harness.app) as viewer_client:
        viewer_token = token_from_latest_mail(harness)
        registered = viewer_client.post(
            "/api/v1/auth/register",
            json={
                "token": viewer_token,
                "display_name": "查看者",
                "password": VALID_PASSWORD,
            },
        )
        viewer_csrf = registered.json()["data"]["csrfToken"]
        assert viewer_client.get("/api/v1/users").status_code == 403
        forbidden = viewer_client.post(
            "/api/v1/invitations",
            json={"email": "other@example.com", "role": "operator"},
            headers={"X-CSRF-Token": viewer_csrf},
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "PERMISSION_DENIED"


def test_repeated_resend_of_old_invitation_keeps_only_latest_token(
    harness: AuthHarness,
) -> None:
    admin_client, admin_data, _ = register_user(
        harness,
        "resend-admin@example.com",
        UserRole.ADMIN,
    )
    headers = {"X-CSRF-Token": admin_data["csrfToken"]}
    created = admin_client.post(
        "/api/v1/invitations",
        json={"email": "resend-target@example.com", "role": "viewer"},
        headers=headers,
    )
    assert created.status_code == 200
    original_id = created.json()["data"]["id"]

    first = admin_client.post(
        f"/api/v1/invitations/{original_id}/resend",
        headers=headers,
    )
    assert first.status_code == 200
    first_replacement = token_from_latest_mail(harness)
    second = admin_client.post(
        f"/api/v1/invitations/{original_id}/resend",
        headers=headers,
    )
    assert second.status_code == 200
    latest_replacement = token_from_latest_mail(harness)

    revoked = admin_client.post(
        "/api/v1/auth/invitations/validate",
        json={"token": first_replacement},
    )
    assert revoked.status_code == 400
    assert revoked.json()["error"]["code"] == "INVITATION_REVOKED"
    assert (
        admin_client.post(
            "/api/v1/auth/invitations/validate",
            json={"token": latest_replacement},
        ).status_code
        == 200
    )

    with harness.session_factory() as db:
        target = db.scalar(select(AppUser).where(AppUser.email == "resend-target@example.com"))
        assert target is not None
        invitations = db.scalars(
            select(AuthActionToken).where(
                AuthActionToken.user_id == target.id,
                AuthActionToken.purpose == "invitation",
            )
        ).all()
        active = [
            invitation
            for invitation in invitations
            if invitation.used_at is None and invitation.revoked_at is None
        ]
        assert len(active) == 1


def test_resend_invitation_locks_user_and_invitations_in_mysql_order(
    harness: AuthHarness,
) -> None:
    now = utc_now()
    invitation = AuthActionToken(
        id=1,
        user_id=7,
        email="lock-target@example.com",
        purpose="invitation",
        token_hash="a" * 64,
        expires_at=now + timedelta(hours=1),
    )
    user = AppUser(
        id=7,
        email=invitation.email,
        role=UserRole.VIEWER,
        status=UserStatus.INVITED,
        failed_login_count=0,
    )

    class ScalarRows:
        def all(self) -> list[AuthActionToken]:
            return [invitation]

    class CapturingSession:
        invitation_statement: Any = None
        user_statement: Any = None
        replacement: AuthActionToken | None = None
        lock_sequence: list[str] = []

        def scalar(self, statement: Any) -> int | AppUser | None:
            compiled = mysql_sql(statement)
            if "FROM AUTH_ACTION_TOKEN" in compiled:
                return invitation.user_id
            if "FROM APP_USER" in compiled:
                self.user_statement = statement
                self.lock_sequence.append("user")
                return user
            return None

        def scalars(self, statement: Any) -> ScalarRows:
            self.invitation_statement = statement
            self.lock_sequence.append("invitations")
            return ScalarRows()

        def get(self, _model: Any, _identity: int) -> AppUser:
            return user

        def add(self, instance: Any) -> None:
            if isinstance(instance, AuthActionToken):
                self.replacement = instance

        def flush(self) -> None:
            assert self.replacement is not None
            self.replacement.id = 2

        def commit(self) -> None:
            if self.replacement is not None and self.replacement.id is None:
                self.replacement.id = 2

        def rollback(self) -> None:
            return None

        def refresh(self, _replacement: AuthActionToken) -> None:
            return None

    session = CapturingSession()
    resend_invitation(
        cast(Session, session),
        invitation.id,
        actor_id=9,
        settings=harness.settings,
        mail_sender=harness.mail_sender,
        request_id="request-resend-lock",
    )

    invitation_sql = mysql_sql(session.invitation_statement)
    assert "FOR UPDATE" in invitation_sql
    assert "ORDER BY AUTH_ACTION_TOKEN.ID" in invitation_sql
    assert session.user_statement is not None
    assert "FOR UPDATE" in mysql_sql(session.user_statement)
    assert session.lock_sequence == ["user", "invitations"]


def test_resend_mail_failure_rolls_back_invitation_state(harness: AuthHarness) -> None:
    create_pending_invitation(harness, "mail-failure@example.com", UserRole.VIEWER)
    with harness.session_factory() as db:
        invitation = db.scalar(
            select(AuthActionToken).where(AuthActionToken.email == "mail-failure@example.com")
        )
        assert invitation is not None
        invitation_id = invitation.id
        actor_id = invitation.user_id

    class FailingMailSender:
        def send_invitation(self, _email: str, _role: str, _url: str) -> None:
            raise RuntimeError("synthetic mail failure")

    with harness.session_factory() as db:
        with pytest.raises(RuntimeError, match="synthetic mail failure"):
            resend_invitation(
                db,
                invitation_id,
                actor_id,
                harness.settings,
                FailingMailSender(),
                "request-mail-failure",
            )

    with harness.session_factory() as db:
        invitations = db.scalars(
            select(AuthActionToken).where(AuthActionToken.email == "mail-failure@example.com")
        ).all()
        assert len(invitations) == 1
        assert invitations[0].revoked_at is None
        assert (
            db.scalar(select(AuditLog).where(AuditLog.request_id == "request-mail-failure")) is None
        )


def test_concurrent_resends_deliver_only_committed_latest_token(
    tmp_path: Path,
    harness: AuthHarness,
) -> None:
    """第二个事务必须等首封邮件发送并提交后，才能生成并发送新令牌。"""
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'resend.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db:
        user = AppUser(
            email="concurrent-resend@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.INVITED,
            failed_login_count=0,
        )
        db.add(user)
        db.flush()
        invitation = AuthActionToken(
            user_id=user.id,
            email=user.email,
            purpose="invitation",
            token_hash=hash_token("original-invitation-token"),
            expires_at=utc_now() + timedelta(hours=1),
            created_by=user.id,
        )
        db.add(invitation)
        db.commit()
        invitation_id = invitation.id
        actor_id = user.id

    invitation_lock = Lock()
    second_waiting = Event()

    class MysqlLockModelSession:
        """用进程锁模拟 MySQL 锁定读，底层仍是两个独立 SQLite Session。"""

        def __init__(self, db: Session) -> None:
            self.db = db
            self.owns_lock = False

        def _acquire_for_update(self, statement: Any) -> None:
            if getattr(statement, "_for_update_arg", None) is None or self.owns_lock:
                return
            if not invitation_lock.acquire(blocking=False):
                second_waiting.set()
                invitation_lock.acquire()
            self.owns_lock = True
            # MySQL 锁定读读取最新提交值；重开 SQLite 只读快照模拟该语义。
            self.db.rollback()

        def scalar(self, statement: Any) -> Any:
            self._acquire_for_update(statement)
            return self.db.scalar(statement)

        def scalars(self, statement: Any) -> Any:
            self._acquire_for_update(statement)
            return self.db.scalars(statement)

        def add(self, instance: Any) -> None:
            self.db.add(instance)

        def flush(self) -> None:
            self.db.flush()

        def commit(self) -> None:
            try:
                self.db.commit()
            finally:
                self._release()

        def rollback(self) -> None:
            try:
                self.db.rollback()
            finally:
                self._release()

        def refresh(self, instance: Any) -> None:
            self.db.refresh(instance)

        def close(self) -> None:
            try:
                self.db.close()
            finally:
                self._release()

        def _release(self) -> None:
            if self.owns_lock:
                self.owns_lock = False
                invitation_lock.release()

    class DeferredMailSender:
        def __init__(self) -> None:
            self.first_started = Event()
            self.release_first = Event()
            self.second_started = Event()
            self.urls: list[str] = []
            self.calls_lock = Lock()

        def send_invitation(self, _email: str, _role: str, url: str) -> None:
            with self.calls_lock:
                call_index = len(self.urls)
                self.urls.append(url)
            if call_index == 0:
                self.first_started.set()
                if not self.release_first.wait(timeout=5):
                    raise TimeoutError("首封合成邮件未获放行")
            else:
                self.second_started.set()

    mail_sender = DeferredMailSender()

    def resend_once() -> None:
        db = session_factory()
        locking_db = MysqlLockModelSession(db)
        try:
            resend_invitation(
                cast(Session, locking_db),
                invitation_id,
                actor_id,
                harness.settings,
                mail_sender,
                "request-concurrent-resend",
            )
        finally:
            locking_db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(resend_once)
        assert mail_sender.first_started.wait(timeout=5)
        second = executor.submit(resend_once)
        assert second_waiting.wait(timeout=5)
        assert not mail_sender.second_started.is_set()
        mail_sender.release_first.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert mail_sender.second_started.is_set()
    assert len(mail_sender.urls) == 2
    first_token = parse_qs(urlparse(mail_sender.urls[0]).fragment)["token"][0]
    latest_token = parse_qs(urlparse(mail_sender.urls[-1]).fragment)["token"][0]
    with session_factory() as db:
        with pytest.raises(ApiError) as revoked:
            validate_invitation(db, first_token)
        assert revoked.value.code == "INVITATION_REVOKED"
        latest, _user = validate_invitation(db, latest_token)
        assert latest.revoked_at is None
    engine.dispose()


def test_self_registration_without_invitation_is_rejected(harness: AuthHarness) -> None:
    response = harness.client.post(
        "/api/v1/auth/register",
        json={
            "token": "x" * 32,
            "display_name": "未邀请用户",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVITATION_INVALID"


def test_invitation_token_can_only_be_consumed_once(harness: AuthHarness) -> None:
    token = create_pending_invitation(harness, "single-use@example.com", UserRole.VIEWER)
    first = harness.client.post(
        "/api/v1/auth/register",
        json={
            "token": token,
            "display_name": "首次注册",
            "password": VALID_PASSWORD,
        },
    )
    assert first.status_code == 200

    second = harness.client.post(
        "/api/v1/auth/register",
        json={
            "token": token,
            "display_name": "重复注册",
            "password": VALID_PASSWORD,
        },
    )
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "INVITATION_USED"


def test_last_active_admin_cannot_be_demoted_or_disabled(harness: AuthHarness) -> None:
    client, data, _ = register_user(harness, "admin@example.com", UserRole.ADMIN)
    user_id = data["user"]["id"]
    headers = {"X-CSRF-Token": data["csrfToken"]}

    demote = client.patch(
        f"/api/v1/users/{user_id}",
        json={"role": "operator"},
        headers=headers,
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"

    disable = client.patch(
        f"/api/v1/users/{user_id}",
        json={"status": "disabled"},
        headers=headers,
    )
    assert disable.status_code == 409
    assert disable.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"


def test_concurrent_admin_demotions_keep_one_active_admin() -> None:
    """两个事务同时降级管理员时，第二个必须读取第一个提交后的状态。"""
    now = utc_now()
    admins = {
        user_id: AppUser(
            id=user_id,
            email=f"admin-{user_id}@example.com",
            display_name=f"admin-{user_id}",
            password_hash="synthetic-hash",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
        )
        for user_id in (1, 2)
    }
    row_lock = Lock()
    unlocked_reads = Barrier(2)
    start = Barrier(2)

    class ScalarRows:
        def __init__(self, rows: list[AppUser]) -> None:
            self.rows = rows

        def all(self) -> list[AppUser]:
            return self.rows

    class AdminSession:
        def __init__(self, target_id: int) -> None:
            self.target_id = target_id
            self.owns_lock = False

        def scalars(self, statement: Any) -> ScalarRows:
            compiled = mysql_sql(statement)
            if "FOR UPDATE" not in compiled or "ORDER BY APP_USER.ID" not in compiled:
                raise AssertionError("管理员集合必须按主键顺序锁定")
            row_lock.acquire()
            self.owns_lock = True
            return ScalarRows(
                [
                    user
                    for user in admins.values()
                    if user.role == UserRole.ADMIN and user.status == UserStatus.ACTIVE
                ]
            )

        def scalar(self, _statement: Any) -> int:
            count = sum(
                user.id != self.target_id
                and user.role == UserRole.ADMIN
                and user.status == UserStatus.ACTIVE
                for user in admins.values()
            )
            unlocked_reads.wait()
            return count

        def get(self, _model: Any, user_id: int) -> AppUser | None:
            return admins.get(user_id)

        def commit(self) -> None:
            self.close()

        def add(self, _instance: Any) -> None:
            return None

        def refresh(self, _user: AppUser) -> None:
            return None

        def close(self) -> None:
            if self.owns_lock:
                self.owns_lock = False
                row_lock.release()

    def demote(user_id: int) -> str:
        session = AdminSession(user_id)
        request = SimpleNamespace(state=SimpleNamespace(request_id=f"request-{user_id}"))
        start.wait()
        try:
            update_user(
                user_id,
                UserUpdateRequest(role=UserRole.OPERATOR),
                cast(Request, request),
                cast(Session, session),
                cast(Any, SimpleNamespace(user=admins[user_id])),
            )
            return "updated"
        except ApiError as error:
            return error.code
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=5)
            for future in [executor.submit(demote, user_id) for user_id in admins]
        ]

    assert sorted(results) == ["LAST_ADMIN_REQUIRED", "updated"]
    assert (
        sum(
            user.role == UserRole.ADMIN and user.status == UserStatus.ACTIVE
            for user in admins.values()
        )
        == 1
    )
