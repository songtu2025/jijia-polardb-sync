from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context, require_csrf
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.core.security import generate_token, hash_token, utc_now
from backend.app.models.user import AppUser
from backend.app.schemas.auth import (
    InvitationValidateRequest,
    LoginRequest,
    RegisterRequest,
)
from backend.app.services.auth_service import (
    authenticate_user,
    register_user,
    validate_invitation,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_data(user: AppUser) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "displayName": user.display_name,
        "role": user.role.value,
        "status": user.status.value,
    }


def set_session_cookie(response: Response, raw_session: str, settings: WebSettings) -> None:
    """写入浏览器会话 Cookie，令牌不可被 JavaScript 读取。"""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> dict[str, object]:
    user, credentials = authenticate_user(
        db,
        payload.email,
        payload.password,
        settings,
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, credentials.session_token, settings)
    return success_response(
        request,
        {"user": user_data(user), "csrfToken": credentials.csrf_token},
    )


@router.post("/invitations/validate")
def validate_registration_invitation(
    payload: InvitationValidateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    invitation, user = validate_invitation(db, payload.token)
    return success_response(
        request,
        {
            "email": invitation.email,
            "role": user.role.value,
            "expiresAt": invitation.expires_at.isoformat(),
        },
    )


@router.post("/register")
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> dict[str, object]:
    user, credentials = register_user(
        db,
        payload.token,
        payload.display_name,
        payload.password,
        settings,
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, credentials.session_token, settings)
    return success_response(
        request,
        {"user": user_data(user), "csrfToken": credentials.csrf_token},
    )


@router.get("/session")
def get_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    # 页面刷新后轮换 CSRF，前端无需持久化任何认证令牌。
    csrf_token = generate_token()
    context.session.csrf_hash = hash_token(csrf_token)
    db.commit()
    return success_response(
        request,
        {"user": user_data(context.user), "csrfToken": csrf_token},
    )


@router.get("/me")
def get_me(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    return success_response(request, user_data(context.user))


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(require_csrf)],
) -> dict[str, object]:
    context.session.revoked_at = utc_now()
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return success_response(request, {"loggedOut": True})
