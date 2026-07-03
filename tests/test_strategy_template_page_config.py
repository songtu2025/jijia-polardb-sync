import unittest

from app.config import load_api_configs


class StrategyTemplatePageConfigTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_strategy_template_page_uses_records_window_and_stays_disabled(self):
        self.assertIn("strategy_template_page", self.apis)
        api = self.apis["strategy_template_page"]

        self.assertFalse(api["enabled"])
        self.assertEqual(api["method"], "POST")
        self.assertEqual(api["path"], "/operation/ads/strategyTemplate/page")
        self.assertTrue(api["page"]["enabled"])
        self.assertEqual(api["page"]["page_no_field"], "page")
        self.assertEqual(api["page"]["page_size_field"], "pagesize")
        self.assertEqual(api["page"]["page_size"], 100)
        self.assertEqual(api["page"]["max_pages"], 3)
        self.assertEqual(api["page"]["list_field"], "data.records")
        self.assertEqual(api["page"]["total_field"], "data.total")
        self.assertEqual(api["primary_key"]["field"], "id")
        self.assertEqual(api["date_field"], "updateTime")
        self.assertEqual(api["params"]["page"], 1)
        self.assertEqual(api["params"]["pagesize"], 100)
        self.assertEqual(api["params"]["model"], {})


if __name__ == "__main__":
    unittest.main()
