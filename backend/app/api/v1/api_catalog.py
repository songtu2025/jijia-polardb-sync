from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, get_auth_context
from backend.app.api.responses import success_response
from backend.app.core.config import WebSettings, get_web_settings
from backend.app.core.database import get_db
from backend.app.services.api_catalog_service import (
    list_connected_catalog_data,
    list_official_catalog_data,
)

router = APIRouter(prefix="/api-catalog", tags=["api-catalog"])


@router.get("")
def get_api_catalog(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
    jijia_account_id: Annotated[int | None, Query(gt=0)] = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_connected_catalog_data(db, settings.api_catalog_path, jijia_account_id),
    )


@router.get("/official")
def get_official_api_catalog(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[WebSettings, Depends(get_web_settings)],
    _: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, object]:
    """返回本地生成的官方接口目录及当前接入映射。"""
    return success_response(
        request,
        list_official_catalog_data(db, settings.api_catalog_path),
    )
