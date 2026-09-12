from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.core.errors import ApiError
from backend.app.core.security import hash_token, token_matches, utc_now
from backend.app.models.user import AppUser, UserRole, UserStatus
from backend.app.models.user_session import UserSession
from backend.app.services.mail_service import MailSender, create_mail_sender

SESSION_TOUCH_INTERVAL = timedelta(seconds=60)


@dataclass(frozen=True)
class AuthContext:
    """绑定当前已认证用户和服务端 Session。"""

    user: AppUser
    session: UserSession


def get_mail_sender(
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> MailSender:
    """为请求创建当前环境配置的邮件适配器。"""
    return create_mail_sender(settings)


def get_auth_context(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> AuthContext:
    """从 HttpOnly Cookie 解析并续期有效 Session。"""
    raw_session = request.cookies.get(settings.session_cookie_name)
    if not raw_session:
        raise ApiError(401, "AUTH_REQUIRED", "请先登录")

    auth_row = db.execute(
        select(UserSession, AppUser)
        .outerjoin(AppUser, AppUser.id == UserSession.user_id)
        .where(UserSession.session_hash == hash_token(raw_session))
    ).one_or_none()
    now = utc_now()
    if auth_row is None:
        raise ApiError(401, "SESSION_INVALID", "登录状态无效")

    session, user = auth_row
    if session.revoked_at is not None:
        raise ApiError(401, "SESSION_INVALID", "登录状态无效")
    if session.expires_at <= now or session.idle_expires_at <= now:
        session.revoked_at = now
        db.commit()
        raise ApiError(401, "SESSION_EXPIRED", "登录状态已过期")

    if user is None or user.status != UserStatus.ACTIVE:
        session.revoked_at = now
        db.commit()
        raise ApiError(401, "SESSION_INVALID", "登录状态无效")

    touch_before = now - SESSION_TOUCH_INTERVAL
    if session.last_seen_at <= touch_before:
        idle_expires_at = min(
            now + timedelta(minutes=settings.session_idle_minutes), session.expires_at
        )
        # 条件更新同时完成节流和乱序保护，旧请求不会覆盖更新的活动时间。
        db.execute(
            update(UserSession)
            .where(
                UserSession.id == session.id,
                UserSession.last_seen_at <= touch_before,
            )
            .values(last_seen_at=now, idle_expires_at=idle_expires_at)
            .execution_options(synchronize_session=False)
        )
        db.commit()
    return AuthContext(user=user, session=session)


def require_csrf(
    context: Annotated[AuthContext, Depends(get_auth_context)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthContext:
    """拒绝缺失或错误 CSRF 令牌的已认证写请求。"""
    if not csrf_token or not token_matches(csrf_token, context.session.csrf_hash):
        raise ApiError(403, "CSRF_INVALID", "CSRF 校验失败")
    return context


def require_admin(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    """限制成员和邀请读取接口只能由管理员访问。"""
    if context.user.role != UserRole.ADMIN:
        raise ApiError(403, "PERMISSION_DENIED", "无权执行该操作")
    return context


def require_admin_csrf(
    context: Annotated[AuthContext, Depends(require_csrf)],
) -> AuthContext:
    """同时执行管理员权限和 CSRF 校验。"""
    if context.user.role != UserRole.ADMIN:
        raise ApiError(403, "PERMISSION_DENIED", "无权执行该操作")
    return context


def require_operator(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    """只允许管理员和操作员读取敏感业务投影。"""
    if context.user.role not in {UserRole.ADMIN, UserRole.OPERATOR}:
        raise ApiError(403, "PERMISSION_DENIED", "无权执行该操作")
    return context


def require_operator_csrf(
    context: Annotated[AuthContext, Depends(require_csrf)],
) -> AuthContext:
    """允许管理员和操作员执行账号与策略写操作。"""
    if context.user.role not in {UserRole.ADMIN, UserRole.OPERATOR}:
        raise ApiError(403, "PERMISSION_DENIED", "无权执行该操作")
    return context
