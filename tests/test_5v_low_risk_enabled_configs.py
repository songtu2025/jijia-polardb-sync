import unittest

from app.config import load_api_configs


class LowRiskEnabledConfigs5VTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_small_verified_configs_are_enabled_for_daily_sync(self):
        enabled_codes = {code for code, api in self.apis.items() if api["enabled"]}

        self.assertEqual(len(enabled_codes), 25)
        self.assertIn("base_currency_query", enabled_codes)
        self.assertIn("storage_return_page", enabled_codes)
        self.assertIn("strategy_template_page", enabled_codes)
        self.assertIn("platform_msku_page", enabled_codes)
        self.assertIn("traffic_sku_page", enabled_codes)


if __name__ == "__main__":
    unittest.main()
