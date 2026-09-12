import unittest

from sqlalchemy.exc import OperationalError

from app.sync_engine import SyncEngine


class FakeResult:
    def mappings(self):
        return self

    def all(self):
        return []


class FakeConnection:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return FakeResult()


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


class InvalidatedOnceConnection(FakeConnection):
    def __init__(self, name, engine):
        super().__init__(name)
        self.engine = engine

    def execute(self, statement, params=None):
        result = super().execute(statement, params)
        if self.engine.invalidated_writes_remaining > 0 and "INSERT INTO raw_api_data" in str(
            statement
        ):
            self.engine.invalidated_writes_remaining -= 1
            raise OperationalError(
                str(statement),
                params,
                OSError("lost connection"),
                connection_invalidated=True,
            )
        return result


class InvalidatedOnceTransaction(FakeTransaction):
    def __enter__(self):
        self.connection = InvalidatedOnceConnection(self.connection.name, self.engine)
        self.engine.connections.append(self.connection)
        return self.connection


class InvalidatedOnceEngine(FakeEngine):
    def __init__(self):
        super().__init__()
        self.invalidated_writes_remaining = 1

    def begin(self):
        return InvalidatedOnceTransaction(self, f"tx-{len(self.connections) + 1}")


class CommitPerPageSyncEngine(SyncEngine):
    def __init__(self, api_configs, engine, progress_callback=None):
        super().__init__(
            api_configs,
            engine,
            progress_callback=progress_callback,
        )
        self.request_pages = []

    def _new_batch_no(self):
        return "sync_test_commit_per_page"

    def _request_with_retry(self, api, api_client, token, params):
        page_no = int(params["page"])
        self.request_pages.append(page_no)
        return {"data": {"rows": [{"id": page_no}], "total": 3}}, 1


class TruncatedCommitPerPageSyncEngine(CommitPerPageSyncEngine):
    def _request_with_retry(self, api, api_client, token, params):
        page_no = int(params["page"])
        self.request_pages.append(page_no)
        start = (page_no - 1) * 20
        rows = [{"id": item_id} for item_id in range(start, start + 20)]
        return {"data": {"rows": rows, "total": 101}}, 1


class FailingSecondPageSyncEngine(CommitPerPageSyncEngine):
    def _insert_raw_items_in_page_transaction(self, api, items, batch_no, **kwargs):
        if self.request_pages[-1] == 2:
            raise RuntimeError("mock second page write failure")
        return super()._insert_raw_items_in_page_transaction(
            api,
            items,
            batch_no,
            **kwargs,
        )


class FailingPausedLogSyncEngine(CommitPerPageSyncEngine):
    def _insert_api_log(self, connection, batch_no, api_code, status, *args, **kwargs):
        if status == "paused":
            raise RuntimeError("mock paused log failure")
        return super()._insert_api_log(
            connection,
            batch_no,
            api_code,
            status,
            *args,
            **kwargs,
        )


class ConflictingResultSyncEngine(CommitPerPageSyncEngine):
    def _sync_api_with_page_transactions(self, api, batch_no, api_client, token):
        return {
            "item_count": 1,
            "request_count": 1,
            "failed_count": 1,
            "paused": True,
        }


