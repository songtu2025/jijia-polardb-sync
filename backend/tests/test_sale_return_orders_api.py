from datetime import datetime

from sqlalchemy import event, insert, select

from backend.app.models.audit_log import AuditLog
from backend.app.models.sync_records import sale_return_order_table
from backend.app.models.user import UserRole
from backend.tests.conftest import AuthHarness
from backend.tests.test_api_policies_api import create_active_account
from backend.tests.test_auth_api import register_user


def _insert_order(harness: AuthHarness, account_id: int, *, suffix: str = "1") -> None:
    now = datetime(2026, 8, 27, 8, 0, 0)
    with harness.session_factory() as db:
        db.execute(
            insert(sale_return_order_table).values(
                jijia_account_id=account_id,
                raw_data_id=int(suffix),
                source_primary_key=f"return-{suffix}",
                record_identity=suffix.zfill(64),
                market_id=1,
                return_date_time=datetime(2021, 8, int(suffix), 9, 30, 0),
                order_id=f"order-{suffix}",
                seller_order_id=f"seller-{suffix}",
                asin=f"asin-{suffix}",
                sku=f"sku-{suffix}",
                quantity=1,
                fulfillment_center_id="FC-1",
                disposition="SELLABLE",
                reason="reason",
                status="completed",
                source_created_at=now,
                source_updated_at=now,
                data_hash=suffix.zfill(64),
                sync_batch_no="sync-test",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()


def test_authenticated_user_filters_sale_return_orders(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, _, account = create_active_account(harness, monkeypatch)
    _insert_order(harness, account["id"])

    with harness.session_factory() as db:
        engine = db.get_bind()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        response = client.get(
            "/api/v1/sale-return-orders",
            params={
                "jijia_account_id": account["id"],
                "status": "completed",
                "return_date_start": "2021-08-01",
                "return_date_end": "2021-08-01",
                "order_id": "order-1",
                "sku": "sku-1",
                "reason": "reason",
                "disposition": "SELLABLE",
                "fulfillment_center_id": "FC-1",
            },
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [
            {
                "id": 1,
                "jijiaAccountId": account["id"],
                "accountName": account["name"],
                "rawDataId": 1,
                "sourcePrimaryKey": "return-1",
                "marketId": 1,
                "returnDateTime": "2021-08-01T09:30:00",
                "orderId": "order-1",
                "sellerOrderId": "seller-1",
                "asin": "asin-1",
                "msku": None,
                "fnsku": None,
                "sku": "sku-1",
                "productName": None,
                "quantity": 1,
                "fulfillmentCenterId": "FC-1",
                "disposition": "SELLABLE",
                "reason": "reason",
                "status": "completed",
                "sourceCreatedAt": "2026-08-27T08:00:00",
                "sourceUpdatedAt": "2026-08-27T08:00:00",
                "dataHash": "1".zfill(64),
                "syncBatchNo": "sync-test",
            }
        ],
        "nextCursor": None,
    }
    sale_page_selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT") and "FROM sale_return_order" in statement
    ]
    assert len(sale_page_selects) == 1
    assert "JOIN jijia_account" not in sale_page_selects[0]
    with harness.session_factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "sale_return_order.list"))
        assert audit is not None
        assert audit.actor_user_id is not None
        assert audit.jijia_account_id == account["id"]
        assert audit.changes_json == {"resultCount": 1, "filtered": True}

    _insert_order(harness, 0, suffix="2")
    unscoped = client.get("/api/v1/sale-return-orders")
    assert [item["jijiaAccountId"] for item in unscoped.json()["data"]["items"]] == [account["id"]]


def test_sale_return_orders_validate_date_range(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, _, _ = create_active_account(harness, monkeypatch)

    response = client.get(
        "/api/v1/sale-return-orders",
        params={"return_date_start": "2021-08-02", "return_date_end": "2021-08-01"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RETURN_DATE_RANGE_INVALID"


def test_sale_return_orders_require_authentication(harness: AuthHarness) -> None:
    response = harness.client.get("/api/v1/sale-return-orders")

    assert response.status_code == 401


def test_viewer_cannot_read_sensitive_sale_return_projection(harness: AuthHarness) -> None:
    _, _, _ = register_user(
        harness,
        "return-viewer@example.com",
        UserRole.VIEWER,
        harness.client,
    )

    response = harness.client.get("/api/v1/sale-return-orders")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
