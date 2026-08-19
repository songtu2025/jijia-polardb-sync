import tempfile
import unittest
from pathlib import Path

from sqlalchemy.engine import URL

from app.config import AppSettings, load_api_configs
from app.sync_engine import SyncEngine


class ConfigValidationTest(unittest.TestCase):
    def test_database_url_preserves_reserved_password_characters(self):
        settings = AppSettings(
            db_host="db.example.invalid",
            db_port=3307,
            db_name="sync_db",
            db_user="sync_user",
            db_password="p@ss: /?#[]",
            _env_file=None,
        )

        database_url = settings.database_url

        self.assertIsInstance(database_url, URL)
        self.assertEqual(database_url.username, "sync_user")
        self.assertEqual(database_url.password, "p@ss: /?#[]")
        self.assertEqual(database_url.host, "db.example.invalid")
        self.assertEqual(database_url.port, 3307)
        self.assertEqual(database_url.database, "sync_db")
        self.assertEqual(database_url.query, {"charset": "utf8mb4"})

    def test_api_config_rejects_missing_or_non_boolean_enabled(self):
        invalid_configs = {
            "missing enabled": """
apis:
  - api_code: first_api
    path: /first
""",
            "string enabled": """
apis:
  - api_code: first_api
    path: /first
    enabled: "false"
""",
        }

        for case_name, content in invalid_configs.items():
            with self.subTest(case=case_name):
                with self.assertRaises(ValueError):
                    self._load_yaml(content)

    def test_api_config_rejects_duplicate_api_code(self):
        with self.assertRaises(ValueError):
            self._load_yaml(
                """
apis:
  - api_code: duplicate_api
    path: /shared
    enabled: true
  - api_code: duplicate_api
    path: /shared
    enabled: false
"""
            )

    def test_api_config_rejects_missing_identity_or_path(self):
        invalid_configs = {
            "missing api_code": """
apis:
  - path: /first
    enabled: true
""",
            "missing path": """
apis:
  - api_code: first_api
    enabled: true
""",
        }

        for case_name, content in invalid_configs.items():
            with self.subTest(case=case_name):
                with self.assertRaises(ValueError):
                    self._load_yaml(content)

    def test_shared_path_is_valid_when_api_codes_are_unique(self):
        apis = self._load_yaml(
            """
apis:
  - api_code: first_api
    path: /shared
    enabled: true
  - api_code: second_api
    path: /shared
    enabled: false
"""
        )

        self.assertEqual(
            [api["api_code"] for api in apis],
            ["first_api", "second_api"],
        )

    def test_enabled_apis_accepts_only_explicit_true(self):
        engine = SyncEngine(
            [
                {"api_code": "enabled_api", "enabled": True},
                {"api_code": "disabled_api", "enabled": False},
                {"api_code": "missing_enabled"},
                {"api_code": "string_enabled", "enabled": "true"},
            ]
        )

        self.assertEqual(
            engine._enabled_apis(),
            [{"api_code": "enabled_api", "enabled": True}],
        )

    @staticmethod
    def _load_yaml(content):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "api.yaml"
            config_path.write_text(content, encoding="utf-8")
            return load_api_configs(config_path)


if __name__ == "__main__":
    unittest.main()
