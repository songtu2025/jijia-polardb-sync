import unittest

from app.config import load_api_configs


class AmazonShopPageConfigTest(unittest.TestCase):
    def test_amazon_shop_page_uses_short_page_completion(self):
        apis = {api["api_code"]: api for api in load_api_configs("config/api_config.example.yaml")}

        page = apis["amazon_shop_page"]["page"]
        self.assertEqual(page["list_field"], "data.rows")
        self.assertEqual(page["total_field"], "data.total")
        self.assertTrue(page["stop_on_short_page"])


if __name__ == "__main__":
    unittest.main()
