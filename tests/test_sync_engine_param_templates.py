import unittest
import json
from datetime import date

from app.sync_engine import SyncEngine


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class FakeCheckpointConnection:
    def __init__(self, checkpoint_value=None):
        self.checkpoint_value = checkpoint_value
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        if "sync_checkpoint" in str(statement):
            if self.checkpoint_value is None:
                return FakeResult([])
            return FakeResult([{"checkpoint_value": self.checkpoint_value}])
        return FakeResult([])


class FakeApiClient:
    def __init__(self):
        self.calls = []

    def request(self, api, token, params):
        self.calls.append((api, token, params))
        return {"data": {"rows": [], "total": 0}}


class TruncatedApiClient:
    def __init__(self):
        self.calls = []

    def request(self, api, token, params):
        self.calls.append((api, token, params))
        return {"data": {"rows": [{"id": 1}], "total": 2}}


class CapacityLimitedApiClient:
    def __init__(self):
        self.calls = []

    def request(self, api, token, params):
        self.calls.append((api, token, params))
        page = int(params["page"])
        start = (page - 1) * 20
        rows = [{"id": item_id} for item_id in range(start, start + 20)]
        return {"data": {"rows": rows, "total": 101}}


class NoTotalApiClient:
    def request(self, api, token, params):
        return {"data": {"rows": [{"id": 1}]}}


class GrowingTotalApiClient:
    def __init__(self):
        self.calls = []

    def request(self, api, token, params):
        self.calls.append((api, token, params))
        page = int(params["page"])
        total = 2 if page == 1 else 3
        return {"data": {"rows": [{"id": page}], "total": total}}


