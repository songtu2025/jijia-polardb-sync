import unittest
from sqlalchemy.exc import OperationalError, PendingRollbackError


from app.sync_engine import SyncEngine


class FakeConnection:
    def __init__(self, name):
        self.name = name
        self.rolled_back = False
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params or {}))


class FakeTransaction:
    def __init__(self, engine, name):
        self.engine = engine
        self.connection = FakeConnection(name)

    def __enter__(self):
        self.engine.connections.append(self.connection)
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        self.connection.rolled_back = exc_type is not None
        return False


class FakeEngine:
    def __init__(self):
        self.connections = []

    def begin(self):
        return FakeTransaction(self, f"tx-{len(self.connections) + 1}")

class InvalidatingConnection(FakeConnection):
    def __init__(self, name, engine):
        super().__init__(name)
        self.engine = engine
        self.invalidated = False

    def execute(self, statement, params=None):
        if self.invalidated:
            raise PendingRollbackError("transaction is invalidated")
        self.statements.append((str(statement), params or {}))
        if self.engine.invalidated_writes_remaining <= 0:
            return None
        if "INSERT INTO raw_api_data" not in str(statement):
            return None
        self.engine.invalidated_writes_remaining -= 1
        self.invalidated = True
        raise OperationalError(
            str(statement),
            params,
            OSError("lost connection"),
            connection_invalidated=True,
        )


class InvalidatingTransaction(FakeTransaction):
    def __init__(self, engine, name):
        super().__init__(engine, name)
        self.connection = InvalidatingConnection(name, engine)


class InvalidatingEngine(FakeEngine):
    def __init__(self):
        super().__init__()
        self.invalidated_writes_remaining = 1

    def begin(self):
        return InvalidatingTransaction(self, f"tx-{len(self.connections) + 1}")


class OnePageApiClient:
    def request(self, api, token, params):
        return {"data": {"rows": [{"id": api["api_code"]}]}}


class RecoveringSyncEngine(SyncEngine):
    def _new_batch_no(self):
        return "sync_test_invalidated_transaction"


def regular_api(api_code):
    return {
        "api_code": api_code,
        "enabled": True,
        "params": {},
        "page": {
            "enabled": False,
            "list_field": "data.rows",
        },
        "primary_key": {"field": "id"},
        "date_field": "",
    }



class TransactionScopedSyncEngine(SyncEngine):
    def __init__(self, api_configs, engine):
        super().__init__(api_configs, engine)
        self.api_connection_names = []
        self.page_transaction_api_codes = []

    def _new_batch_no(self):
        return "sync_test_5w"

    def _sync_api_in_batch(self, connection, api, batch_no, api_client, token):
        self.api_connection_names.append(connection.name)
        return {"item_count": 1, "request_count": 1, "failed_count": 0}

    def _sync_api_with_page_transactions(self, api, batch_no, api_client, token):
        self.page_transaction_api_codes.append(api["api_code"])
        return {"item_count": 2, "request_count": 3, "failed_count": 0}


class SyncEnabledTransactionScopeTest(unittest.TestCase):
    def test_enabled_sync_commits_batch_and_each_api_separately(self):
        fake_engine = FakeEngine()
        sync_engine = TransactionScopedSyncEngine(
            [
                {"api_code": "first_api", "enabled": True},
                {"api_code": "second_api", "enabled": True},
            ],
            fake_engine,
        )

        result = sync_engine.sync_enabled_apis(api_client=object(), token=object())

        self.assertEqual(result["api_count"], 2)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual([conn.name for conn in fake_engine.connections], ["tx-1", "tx-2", "tx-3", "tx-4"])
        self.assertEqual(sync_engine.api_connection_names, ["tx-2", "tx-3"])

    def test_enabled_sync_dispatches_commit_per_page_without_outer_api_transaction(self):
        fake_engine = FakeEngine()
        sync_engine = TransactionScopedSyncEngine(
            [
                {"api_code": "regular_api", "enabled": True},
                {"api_code": "wide_report", "enabled": True, "commit_per_page": True},
            ],
            fake_engine,
        )

        result = sync_engine.sync_enabled_apis(api_client=object(), token=object())

        self.assertEqual(result["api_count"], 2)
        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["request_count"], 4)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(sync_engine.api_connection_names, ["tx-2"])
        self.assertEqual(sync_engine.page_transaction_api_codes, ["wide_report"])
        self.assertEqual([conn.name for conn in fake_engine.connections], ["tx-1", "tx-2", "tx-3"])

    def test_invalidated_api_transaction_logs_failure_and_continues_enabled_batch(self):
        fake_engine = InvalidatingEngine()
        sync_engine = RecoveringSyncEngine(
            [regular_api("first_api"), regular_api("second_api")],
            fake_engine,
        )

        result = sync_engine.sync_enabled_apis(
            api_client=OnePageApiClient(),
            token=object(),
        )

        self.assertEqual(result["api_count"], 2)
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertTrue(fake_engine.connections[1].rolled_back)
        failed_logs = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.statements
            if "INSERT INTO sync_api_log" in statement and params.get("status") == "failed"
        ]
        success_logs = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.statements
            if "INSERT INTO sync_api_log" in statement and params.get("status") == "success"
        ]
        self.assertEqual(failed_logs[0]["api_code"], "first_api")
        self.assertEqual(failed_logs[0]["request_count"], 1)
        self.assertEqual(failed_logs[0]["success_count"], 0)
        self.assertEqual(success_logs[0]["api_code"], "second_api")
        batch_updates = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.statements
            if "UPDATE sync_batch" in statement
        ]
        self.assertEqual(batch_updates[-1]["status"], "partial_failed")

    def test_single_api_invalidated_transaction_finishes_failed_batch(self):
        fake_engine = InvalidatingEngine()
        sync_engine = RecoveringSyncEngine(
            [regular_api("single_api")],
            fake_engine,
        )

        result = sync_engine.test_api_once(
            "single_api",
            api_client=OnePageApiClient(),
            token=object(),
        )

        self.assertEqual(result["item_count"], 0)
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertTrue(fake_engine.connections[1].rolled_back)
        batch_updates = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.statements
            if "UPDATE sync_batch" in statement
        ]
        self.assertEqual(batch_updates[-1]["status"], "failed")
        self.assertEqual(batch_updates[-1]["failed_api_count"], 1)


if __name__ == "__main__":
    unittest.main()
