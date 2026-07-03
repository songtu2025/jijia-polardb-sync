import unittest

from app.sync_engine import SyncEngine


class FakeConnection:
    def __init__(self, name):
        self.name = name
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
        return False


class FakeEngine:
    def __init__(self):
        self.connections = []

    def begin(self):
        return FakeTransaction(self, f"tx-{len(self.connections) + 1}")


class TransactionScopedSyncEngine(SyncEngine):
    def __init__(self, api_configs, engine):
        super().__init__(api_configs, engine)
        self.api_connection_names = []

    def _new_batch_no(self):
        return "sync_test_5w"

    def _sync_api_in_batch(self, connection, api, batch_no, api_client, token):
        self.api_connection_names.append(connection.name)
        return {"item_count": 1, "request_count": 1, "failed_count": 0}


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


if __name__ == "__main__":
    unittest.main()
