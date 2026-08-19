import unittest

from app.config import load_api_configs
from app.doc_catalog import load_review_overrides
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


class QuickInboundQueryConfigTest(unittest.TestCase):
    def test_quick_inbound_query_is_deferred_after_runtime_rejection(self):
        apis = load_api_configs("config/api_config.example.yaml")
        reviews = load_review_overrides("config/api_review_overrides.yaml")

        self.assertFalse(
            any(item["api_code"] == "quick_inbound_query" for item in apis)
        )
        self.assertEqual(reviews[1080]["status"], "defer_runtime_rejected")

    def test_top_level_param_source_wraps_each_value_in_single_element_list(self):
        engine = SyncEngine([])
        connection = FakeConnection(
            [
                {"source_0": "PO-FICTIONAL-001"},
                {"source_0": "PO-FICTIONAL-002"},
            ]
        )
        api = {
            "api_code": "quick_inbound_query",
            "param_source": {
                "source_api_code": "procure_page",
                "limit": 3,
                "fields": [
                    {
                        "source_field": "raw_json.code",
                        "target_field": "data",
                        "wrap_in_list": True,
                    }
                ],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(
            params,
            [
                {"data": ["PO-FICTIONAL-001"]},
                {"data": ["PO-FICTIONAL-002"]},
            ],
        )

    def test_top_level_param_source_keeps_scalar_behavior_by_default(self):
        engine = SyncEngine([])
        connection = FakeConnection([{"source_0": "PO-FICTIONAL-001"}])
        api = {
            "api_code": "existing_scalar_query",
            "param_source": {
                "source_api_code": "procure_page",
                "limit": 1,
                "fields": [
                    {
                        "source_field": "raw_json.code",
                        "target_field": "code",
                    }
                ],
            },
        }

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"code": "PO-FICTIONAL-001"}])


if __name__ == "__main__":
    unittest.main()
