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


class CountryProvinceParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_country_province_query_uses_fba_warehouse_country_and_is_enabled(self):
        self.assertIn("country_province_query", self.apis)
        api = self.apis["country_province_query"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/middle/base/countryProvince/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["page"]["list_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "")
        self.assertEqual(api["param_source"]["source_api_code"], "fba_warehouse_page")
        self.assertEqual(api["param_source"]["limit"], 3)
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertEqual(
            api["param_source"]["fields"],
            [{"source_field": "raw_json.country", "target_field": "countryCode"}],
        )

    def test_source_param_sets_read_country_codes_from_fba_warehouse_raw_json(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_0": "CA"}, {"source_0": "US"}])
        api = {
            "api_code": "country_province_query",
            "param_source": {
                "source_api_code": "fba_warehouse_page",
                "limit": 3,
                "fields": [{"source_field": "raw_json.country", "target_field": "countryCode"}],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"countryCode": "CA"}, {"countryCode": "US"}])
        self.assertEqual(connection.calls[0][1], {"source_api_code": "fba_warehouse_page", "limit": 3, "offset": 0})
        self.assertIn("JSON_EXTRACT(raw_json, '$.country')", str(connection.calls[0][0]))


if __name__ == "__main__":
    unittest.main()
