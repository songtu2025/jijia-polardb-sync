import unittest

from app.config import load_api_configs
from app.sync_engine import SyncEngine


class BaseCurrencyScalarResponseTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_base_currency_query_wraps_scalar_data_and_is_enabled(self):
        self.assertIn("base_currency_query", self.apis)
        api = self.apis["base_currency_query"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/middle/base/baseCurrency/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["scalar_field"], "data")
        self.assertEqual(api["response"]["scalar_target_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "data")
        self.assertEqual(api["date_field"], "")

    def test_scalar_response_field_is_wrapped_as_one_raw_item(self):
        engine = SyncEngine([])
        api = {
            "api_code": "base_currency_query",
            "response": {"scalar_field": "data", "scalar_target_field": "data"},
            "primary_key": {"field": "data", "required": True},
        }

        self.assertEqual(engine._response_items({"code": 200, "data": "CNY"}, api), [{"data": "CNY"}])

    def test_required_scalar_primary_key_skips_empty_value(self):
        engine = SyncEngine([])
        api = {
            "api_code": "base_currency_query",
            "response": {"scalar_field": "data", "scalar_target_field": "data"},
            "primary_key": {"field": "data", "required": True},
        }

        self.assertEqual(engine._response_items({"code": 200, "data": ""}, api), [])


if __name__ == "__main__":
    unittest.main()
