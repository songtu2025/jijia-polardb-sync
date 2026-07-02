import unittest

from app.config import load_api_configs


class Stage4OCandidateApiConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_kb_product_page_config_matches_doc_and_stays_disabled(self):
        api = self.apis["kb_product_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/goods/kbProduct/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateTime")

    def test_fba_warehouse_page_config_matches_doc_and_stays_disabled(self):
        api = self.apis["fba_warehouse_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/purchase/inventory/fbaWarehouse/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "createDate")
