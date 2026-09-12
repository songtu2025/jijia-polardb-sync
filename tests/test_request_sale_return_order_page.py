import json
import unittest
from datetime import date
from unittest.mock import patch

from requests import Response

from app.sale_return_discovery import discover_earliest_date
from request_sale_return_order_page import (
    request_all_pages,
)


def build_response(page: int, total: int, row_count: int) -> Response:
    """生成不含真实业务字段的分页响应。"""
    response = Response()
    response.status_code = 200
    response._content = json.dumps(
        {
            "code": 200,
            "traceId": f"placeholder-trace-{page}",
            "messages": ["request.success"],
            "data": {
                "total": total,
                "page": page,
                "pagesize": 100,
                "rows": [{"id": f"placeholder-{index}"} for index in range(row_count)],
            },
        }
    ).encode("utf-8")
    return response


class RequestSaleReturnOrderPageTest(unittest.TestCase):
    @patch("app.sale_return_discovery.time.sleep")
    @patch("app.sale_return_discovery.requests.post")
    def test_all_pages_uses_total_and_only_returns_summary(self, post, sleep):
        post.side_effect = [
            build_response(1, 250, 100),
            build_response(2, 250, 100),
            build_response(3, 250, 50),
        ]
        body = {
            "returnStartDate": "2026-08-04",
            "returnEndDate": "2026-08-10",
            "page": 1,
            "pagesize": 100,
        }

        result = request_all_pages(
            "https://placeholder.invalid/api",
            body,
            "placeholder-token",
            30,
        )

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(
            result["data_summary"],
            {
                "total": 250,
                "required_pages": 3,
                "requested_pages": 3,
                "row_count": 250,
                "complete": True,
            },
        )
        self.assertNotIn("rows", json.dumps(result))

    @patch("app.sale_return_discovery.time.sleep")
    @patch("app.sale_return_discovery.requests.post")
    def test_discovery_skips_empty_windows_and_refines_first_nonempty_date(
        self,
        post,
        sleep,
    ):
        earliest = date(2020, 2, 20)

        def respond(_url, *, json, **_kwargs):
            window_start = date.fromisoformat(json["returnStartDate"])
            window_end = date.fromisoformat(json["returnEndDate"])
            total = 1 if window_start <= earliest <= window_end else 0
            return build_response(1, total, min(total, 1))

        post.side_effect = respond

        result = discover_earliest_date(
            "https://placeholder.invalid/api",
            date(2020, 1, 1),
            date(2020, 3, 15),
            "placeholder-token",
            30,
        )

        self.assertEqual(result["earliest_data_date"], "2020-02-20")
        self.assertEqual(result["earliest_day_total"], 1)
        self.assertEqual(result["coarse_windows_checked"], 2)
        self.assertEqual(result["request_count"], post.call_count)
        self.assertEqual(sleep.call_count, post.call_count - 1)
        self.assertTrue(all(call.kwargs["json"]["pagesize"] == 1 for call in post.call_args_list))

    @patch("request_sale_return_order_page.time.sleep")
    @patch("app.sale_return_discovery.requests.post")
    def test_discovery_reports_no_data_without_returning_rows(self, post, sleep):
        post.return_value = build_response(1, 0, 0)

        result = discover_earliest_date(
            "https://placeholder.invalid/api",
            date(2020, 1, 1),
            date(2020, 2, 15),
            "placeholder-token",
            30,
        )

        self.assertEqual(result["earliest_data_date"], None)
        self.assertEqual(result["coarse_windows_checked"], 2)
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(sleep.call_count, 1)
        self.assertNotIn("rows", json.dumps(result))

    @patch("request_sale_return_order_page.requests.post")
    def test_discovery_rejects_invalid_total_without_exposing_response(self, post):
        post.return_value = build_response(1, 0, 0)
        post.return_value._content = json.dumps(
            {"code": 200, "data": {"total": "invalid", "rows": []}}
        ).encode("utf-8")

        with self.assertRaisesRegex(ValueError, "缺少有效的 data.total"):
            discover_earliest_date(
                "https://placeholder.invalid/api",
                date(2020, 1, 1),
                date(2020, 1, 31),
                "placeholder-token",
                30,
            )

    @patch("app.sale_return_discovery.time.sleep")
    @patch("app.sale_return_discovery.requests.post")
    def test_discovery_rejects_inconsistent_final_day(self, post, _sleep):
        responses = [build_response(1, 1, 1)]
        responses.extend(build_response(1, 1, 1) for _ in range(5))
        responses.append(build_response(1, 0, 0))
        post.side_effect = responses

        with self.assertRaisesRegex(ValueError, "结果前后不一致"):
            discover_earliest_date(
                "https://placeholder.invalid/api",
                date(2020, 1, 1),
                date(2020, 1, 31),
                "placeholder-token",
                30,
            )


if __name__ == "__main__":
    unittest.main()
