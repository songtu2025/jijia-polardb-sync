import unittest

from app.sync_engine import SyncEngine


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params))


class SyncEngineBulkInsertTest(unittest.TestCase):
    def test_insert_raw_items_uses_one_execute_for_multiple_items(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "dictionary_query",
            "primary_key": {"field": "id"},
            "date_field": "recordDate",
        }
        items = [
            {"id": 1, "recordDate": "2026-07-01 00:00:00", "name": "A"},
            {"id": 2, "recordDate": "2026-07-02 00:00:00", "name": "B"},
        ]

        engine._insert_raw_items(connection, api, items, "batch-001")

        self.assertEqual(len(connection.calls), 1)
        rows = connection.calls[0][1]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_primary_key"], "1")
        self.assertEqual(str(rows[1]["data_date"]), "2026-07-02")


if __name__ == "__main__":
    unittest.main()
