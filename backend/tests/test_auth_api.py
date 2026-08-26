from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.security import utc_now
from backend.app.models.auth_action_token import AuthActionToken
from backend.app.models.user import AppUser, UserRole
from backend.app.models.user_session import UserSession
from backend.app.services.auth_service import create_invitation
from backend.tests.conftest import AuthHarness

VALID_PASSWORD = "correct-password-123"


def token_from_latest_mail(harness: AuthHarness) -> str:
    url = harness.mail_sender.invitations[-1]["url"]
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
        )
    return token_from_latest_mail(harness)


def register_user(
    harness: AuthHarness,
    email: str,
    role: UserRole,
    client: TestClient | None = None,
) -> tuple[TestClient, dict[str, object], str]:
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


def test_invitation_register_session_and_sensitive_values(harness: AuthHarness) -> None:
    client, data, raw_invitation = register_user(harness, "Admin@Example.com", UserRole.ADMIN)
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["role"] == "admin"

    session_response = client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["data"]["csrfToken"] != data["csrfToken"]

    raw_session = client.cookies.get("jijia_session")
    with harness.session_factory() as db:
        user = db.scalar(select(AppUser).where(AppUser.email == "admin@example.com"))
        invitation = db.scalar(select(AuthActionToken))
        session = db.scalar(select(UserSession))
        assert user is not None and user.password_hash != VALID_PASSWORD
        assert invitation is not None and invitation.token_hash != raw_invitation
        assert session is not None and session.session_hash != raw_session
        assert len(invitation.token_hash) == 64
        assert len(session.session_hash) == 64


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
