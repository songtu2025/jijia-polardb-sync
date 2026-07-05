import unittest

from app.config import load_api_configs


class LowRiskEnabledConfigs5VTest(unittest.TestCase):
    def setUp(self):
        self.apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

    def test_small_verified_configs_are_enabled_for_daily_sync(self):
        enabled_codes = {code for code, api in self.apis.items() if api["enabled"]}

        self.assertEqual(len(enabled_codes), 45)
        self.assertIn("base_currency_query", enabled_codes)
        self.assertIn("storage_return_page", enabled_codes)
        self.assertIn("strategy_template_page", enabled_codes)
        self.assertIn("platform_msku_page", enabled_codes)
        self.assertIn("amazon_msku_page", enabled_codes)
        self.assertIn("fba_inventory_page", enabled_codes)
        self.assertIn("fba_inventory_v2_page", enabled_codes)
        self.assertIn("traffic_sku_page", enabled_codes)
        self.assertIn("traffic_page", enabled_codes)
        self.assertIn("traffic_analysis_page", enabled_codes)
        self.assertIn("storage_ledger_page", enabled_codes)
        self.assertIn("storage_ledger_month_page", enabled_codes)
        self.assertIn("storage_ledger_detail_page", enabled_codes)
        self.assertIn("inventory_adjustments_page", enabled_codes)
        self.assertIn("purchase_sale_storage_fba_page", enabled_codes)
        self.assertIn("inventory_receipts_page", enabled_codes)
        self.assertIn("shipment_data_page", enabled_codes)
        self.assertIn("country_province_query", enabled_codes)
        self.assertIn("product_detail", enabled_codes)
        self.assertIn("purchase_plan_page", enabled_codes)
        self.assertIn("transfer_detail", enabled_codes)
        self.assertIn("lot_no_detail", enabled_codes)
        self.assertIn("transfer_page", enabled_codes)
        self.assertIn("lot_no_page", enabled_codes)
        self.assertIn("procure_detail", enabled_codes)


if __name__ == "__main__":
    unittest.main()
