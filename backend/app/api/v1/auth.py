from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    AuthContext,
    get_auth_context,
    get_mail_sender,
    require_csrf,
)
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.core.security import generate_token, hash_token, token_matches, utc_now
from backend.app.models.user import AppUser
from backend.app.schemas.auth import (
    InvitationValidateRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetCompleteRequest,
    PasswordResetRequest,
    PasswordResetValidateRequest,
    RegisterRequest,
)
from backend.app.services.audit_service import add_audit_log
from backend.app.services.auth_service import (
    PasswordChangeDetails,
    authenticate_user,
    change_password,
    complete_password_reset,
    register_user,
    request_password_reset,
    validate_invitation,
    validate_password_reset,
)
from backend.app.services.mail_service import MailSender

router = APIRouter(prefix="/auth", tags=["auth"])


def user_data(user: AppUser) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "displayName": user.display_name,
        "role": user.role.value,
        "status": user.status.value,
    }


def csrf_cookie_name(settings: WebSettings) -> str:
    """返回与 Session Cookie 绑定的可读 CSRF Cookie 名称。"""
    return f"{settings.session_cookie_name}_csrf"


def set_session_cookie(
    response: Response,
    raw_session: str,
    csrf_token: str,
    settings: WebSettings,
) -> None:
    """写入稳定的服务端 Session 和当前 Session 的 CSRF Cookie。"""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=csrf_cookie_name(settings),
        value=csrf_token,
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )


def delete_session_cookies(response: Response, settings: WebSettings) -> None:
    """用写入时相同的安全属性删除 Session 和 CSRF Cookie。"""
    response.delete_cookie(
        settings.session_cookie_name,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        csrf_cookie_name(settings),
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )


@router.get("/password-policy")
def get_password_policy(
    request: Request,
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> dict[str, object]:
    """返回所有密码入口共用的公开最小长度策略。"""
    return success_response(request, {"minimumLength": settings.password_min_length})


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
        request.state.request_id,
    )
    set_session_cookie(response, credentials.session_token, credentials.csrf_token, settings)
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
    set_session_cookie(response, credentials.session_token, credentials.csrf_token, settings)
    return success_response(
        request,
        {"user": user_data(user), "csrfToken": credentials.csrf_token},
    )


@router.post("/password/change")
def change_current_user_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(require_csrf)],
) -> Response:
    change_password(
        db,
        context.user.id,
        PasswordChangeDetails(
            current_password=payload.current_password,
            new_password=payload.new_password,
            request_id=request.state.request_id,
        ),
        settings,
    )
    response = JSONResponse(content=success_response(request, {"passwordChanged": True}))
    delete_session_cookies(response, settings)
    return response


@router.post("/password-reset/request")
def request_current_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    mail_sender: Annotated[MailSender, Depends(get_mail_sender)],
) -> dict[str, object]:
    request_password_reset(db, str(payload.email), settings, mail_sender)
    return success_response(request, {"accepted": True})


@router.post("/password-reset/validate")
def validate_current_password_reset(
    payload: PasswordResetValidateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    validate_password_reset(db, payload.token)
    return success_response(request, {"valid": True})


@router.post("/password-reset/complete")
def complete_current_password_reset(
    payload: PasswordResetCompleteRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
) -> dict[str, object]:
    complete_password_reset(
        db,
        payload.token,
        payload.new_password,
        settings,
        request.state.request_id,
    )
    delete_session_cookies(response, settings)
    return success_response(request, {"passwordReset": True})


@router.get("/session")
def get_session(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    # CSRF 按 Session 稳定；浏览器标签页共享该 Cookie，恢复会话不会使其他标签页失效。
    csrf_token = request.cookies.get(csrf_cookie_name(settings))
    if csrf_token is None or not token_matches(csrf_token, context.session.csrf_hash):
        csrf_token = generate_token()
        context.session.csrf_hash = hash_token(csrf_token)
        db.commit()
        response.set_cookie(
            key=csrf_cookie_name(settings),
            value=csrf_token,
            secure=settings.session_cookie_secure,
            httponly=False,
            samesite="lax",
            path="/",
        )
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
    add_audit_log(
        db,
        actor_user_id=context.user.id,
        jijia_account_id=None,
        action="auth.logout",
        resource_type="user_session",
        resource_id=context.session.id,
        request_id=request.state.request_id,
        result="success",
        changes={"revoked": True},
    )
    db.commit()
    delete_session_cookies(response, settings)
    return success_response(request, {"loggedOut": True})
