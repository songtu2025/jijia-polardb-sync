import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
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
from backend.app.services.audit_service import add_audit_log
from backend.app.services.mail_service import MailSender

logger = logging.getLogger(__name__)
PASSWORD_RESET_PURPOSE = "password_reset"


@dataclass(frozen=True)
class SessionCredentials:
    """只在当前请求内传递 Session 和 CSRF 原始令牌。"""

    session_token: str
    csrf_token: str
    session: UserSession


@dataclass(frozen=True)
class PasswordChangeDetails:
    """保存一次密码修改所需的敏感输入和审计请求标识。"""

    current_password: str
    new_password: str
    request_id: str


def _validate_password_length(password: str, settings: WebSettings) -> None:
    """统一执行注册、修改和重置密码的最小长度策略。"""
    if len(password) < settings.password_min_length:
        raise ApiError(
            422,
            "PASSWORD_TOO_SHORT",
            f"密码至少需要 {settings.password_min_length} 位",
        )


def _validate_new_password(
    password: str,
    current_password_hash: str | None,
    settings: WebSettings,
) -> None:
    """拒绝不符合长度策略或与当前密码相同的新密码。"""
    _validate_password_length(password, settings)
    if current_password_hash and verify_password(password, current_password_hash):
        raise ApiError(422, "PASSWORD_UNCHANGED", "新密码不能与当前密码相同")


