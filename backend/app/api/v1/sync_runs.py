from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.services.sync_query_service import (
    get_sync_run,
    list_failed_requests,
    list_run_logs,
    list_sync_runs,
)

router = APIRouter(prefix="/sync-runs", tags=["sync-runs"])


@router.get("")
def get_sync_runs(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    jijia_account_id: int | None = None,
    status: str | None = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_sync_runs(
            db,
            cursor,
            limit,
            account_id=jijia_account_id,
            status=status,
        ),
    )


@router.get("/{run_id}/logs")
def get_sync_run_logs(
    run_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    return success_response(request, list_run_logs(db, run_id, cursor, limit))


@router.get("/{run_id}")
def get_sync_run_detail(
    run_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    return success_response(request, get_sync_run(db, run_id))


@router.get("/{run_id}/failed-requests")
def get_sync_run_failed_requests(
    run_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    return success_response(
        request,
        list_failed_requests(db, run_id, cursor, limit),
    )
