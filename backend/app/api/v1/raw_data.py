from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.services.sync_query_service import (
    get_raw_data,
    list_raw_data,
    list_raw_versions,
)

router = APIRouter(prefix="/raw-data", tags=["raw-data"])


@router.get("")
def get_raw_data_list(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    jijia_account_id: int | None = None,
    api_code: str | None = None,
    sync_batch_no: str | None = None,
    observed_sync_batch_no: str | None = None,
    source_primary_key: str | None = None,
    data_date_start: date | None = None,
    data_date_end: date | None = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_raw_data(
            db,
            cursor,
            limit,
            account_id=jijia_account_id,
            api_code=api_code,
            sync_batch_no=sync_batch_no,
            observed_sync_batch_no=observed_sync_batch_no,
            source_primary_key=source_primary_key,
            data_date_start=data_date_start,
            data_date_end=data_date_end,
        ),
    )


@router.get("/{raw_data_id}")
def get_raw_data_detail(
    raw_data_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    data = get_raw_data(
        db,
        raw_data_id,
        context.user.role,
        context.user.id,
        request.state.request_id,
    )
    return success_response(request, data)


@router.get("/{raw_data_id}/versions")
def get_raw_data_versions(
    raw_data_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(get_auth_context)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    data = list_raw_versions(
        db,
        raw_data_id,
        context.user.role,
        context.user.id,
        request.state.request_id,
        cursor,
        limit,
    )
    return success_response(request, data)
