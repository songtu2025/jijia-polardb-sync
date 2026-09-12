import copy
import unittest

from app.sync_context import SyncContext
from app.sync_engine import SyncEngine


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows


class MemoryState:
    def __init__(self):
        self.raw_identities = set()
        self.stats = {}


class MemoryConnection:
    def __init__(self, state):
        self.state = state

    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT record_identity" in sql:
            identities = set(params["record_identities"])
            rows = [
                {"record_identity": identity}
                for account_id, api_code, identity in self.state.raw_identities
                if account_id == params["jijia_account_id"]
                and api_code == params["api_code"]
                and identity in identities
            ]
            return FakeResult(rows)
        if "INSERT INTO raw_api_data (" in sql:
            for row in params:
                self.state.raw_identities.add(
                    (
                        row["jijia_account_id"],
                        row["api_code"],
                        row["record_identity"],
                    )
                )
            return FakeResult()
        if "INSERT INTO raw_api_data_stat" in sql:
            key = (params["jijia_account_id"], params["api_code"])
            self.state.stats[key] = self.state.stats.get(key, 0) + params["record_count"]
        return FakeResult()


class MemoryTransaction:
    def __init__(self, state):
        self.state = state
        self.snapshot = None

    def __enter__(self):
        self.snapshot = copy.deepcopy(self.state.__dict__)
        return MemoryConnection(self.state)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.state.__dict__.clear()
            self.state.__dict__.update(self.snapshot)
        return False


class MemoryEngine:
    def __init__(self):
        self.state = MemoryState()

    def begin(self):
        return MemoryTransaction(self.state)


class RawApiDataStatTest(unittest.TestCase):
    def test_only_new_identities_increment_and_rollback_keeps_counts_consistent(self):
        memory_engine = MemoryEngine()
        api = {
            "api_code": "sample_api",
            "primary_key": {"field": "id"},
            "date_field": "",
        }
        sync_engine = SyncEngine(
            [api],
            sync_context=SyncContext(jijia_account_id=7),
        )

        with memory_engine.begin() as connection:
            sync_engine._insert_raw_items(
                connection,
                api,
                [{"id": 1}, {"id": 1}, {"id": 2}],
                "batch-1",
            )
        with memory_engine.begin() as connection:
            sync_engine._insert_raw_items(
                connection,
                api,
                [{"id": 1, "value": "updated"}],
                "batch-2",
            )

        self.assertEqual(memory_engine.state.stats[(7, "sample_api")], 2)
        self.assertEqual(len(memory_engine.state.raw_identities), 2)

        with self.assertRaisesRegex(RuntimeError, "force rollback"):
            with memory_engine.begin() as connection:
                sync_engine._insert_raw_items(
                    connection,
                    api,
                    [{"id": 3}],
                    "batch-3",
                )
                raise RuntimeError("force rollback")

        self.assertEqual(memory_engine.state.stats[(7, "sample_api")], 2)
        self.assertEqual(len(memory_engine.state.raw_identities), 2)


if __name__ == "__main__":
    unittest.main()
