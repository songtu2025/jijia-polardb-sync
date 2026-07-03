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


class ProductDetailParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_product_detail_config_uses_product_page_ids_and_stays_disabled(self):
        api = self.apis["product_detail"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/purchase/goods/product/detail")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "")
        self.assertEqual(api["param_source"]["source_api_code"], "product_page")
        self.assertEqual(api["param_source"]["source_field"], "source_primary_key")
        self.assertEqual(api["param_source"]["target_field"], "id")
        self.assertEqual(api["param_source"]["limit"], 500)
        self.assertIn("auto_advance", api["param_source"])
        self.assertTrue(api["param_source"]["auto_advance"])

    def test_response_items_accepts_single_dict_item_field(self):
        engine = SyncEngine([])
        api = {"api_code": "product_detail", "response": {"item_field": "data"}}

        items = engine._response_items({"data": {"id": 123, "name": "A"}}, api)

        self.assertEqual(items, [{"id": 123, "name": "A"}])

    def test_source_param_sets_read_source_primary_keys(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_value": "101"}, {"source_value": "202"}])
        api = {
            "api_code": "product_detail",
            "param_source": {
                "source_api_code": "product_page",
                "source_field": "source_primary_key",
                "target_field": "id",
                "limit": 3,
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"id": "101"}, {"id": "202"}])
        self.assertEqual(connection.calls[0][1], {"source_api_code": "product_page", "limit": 3, "offset": 0})

    def test_param_source_config_error_is_recorded_as_api_failure(self):
        engine = SyncEngine([])
        connection = FakeConnection([])
        api = {
            "api_code": "bad_detail",
            "param_source": {
                "source_api_code": "product_page",
                "source_field": "raw_json.id",
                "target_field": "id",
                "limit": 3,
            },
        }

        result = engine._sync_api_from_param_source_in_batch(connection, api, "batch-001", object(), object())

        self.assertEqual(result, {"item_count": 0, "request_count": 0, "failed_count": 1})
        self.assertEqual(connection.calls[0][1]["api_code"], "bad_detail")
        self.assertEqual(connection.calls[0][1]["status"], "failed")
        self.assertIn("unsupported param source field", connection.calls[0][1]["error_message"])


if __name__ == "__main__":
    unittest.main()
