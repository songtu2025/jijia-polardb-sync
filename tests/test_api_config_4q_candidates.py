import unittest

from app.config import load_api_configs


class Stage4QCandidateApiConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_store_location_page_config_matches_doc_and_is_enabled(self):
        api = self.apis["store_location_page"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/store/location/page")
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["list_field"], "data.rows")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateTime")

    def test_multi_shop_query_config_matches_doc_and_is_enabled(self):
        api = self.apis["multi_shop_query"]

        self.assertTrue(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/platform/multiplatform/multiShop/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["page"]["list_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "shopId")
        self.assertEqual(api["date_field"], "")
