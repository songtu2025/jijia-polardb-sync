from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, require_admin
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.services.sync_query_service import list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def get_audit_logs(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_admin)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    jijia_account_id: int | None = None,
    actor_user_id: Annotated[int | None, Query(gt=0)] = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
    resource_type: Annotated[str | None, Query(max_length=64)] = None,
    resource_id: Annotated[str | None, Query(max_length=100)] = None,
    result: Literal["success", "failure"] | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_audit_logs(
            db,
            cursor,
            limit,
            account_id=jijia_account_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            created_from=created_from,
            created_to=created_to,
        ),
    )
