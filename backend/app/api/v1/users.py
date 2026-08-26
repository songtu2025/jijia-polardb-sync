from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, require_admin, require_admin_csrf
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.core.errors import ApiError
from backend.app.core.security import utc_now
from backend.app.models.user import AppUser, UserRole, UserStatus
from backend.app.models.user_session import UserSession
from backend.app.schemas.user import UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


def user_data(user: AppUser) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "displayName": user.display_name,
        "role": user.role.value,
        "status": user.status.value,
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
        "createdAt": user.created_at.isoformat(),
    }


@router.get("")
def list_users(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_admin)],
) -> dict[str, object]:
    users = db.scalars(select(AppUser).order_by(AppUser.id)).all()
    return success_response(request, [user_data(user) for user in users])


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_admin_csrf)],
) -> dict[str, object]:
    user = db.get(AppUser, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
    if payload.status == UserStatus.INVITED:
        raise ApiError(422, "USER_STATUS_INVALID", "不能把用户改回受邀状态")
    removes_active_admin = (
        user.role == UserRole.ADMIN
        and user.status == UserStatus.ACTIVE
        and (
            (payload.role is not None and payload.role != UserRole.ADMIN)
            or payload.status == UserStatus.DISABLED
        )
    )
    if removes_active_admin:
        other_admins = db.scalar(
            select(func.count(AppUser.id)).where(
                AppUser.id != user.id,
                AppUser.role == UserRole.ADMIN,
                AppUser.status == UserStatus.ACTIVE,
            )
        )
        if not other_admins:
            raise ApiError(409, "LAST_ADMIN_REQUIRED", "至少保留 1 名可用管理员")
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status
        if payload.status == UserStatus.DISABLED:
            db.execute(
                update(UserSession)
                .where(
                    UserSession.user_id == user.id,
                    UserSession.revoked_at.is_(None),
                )
                .values(revoked_at=utc_now())
            )
    db.commit()
    db.refresh(user)
    return success_response(request, user_data(user))
