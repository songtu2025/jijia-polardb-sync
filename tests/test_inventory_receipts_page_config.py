import unittest

from app.config import load_api_configs


class InventoryReceiptsPageConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {
            api["api_code"]: api
            for api in load_api_configs("config/api_config.example.yaml")
        }

    def test_inventory_receipts_page_uses_market_date_window_and_stays_disabled(self):
        self.assertIn("inventory_receipts_page", self.apis)
        api = self.apis["inventory_receipts_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/store/inventoryReceipts/page")
        self.assertTrue(api["page"]["enabled"])
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["page_size"], 100)
        self.assertEqual(api["page"]["max_pages"], 1)
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "marketTimeZone")
        self.assertTrue(api["date_window"]["enabled"])
        self.assertEqual(api["date_window"]["start_field"], "marketDateBegin")
        self.assertEqual(api["date_window"]["end_field"], "marketDateEnd")
        self.assertEqual(api["date_window"]["default_start"], "2026-07-02")
        self.assertEqual(api["date_window"]["days"], 1)
        self.assertEqual(api["params"]["page"], 1)
        self.assertEqual(api["params"]["pagesize"], 100)


if __name__ == "__main__":
    unittest.main()
