import unittest

from app.config import load_api_configs
from app.doc_catalog import load_review_overrides


class SaleReturnOrderPageConfigTest(unittest.TestCase):
    def test_sale_return_order_page_returns_to_pending_after_successful_probe(self):
        api_configs = load_api_configs("config/api_config.example.yaml")
        reviews = load_review_overrides("config/api_review_overrides.yaml")

        self.assertFalse(
            any(item["api_code"] == "sale_return_order_page" for item in api_configs)
        )
        self.assertNotIn(9, reviews)


if __name__ == "__main__":
    unittest.main()
