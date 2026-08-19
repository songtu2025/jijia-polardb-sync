import json
import unittest
from unittest.mock import patch

from requests import Response

from request_sale_return_order_page import request_all_pages


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
    @patch("request_sale_return_order_page.time.sleep")
    @patch("request_sale_return_order_page.requests.post")
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


if __name__ == "__main__":
    unittest.main()
