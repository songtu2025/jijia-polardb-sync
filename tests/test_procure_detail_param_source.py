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


class ProcureDetailParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_procure_detail_uses_lot_no_po_codes_and_stays_disabled(self):
        self.assertIn("procure_detail", self.apis)
        api = self.apis["procure_detail"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/purchase/srm/procure/detail")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "")
        self.assertFalse(api["primary_key"]["required"])
        self.assertEqual(api["date_field"], "")
        self.assertEqual(api["param_source"]["source_api_code"], "lot_no_page")
        self.assertEqual(api["param_source"]["limit"], 3)
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertEqual(
            api["param_source"]["fields"],
            [{"source_field": "raw_json.poCode", "target_field": "poCode"}],
        )

    def test_source_param_sets_read_procure_po_codes_from_lot_no_page(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_0": "PO2209200001"}, {"source_0": "PO2209210002"}])
        api = {
            "api_code": "procure_detail",
            "param_source": {
                "source_api_code": "lot_no_page",
                "limit": 3,
                "fields": [{"source_field": "raw_json.poCode", "target_field": "poCode"}],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"poCode": "PO2209200001"}, {"poCode": "PO2209210002"}])
        self.assertEqual(
            connection.calls[0][1],
            {
                "source_api_code": "lot_no_page",
                "limit": 3,
                "offset": 0,
            },
        )
        sql = str(connection.calls[0][0])
        self.assertIn("JSON_EXTRACT(raw_json, '$.poCode')", sql)


if __name__ == "__main__":
    unittest.main()
