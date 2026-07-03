import unittest

from app.config import load_api_configs


class StorageLedgerPageConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {
            api["api_code"]: api
            for api in load_api_configs("config/api_config.example.yaml")
        }

    def test_storage_ledger_page_uses_nested_date_window_and_stays_disabled(self):
        self.assertIn("storage_ledger_page", self.apis)
        api = self.apis["storage_ledger_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/inventory/storageLedger/page")
        self.assertTrue(api["page"]["enabled"])
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["page_size"], 100)
        self.assertEqual(api["page"]["max_pages"], 1)
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "")
        self.assertEqual(api["date_field"], "reportDate")
        self.assertTrue(api["date_window"]["enabled"])
        self.assertEqual(api["date_window"]["start_field"], "model.reportStartDate")
        self.assertEqual(api["date_window"]["end_field"], "model.reportEndDate")
        self.assertEqual(api["date_window"]["default_start"], "2026-07-02")
        self.assertEqual(api["date_window"]["days"], 1)
        self.assertEqual(api["params"]["page"], 1)
        self.assertEqual(api["params"]["pagesize"], 100)
        self.assertEqual(api["params"]["model"], {})


if __name__ == "__main__":
    unittest.main()
