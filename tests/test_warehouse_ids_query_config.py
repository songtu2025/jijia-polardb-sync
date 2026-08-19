import unittest

from app.config import load_api_configs
from app.doc_catalog import load_review_overrides


class WarehouseIdsQueryConfigTest(unittest.TestCase):
    def test_warehouse_ids_query_is_deferred_after_runtime_rejection(self):
        apis = load_api_configs("config/api_config.example.yaml")
        reviews = load_review_overrides("config/api_review_overrides.yaml")

        self.assertFalse(
            any(api["api_code"] == "warehouse_ids_query" for api in apis)
        )
        self.assertEqual(
            reviews[1179]["status"],
            "defer_runtime_rejected",
        )


if __name__ == "__main__":
    unittest.main()
