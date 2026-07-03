import unittest

from app.config import load_api_configs


class InventoryAgePageConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {
            api["api_code"]: api
            for api in load_api_configs("config/api_config.example.yaml")
        }

    def test_inventory_age_page_is_limited_and_stays_disabled(self):
        self.assertIn("inventory_age_page", self.apis)
        api = self.apis["inventory_age_page"]
        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/inventory/inventoryAge/page")
        self.assertTrue(api["page"]["enabled"])
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["page_size"], 10)
        self.assertEqual(api["page"]["max_pages"], 3)
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateDate")
        self.assertEqual(api["timeout_seconds"], 90)
        self.assertEqual(api["params"]["page"], 1)
        self.assertEqual(api["params"]["pagesize"], 10)


if __name__ == "__main__":
    unittest.main()
