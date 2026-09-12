import hashlib
import json
import unittest
from datetime import date, datetime
from itertools import pairwise

from app.sync_context import (
    CHANGE_CATCHUP,
    DATE_WINDOW,
    HISTORY_BACKFILL,
    INCREMENTAL_READY,
    UPDATE_INCREMENTAL,
    BackfillSequence,
    SyncContext,
    closed_date_windows,
)
from app.sync_engine import SyncEngine


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class MemoryDatabase:
    def __init__(self):
        self.calls = []
        self.checkpoints = {}
        self.history = {}
        self.snapshots = {}
        self.stats = {}


class MemoryConnection:
    def __init__(self, database):
        self.database = database

    def execute(self, statement, params=None):
        sql = str(statement)
        self.database.calls.append((sql, params))
        if "SELECT record_identity" in sql and "FROM raw_api_data" in sql:
            identities = set(params["record_identities"])
            return FakeResult(
                [
                    {"record_identity": key[2]}
                    for key in self.database.snapshots
                    if key[0] == params["jijia_account_id"]
                    and key[1] == params["api_code"]
                    and key[2] in identities
                ]
            )
        if "SELECT checkpoint_value" in sql:
            key = (
                params["jijia_account_id"],
                params["api_code"],
                params["checkpoint_kind"],
            )
            value = self.database.checkpoints.get(key)
            return FakeResult([{"checkpoint_value": value}] if value is not None else [])
        if "INSERT INTO sync_checkpoint" in sql:
            key = (
                params["jijia_account_id"],
                params["api_code"],
                params["checkpoint_kind"],
            )
            self.database.checkpoints[key] = params["checkpoint_value"]
            return FakeResult()
        if "INSERT INTO raw_api_data_history" in sql:
            for row in params:
                key = (
                    row["jijia_account_id"],
                    row["api_code"],
                    row["record_identity"],
                    row["data_hash"],
                )
                self.database.history.setdefault(key, dict(row))
            return FakeResult()
        if "INSERT INTO raw_api_data_stat" in sql:
            key = (params["jijia_account_id"], params["api_code"])
            self.database.stats[key] = self.database.stats.get(key, 0) + params["record_count"]
            return FakeResult()
        if "INSERT INTO raw_api_data" in sql:
            for row in params:
                key = (
                    row["jijia_account_id"],
                    row["api_code"],
                    row["record_identity"],
                )
                existing = self.database.snapshots.get(key)
                if existing is None:
                    self.database.snapshots[key] = dict(row)
                    continue
                incoming_json = json.loads(row["raw_json"])
                existing_json = json.loads(existing["raw_json"])
                incoming_time = incoming_json.get("updateTime")
                existing_time = existing_json.get("updateTime")
                if existing_time is None or (
                    incoming_time is not None and incoming_time >= existing_time
                ):
                    existing.update(
                        {
                            "data_hash": row["data_hash"],
                            "raw_json": row["raw_json"],
                            "data_date": row["data_date"],
                        }
                    )
                existing["sync_batch_no"] = row["sync_batch_no"]
                existing["last_observed_at"] = row["last_observed_at"]
                existing["observation_count"] += 1
            return FakeResult()
        return FakeResult()


class MemoryTransaction:
    def __init__(self, database):
        self.connection = MemoryConnection(database)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class MemoryEngine:
    def __init__(self):
        self.database = MemoryDatabase()

    def begin(self):
        return MemoryTransaction(self.database)


class RetryApiClient:
    def __init__(self):
        self.fail_page_two_once = True
        self.requested_pages = []

    def request(self, api, token, params):
        page = params["page"]
        self.requested_pages.append(page)
        if page == 2 and self.fail_page_two_once:
            self.fail_page_two_once = False
            raise RuntimeError("mock page failure")
        return {
            "data": {
                "total": 2,
                "rows": [
                    {
                        "id": page,
                        "returnDateTime": "2020-01-01 00:00:00",
                        "updateTime": f"2020-01-0{page} 00:00:00",
                    }
                ],
            }
        }

    @staticmethod
    def request_url(api):
        return "https://example.invalid/returnOrder/page"


