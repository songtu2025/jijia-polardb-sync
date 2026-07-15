import unittest
from contextlib import nullcontext
from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError

import app.main as main_module


class MainErrorLoggingTest(unittest.TestCase):
    def test_single_api_logs_exception_type_and_message(self):
        sync_engine = Mock()
        sync_engine.test_api_once.side_effect = ValueError("inventory adjustments failed")
        auth_client = Mock()
        auth_client.get_access_token.return_value = object()

        with (
            patch.object(main_module, "create_db_engine", return_value=object()),
            patch.object(main_module, "_sync_task_lock", side_effect=lambda engine: nullcontext()),
            patch.object(main_module, "JijiaAuthClient", return_value=auth_client),
            patch.object(main_module, "JijiaApiClient", return_value=object()),
            patch.object(main_module, "SyncEngine", return_value=sync_engine),
            self.assertLogs("app.main", level="ERROR") as logs,
            self.assertRaises(SystemExit) as raised,
        ):
            main_module._run_single_api(object(), [], "inventory_adjustments_page", "sync api")

        self.assertEqual(raised.exception.code, 1)
        message = "\n".join(logs.output)
        self.assertIn("ValueError", message)
        self.assertIn("inventory adjustments failed", message)

    def test_sync_enabled_logs_exception_type_and_message(self):
        sync_engine = Mock()
        sync_engine.sync_enabled_apis.side_effect = SQLAlchemyError("database connection closed")
        auth_client = Mock()
        auth_client.get_access_token.return_value = object()

        with (
            patch.object(main_module, "create_db_engine", return_value=object()),
            patch.object(main_module, "_sync_task_lock", side_effect=lambda engine: nullcontext()),
            patch.object(main_module, "JijiaAuthClient", return_value=auth_client),
            patch.object(main_module, "JijiaApiClient", return_value=object()),
            patch.object(main_module, "SyncEngine", return_value=sync_engine),
            self.assertLogs("app.main", level="ERROR") as logs,
            self.assertRaises(SystemExit) as raised,
        ):
            main_module._sync_enabled(object(), [])

        self.assertEqual(raised.exception.code, 1)
        message = "\n".join(logs.output)
        self.assertIn("SQLAlchemyError", message)
        self.assertIn("database connection closed", message)


if __name__ == "__main__":
    unittest.main()
