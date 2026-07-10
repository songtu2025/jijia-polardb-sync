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

    def test_insert_raw_items_can_chunk_large_raw_payloads(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "sales_analysis_asin_page",
            "primary_key": {"field": ""},
            "date_field": "dateLine",
            "write_batch_size": 2,
        }
        items = [
            {"dateLine": "2026-07-02", "uniqueValue": "a"},
            {"dateLine": "2026-07-02", "uniqueValue": "b"},
            {"dateLine": "2026-07-02", "uniqueValue": "c"},
            {"dateLine": "2026-07-02", "uniqueValue": "d"},
            {"dateLine": "2026-07-02", "uniqueValue": "e"},
        ]

        engine._insert_raw_items(connection, api, items, "batch-001")

        self.assertEqual(len(connection.calls), 3)
        self.assertEqual([len(call[1]) for call in connection.calls], [2, 2, 1])

    def test_insert_raw_items_can_use_request_window_date(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "sales_analysis_asin_page",
            "primary_key": {"field": ""},
            "date_field": "dateLine",
        }

        engine._insert_raw_items(connection, api, [{"dateLine": None, "uniqueValue": "a"}], "batch-001", data_date_override="2026-07-02")

        rows = connection.calls[0][1]
        self.assertEqual(str(rows[0]["data_date"]), "2026-07-02")


if __name__ == "__main__":
    unittest.main()
