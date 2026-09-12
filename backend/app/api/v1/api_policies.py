from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context, require_operator_csrf
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.schemas.api_policy import ApiPolicyBatchUpdateRequest, ApiPolicyUpdateRequest
from backend.app.services.api_policy_service import (
    batch_update_account_policies,
    list_account_policies,
    update_account_policy,
)

router = APIRouter(prefix="/jijia-accounts/{account_id}/api-policies", tags=["api-policies"])


@router.get("")
def list_policies(
    account_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    policies = list_account_policies(db, account_id)
    return success_response(request, policies)


@router.put("/batch")
def batch_update_policies(
    account_id: int,
    payload: ApiPolicyBatchUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    policies = batch_update_account_policies(
        db,
        account_id,
        payload,
        context.user.id,
        request.state.request_id,
    )
    return success_response(request, policies)


@router.put("/{api_code}")
def update_policy(
    account_id: int,
    api_code: str,
    payload: ApiPolicyUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_operator_csrf)],
) -> dict[str, object]:
    policy = update_account_policy(
        db,
        account_id,
        api_code,
        payload,
        context.user.id,
        request.state.request_id,
    )
    return success_response(request, policy)
