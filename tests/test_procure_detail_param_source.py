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

    def test_procure_detail_uses_lot_no_po_codes_with_missing_target_scan_and_is_enabled(self):
        self.assertIn("procure_detail", self.apis)
        api = self.apis["procure_detail"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/purchase/srm/procure/detail")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "")
        self.assertEqual(api["primary_key"]["param_field"], "poCode")
        self.assertFalse(api["primary_key"]["required"])
        self.assertEqual(api["date_field"], "")
        self.assertEqual(api["param_source"]["source_api_code"], "lot_no_page")
        self.assertEqual(api["param_source"]["limit"], 100)
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertTrue(api["param_source"]["exclude_existing_target"])
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

    def test_insert_procure_detail_can_use_request_po_code_as_primary_key_without_changing_raw_json(self):
        engine = SyncEngine([])
        connection = FakeConnection([])
        api = {
            "api_code": "procure_detail",
            "primary_key": {"field": "", "param_field": "poCode"},
            "date_field": "",
        }
        item = {"warehouseProcureItemVos": [{"procureItemVos": [{"code": "PO2209200001"}]}]}

        engine._insert_raw_items(connection, api, [item], "batch-001", source_primary_key="PO2209200001")

        rows = connection.calls[0][1]
        self.assertEqual(rows[0]["source_primary_key"], "PO2209200001")
        self.assertNotIn("poCode", rows[0]["raw_json"])


if __name__ == "__main__":
    unittest.main()
