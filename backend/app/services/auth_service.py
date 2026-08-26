from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.config import WebSettings
from backend.app.core.errors import ApiError
from backend.app.core.security import (
    DUMMY_PASSWORD_HASH,
    generate_token,
    hash_password,
    hash_token,
    normalize_email,
    password_hasher,
    utc_now,
    verify_password,
)
from backend.app.models.auth_action_token import AuthActionToken
from backend.app.models.user import AppUser, UserRole, UserStatus
from backend.app.models.user_session import UserSession
from backend.app.services.mail_service import MailSender


@dataclass(frozen=True)
class SessionCredentials:
    """只在当前请求内传递 Session 和 CSRF 原始令牌。"""

    session_token: str
    csrf_token: str
    session: UserSession


def create_invitation(
    db: Session,
    email: str,
    role: UserRole,
    created_by: int | None,
    settings: WebSettings,
    mail_sender: MailSender,
) -> AuthActionToken:
    """创建受邀用户和一次性邀请，令牌原文只发送一次。"""
    normalized_email = normalize_email(email)
    existing_user = db.scalar(select(AppUser).where(AppUser.email == normalized_email))
    if existing_user is not None:
        raise ApiError(409, "USER_ALREADY_EXISTS", "该邮箱已经存在")

    user = AppUser(
        email=normalized_email,
        role=role,
        status=UserStatus.INVITED,
    )
    db.add(user)
    db.flush()

    raw_token = generate_token()
    invitation = AuthActionToken(
        user_id=user.id,
        email=normalized_email,
        purpose="invitation",
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.invitation_ttl_hours),
        created_by=created_by,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    invitation_url = f"{settings.public_web_url.rstrip('/')}/register#token={quote(raw_token)}"
    mail_sender.send_invitation(normalized_email, role.value, invitation_url)
    return invitation


def validate_invitation(db: Session, raw_token: str) -> tuple[AuthActionToken, AppUser]:
    """验证邀请存在、未撤销、未使用且仍在有效期内。"""
    invitation = db.scalar(
        select(AuthActionToken).where(
            AuthActionToken.token_hash == hash_token(raw_token),
            AuthActionToken.purpose == "invitation",
        )
    )
    if invitation is None:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")
    if invitation.revoked_at is not None:
        raise ApiError(400, "INVITATION_REVOKED", "邀请已撤销")
    if invitation.used_at is not None:
        raise ApiError(400, "INVITATION_USED", "邀请已使用")
    if invitation.expires_at <= utc_now():
        raise ApiError(400, "INVITATION_EXPIRED", "邀请已过期")

    user = db.get(AppUser, invitation.user_id)
    if user is None or user.status != UserStatus.INVITED:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")
    return invitation, user


def register_user(
    db: Session,
    raw_token: str,
    display_name: str,
    password: str,
    settings: WebSettings,
    user_agent: str | None,
) -> tuple[AppUser, SessionCredentials]:
    """使用有效邀请激活用户，并立即创建服务端 Session。"""
    if len(password) < settings.password_min_length:
        raise ApiError(
            422,
            "PASSWORD_TOO_SHORT",
            f"密码至少需要 {settings.password_min_length} 位",
        )

    invitation, user = validate_invitation(db, raw_token)
    now = utc_now()
    user.display_name = display_name.strip()
    user.password_hash = hash_password(password)
    user.status = UserStatus.ACTIVE
    user.failed_login_count = 0
    invitation.used_at = now
    db.execute(
        update(AuthActionToken)
        .where(
            AuthActionToken.user_id == user.id,
            AuthActionToken.id != invitation.id,
            AuthActionToken.used_at.is_(None),
            AuthActionToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    credentials = create_user_session(db, user.id, settings, user_agent)
    db.commit()
    db.refresh(user)
    return user, credentials


def authenticate_user(
    db: Session,
    email: str,
    password: str,
    settings: WebSettings,
    user_agent: str | None,
) -> tuple[AppUser, SessionCredentials]:
    """验证邮箱密码，记录连续失败并在成功后创建 Session。"""
    normalized_email = normalize_email(email)
    user = db.scalar(select(AppUser).where(AppUser.email == normalized_email))
    now = utc_now()

    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise ApiError(401, "LOGIN_FAILED", "邮箱或密码错误")
    if user.locked_until is not None and user.locked_until > now:
        raise ApiError(423, "LOGIN_LOCKED", "登录暂时锁定，请稍后重试")

    candidate_hash = user.password_hash or DUMMY_PASSWORD_HASH
    valid_password = verify_password(password, candidate_hash) and user.status == UserStatus.ACTIVE
    if not valid_password:
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_failures:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        db.commit()
        raise ApiError(401, "LOGIN_FAILED", "邮箱或密码错误")

    if user.password_hash and password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    credentials = create_user_session(db, user.id, settings, user_agent)
    db.commit()
    db.refresh(user)
    return user, credentials


def create_user_session(
    db: Session,
    user_id: int,
    settings: WebSettings,
    user_agent: str | None,
) -> SessionCredentials:
    """创建只在 Cookie 中返回原文的服务端 Session。"""
    now = utc_now()
    absolute_expires_at = now + timedelta(hours=settings.session_absolute_hours)
    idle_expires_at = min(
        now + timedelta(minutes=settings.session_idle_minutes),
        absolute_expires_at,
    )
    session_token = generate_token()
    csrf_token = generate_token()
    session = UserSession(
        user_id=user_id,
        session_hash=hash_token(session_token),
        csrf_hash=hash_token(csrf_token),
        expires_at=absolute_expires_at,
        idle_expires_at=idle_expires_at,
        last_seen_at=now,
        user_agent_summary=(user_agent or "")[:255] or None,
    )
    db.add(session)
    db.flush()
    return SessionCredentials(session_token, csrf_token, session)


def resend_invitation(
    db: Session,
    invitation_id: int,
    actor_id: int,
    settings: WebSettings,
    mail_sender: MailSender,
) -> AuthActionToken:
    """撤销旧邀请并为同一受邀用户发送新令牌。"""
    invitation = db.get(AuthActionToken, invitation_id)
    if invitation is None or invitation.purpose != "invitation":
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    user = db.get(AppUser, invitation.user_id)
    if user is None or user.status != UserStatus.INVITED:
        raise ApiError(409, "INVITATION_NOT_PENDING", "该邀请已不能重发")

    invitation.revoked_at = utc_now()
    raw_token = generate_token()
    replacement = AuthActionToken(
        user_id=user.id,
        email=user.email,
        purpose="invitation",
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.invitation_ttl_hours),
        created_by=actor_id,
    )
    db.add(replacement)
    db.commit()
    db.refresh(replacement)
    invitation_url = f"{settings.public_web_url.rstrip('/')}/register#token={quote(raw_token)}"
    mail_sender.send_invitation(user.email, user.role.value, invitation_url)
    return replacement


def revoke_invitation(db: Session, invitation_id: int) -> AuthActionToken:
    """撤销仍未使用的邀请。"""
    invitation = db.get(AuthActionToken, invitation_id)
    if invitation is None or invitation.purpose != "invitation":
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    if invitation.used_at is not None:
        raise ApiError(409, "INVITATION_USED", "已使用的邀请不能撤销")
    if invitation.revoked_at is None:
        invitation.revoked_at = utc_now()
        db.commit()
        db.refresh(invitation)
    return invitation