def history_api():
    return {
        "api_code": "sale_return_order_page",
        "enabled": False,
        "method": "POST",
        "path": "/operation/sale/returnOrder/page",
        "storage_mode": "history_on_change",
        "checkpoint_kind": "history_backfill",
        "commit_per_page": True,
        "page": {
            "enabled": True,
            "page_no_field": "page",
            "page_size_field": "pagesize",
            "page_size": 1,
            "list_field": "data.rows",
            "total_field": "data.total",
        },
        "primary_key": {"field": "id", "required": False},
        "date_field": "returnDateTime",
        "date_window": {
            "enabled": True,
            "start_field": "returnStartDate",
            "end_field": "returnEndDate",
            "default_start": "2020-01-01",
            "days": 31,
            "lag_days": 1,
        },
        "update_window": {
            "enabled": True,
            "verified_doc_id": 9,
            "start_field": "updateTimeBegin",
            "end_field": "updateTimeEnd",
            "default_start": "2020-01-01",
            "days": 31,
            "lag_days": 1,
            "value_format": "datetime",
        },
        "retry": {"retries": 1, "delay_seconds": 0},
        "params": {"page": 1, "pagesize": 1},
    }


class M3SyncCoreTest(unittest.TestCase):
    def test_record_identity_prefers_normalized_primary_key(self):
        engine = SyncEngine([])
        data_hash = engine._data_hash({"value": "same"})

        primary_identity = engine._record_identity("R-1", data_hash)
        hash_identity = engine._record_identity(None, data_hash)

        self.assertEqual(
            primary_identity,
            hashlib.sha256(b"pk:R-1").hexdigest(),
        )
        self.assertEqual(
            hash_identity,
            hashlib.sha256(f"hash:{data_hash}".encode()).hexdigest(),
        )

    def test_history_windows_are_continuous_and_end_at_frozen_date(self):
        windows = closed_date_windows(
            date(2020, 1, 1),
            date(2026, 8, 25),
        )

        self.assertEqual(len(windows), 79)
        self.assertEqual(windows[0], (date(2020, 1, 1), date(2020, 1, 31)))
        self.assertEqual(windows[-1], (date(2026, 8, 15), date(2026, 8, 25)))
        for previous, current in pairwise(windows):
            self.assertEqual((current[0] - previous[1]).days, 1)

    def test_empty_middle_window_does_not_stop_planned_backfill(self):
        api = history_api()
        memory_engine = MemoryEngine()
        windows = closed_date_windows(date(2020, 1, 1), date(2020, 4, 2))
        totals = {
            windows[0][0].isoformat(): 1,
            windows[1][0].isoformat(): 0,
            windows[2][0].isoformat(): 1,
        }

        class Client:
            def __init__(self):
                self.windows = []

            def request(self, api_config, token, params):
                window_start = params["returnStartDate"]
                self.windows.append((window_start, params["page"]))
                total = totals[window_start]
                rows = []
                if total:
                    rows = [
                        {
                            "id": window_start,
                            "returnDateTime": f"{window_start} 00:00:00",
                            "updateTime": f"{window_start} 12:00:00",
                        }
                    ]
                return {"data": {"total": total, "rows": rows}}

        client = Client()
        t0 = datetime(2026, 8, 26, 8, 0, 0)
        for window_start, window_end in windows:
            context = SyncContext(
                jijia_account_id=3,
                checkpoint_kind=HISTORY_BACKFILL,
                window_start=window_start,
                window_end=window_end,
                frozen_window_end=windows[-1][1],
                backfill_started_at=t0,
            )
            result = SyncEngine(
                [api],
                memory_engine,
                context,
            ).test_api_once(api["api_code"], client, object())
            self.assertEqual(result["failed_count"], 0)

        self.assertEqual(
            client.windows,
            [(window[0].isoformat(), 1) for window in windows],
        )
        checkpoint = json.loads(
            memory_engine.database.checkpoints[(3, api["api_code"], HISTORY_BACKFILL)]
        )
        self.assertEqual(checkpoint["next_window_start"], "2020-04-03")

    def test_history_checkpoint_preserves_discovered_absolute_lower_bound(self):
        api = history_api()
        memory_engine = MemoryEngine()
        checkpoint_key = (3, api["api_code"], HISTORY_BACKFILL)
        memory_engine.database.checkpoints[checkpoint_key] = json.dumps(
            {
                "next_window_start": "2020-02-20",
                "absolute_lower_bound": "2020-02-20",
                "start_source": "earliest_date_discovery",
            }
        )

        class EmptyClient:
            @staticmethod
            def request(api_config, token, params):
                return {"data": {"total": 0, "rows": []}}

        result = SyncEngine(
            [api],
            memory_engine,
            SyncContext(
                jijia_account_id=3,
                checkpoint_kind=HISTORY_BACKFILL,
                window_start=date(2020, 2, 20),
                window_end=date(2020, 3, 21),
                frozen_window_end=date(2020, 3, 21),
                backfill_started_at=datetime(2026, 8, 26, 8, 0, 0),
            ),
        ).test_api_once(api["api_code"], EmptyClient(), object())

        self.assertEqual(result["failed_count"], 0)
        checkpoint = json.loads(memory_engine.database.checkpoints[checkpoint_key])
        self.assertEqual(checkpoint["next_window_start"], "2020-03-22")
        self.assertEqual(checkpoint["absolute_lower_bound"], "2020-02-20")

    def test_total_driven_pagination_requests_first_page_once(self):
        api = history_api()
        api["page"]["page_size"] = 100
        api["params"]["pagesize"] = 100
        requested_pages = []

        class Client:
            @staticmethod
            def request(api_config, token, params):
                requested_pages.append(params["page"])
                return {"data": {"total": 201, "rows": []}}

        payloads = list(
            SyncEngine([api])._paged_payloads_from_params(
                api,
                Client(),
                object(),
                {"page": 1, "pagesize": 100},
            )
        )

        self.assertEqual([item[0] for item in payloads], [1, 2, 3])
        self.assertEqual(requested_pages, [1, 2, 3])

    def test_history_on_change_deduplicates_versions_and_scopes_accounts(self):
        database = MemoryDatabase()
        connection = MemoryConnection(database)
        api = history_api()
        original = {
            "id": " R-1 ",
            "returnDateTime": "2020-01-01 00:00:00",
            "updateTime": "2026-08-01 10:00:00",
            "status": "pending",
        }
        changed = {**original, "updateTime": "2026-08-02 10:00:00", "status": "done"}

        account_one = SyncEngine(
            [api],
            sync_context=SyncContext(jijia_account_id=1),
        )
        account_two = SyncEngine(
            [api],
            sync_context=SyncContext(jijia_account_id=2),
        )
        account_one._insert_raw_items(connection, api, [original], "batch-1")
        account_one._insert_raw_items(connection, api, [original], "batch-2")
        account_one._insert_raw_items(connection, api, [changed], "batch-3")
        account_two._insert_raw_items(connection, api, [original], "batch-4")

        first_two_writes = [
            sql
            for sql, _ in database.calls
            if "INSERT INTO raw_api_data_history" in sql or "INSERT INTO raw_api_data (" in sql
        ][:2]
        self.assertIn("raw_api_data_history", first_two_writes[0])
        self.assertIn("raw_api_data", first_two_writes[1])
        account_one_history = [key for key in database.history if key[0] == 1]
        self.assertEqual(len(account_one_history), 2)
        self.assertEqual(len(database.snapshots), 2)
        self.assertEqual(database.stats[(1, api["api_code"])], 1)
        self.assertEqual(database.stats[(2, api["api_code"])], 1)
        account_one_snapshot = next(
            value for key, value in database.snapshots.items() if key[0] == 1
        )
        self.assertEqual(account_one_snapshot["source_primary_key"], "R-1")
        self.assertIsNotNone(account_one_snapshot["first_observed_at"])
        self.assertEqual(account_one_snapshot["observation_count"], 3)
        self.assertEqual(account_one_snapshot["sync_batch_no"], "batch-3")
        self.assertEqual(json.loads(account_one_snapshot["raw_json"])["status"], "done")

    def test_older_backfill_observation_cannot_replace_new_snapshot(self):
        database = MemoryDatabase()
        connection = MemoryConnection(database)
        api = history_api()
        engine = SyncEngine([api], sync_context=SyncContext(jijia_account_id=1))
        newer = {
            "id": "R-1",
            "updateTime": "2026-08-02 10:00:00",
            "status": "done",
        }
        older = {
            "id": "R-1",
            "updateTime": "2026-08-01 10:00:00",
            "status": "pending",
        }

        engine._insert_raw_items(connection, api, [newer], "batch-new")
        engine._insert_raw_items(connection, api, [older], "batch-old-retry")

        snapshot = next(iter(database.snapshots.values()))
        self.assertEqual(json.loads(snapshot["raw_json"])["status"], "done")
        self.assertEqual(snapshot["sync_batch_no"], "batch-old-retry")
        self.assertEqual(snapshot["observation_count"], 2)

    def test_failed_window_does_not_advance_and_retry_starts_at_page_one(self):
        api = history_api()
        memory_engine = MemoryEngine()
        context = SyncContext(
            jijia_account_id=7,
            checkpoint_kind=HISTORY_BACKFILL,
            sync_job_id=99,
            window_start=date(2020, 1, 1),
            window_end=date(2020, 1, 31),
            frozen_window_end=date(2020, 1, 31),
            backfill_started_at=datetime(2026, 8, 26, 8, 0, 0),
        )
        engine = SyncEngine([api], memory_engine, context)
        client = RetryApiClient()

        first = engine.test_api_once(api["api_code"], client, object())
        checkpoint_key = (7, api["api_code"], HISTORY_BACKFILL)
        self.assertEqual(first["failed_count"], 1)
        self.assertNotIn(checkpoint_key, memory_engine.database.checkpoints)
        failed_request = next(
            params
            for sql, params in memory_engine.database.calls
            if "INSERT INTO failed_request_log" in sql
        )
        self.assertEqual(failed_request["jijia_account_id"], 7)

        second = engine.test_api_once(api["api_code"], client, object())

        self.assertEqual(second["failed_count"], 0)
        self.assertEqual(client.requested_pages, [1, 2, 1, 2])
        checkpoint = json.loads(memory_engine.database.checkpoints[checkpoint_key])
        self.assertEqual(checkpoint["next_window_start"], "2020-02-01")
        self.assertEqual(len(memory_engine.database.history), 2)
        first_snapshot = next(
            value
            for value in memory_engine.database.snapshots.values()
            if value["source_primary_key"] == "1"
        )
        self.assertEqual(first_snapshot["observation_count"], 2)
        batch_insert = next(
            params
            for sql, params in memory_engine.database.calls
            if "INSERT INTO sync_batch" in sql
        )
        self.assertEqual(batch_insert["jijia_account_id"], 7)
        self.assertEqual(batch_insert["sync_job_id"], 99)

    def test_checkpoint_kinds_do_not_overwrite_each_other(self):
        api = {"api_code": "test_api"}
        database = MemoryDatabase()
        connection = MemoryConnection(database)

        for checkpoint_kind in (
            DATE_WINDOW,
            HISTORY_BACKFILL,
            UPDATE_INCREMENTAL,
        ):
            engine = SyncEngine(
                [api],
                sync_context=SyncContext(
                    jijia_account_id=5,
                    checkpoint_kind=checkpoint_kind,
                ),
            )
            engine._update_checkpoint(
                connection,
                api["api_code"],
                f"batch-{checkpoint_kind}",
                0,
                1,
                1,
                0,
            )

        self.assertEqual(len(database.checkpoints), 3)

    def test_checkpoint_accepts_driver_decoded_json_object(self):
        api = {"api_code": "test_api"}
        database = MemoryDatabase()
        database.checkpoints[(5, "test_api", HISTORY_BACKFILL)] = {
            "next_window_start": "2020-02-01"
        }
        engine = SyncEngine(
            [api],
            sync_context=SyncContext(
                jijia_account_id=5,
                checkpoint_kind=HISTORY_BACKFILL,
            ),
        )

        checkpoint = engine._checkpoint_data(
            api,
            MemoryConnection(database),
        )

        self.assertEqual(checkpoint["next_window_start"], "2020-02-01")

    def test_param_source_reads_are_scoped_to_current_account(self):
        class SourceConnection:
            def __init__(self):
                self.calls = []

            def execute(self, statement, params=None):
                self.calls.append((str(statement), params))
                return FakeResult([{"source_value": "P-1"}])

        connection = SourceConnection()
        api = {
            "api_code": "detail_api",
            "param_source": {
                "source_api_code": "source_api",
                "source_field": "source_primary_key",
                "target_field": "id",
                "limit": 1,
            },
        }
        engine = SyncEngine(
            [api],
            sync_context=SyncContext(jijia_account_id=12),
        )

        params = engine._source_param_sets(connection, api)

        self.assertEqual(params, [{"id": "P-1"}])
        self.assertEqual(connection.calls[0][1]["jijia_account_id"], 12)
        self.assertIn("jijia_account_id = :jijia_account_id", connection.calls[0][0])

    def test_backfill_catchup_incremental_sequence_is_strict(self):
        t0 = datetime(2026, 8, 26, 8, 0, 0)
        state = BackfillSequence(t0)
        with self.assertRaisesRegex(ValueError, "completed change catch-up"):
            state.complete_change_catchup(datetime(2026, 8, 26, 9, 0, 0))

        catchup = state.begin_change_catchup(datetime(2026, 8, 26, 9, 0, 0))
        ready = catchup.complete_change_catchup(datetime(2026, 8, 26, 10, 0, 0))

        self.assertEqual(catchup.phase, CHANGE_CATCHUP)
        self.assertEqual(ready.phase, INCREMENTAL_READY)
        self.assertEqual(ready.catchup_completed_through, datetime(2026, 8, 26, 10, 0, 0))

    def test_verified_update_incremental_uses_official_datetime_fields(self):
        api = history_api()
        engine = SyncEngine(
            [api],
            sync_context=SyncContext(
                checkpoint_kind=UPDATE_INCREMENTAL,
                window_start=date(2026, 8, 24),
                window_end=date(2026, 8, 24),
                target_window_end=date(2026, 8, 24),
            ),
        )

        engine._ensure_execution_allowed(api)
        params = engine._request_params(api, today=date(2026, 8, 26))

        self.assertEqual(params["updateTimeBegin"], "2026-08-24 00:00:00")
        self.assertEqual(params["updateTimeEnd"], "2026-08-24 23:59:59")
        self.assertNotIn("returnStartDate", params)
        self.assertNotIn("returnEndDate", params)

    def test_update_incremental_advances_its_own_checkpoint(self):
        api = history_api()
        memory_engine = MemoryEngine()
        requested_params = []

        class Client:
            @staticmethod
            def request(api_config, token, params):
                requested_params.append(dict(params))
                return {
                    "data": {
                        "total": 1,
                        "rows": [
                            {
                                "id": "R-9",
                                "returnDateTime": "2020-01-02 08:00:00",
                                "updateTime": "2026-08-24 12:00:00",
                            }
                        ],
                    }
                }

        context = SyncContext(
            jijia_account_id=9,
            checkpoint_kind=UPDATE_INCREMENTAL,
            window_start=date(2026, 8, 24),
            window_end=date(2026, 8, 24),
            target_window_end=date(2026, 8, 24),
        )

        result = SyncEngine([api], memory_engine, context).test_api_once(
            api["api_code"],
            Client(),
            object(),
        )

        self.assertEqual(result["failed_count"], 0)
        checkpoint = json.loads(
            memory_engine.database.checkpoints[(9, api["api_code"], UPDATE_INCREMENTAL)]
        )
        self.assertEqual(checkpoint["window_start"], "2026-08-24")
        self.assertEqual(checkpoint["next_window_start"], "2026-08-25")
        self.assertEqual(requested_params[0]["updateTimeBegin"], "2026-08-24 00:00:00")
        self.assertNotIn("returnStartDate", requested_params[0])

    def test_unverified_update_incremental_cannot_execute(self):
        api = history_api()
        api.pop("update_window")
        engine = SyncEngine(
            [api],
            sync_context=SyncContext(checkpoint_kind=UPDATE_INCREMENTAL),
        )

        with self.assertRaisesRegex(ValueError, "updateTime contract"):
            engine._ensure_execution_allowed(api)


if __name__ == "__main__":
    unittest.main()
