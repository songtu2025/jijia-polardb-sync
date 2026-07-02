import unittest

from app.config import load_api_configs
from app.sync_engine import SyncEngine


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params))
        return FakeResult(self.rows)


class MarketInventoryParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_market_inventory_query_config_uses_inventory_sku_warehouse_and_stays_disabled(self):
        api = self.apis["market_inventory_query"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/purchase/inventory/marketInventory/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["page"]["list_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "")
        self.assertEqual(api["date_field"], "")
        self.assertEqual(api["param_source"]["source_api_code"], "product_inventory_page")
        self.assertEqual(api["param_source"]["limit"], 3)
        self.assertEqual(
            api["param_source"]["fields"],
            [
                {"source_field": "raw_json.sku", "target_field": "sku"},
                {"source_field": "raw_json.warehouseId", "target_field": "warehouseId"},
            ],
        )

    def test_source_param_sets_read_multiple_fields_from_raw_json(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [
                {"source_0": "SKU-A", "source_1": "12"},
                {"source_0": "SKU-B", "source_1": "17"},
            ]
        )
        api = {
            "api_code": "market_inventory_query",
            "param_source": {
                "source_api_code": "product_inventory_page",
                "limit": 3,
                "fields": [
                    {"source_field": "raw_json.sku", "target_field": "sku"},
                    {"source_field": "raw_json.warehouseId", "target_field": "warehouseId"},
                ],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"sku": "SKU-A", "warehouseId": "12"}, {"sku": "SKU-B", "warehouseId": "17"}])
        self.assertEqual(connection.calls[0][1], {"source_api_code": "product_inventory_page", "limit": 3})
        self.assertIn("JSON_EXTRACT(raw_json, '$.sku')", str(connection.calls[0][0]))
        self.assertIn("JSON_EXTRACT(raw_json, '$.warehouseId')", str(connection.calls[0][0]))


if __name__ == "__main__":
    unittest.main()
