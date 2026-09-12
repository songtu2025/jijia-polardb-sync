from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    AuthContext,
    get_mail_sender,
    require_admin,
    require_admin_csrf,
)
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.models.auth_action_token import AuthActionToken
from backend.app.models.user import AppUser
from backend.app.schemas.auth import InvitationCreateRequest
from backend.app.services.auth_service import (
    create_invitation,
    resend_invitation,
    revoke_invitation,
)
from backend.app.services.mail_service import MailSender

router = APIRouter(prefix="/invitations", tags=["invitations"])


def invitation_data(invitation: AuthActionToken, user: AppUser) -> dict[str, object]:
    return {
        "id": invitation.id,
        "email": invitation.email,
        "role": user.role.value,
        "expiresAt": invitation.expires_at.isoformat(),
        "usedAt": invitation.used_at.isoformat() if invitation.used_at else None,
        "revokedAt": invitation.revoked_at.isoformat() if invitation.revoked_at else None,
    }


@router.get("")
def list_invitations(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_admin)],
) -> dict[str, object]:
    rows = db.execute(
        select(AuthActionToken, AppUser)
        .join(AppUser, AppUser.id == AuthActionToken.user_id)
        .where(AuthActionToken.purpose == "invitation")
        .order_by(AuthActionToken.id.desc())
    ).all()
    return success_response(
        request,
        [invitation_data(invitation, user) for invitation, user in rows],
    )


@router.post("")
def invite_user(
    payload: InvitationCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    mail_sender: Annotated[MailSender, Depends(get_mail_sender)],
    context: Annotated[AuthContext, Depends(require_admin_csrf)],
) -> dict[str, object]:
    invitation = create_invitation(
        db,
        payload.email,
        payload.role,
        context.user.id,
        settings,
        mail_sender,
        request.state.request_id,
    )
    user = db.get(AppUser, invitation.user_id)
    if user is None:
        raise RuntimeError("邀请关联用户不存在")
    return success_response(request, invitation_data(invitation, user))


@router.post("/{invitation_id}/resend")
def resend(
    invitation_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    mail_sender: Annotated[MailSender, Depends(get_mail_sender)],
    context: Annotated[AuthContext, Depends(require_admin_csrf)],
) -> dict[str, object]:
    invitation = resend_invitation(
        db,
        invitation_id,
        context.user.id,
        settings,
        mail_sender,
        request.state.request_id,
    )
    user = db.get(AppUser, invitation.user_id)
    if user is None:
        raise RuntimeError("邀请关联用户不存在")
    return success_response(request, invitation_data(invitation, user))


@router.post("/{invitation_id}/revoke")
def revoke(
    invitation_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_admin_csrf)],
) -> dict[str, object]:
    invitation = revoke_invitation(
        db,
        invitation_id,
        context.user.id,
        request.state.request_id,
    )
    user = db.get(AppUser, invitation.user_id)
    if user is None:
        raise RuntimeError("邀请关联用户不存在")
    return success_response(request, invitation_data(invitation, user))
