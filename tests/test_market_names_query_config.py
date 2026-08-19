import json
import unittest

from app.config import load_api_configs
from app.sync_engine import SyncEngine
from app.doc_catalog import load_review_overrides


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

    def execute(self, statement, params=None):
        return FakeResult(self.rows)


class MarketNamesQueryConfigTest(unittest.TestCase):
    def test_market_names_query_is_deferred_after_runtime_rejection(self):
        apis = load_api_configs("config/api_config.example.yaml")
        reviews = load_review_overrides("config/api_review_overrides.yaml")

        self.assertFalse(any(item["api_code"] == "market_names_query" for item in apis))
        self.assertEqual(
            reviews[1177]["status"],
            "defer_runtime_rejected",
        )

    def test_array_param_source_wraps_each_value_in_single_element_list(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [
                {
                    "raw_json": json.dumps(
                        {
                            "marketListVos": [
                                {"marketId": 11},
                                {"marketId": 22},
                            ]
                        }
                    )
                }
            ]
        )
        api = {
            "api_code": "market_names_query",
            "param_source": {
                "source_api_code": "amazon_shop_page",
                "limit": 3,
                "fields": [
                    {
                        "source_field": "raw_json.marketListVos[].marketId",
                        "target_field": "markerIds",
                        "wrap_in_list": True,
                    }
                ],
            },
        }

        params = engine._source_param_sets(connection, api, offset=0)

        self.assertEqual(params, [{"markerIds": ["11"]}, {"markerIds": ["22"]}])

    def test_array_param_source_keeps_existing_scalar_behavior_by_default(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [{"raw_json": json.dumps({"marketListVos": [{"marketId": 11}]})}]
        )
        api = {
            "api_code": "existing_scalar_query",
            "param_source": {
                "source_api_code": "amazon_shop_page",
                "limit": 1,
                "fields": [
                    {
                        "source_field": "raw_json.marketListVos[].marketId",
                        "target_field": "marketId",
                    }
                ],
            },
        }

        params = engine._source_param_sets(connection, api, offset=0)

        self.assertEqual(params, [{"marketId": "11"}])

    def test_single_element_array_param_uses_scalar_source_primary_key(self):
        engine = SyncEngine([])
        api = {"primary_key": {"param_field": "markerIds"}}

        source_primary_key = engine._source_primary_key_from_params(
            api,
            {"markerIds": ["11"]},
        )

        self.assertEqual(source_primary_key, "11")


if __name__ == "__main__":
    unittest.main()
