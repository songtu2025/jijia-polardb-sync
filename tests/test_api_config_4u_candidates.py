import unittest

from app.config import load_api_configs


class Stage4UCandidateApiConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_product_inventory_page_config_matches_doc_and_is_enabled(self):
        api = self.apis["product_inventory_page"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/store/inventory/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertGreaterEqual(api["page"]["max_pages"], 1300)
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateTime")

    def test_storage_inbound_page_config_matches_doc_and_is_enabled(self):
        api = self.apis["storage_inbound_page"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/inventory/storageInbound/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertGreaterEqual(api["page"]["max_pages"], 1800)
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "createdAt")
