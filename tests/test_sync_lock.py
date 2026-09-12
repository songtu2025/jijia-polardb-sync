import unittest
from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app.sync_lock import (
    SYNC_TASK_LOCK_NAME,
    SyncTaskLockUnavailable,
    sync_task_lock,
    sync_task_lock_name,
)


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class FakeConnection:
    def __init__(self, lock_result=1, release_error=None):
        self.lock_result = lock_result
        self.release_error = release_error
        self.statements = []
        self.parameters = []
        self.closed = False

    def execution_options(self, **_kwargs):
        return self

    def execute(self, statement, _params=None):
        sql = str(statement)
        self.statements.append(sql)
        self.parameters.append(_params or {})
        if "RELEASE_LOCK" in sql and self.release_error is not None:
            raise self.release_error
        return FakeScalarResult(self.lock_result if "GET_LOCK" in sql else 1)

    def close(self):
        self.closed = True


class FakeEngine:
    def __init__(self, lock_result=1, dialect_name="mysql", release_error=None):
        self.connection = FakeConnection(lock_result, release_error)
        self.dialect = type("Dialect", (), {"name": dialect_name})()

    def connect(self):
        return self.connection


class SyncLockTest(unittest.TestCase):
    def test_lock_names_share_accounts_and_separate_different_accounts(self):
        self.assertEqual(sync_task_lock_name(), SYNC_TASK_LOCK_NAME)
        self.assertEqual(
            sync_task_lock_name("account", 7),
            sync_task_lock_name("account", 7),
        )
        self.assertNotEqual(
            sync_task_lock_name("account", 7),
            sync_task_lock_name("account", 8),
        )

    def test_account_lock_rejects_invalid_or_oversized_account_id(self):
        for account_id in (None, 0, -1, True, int("9" * 80)):
            with self.subTest(account_id=account_id), self.assertRaises(ValueError):
                sync_task_lock_name("account", account_id)

    def test_invalid_scope_is_rejected_before_sqlite_bypass(self):
        engine = FakeEngine(dialect_name="sqlite")

        with self.assertRaises(ValueError):
            with sync_task_lock(engine, scope=cast(Any, "invalid")):
                self.fail("非法锁范围不能执行任务")

    def test_mysql_lock_is_held_and_released(self):
        engine = FakeEngine()

        with sync_task_lock(engine):
            self.assertEqual(len(engine.connection.statements), 1)

        self.assertIn("GET_LOCK", engine.connection.statements[0])
        self.assertIn("RELEASE_LOCK", engine.connection.statements[1])
        self.assertTrue(engine.connection.closed)

    def test_mysql_account_lock_uses_stable_account_key(self):
        engine = FakeEngine()

        with sync_task_lock(engine, scope="account", account_id=42):
            pass

        self.assertEqual(len(engine.connection.statements), 2)
        self.assertEqual(
            engine.connection.parameters,
            [
                {"lock_name": "jijia_polardb_sync_account:42"},
                {"lock_name": "jijia_polardb_sync_account:42"},
            ],
        )

    def test_unavailable_mysql_lock_stops_before_task(self):
        engine = FakeEngine(lock_result=0)

        with self.assertRaises(SyncTaskLockUnavailable):
            with sync_task_lock(engine):
                self.fail("拿不到锁时不能执行任务")

        self.assertFalse(any("RELEASE_LOCK" in sql for sql in engine.connection.statements))
        self.assertTrue(engine.connection.closed)

    def test_mysql_lock_error_is_not_reported_as_contention(self):
        engine = FakeEngine(lock_result=None)

        with self.assertRaisesRegex(RuntimeError, "获取同步任务锁失败"):
            with sync_task_lock(engine):
                self.fail("数据库锁错误时不能执行任务")

        self.assertFalse(any("RELEASE_LOCK" in sql for sql in engine.connection.statements))
        self.assertTrue(engine.connection.closed)

    def test_sqlite_does_not_execute_mysql_lock_statement(self):
        engine = FakeEngine(dialect_name="sqlite")

        with sync_task_lock(engine):
            pass

        self.assertEqual(engine.connection.statements, [])
        self.assertFalse(engine.connection.closed)

    def test_release_error_log_does_not_include_exception_message(self):
        secret = "token=token-value appKey=app-key mysql://user:pass@db/private"
        engine = FakeEngine(release_error=SQLAlchemyError(secret))

        with self.assertLogs("app.sync_lock", level="WARNING") as logs:
            with sync_task_lock(engine):
                pass

        message = "\n".join(logs.output)
        self.assertIn("error_type=SQLAlchemyError", message)
        self.assertNotIn("token-value", message)
        self.assertNotIn("app-key", message)
        self.assertNotIn("mysql://", message)


if __name__ == "__main__":
    unittest.main()
