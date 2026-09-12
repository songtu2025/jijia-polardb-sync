from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context, require_operator_csrf
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.schemas.jijia_account import JijiaAccountCreateRequest, JijiaAccountUpdateRequest
from backend.app.services.jijia_account_service import (
    account_data,
    create_account,
    deactivate_account,
    get_account_data,
    list_account_data,
    update_account,
    verify_account,
)

router = APIRouter(prefix="/jijia-accounts", tags=["jijia-accounts"])


@router.get("")
def list_jijia_accounts(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    return success_response(request, list_account_data(db))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_jijia_account(
    payload: JijiaAccountCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    account = create_account(
        db,
        payload,
        context.user.id,
        settings,
        request.state.request_id,
    )
    return success_response(request, account_data(account))


@router.get("/{account_id}")
def get_jijia_account(
    account_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    return success_response(
        request,
        get_account_data(db, account_id),
    )


@router.patch("/{account_id}")
def update_jijia_account(
    account_id: int,
    payload: JijiaAccountUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    account = update_account(
        db,
        account_id,
        payload,
        context.user.id,
        settings,
        request.state.request_id,
    )
    return success_response(request, account_data(account))


@router.post("/{account_id}/verify")
def verify_jijia_account(
    account_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    account = verify_account(
        db,
        account_id,
        context.user.id,
        settings,
        request.state.request_id,
    )
    return success_response(request, account_data(account))


@router.post("/{account_id}/deactivate")
def deactivate_jijia_account(
    account_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    account = deactivate_account(
        db,
        account_id,
        context.user.id,
        request.state.request_id,
    )
    return success_response(request, account_data(account))
