import unittest

from app.sync_engine import SyncEngine


class FakeConnection:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))


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


class CommitPerPageSyncEngine(SyncEngine):
    def __init__(self, api_configs, engine):
        super().__init__(api_configs, engine)
        self.request_pages = []

    def _new_batch_no(self):
        return "sync_test_commit_per_page"

    def _request_with_retry(self, api, api_client, token, params):
        page_no = int(params["page"])
        self.request_pages.append(page_no)
        return {"data": {"rows": [{"id": page_no}], "total": 3}}, 1


class SyncApiCommitPerPageTest(unittest.TestCase):
    def test_single_api_commit_per_page_writes_each_page_in_short_transaction(self):
        fake_engine = FakeEngine()
        sync_engine = CommitPerPageSyncEngine(
            [
                {
                    "api_code": "wide_report",
                    "enabled": False,
                    "commit_per_page": True,
                    "params": {"page": 1, "pagesize": 1},
                    "page": {
                        "enabled": True,
                        "page_no_field": "page",
                        "page_size_field": "pagesize",
                        "page_size": 1,
                        "max_pages": 3,
                        "list_field": "data.rows",
                        "total_field": "data.total",
                    },
                    "primary_key": {"field": "id"},
                    "date_field": "",
                }
            ],
            fake_engine,
        )

        result = sync_engine.test_api_once("wide_report", api_client=object(), token=object())

        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["request_count"], 3)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(sync_engine.request_pages, [1, 2, 3])
        self.assertEqual([connection.name for connection in fake_engine.connections], ["tx-1", "tx-2", "tx-3", "tx-4", "tx-5", "tx-6"])
        raw_write_transactions = [
            connection.name
            for connection in fake_engine.connections
            if any("INSERT INTO raw_api_data" in statement for statement, _ in connection.calls)
        ]
        self.assertEqual(raw_write_transactions, ["tx-2", "tx-3", "tx-4"])


if __name__ == "__main__":
    unittest.main()
