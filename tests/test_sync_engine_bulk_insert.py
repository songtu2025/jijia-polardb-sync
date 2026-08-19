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


    def test_optional_missing_and_empty_primary_keys_are_written_as_null(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "optional_primary_key_api",
            "primary_key": {"field": "id", "required": False},
            "date_field": "",
        }

        engine._insert_raw_items(
            connection,
            api,
            [{"value": "missing"}, {"id": "", "value": "empty"}],
            "batch-001",
        )

        rows = connection.calls[0][1]
        self.assertEqual([row["source_primary_key"] for row in rows], [None, None])

    def test_zero_is_preserved_as_valid_primary_key(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "zero_primary_key_api",
            "primary_key": {"field": "id", "required": False},
            "date_field": "",
        }

        engine._insert_raw_items(
            connection,
            api,
            [{"id": 0, "value": "zero"}],
            "batch-001",
        )

        self.assertEqual(connection.calls[0][1][0]["source_primary_key"], "0")

    def test_upsert_updates_hash_with_raw_json(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "hash_consistency_api",
            "primary_key": {"field": "id"},
            "date_field": "",
        }

        engine._insert_raw_items(
            connection,
            api,
            [{"id": 1, "value": "updated"}],
            "batch-001",
        )

        statement = str(connection.calls[0][0])
        self.assertIn("data_hash = VALUES(data_hash)", statement)

    def test_same_raw_with_different_request_keys_does_not_reassign_existing_key(self):
        engine = SyncEngine([])
        connection = FakeConnection()
        api = {
            "api_code": "request_key_api",
            "primary_key": {"field": "", "required": False},
            "date_field": "",
        }
        item = {"value": "same raw"}

        engine._insert_raw_items(
            connection,
            api,
            [item],
            "batch-001",
            source_primary_key="first",
        )
        engine._insert_raw_items(
            connection,
            api,
            [item],
            "batch-002",
            source_primary_key="second",
        )

        first_row = connection.calls[0][1][0]
        second_row = connection.calls[1][1][0]
        self.assertEqual(first_row["data_hash"], second_row["data_hash"])
        self.assertNotEqual(
            first_row["source_primary_key"],
            second_row["source_primary_key"],
        )
        statement = str(connection.calls[0][0])
        self.assertNotIn(
            "source_primary_key =",
            statement.split("ON DUPLICATE KEY UPDATE", 1)[1],
        )

    def test_required_primary_key_filter_still_rejects_empty_values(self):
        engine = SyncEngine([])
        api = {
            "api_code": "required_primary_key_api",
            "primary_key": {"field": "id", "required": True},
        }

        self.assertFalse(engine._has_required_primary_key(api, {}))
        self.assertFalse(engine._has_required_primary_key(api, {"id": ""}))
        self.assertTrue(engine._has_required_primary_key(api, {"id": 0}))


if __name__ == "__main__":
    unittest.main()
