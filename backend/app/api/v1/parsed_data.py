from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, require_operator
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.services.parsed_data_service import list_parsed_data

router = APIRouter(prefix="/parsed-data", tags=["parsed-data"])


@router.get("/{dataset}")
def get_parsed_data(
    dataset: Literal["stores", "products", "inventory", "warehouses"],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_operator)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    jijia_account_id: int | None = None,
    keyword: str | None = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_parsed_data(
            db,
            dataset,
            cursor,
            context.user.id,
            request.state.request_id,
            limit,
            account_id=jijia_account_id,
            keyword=keyword,
        ),
    )
