from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import AuthContext, require_operator
from backend.app.api.responses import success_response
from backend.app.core.database import get_db
from backend.app.services.sync_query_service import list_sale_return_orders

router = APIRouter(prefix="/sale-return-orders", tags=["sale-return-orders"])


@router.get("")
def get_sale_return_orders(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_operator)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    jijia_account_id: int | None = None,
    status: str | None = None,
    return_date_start: date | None = None,
    return_date_end: date | None = None,
    order_id: str | None = None,
    sku: str | None = None,
    reason: str | None = None,
    disposition: str | None = None,
    fulfillment_center_id: str | None = None,
) -> dict[str, object]:
    return success_response(
        request,
        list_sale_return_orders(
            db,
            cursor,
            context.user.id,
            request.state.request_id,
            limit,
            account_id=jijia_account_id,
            status=status,
            return_date_start=return_date_start,
            return_date_end=return_date_end,
            order_id=order_id,
            sku=sku,
            reason=reason,
            disposition=disposition,
            fulfillment_center_id=fulfillment_center_id,
        ),
    )
