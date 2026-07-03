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


class DeliveryFeeParamSourceTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_delivery_fee_uses_outbound_fcodes_and_stays_disabled(self):
        self.assertIn("delivery_fee_query", self.apis)
        api = self.apis["delivery_fee_query"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/fulfillment/ship/deliveryFee/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["response"]["item_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "code")
        self.assertTrue(api["primary_key"]["required"])
        self.assertEqual(api["date_field"], "createdAt")
        self.assertEqual(api["param_source"]["source_api_code"], "storage_inbound_page")
        self.assertEqual(api["param_source"]["limit"], 3)
        self.assertTrue(api["param_source"]["auto_advance"])
        self.assertEqual(
            api["param_source"]["fields"],
            [{"source_field": "raw_json.fcode", "target_field": "code"}],
        )
        self.assertEqual(
            api["param_source"]["filters"],
            [{"source_field": "raw_json.opType", "equals": "OROutbound"}],
        )

    def test_source_param_sets_filter_delivery_fcodes_by_op_type(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [{"source_0": "FO2409200112422392484582"}, {"source_0": "FO2409200242871875383389"}]
        )
        api = {
            "api_code": "delivery_fee_query",
            "param_source": {
                "source_api_code": "storage_inbound_page",
                "limit": 3,
                "fields": [{"source_field": "raw_json.fcode", "target_field": "code"}],
                "filters": [{"source_field": "raw_json.opType", "equals": "OROutbound"}],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(
            params,
            [{"code": "FO2409200112422392484582"}, {"code": "FO2409200242871875383389"}],
        )
        self.assertEqual(
            connection.calls[0][1],
            {
                "source_api_code": "storage_inbound_page",
                "limit": 3,
                "offset": 0,
                "filter_0": "OROutbound",
            },
        )
        sql = str(connection.calls[0][0])
        self.assertIn("JSON_EXTRACT(raw_json, '$.fcode')", sql)
        self.assertIn("JSON_EXTRACT(raw_json, '$.opType')", sql)
        self.assertIn("= :filter_0", sql)

    def test_required_primary_key_skips_empty_detail_object(self):
        engine = SyncEngine([])
        api = {
            "api_code": "delivery_fee_query",
            "response": {"item_field": "data"},
            "primary_key": {"field": "code", "required": True},
        }
        payload = {"code": 0, "data": {"code": None, "createdAt": None, "id": None}}

        self.assertEqual(engine._response_items(payload, api), [])


if __name__ == "__main__":
    unittest.main()
