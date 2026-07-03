import unittest
from datetime import date

from app.sync_engine import SyncEngine


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


if __name__ == "__main__":
    unittest.main()