class SyncEngineParamTemplatesTest(unittest.TestCase):
    def test_resolves_date_param_templates_without_touching_unknown_values(self):
        engine = SyncEngine([])

        params = engine._resolve_param_templates(
            {
                "beginDate": "{{ days_ago:7 }}",
                "endDate": "{{ yesterday }}",
                "nested": {"runDate": "{{ today }}"},
                "unchanged": "{{ checkpoint_or_default_start }}",
            },
            today=date(2026, 7, 3),
        )

        self.assertEqual(
            params,
            {
                "beginDate": "2026-06-26",
                "endDate": "2026-07-02",
                "nested": {"runDate": "2026-07-03"},
                "unchanged": "{{ checkpoint_or_default_start }}",
            },
        )

    def test_date_window_params_start_from_default_when_checkpoint_is_empty(self):
        engine = SyncEngine([])
        api = {
            "api_code": "windowed_report",
            "params": {"page": 1, "pagesize": 100},
            "date_window": {
                "enabled": True,
                "start_field": "beginDate",
                "end_field": "endDate",
                "default_start": "2026-06-01",
                "days": 3,
            },
        }

        params = engine._request_params(
            api,
            connection=FakeCheckpointConnection(),
            today=date(2026, 7, 3),
        )

        self.assertEqual(params["beginDate"], "2026-06-01")
        self.assertEqual(params["endDate"], "2026-06-03")
        self.assertEqual(
            engine._date_window_checkpoint_extra(api, params),
            {
                "window_start": "2026-06-01",
                "window_end": "2026-06-03",
                "next_window_start": "2026-06-04",
                "window_days": 3,
            },
        )

    def test_date_window_params_continue_from_checkpoint_next_window_start(self):
        engine = SyncEngine([])
        api = {
            "api_code": "windowed_report",
            "params": {},
            "date_window": {
                "enabled": True,
                "start_field": "startDate",
                "end_field": "endDate",
                "default_start": "2026-06-01",
                "days": 2,
            },
        }
        connection = FakeCheckpointConnection(
            json.dumps({"next_window_start": "2026-06-04"}, ensure_ascii=False)
        )

        params = engine._request_params(api, connection=connection, today=date(2026, 7, 3))

        self.assertEqual(params["startDate"], "2026-06-04")
        self.assertEqual(params["endDate"], "2026-06-05")

    def test_date_window_params_can_write_nested_model_fields(self):
        engine = SyncEngine([])
        api = {
            "api_code": "nested_windowed_report",
            "params": {"page": 1, "pagesize": 100, "model": {}},
            "date_window": {
                "enabled": True,
                "start_field": "model.reportStartDate",
                "end_field": "model.reportEndDate",
                "default_start": "2026-07-02",
                "days": 1,
            },
        }

        params = engine._request_params(
            api,
            connection=FakeCheckpointConnection(),
            today=date(2026, 7, 3),
        )

        self.assertEqual(params["model"]["reportStartDate"], "2026-07-02")
        self.assertEqual(params["model"]["reportEndDate"], "2026-07-02")
        self.assertNotIn("model.reportStartDate", params)
        self.assertEqual(
            engine._date_window_checkpoint_extra(api, params),
            {
                "window_start": "2026-07-02",
                "window_end": "2026-07-02",
                "next_window_start": "2026-07-03",
                "window_days": 1,
            },
        )

    def test_date_window_skips_request_when_next_window_is_after_today(self):
        engine = SyncEngine([])
        api_client = FakeApiClient()
        api = {
            "api_code": "windowed_report",
            "params": {"page": 1, "pagesize": 100},
            "page": {
                "enabled": True,
                "page_no_field": "page",
                "page_size_field": "pagesize",
                "page_size": 100,
                "max_pages": 1,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
            "date_window": {
                "enabled": True,
                "start_field": "beginDate",
                "end_field": "endDate",
                "default_start": "2026-07-01",
                "days": 1,
            },
        }
        connection = FakeCheckpointConnection(
            json.dumps({"next_window_start": "2999-01-01"}, ensure_ascii=False)
        )

        payloads = list(engine._paged_payloads(api, api_client, token="token", connection=connection))

        self.assertEqual(payloads, [])
        self.assertEqual(api_client.calls, [])

    def test_date_window_lag_days_treats_today_as_not_ready(self):
        engine = SyncEngine([])
        api = {
            "api_code": "complete_day_report",
            "params": {"page": 1, "pagesize": 100},
            "date_window": {
                "enabled": True,
                "start_field": "beginDate",
                "end_field": "endDate",
                "default_start": "2026-07-01",
                "days": 1,
                "lag_days": 1,
            },
        }
        connection = FakeCheckpointConnection(
            json.dumps({"next_window_start": "2026-07-05"}, ensure_ascii=False)
        )

        params = engine._date_window_params(api, connection=connection, today=date(2026, 7, 5))

        self.assertIsNone(params)
        self.assertTrue(engine._date_window_caught_up(api, connection, today=date(2026, 7, 5)))

    def test_date_window_capacity_fails_before_raw_write(self):
        engine = SyncEngine([])
        api_client = TruncatedApiClient()
        connection = FakeCheckpointConnection()
        api = {
            "api_code": "windowed_report",
            "params": {"page": 1, "pagesize": 1},
            "page": {
                "enabled": True,
                "page_no_field": "page",
                "page_size_field": "pagesize",
                "page_size": 1,
                "max_pages": 1,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
            "primary_key": {"field": "id"},
            "date_field": "",
            "date_window": {
                "enabled": True,
                "start_field": "beginDate",
                "end_field": "endDate",
                "default_start": "2026-07-01",
                "days": 1,
            },
        }

        result = engine._sync_api_in_batch(connection, api, "batch-001", api_client, token="token")

        self.assertEqual(result, {"item_count": 0, "request_count": 1, "failed_count": 1})
        raw_writes = [
            call for call in connection.calls if "INSERT INTO raw_api_data" in call[0]
        ]
        checkpoint_writes = [
            call
            for call in connection.calls
            if "INSERT INTO sync_checkpoint" in call[0]
        ]
        api_log_params = connection.calls[-1][1]
        self.assertEqual(raw_writes, [])
        self.assertEqual(checkpoint_writes, [])
        self.assertEqual(api_log_params["status"], "failed")
        self.assertIn("pagination capacity insufficient", api_log_params["error_message"])
        self.assertIn("required_pages=2", api_log_params["error_message"])

    def test_regular_pagination_capacity_fails_before_raw_write(self):
        engine = SyncEngine([])
        connection = FakeCheckpointConnection()
        api = {
            "api_code": "regular_report",
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

        client = CapacityLimitedApiClient()
        result = engine._sync_api_in_batch(
            connection,
            api,
            "batch-regular-truncated",
            client,
            token="token",
        )

        self.assertEqual(
            result,
            {"item_count": 0, "request_count": 1, "failed_count": 1},
        )
        self.assertEqual([call[2]["page"] for call in client.calls], [1])
        raw_writes = [
            call for call in connection.calls if "INSERT INTO raw_api_data" in call[0]
        ]
        checkpoint_writes = [
            call
            for call in connection.calls
            if "INSERT INTO sync_checkpoint" in call[0]
        ]
        self.assertEqual(raw_writes, [])
        self.assertEqual(checkpoint_writes, [])
        api_log_params = connection.calls[-1][1]
        self.assertEqual(api_log_params["status"], "failed")
        self.assertIn("pagination capacity insufficient", api_log_params["error_message"])
        self.assertIn("required_pages=6", api_log_params["error_message"])

    def test_total_driven_pagination_follows_latest_total_without_fixed_cap(self):
        engine = SyncEngine([])
        connection = FakeCheckpointConnection()
        api = {
            "api_code": "growing_report",
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
        client = GrowingTotalApiClient()

        result = engine._sync_api_in_batch(
            connection,
            api,
            "batch-growing-total",
            client,
            token="token",
        )

        self.assertEqual(
            result,
            {"item_count": 3, "request_count": 3, "failed_count": 0},
        )
        self.assertEqual([call[2]["page"] for call in client.calls], [1, 2, 3])
        checkpoint_params = next(
            params
            for statement, params in connection.calls
            if "INSERT INTO sync_checkpoint" in statement
        )
        checkpoint_value = json.loads(checkpoint_params["checkpoint_value"])
        self.assertEqual(checkpoint_value["last_page"], 3)
        self.assertEqual(checkpoint_value["total_count"], 3)

    def test_total_driven_pagination_requires_valid_total_before_raw_write(self):
        engine = SyncEngine([])
        connection = FakeCheckpointConnection()
        api = {
            "api_code": "missing_total_report",
            "params": {"page": 1, "pagesize": 20},
            "page": {
                "enabled": True,
                "page_no_field": "page",
                "page_size_field": "pagesize",
                "page_size": 20,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
            "primary_key": {"field": "id"},
            "date_field": "",
        }

        result = engine._sync_api_in_batch(
            connection,
            api,
            "batch-missing-total",
            NoTotalApiClient(),
            token="token",
        )

        self.assertEqual(
            result,
            {"item_count": 0, "request_count": 1, "failed_count": 1},
        )
        raw_writes = [
            call for call in connection.calls if "INSERT INTO raw_api_data" in call[0]
        ]
        self.assertEqual(raw_writes, [])
        api_log_params = connection.calls[-1][1]
        self.assertIn(
            "total-driven pagination requires valid total",
            api_log_params["error_message"],
        )

    def test_probe_api_reads_first_page_total_without_database_engine(self):
        api = {
            "api_code": "regular_report",
            "params": {"page": 1, "pagesize": 20},
            "page": {
                "enabled": True,
                "page_no_field": "page",
                "page_size_field": "pagesize",
                "page_size": 20,
                "max_pages": 1,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
        }
        client = CapacityLimitedApiClient()

        result = SyncEngine([api]).probe_api(
            "regular_report",
            client,
            token="token",
        )

        self.assertEqual(
            result,
            {
                "api_code": "regular_report",
                "total_count": 101,
                "page_size": 20,
                "required_pages": 6,
                "request_count": 1,
            },
        )
        self.assertEqual([call[2]["page"] for call in client.calls], [1])

    def test_non_paged_response_without_total_stays_successful(self):
        engine = SyncEngine([])
        connection = FakeCheckpointConnection()
        api = {
            "api_code": "non_paged_report",
            "params": {},
            "page": {
                "enabled": False,
                "list_field": "data.rows",
            },
            "primary_key": {"field": "id"},
            "date_field": "",
        }

        result = engine._sync_api_in_batch(
            connection,
            api,
            "batch-non-paged",
            NoTotalApiClient(),
            token="token",
        )

        self.assertEqual(
            result,
            {"item_count": 1, "request_count": 1, "failed_count": 0},
        )
        checkpoint_writes = [
            call
            for call in connection.calls
            if "INSERT INTO sync_checkpoint" in call[0]
        ]
        self.assertEqual(len(checkpoint_writes), 1)
        self.assertEqual(connection.calls[-1][1]["status"], "success")

    def test_paged_payloads_write_nested_page_fields(self):
        engine = SyncEngine([])
        api = self._nested_page_api()
        api_client = FakeApiClient()

        list(engine._paged_payloads(api, api_client, token="token"))
        params = api_client.calls[0][2]

        self.assertEqual(params, {"pageInfo": {"page": 1, "pagesize": 100}})
        self.assertNotIn("pageInfo.page", params)

    def test_paged_payloads_from_params_write_nested_page_fields(self):
        engine = SyncEngine([])
        api = self._nested_page_api()
        base_params = {"pageInfo": {"page": 1, "pagesize": 10}}
        api_client = FakeApiClient()

        list(engine._paged_payloads_from_params(api, api_client, token="token", base_params=base_params))
        params = api_client.calls[0][2]

        self.assertEqual(params, {"pageInfo": {"page": 1, "pagesize": 100}})
        self.assertNotIn("pageInfo.pagesize", params)

    @staticmethod
    def _nested_page_api():
        return {
            "api_code": "nested_page",
            "params": {"pageInfo": {"page": 1, "pagesize": 10}},
            "page": {
                "enabled": True,
                "page_no_field": "pageInfo.page",
                "page_size_field": "pageInfo.pagesize",
                "page_size": 100,
                "max_pages": 1,
                "list_field": "data.rows",
                "total_field": "data.total",
            },
            "retry": {"retries": 1, "delay_seconds": 1},
        }


if __name__ == "__main__":
    unittest.main()
