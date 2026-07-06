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

    def first(self):
        if not self.rows:
            return None
        return self.rows[0]


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params))
        return FakeResult(self.rows)


class StorageInboundDetailParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_storage_inbound_detail_uses_missing_storage_inbound_codes_and_stays_disabled(self):
        self.assertIn("storage_inbound_detail", self.apis)
        api = self.apis["storage_inbound_detail"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/purchase/inventory/storageInbound/detail")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "code")
        self.assertEqual(api["date_field"], "createdAt")
        self.assertEqual(api["param_source"]["source_api_code"], "storage_inbound_page")
        self.assertEqual(api["param_source"]["limit"], 5000)
        self.assertIn("auto_advance", api["param_source"])
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertTrue(api["param_source"]["exclude_existing_target"])
        self.assertEqual(
            api["param_source"]["fields"],
            [{"source_field": "raw_json.code", "target_field": "code"}],
        )

    def test_source_param_sets_read_storage_inbound_codes_from_raw_json(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_0": "GIB00922092000000001"}, {"source_0": "GIB00922092100000002"}])
        api = {
            "api_code": "storage_inbound_detail",
            "param_source": {
                "source_api_code": "storage_inbound_page",
                "limit": 3,
                "fields": [{"source_field": "raw_json.code", "target_field": "code"}],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"code": "GIB00922092000000001"}, {"code": "GIB00922092100000002"}])
        self.assertEqual(connection.calls[0][1], {"source_api_code": "storage_inbound_page", "limit": 3, "offset": 0})
        self.assertIn("JSON_EXTRACT(raw_json, '$.code')", str(connection.calls[0][0]))


if __name__ == "__main__":
    unittest.main()
