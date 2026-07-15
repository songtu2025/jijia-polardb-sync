import argparse
import unittest

from sqlalchemy.exc import SQLAlchemyError

import app.main as main_module


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class FakeLockConnection:
    def __init__(self, lock_result):
        self.lock_result = lock_result
        self.statements = []
        self.params = []
        self.execution_options_calls = []
        self.closed = False

    def execution_options(self, **kwargs):
        self.execution_options_calls.append(kwargs)
        return self

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        self.params.append(params or {})
        if "GET_LOCK" in str(statement):
            return FakeScalarResult(self.lock_result)
        return FakeScalarResult(1)

    def close(self):
        self.closed = True


class FakeLockEngine:
    def __init__(self, lock_result):
        self.connection = FakeLockConnection(lock_result)

    def connect(self):
        return self.connection


class FakeReleaseFailLockConnection(FakeLockConnection):
    def execute(self, statement, params=None):
        if "RELEASE_LOCK" in str(statement):
            raise SQLAlchemyError("release failed")
        return super().execute(statement, params)


class FakeReleaseFailLockEngine(FakeLockEngine):
    def __init__(self):
        self.connection = FakeReleaseFailLockConnection(lock_result=1)


class SyncTaskLockTest(unittest.TestCase):
    def test_exits_before_task_when_named_lock_is_unavailable(self):
        engine = FakeLockEngine(lock_result=0)

        with self.assertLogs("app.main", level="ERROR"):
            with self.assertRaises(SystemExit) as raised:
                with main_module._sync_task_lock(engine):
                    self.fail("task body must not run without the named lock")

        self.assertEqual(raised.exception.code, 1)
        self.assertIn({"isolation_level": "AUTOCOMMIT"}, engine.connection.execution_options_calls)
        self.assertIn("GET_LOCK", engine.connection.statements[0])
        self.assertEqual(engine.connection.params[0]["lock_name"], "jijia_polardb_sync_task")
        self.assertTrue(engine.connection.closed)
        self.assertFalse(any("RELEASE_LOCK" in statement for statement in engine.connection.statements))

    def test_releases_named_lock_when_task_raises(self):
        engine = FakeLockEngine(lock_result=1)

        with self.assertRaises(RuntimeError):
            with main_module._sync_task_lock(engine):
                raise RuntimeError("task failed")

        self.assertIn("GET_LOCK", engine.connection.statements[0])
        self.assertIn({"isolation_level": "AUTOCOMMIT"}, engine.connection.execution_options_calls)
        self.assertTrue(any("RELEASE_LOCK" in statement for statement in engine.connection.statements))
        self.assertTrue(engine.connection.closed)

    def test_release_failure_after_successful_task_does_not_fail_task(self):
        engine = FakeReleaseFailLockEngine()
        task_ran = False

        with self.assertLogs("app.main", level="WARNING") as logs:
            with main_module._sync_task_lock(engine):
                task_ran = True

        self.assertTrue(task_ran)
        self.assertTrue(engine.connection.closed)
        self.assertTrue(any("release sync task lock failed" in message for message in logs.output))
        self.assertTrue(any("SQLAlchemyError" in message for message in logs.output))
        self.assertTrue(any("release failed" in message for message in logs.output))

    def test_only_database_write_modes_require_sync_lock(self):
        args = argparse.Namespace(
            check_db=False,
            mock_sync=False,
            test_token=False,
            test_api=None,
            sync_api=None,
            sync_enabled=False,
            sync_api_configs=False,
        )
        self.assertFalse(main_module._requires_sync_lock(args))

        args.mock_sync = True
        self.assertTrue(main_module._requires_sync_lock(args))
        args.mock_sync = False
        args.sync_api_configs = True
        self.assertTrue(main_module._requires_sync_lock(args))
        args.sync_api_configs = False
        args.sync_enabled = True
        self.assertTrue(main_module._requires_sync_lock(args))
        args.sync_enabled = False
        args.sync_api = "amazon_shop_page"
        self.assertTrue(main_module._requires_sync_lock(args))
        args.sync_api = None
        args.test_api = "amazon_shop_page"
        self.assertTrue(main_module._requires_sync_lock(args))


if __name__ == "__main__":
    unittest.main()
