import unittest

from app.config import load_api_configs


class ShipmentDataPageConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {
            api["api_code"]: api
            for api in load_api_configs("config/api_config.example.yaml")
        }

    def test_shipment_data_page_uses_date_window_and_stays_disabled(self):
        self.assertIn("shipment_data_page", self.apis)
        api = self.apis["shipment_data_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/ship/shipmentData/page")
        self.assertTrue(api["page"]["enabled"])
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["page_size"], 100)
        self.assertEqual(api["page"]["max_pages"], 12)
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "")
        self.assertEqual(api["date_field"], "receivingAt")
        self.assertTrue(api["date_window"]["enabled"])
        self.assertEqual(api["date_window"]["start_field"], "receivingDateBegin")
        self.assertEqual(api["date_window"]["end_field"], "receivingDateEnd")
        self.assertEqual(api["date_window"]["default_start"], "2026-07-02")
        self.assertEqual(api["date_window"]["days"], 1)
        self.assertEqual(api["params"]["page"], 1)
        self.assertEqual(api["params"]["pagesize"], 100)


if __name__ == "__main__":
    unittest.main()
