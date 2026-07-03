import json
import unittest

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


class NestedArrayParamSourceTest(unittest.TestCase):
    def test_source_param_sets_expand_raw_json_array_values(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [
                {
                    "raw_json": json.dumps(
                        {
                            "sellerId": "A",
                            "marketListVos": [
                                {"marketId": 11, "marketName": "US"},
                                {"marketId": 22, "marketName": "CA"},
                            ],
                        }
                    )
                },
                {
                    "raw_json": json.dumps(
                        {
                            "sellerId": "B",
                            "marketListVos": [
                                {"marketId": 22, "marketName": "CA"},
                                {"marketId": 33, "marketName": "MX"},
                            ],
                        }
                    )
                },
            ]
        )
        api = {
            "api_code": "ads_coupon_query",
            "param_source": {
                "source_api_code": "amazon_shop_page",
                "limit": 2,
                "fields": [
                    {"source_field": "raw_json.marketListVos[].marketId", "target_field": "marketId"},
                ],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"marketId": "11"}, {"marketId": "22"}])
        self.assertIn("raw_json", str(connection.calls[0][0]))
        self.assertEqual(connection.calls[0][1], {"source_api_code": "amazon_shop_page"})


if __name__ == "__main__":
    unittest.main()
