from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.services.sync_query_service import dashboard_summary
from backend.app.services.worker_runtime_service import worker_runtime_data

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    return success_response(
        request,
        {**dashboard_summary(db), "worker": worker_runtime_data(db, settings)},
    )