class SyncApiCommitPerPageTest(unittest.TestCase):
    def test_failure_after_pause_clears_pause_and_finishes_failed(self):
        fake_engine = FakeEngine()
        sync_engine = FailingPausedLogSyncEngine(
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
                        "list_field": "data.rows",
                        "total_field": "data.total",
                    },
                    "primary_key": {"field": "id"},
                    "date_field": "",
                }
            ],
            fake_engine,
        )
        sync_engine.pause_callback = lambda: True

        result = sync_engine.test_api_once("wide_report", object(), object())

        self.assertEqual(result["failed_count"], 1)
        self.assertFalse(result["paused"])
        batch_updates = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.calls
            if "UPDATE sync_batch" in statement
        ]
        self.assertEqual(batch_updates[-1]["status"], "failed")
        self.assertEqual(batch_updates[-1]["failed_api_count"], 1)

    def test_failed_result_takes_precedence_over_paused_when_finishing_batch(self):
        fake_engine = FakeEngine()
        sync_engine = ConflictingResultSyncEngine(
            [
                {
                    "api_code": "wide_report",
                    "enabled": False,
                    "commit_per_page": True,
                }
            ],
            fake_engine,
        )

        result = sync_engine.test_api_once("wide_report", object(), object())

        self.assertEqual(result["failed_count"], 1)
        self.assertTrue(result["paused"])
        batch_updates = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.calls
            if "UPDATE sync_batch" in statement
        ]
        self.assertEqual(batch_updates[-1]["status"], "failed")

    def test_pause_stops_after_committed_page_without_advancing_checkpoint(self):
        fake_engine = FakeEngine()
        page_progress = []
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
                        "list_field": "data.rows",
                        "total_field": "data.total",
                    },
                    "primary_key": {"field": "id"},
                    "date_field": "",
                }
            ],
            fake_engine,
            progress_callback=lambda current, total: page_progress.append((current, total)),
        )
        sync_engine.pause_callback = lambda: True

        result = sync_engine.test_api_once("wide_report", object(), object())

        self.assertTrue(result["paused"])
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(sync_engine.request_pages, [1])
        self.assertEqual(page_progress, [(1, 3)])
        statements = [
            statement for connection in fake_engine.connections for statement, _ in connection.calls
        ]
        self.assertFalse(any("sync_checkpoint" in statement for statement in statements))
        self.assertTrue(any("status = :status" in statement for statement in statements))

    def test_single_api_total_driven_pagination_writes_each_page_in_short_transaction(self):
        fake_engine = FakeEngine()
        page_progress = []
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
                        "list_field": "data.rows",
                        "total_field": "data.total",
                    },
                    "primary_key": {"field": "id"},
                    "date_field": "",
                }
            ],
            fake_engine,
            progress_callback=lambda current, total: page_progress.append((current, total)),
        )

        result = sync_engine.test_api_once("wide_report", api_client=object(), token=object())

        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["request_count"], 3)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(sync_engine.request_pages, [1, 2, 3])
        self.assertEqual(page_progress, [(1, 3), (2, 3), (3, 3)])
        self.assertEqual(
            [connection.name for connection in fake_engine.connections],
            ["tx-1", "tx-2", "tx-3", "tx-4", "tx-5", "tx-6"],
        )
        raw_write_transactions = [
            connection.name
            for connection in fake_engine.connections
            if any("INSERT INTO raw_api_data" in statement for statement, _ in connection.calls)
        ]
        self.assertEqual(raw_write_transactions, ["tx-2", "tx-3", "tx-4"])

    def test_live_progress_only_reports_committed_short_transactions(self):
        api = {
            "api_code": "wide_report",
            "enabled": False,
            "commit_per_page": True,
            "params": {"page": 1, "pagesize": 1},
            "page": {
                "enabled": True,
                "page_no_field": "page",
                "page_size_field": "pagesize",
                "page_size": 1,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
            "primary_key": {"field": "id"},
            "date_field": "",
        }
        page_progress = []
        failed = FailingSecondPageSyncEngine(
            [api],
            FakeEngine(),
            progress_callback=lambda current, total: page_progress.append((current, total)),
        )

        result = failed.test_api_once("wide_report", object(), object())

        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(page_progress, [(1, 3)])

        page_progress.clear()
        api["commit_per_page"] = False
        regular = CommitPerPageSyncEngine(
            [api],
            FakeEngine(),
            progress_callback=lambda current, total: page_progress.append((current, total)),
        )

        result = regular.test_api_once("wide_report", object(), object())

        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(page_progress, [])

    def test_page_write_retries_once_when_checked_out_connection_is_invalidated(self):
        fake_engine = InvalidatedOnceEngine()
        sync_engine = SyncEngine([], fake_engine)

        with self.assertLogs("app.sync_engine", level="WARNING") as logs:
            sync_engine._insert_raw_items_in_page_transaction(
                {"api_code": "wide_report", "primary_key": {"field": "id"}, "date_field": ""},
                [{"id": 1}],
                "sync_test_invalidated_once",
            )

        self.assertEqual(fake_engine.invalidated_writes_remaining, 0)
        self.assertEqual(len(fake_engine.connections), 2)
        self.assertIn("connection invalidated", logs.output[0])
        self.assertTrue(
            any(
                "INSERT INTO raw_api_data" in statement
                for statement, _ in fake_engine.connections[-1].calls
            )
        )

    def test_commit_per_page_capacity_fails_before_raw_write(self):
        fake_engine = FakeEngine()
        sync_engine = TruncatedCommitPerPageSyncEngine(
            [
                {
                    "api_code": "wide_report",
                    "enabled": False,
                    "commit_per_page": True,
                    "params": {"page": 1, "pagesize": 20},
                    "page": {
                        "enabled": True,
                        "page_no_field": "page",
                        "page_size_field": "pagesize",
                        "page_size": 20,
                        "max_pages": 5,
                        "list_field": "data.rows",
                        "total_field": "data.total",
                    },
                    "primary_key": {"field": "id"},
                    "date_field": "",
                }
            ],
            fake_engine,
        )

        result = sync_engine.test_api_once(
            "wide_report",
            api_client=object(),
            token=object(),
        )

        self.assertEqual(result["item_count"], 0)
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(sync_engine.request_pages, [1])
        raw_writes = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.calls
            if "INSERT INTO raw_api_data" in statement
        ]
        checkpoint_writes = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.calls
            if "INSERT INTO sync_checkpoint" in statement
        ]
        self.assertEqual(raw_writes, [])
        self.assertEqual(checkpoint_writes, [])
        failed_logs = [
            params
            for connection in fake_engine.connections
            for statement, params in connection.calls
            if "INSERT INTO sync_api_log" in statement and params.get("status") == "failed"
        ]
        self.assertEqual(len(failed_logs), 1)
        self.assertIn("pagination capacity insufficient", failed_logs[0]["error_message"])
        self.assertIn("required_pages=6", failed_logs[0]["error_message"])


if __name__ == "__main__":
    unittest.main()
