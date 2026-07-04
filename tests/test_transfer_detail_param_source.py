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


class TransferDetailParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_transfer_detail_uses_transfer_fcodes_and_stays_disabled(self):
        self.assertIn("transfer_detail", self.apis)
        api = self.apis["transfer_detail"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/inventory/transfer/detail")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "code")
        self.assertEqual(api["date_field"], "createDate")
        self.assertEqual(api["param_source"]["source_api_code"], "storage_inbound_page")
        self.assertEqual(api["param_source"]["limit"], 200)
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertEqual(
            api["param_source"]["fields"],
            [{"source_field": "raw_json.fcode", "target_field": "code"}],
        )
        self.assertEqual(
            api["param_source"]["filters"],
            [{"source_field": "raw_json.opType", "equals": "TFOutbound"}],
        )

    def test_source_param_sets_filter_transfer_fcodes_by_op_type(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_0": "TF20230616000001"}, {"source_0": "TF20230616000002"}])
        api = {
            "api_code": "transfer_detail",
            "param_source": {
                "source_api_code": "storage_inbound_page",
                "limit": 3,
                "fields": [{"source_field": "raw_json.fcode", "target_field": "code"}],
                "filters": [{"source_field": "raw_json.opType", "equals": "TFOutbound"}],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"code": "TF20230616000001"}, {"code": "TF20230616000002"}])
        self.assertEqual(
            connection.calls[0][1],
            {
                "source_api_code": "storage_inbound_page",
                "limit": 3,
                "offset": 0,
                "filter_0": "TFOutbound",
            },
        )
        sql = str(connection.calls[0][0])
        self.assertIn("JSON_EXTRACT(raw_json, '$.fcode')", sql)
        self.assertIn("JSON_EXTRACT(raw_json, '$.opType')", sql)
        self.assertIn("= :filter_0", sql)


if __name__ == "__main__":
    unittest.main()
