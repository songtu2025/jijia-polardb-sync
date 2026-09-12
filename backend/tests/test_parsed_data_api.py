from datetime import date, datetime, timedelta

from sqlalchemy import insert

from backend.app.models.sync_records import raw_api_data_table
from backend.app.models.user import UserRole
from backend.tests.conftest import AuthHarness
from backend.tests.test_api_policies_api import create_active_account
from backend.tests.test_auth_api import register_user


def _insert_raw(
    harness: AuthHarness,
    account_id: int,
    api_code: str,
    raw_json: dict[str, object],
    suffix: str,
    created_at: datetime,
) -> int:
    with harness.session_factory() as db:
        raw_id = db.execute(
            insert(raw_api_data_table).values(
                jijia_account_id=account_id,
                api_code=api_code,
                source_primary_key=f"source-{suffix}",
                record_identity=f"identity-{suffix}",
                data_hash=f"hash-{suffix}",
                raw_json=raw_json,
                data_date=date(2026, 9, 6),
                sync_batch_no=f"batch-{suffix}",
                first_observed_at=created_at,
                last_observed_at=created_at,
                observation_count=1,
                created_at=created_at,
                updated_at=created_at,
            )
        ).inserted_primary_key[0]
        db.commit()
    return int(raw_id)


def test_store_projection_flattens_markets_without_exposing_sensitive_fields(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, _, account = create_active_account(harness, monkeypatch)
    raw_id = _insert_raw(
        harness,
        account["id"],
        "amazon_shop_page",
        {
            "sellerId": "SENSITIVE_TOP_SELLER",
            "marketListVos": [
                {
                    "marketId": 70,
                    "store": "北美旗舰店",
                    "marketName": "Amazon.com",
                    "countryName": "美国",
                    "areaName": "北美",
                    "apiState": "Normal",
                    "adsState": "Successfully",
                    "warehouseName": "FBA",
                    "authType": "SP-API",
                    "recordDate": "2026-09-05 12:00:00",
                    "account": "SENSITIVE_ACCOUNT",
                    "sellerId": "SENSITIVE_SELLER",
                    "serverName": "SENSITIVE_SERVER",
                    "publicToken": "SENSITIVE_PUBLIC_TOKEN",
                    "refreshToken": "SENSITIVE_REFRESH_TOKEN",
                },
                {
                    "marketId": 71,
                    "store": "加拿大店",
                    "marketName": "Amazon.ca",
                    "countryName": "加拿大",
                },
            ],
        },
        "store",
        datetime(2026, 9, 6, 8, 0),
    )

    response = client.get("/api/v1/parsed-data/stores")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 2
    assert items[0]["rawDataId"] == raw_id
    assert items[0]["fields"] == {
        "marketId": 70,
        "store": "北美旗舰店",
        "marketName": "Amazon.com",
        "countryName": "美国",
        "areaName": "北美",
        "apiState": "Normal",
        "adsState": "Successfully",
        "warehouseName": "FBA",
        "authType": "SP-API",
        "recordDate": "2026-09-05 12:00:00",
    }
    assert "sourcePrimaryKey" not in items[0]
    assert "SENSITIVE_" not in response.text


def test_store_projection_paginates_visible_market_rows(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, _, account = create_active_account(harness, monkeypatch)
    _insert_raw(
        harness,
        account["id"],
        "amazon_shop_page",
        {
            "marketListVos": [
                {"marketId": 70, "store": "美国店", "marketName": "Amazon.com"},
                {"marketId": 71, "store": "加拿大店", "marketName": "Amazon.ca"},
            ],
        },
        "store-page",
        datetime(2026, 9, 6, 8, 0),
    )

    first_page = client.get("/api/v1/parsed-data/stores", params={"limit": 1})
    cursor = first_page.json()["data"]["nextCursor"]
    second_page = client.get(
        "/api/v1/parsed-data/stores",
        params={"limit": 1, "cursor": cursor},
    )

    assert [item["fields"]["store"] for item in first_page.json()["data"]["items"]] == ["美国店"]
    assert [item["fields"]["store"] for item in second_page.json()["data"]["items"]] == ["加拿大店"]
    assert second_page.json()["data"]["nextCursor"] is None


def test_product_inventory_and_warehouse_projections_use_allowlisted_fields(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, _, account = create_active_account(harness, monkeypatch)
    now = datetime(2026, 9, 6, 9, 0)
    fixtures = [
        (
            "products",
            "product_page",
            {
                "sku": "SKU-1",
                "name": "充电器",
                "briefName": "快充",
                "brandName": "示例品牌",
                "categoryName": "电子配件",
                "productTypeName": "标准品",
                "state": "0",
                "unit": "件",
                "lastDate": "2026-09-06 09:00:00",
                "purchaseCost": "SENSITIVE_PRODUCT_COST",
            },
            {"sku": "SKU-1", "stateName": "正常"},
        ),
        (
            "inventory",
            "fba_inventory_v2_page",
            {
                "sku": "SKU-2",
                "msku": "MSKU-2",
                "fnsku": "FNSKU-2",
                "asin": "ASIN-2",
                "productName": "数据线",
                "warehouseName": "ONT8",
                "afnFulfillableQuantity": 12,
                "reserved": 2,
                "inTransitQty": 3,
                "totalInventoryQty": 17,
                "availableTurnoverDays": 24.5,
                "updateTime": "2026-09-06 09:00:00",
                "arriveCost": "SENSITIVE_INVENTORY_COST",
                "inventoryValue": "SENSITIVE_INVENTORY_VALUE",
            },
            {"sku": "SKU-2", "totalInventoryQty": 17},
        ),
        (
            "warehouses",
            "fba_warehouse_page",
            {
                "name": "ONT8",
                "marketName": "北美旗舰店",
                "country": "美国",
                "stateStr": "加利福尼亚州",
                "statusName": "启用",
                "typeName": "FBA",
                "fbaProcurementMethodName": "平台采购",
                "transferWarehouseName": "洛杉矶中转仓",
                "createDate": "2026-08-01 10:00:00",
                "internalCode": "SENSITIVE_WAREHOUSE_INTERNAL",
            },
            {"name": "ONT8", "statusName": "启用"},
        ),
    ]
    for index, (_, api_code, raw_json, _) in enumerate(fixtures):
        _insert_raw(
            harness,
            account["id"],
            api_code,
            raw_json,
            str(index),
            now + timedelta(minutes=index),
        )

    for dataset, _, _, expected in fixtures:
        response = client.get(f"/api/v1/parsed-data/{dataset}")
        assert response.status_code == 200
        item = response.json()["data"]["items"][0]
        assert item["accountName"] == account["name"]
        assert item["fields"] | expected == item["fields"]
        assert "SENSITIVE_" not in response.text


def test_parsed_data_filters_accounts_keywords_and_paginates(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    client, auth, first_account = create_active_account(harness, monkeypatch)
    second_account = client.post(
        "/api/v1/jijia-accounts",
        json={"name": "第二账号", "app_id": "second-app", "app_key": "second-key"},
        headers={"X-CSRF-Token": auth["csrfToken"]},
    ).json()["data"]
    now = datetime(2026, 9, 6, 10, 0)
    _insert_raw(
        harness,
        first_account["id"],
        "product_page",
        {"sku": "MATCH-1", "name": "目标产品"},
        "filter-1",
        now,
    )
    _insert_raw(
        harness,
        first_account["id"],
        "product_page",
        {"sku": "OTHER-1", "name": "其他产品"},
        "filter-2",
        now - timedelta(minutes=1),
    )
    _insert_raw(
        harness,
        second_account["id"],
        "product_page",
        {"sku": "MATCH-2", "name": "第二账号产品"},
        "filter-3",
        now - timedelta(minutes=2),
    )

    filtered = client.get(
        "/api/v1/parsed-data/products",
        params={"jijia_account_id": first_account["id"], "keyword": "MATCH"},
    )
    first_page = client.get(
        "/api/v1/parsed-data/products",
        params={"jijia_account_id": first_account["id"], "limit": 1},
    )
    cursor = first_page.json()["data"]["nextCursor"]
    second_page = client.get(
        "/api/v1/parsed-data/products",
        params={
            "jijia_account_id": first_account["id"],
            "limit": 1,
            "cursor": cursor,
        },
    )

    assert [item["fields"]["sku"] for item in filtered.json()["data"]["items"]] == ["MATCH-1"]
    assert first_page.json()["data"]["items"][0]["fields"]["sku"] == "MATCH-1"
    assert second_page.json()["data"]["items"][0]["fields"]["sku"] == "OTHER-1"
    assert second_page.json()["data"]["nextCursor"] is None


def test_parsed_data_requires_operator_role(harness: AuthHarness) -> None:
    _, _, _ = register_user(
        harness,
        "parsed-viewer@example.com",
        UserRole.VIEWER,
        harness.client,
    )

    response = harness.client.get("/api/v1/parsed-data/products")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
