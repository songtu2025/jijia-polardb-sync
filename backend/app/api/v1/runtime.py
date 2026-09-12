from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.services.worker_runtime_service import worker_runtime_data

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/worker")
def get_worker_runtime(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    """向已登录成员返回脱敏后的任务执行服务状态。"""
    return success_response(request, worker_runtime_data(db, settings))