def create_invitation(
    db: Session,
    email: str,
    role: UserRole,
    created_by: int | None,
    settings: WebSettings,
    mail_sender: MailSender,
    request_id: str | None,
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
    invitation_url = f"{settings.public_web_url.rstrip('/')}/register#token={quote(raw_token)}"
    try:
        mail_sender.send_invitation(normalized_email, role.value, invitation_url)
    except Exception:
        # 首个管理员没有可用的登录入口，邮件失败时必须回滚未提交邀请，允许安全重试。
        db.rollback()
        raise

    db.add(invitation)
    db.flush()
    add_audit_log(
        db,
        actor_user_id=created_by,
        jijia_account_id=None,
        action="invitation.create",
        resource_type="invitation",
        resource_id=invitation.id,
        request_id=request_id,
        result="success",
        changes={"role": role.value},
    )
    db.commit()
    db.refresh(invitation)
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
    _validate_password_length(password, settings)

    invitation_hash = hash_token(raw_token)
    candidate_user_id = db.scalar(
        select(AuthActionToken.user_id).where(
            AuthActionToken.token_hash == invitation_hash,
            AuthActionToken.purpose == "invitation",
        )
    )
    if candidate_user_id is None:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")
    user, invitations = _lock_user_invitations(db, candidate_user_id)
    invitation = next(
        (item for item in invitations if item.token_hash == invitation_hash),
        None,
    )
    if invitation is None:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")
    if invitation.revoked_at is not None:
        raise ApiError(400, "INVITATION_REVOKED", "邀请已撤销")
    if invitation.used_at is not None:
        raise ApiError(400, "INVITATION_USED", "邀请已使用")
    now = utc_now()
    if invitation.expires_at <= now:
        raise ApiError(400, "INVITATION_EXPIRED", "邀请已过期")
    if user is None or user.status != UserStatus.INVITED:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")

    consume_result = cast(
        CursorResult[Any],
        db.execute(
            update(AuthActionToken)
            .where(
                AuthActionToken.id == invitation.id,
                AuthActionToken.token_hash == invitation_hash,
                AuthActionToken.purpose == "invitation",
                AuthActionToken.used_at.is_(None),
                AuthActionToken.revoked_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .values(used_at=now)
        ),
    )
    if consume_result.rowcount != 1:
        raise ApiError(400, "INVITATION_INVALID", "邀请链接无效")

    user.display_name = display_name.strip()
    user.password_hash = hash_password(password)
    user.status = UserStatus.ACTIVE
    user.failed_login_count = 0
    for existing in invitations:
        if (
            existing.id != invitation.id
            and existing.used_at is None
            and existing.revoked_at is None
        ):
            existing.revoked_at = now
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
    request_id: str,
) -> tuple[AppUser, SessionCredentials]:
    """验证邮箱密码，记录连续失败并在成功后创建 Session。"""
    normalized_email = normalize_email(email)
    user = db.scalar(select(AppUser).where(AppUser.email == normalized_email).with_for_update())
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
            add_audit_log(
                db,
                actor_user_id=None,
                jijia_account_id=None,
                action="auth.login.lock",
                resource_type="user",
                resource_id=user.id,
                request_id=request_id,
                result="failure",
                changes={"locked": True},
            )
        db.commit()
        raise ApiError(401, "LOGIN_FAILED", "邮箱或密码错误")

    if user.password_hash and password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    credentials = create_user_session(db, user.id, settings, user_agent)
    add_audit_log(
        db,
        actor_user_id=user.id,
        jijia_account_id=None,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
        request_id=request_id,
        result="success",
    )
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


def change_password(
    db: Session,
    user_id: int,
    details: PasswordChangeDetails,
    settings: WebSettings,
) -> None:
    """验证当前密码，更新密码并撤销该用户的全部 Session。"""
    user = db.scalar(select(AppUser).where(AppUser.id == user_id).with_for_update())
    if user is None or user.status != UserStatus.ACTIVE or not user.password_hash:
        raise ApiError(401, "SESSION_INVALID", "登录状态无效")
    if not verify_password(details.current_password, user.password_hash):
        raise ApiError(400, "CURRENT_PASSWORD_INVALID", "当前密码不正确")

    _validate_new_password(details.new_password, user.password_hash, settings)
    now = utc_now()
    user.password_hash = hash_password(details.new_password)
    _revoke_user_sessions(db, user.id, now)
    add_audit_log(
        db,
        actor_user_id=user.id,
        jijia_account_id=None,
        action="auth.password.change",
        resource_type="user",
        resource_id=user.id,
        request_id=details.request_id,
        result="success",
    )
    db.commit()


def request_password_reset(
    db: Session,
    email: str,
    settings: WebSettings,
    mail_sender: MailSender,
) -> None:
    """为有效用户创建重置令牌；任何结果都不向请求方暴露账号状态。"""
    normalized_email = normalize_email(email)
    user = db.scalar(
        select(AppUser)
        .where(
            AppUser.email == normalized_email,
            AppUser.status == UserStatus.ACTIVE,
        )
        .with_for_update()
    )
    if user is None:
        return

    password_resets = _lock_user_password_resets(db, user.id)
    now = utc_now()
    for existing in password_resets:
        if existing.used_at is None and existing.revoked_at is None:
            existing.revoked_at = now

    raw_token = generate_token()
    reset = AuthActionToken(
        user_id=user.id,
        email=user.email,
        purpose=PASSWORD_RESET_PURPOSE,
        token_hash=hash_token(raw_token),
        expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
        created_by=None,
    )
    db.add(reset)
    db.flush()
    reset_url = f"{settings.public_web_url.rstrip('/')}/reset-password#token={quote(raw_token)}"
    try:
        # 邮件和令牌在同一事务内完成，发送失败时旧令牌保持原状态，允许安全重试。
        mail_sender.send_password_reset(user.email, reset_url)
    except Exception as error:
        db.rollback()
        logger.error("密码重置邮件发送失败: error_type=%s", type(error).__name__)
        return
    db.commit()


def validate_password_reset(db: Session, raw_token: str) -> None:
    """验证重置令牌有效，但不返回或暴露关联邮箱。"""
    reset = db.scalar(
        select(AuthActionToken).where(
            AuthActionToken.token_hash == hash_token(raw_token),
            AuthActionToken.purpose == PASSWORD_RESET_PURPOSE,
        )
    )
    user = db.get(AppUser, reset.user_id) if reset is not None else None
    if not _password_reset_is_valid(reset, user, utc_now()):
        raise _invalid_password_reset()


def complete_password_reset(
    db: Session,
    raw_token: str,
    new_password: str,
    settings: WebSettings,
    request_id: str,
) -> None:
    """单次消费重置令牌，更新密码、解锁账号并撤销全部 Session。"""
    _validate_password_length(new_password, settings)
    reset_hash = hash_token(raw_token)
    candidate_user_id = db.scalar(
        select(AuthActionToken.user_id).where(
            AuthActionToken.token_hash == reset_hash,
            AuthActionToken.purpose == PASSWORD_RESET_PURPOSE,
        )
    )
    if candidate_user_id is None:
        raise _invalid_password_reset()

    user = db.scalar(select(AppUser).where(AppUser.id == candidate_user_id).with_for_update())
    password_resets = _lock_user_password_resets(db, candidate_user_id)
    reset = next((item for item in password_resets if item.token_hash == reset_hash), None)
    now = utc_now()
    if not _password_reset_is_valid(reset, user, now):
        raise _invalid_password_reset()
    assert reset is not None
    assert user is not None
    _validate_new_password(new_password, user.password_hash, settings)

    consume_result = cast(
        CursorResult[Any],
        db.execute(
            update(AuthActionToken)
            .where(
                AuthActionToken.id == reset.id,
                AuthActionToken.token_hash == reset_hash,
                AuthActionToken.purpose == PASSWORD_RESET_PURPOSE,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.revoked_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .values(used_at=now)
        ),
    )
    if consume_result.rowcount != 1:
        raise _invalid_password_reset()

    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    for existing in password_resets:
        if existing.id != reset.id and existing.used_at is None and existing.revoked_at is None:
            existing.revoked_at = now
    _revoke_user_sessions(db, user.id, now)
    add_audit_log(
        db,
        actor_user_id=user.id,
        jijia_account_id=None,
        action="auth.password.reset",
        resource_type="user",
        resource_id=user.id,
        request_id=request_id,
        result="success",
    )
    db.commit()


def _lock_user_password_resets(db: Session, user_id: int) -> list[AuthActionToken]:
    """按主键顺序锁定同一用户的密码重置令牌。"""
    return list(
        db.scalars(
            select(AuthActionToken)
            .where(
                AuthActionToken.user_id == user_id,
                AuthActionToken.purpose == PASSWORD_RESET_PURPOSE,
            )
            .order_by(AuthActionToken.id)
            .with_for_update()
        ).all()
    )


def _password_reset_is_valid(
    reset: AuthActionToken | None,
    user: AppUser | None,
    now: datetime,
) -> bool:
    """使用统一规则判断重置令牌和目标账号是否可用。"""
    return bool(
        reset is not None
        and reset.revoked_at is None
        and reset.used_at is None
        and reset.expires_at > now
        and user is not None
        and user.status == UserStatus.ACTIVE
        and user.password_hash
    )


def _invalid_password_reset() -> ApiError:
    """返回不区分失效原因的重置错误，避免泄露令牌状态。"""
    return ApiError(400, "PASSWORD_RESET_INVALID", "重置链接无效或已过期")


def _revoke_user_sessions(db: Session, user_id: int, revoked_at: datetime) -> None:
    """撤销用户仍有效的全部服务端 Session。"""
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )


def resend_invitation(
    db: Session,
    invitation_id: int,
    actor_id: int,
    settings: WebSettings,
    mail_sender: MailSender,
    request_id: str,
) -> AuthActionToken:
    """撤销旧邀请并为同一受邀用户发送新令牌。"""
    candidate_user_id = db.scalar(
        select(AuthActionToken.user_id).where(
            AuthActionToken.id == invitation_id,
            AuthActionToken.purpose == "invitation",
        )
    )
    if candidate_user_id is None:
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    user, invitations = _lock_user_invitations(db, candidate_user_id)
    invitation = next(
        (item for item in invitations if item.id == invitation_id),
        None,
    )
    if invitation is None:
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    if user is None or user.status != UserStatus.INVITED:
        raise ApiError(409, "INVITATION_NOT_PENDING", "该邀请已不能重发")

    now = utc_now()
    for existing in invitations:
        if existing.used_at is None and existing.revoked_at is None:
            existing.revoked_at = now
    raw_token = generate_token()
    replacement = AuthActionToken(
        user_id=user.id,
        email=user.email,
        purpose="invitation",
        token_hash=hash_token(raw_token),
        expires_at=now + timedelta(hours=settings.invitation_ttl_hours),
        created_by=actor_id,
    )
    db.add(replacement)
    db.flush()
    invitation_url = f"{settings.public_web_url.rstrip('/')}/register#token={quote(raw_token)}"
    try:
        # 锁保持到邮件发送完成，确保最后送达的令牌也是最后提交的有效令牌。
        mail_sender.send_invitation(user.email, user.role.value, invitation_url)
    except Exception:
        db.rollback()
        raise
    add_audit_log(
        db,
        actor_user_id=actor_id,
        jijia_account_id=None,
        action="invitation.resend",
        resource_type="invitation",
        resource_id=replacement.id,
        request_id=request_id,
        result="success",
        changes={"role": user.role.value},
    )
    db.commit()
    db.refresh(replacement)
    return replacement


def revoke_invitation(
    db: Session,
    invitation_id: int,
    actor_id: int,
    request_id: str,
) -> AuthActionToken:
    """撤销仍未使用的邀请。"""
    candidate_user_id = db.scalar(
        select(AuthActionToken.user_id).where(
            AuthActionToken.id == invitation_id,
            AuthActionToken.purpose == "invitation",
        )
    )
    if candidate_user_id is None:
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    _user, invitations = _lock_user_invitations(db, candidate_user_id)
    invitation = next(
        (item for item in invitations if item.id == invitation_id),
        None,
    )
    if invitation is None:
        raise ApiError(404, "INVITATION_NOT_FOUND", "邀请不存在")
    if invitation.used_at is not None:
        raise ApiError(409, "INVITATION_USED", "已使用的邀请不能撤销")
    if invitation.revoked_at is None:
        invitation.revoked_at = utc_now()
    add_audit_log(
        db,
        actor_user_id=actor_id,
        jijia_account_id=None,
        action="invitation.revoke",
        resource_type="invitation",
        resource_id=invitation.id,
        request_id=request_id,
        result="success",
        changes={"revoked": True},
    )
    db.commit()
    db.refresh(invitation)
    return invitation


def _lock_user_invitations(
    db: Session,
    user_id: int,
) -> tuple[AppUser | None, list[AuthActionToken]]:
    """按用户、邀请主键的固定顺序锁定同一邀请域。"""
    user = db.scalar(select(AppUser).where(AppUser.id == user_id).with_for_update())
    if user is None:
        return None, []
    invitations = list(
        db.scalars(
            select(AuthActionToken)
            .where(
                AuthActionToken.user_id == user_id,
                AuthActionToken.purpose == "invitation",
            )
            .order_by(AuthActionToken.id)
            .with_for_update()
        ).all()
    )
    return user, invitations
