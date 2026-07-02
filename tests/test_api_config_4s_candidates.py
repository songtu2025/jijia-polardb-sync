import unittest

from app.config import load_api_configs


class Stage4SCandidateApiConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_crm_tags_page_config_matches_doc_and_stays_disabled(self):
        api = self.apis["crm_tags_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "GET")
        self.assertEqual(api["path"], "/operation/crm/tags/page")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["page"]["list_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateTime")

    def test_inventory_team_query_config_matches_doc_and_stays_disabled(self):
        api = self.apis["inventory_team_query"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/fulfillment/inventory/teamManagement/query")
        self.assertFalse(api["page"]["enabled"])
        self.assertEqual(api["page"]["list_field"], "data")
        self.assertEqual(api["primary_key"]["field"], "teamId")
        self.assertEqual(api["date_field"], "")
