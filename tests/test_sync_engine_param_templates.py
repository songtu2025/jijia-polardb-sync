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

    def execute(self, statement, params=None):
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


if __name__ == "__main__":
    unittest.main()
