import unittest

from app.config import load_api_configs


class ProductCandidateApiConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_product_page_config_matches_doc_and_stays_disabled(self):
        api = self.apis["product_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/goods/product/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertGreaterEqual(api["page"]["max_pages"], 90)
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "lastDate")

    def test_parent_product_page_config_matches_doc_and_stays_disabled(self):
        api = self.apis["parent_product_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/goods/parentProduct/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "lastDate")
