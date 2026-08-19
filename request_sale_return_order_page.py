import argparse
import json
import math
import time
from datetime import date
from typing import Any

import requests

from app.api_client import JijiaApiClient
from app.auth import JijiaAuthClient
from app.config import load_settings


API_PATH = "/operation/sale/returnOrder/page"


def parse_args() -> argparse.Namespace:
    """解析退货订单分页接口的请求参数。"""
    parser = argparse.ArgumentParser(
        description="单独请求积加退货订单分页接口，不写入数据库",
    )
    parser.add_argument(
        "--return-start-date",
        required=True,
        help="退货开始日期，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--return-end-date",
        required=True,
        help="退货结束日期，格式 YYYY-MM-DD",
    )
    parser.add_argument("--page", type=int, default=1, help="页码，默认 1")
    parser.add_argument("--pagesize", type=int, default=100, help="每页数量，官方上限 100")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="请求超时秒数，默认 30",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="根据每页实时 total 拉取完整日期窗口，只输出汇总",
    )
    return parser.parse_args()


def build_request_body(args: argparse.Namespace) -> dict[str, Any]:
    """校验命令行参数并生成官方字段格式的请求体。"""
    start_date = date.fromisoformat(args.return_start_date)
    end_date = date.fromisoformat(args.return_end_date)
    if end_date < start_date:
        raise ValueError("return-end-date 不能早于 return-start-date")
    if args.page < 1:
        raise ValueError("page 必须大于等于 1")
    if not 1 <= args.pagesize <= 100:
        raise ValueError("pagesize 必须在 1 到 100 之间")
    if args.timeout_seconds < 1:
        raise ValueError("timeout-seconds 必须大于等于 1")

    return {
        "returnStartDate": start_date.isoformat(),
        "returnEndDate": end_date.isoformat(),
        "page": args.page,
        "pagesize": args.pagesize,
    }


def summarize_response(response: requests.Response) -> dict[str, Any]:
    """只保留排查所需元数据，禁止输出退货订单明细。"""
    result: dict[str, Any] = {"http_status": response.status_code}
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        result["error"] = "响应不是有效 JSON"
        return result

    if not isinstance(payload, dict):
        result["error"] = "响应 JSON 顶层不是对象"
        return result

    result["business_code"] = payload.get("code")
    result["trace_id"] = payload.get("traceId") or payload.get("trace_id")
    messages = payload.get("messages")
    if messages:
        result["messages"] = messages

    data = payload.get("data")
    if isinstance(data, dict):
        rows = data.get("rows")
        result["data_summary"] = {
            "total": data.get("total"),
            "page": data.get("page"),
            "pagesize": data.get("pagesize"),
            "row_count": len(rows) if isinstance(rows, list) else None,
        }
    return result


def request_all_pages(
    url: str,
    request_body: dict[str, Any],
    access_token: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """按实时 total 拉取完整窗口，返回不含订单明细的汇总。"""
    page_no = int(request_body["page"])
    page_size = int(request_body["pagesize"])
    request_count = 0
    row_count = 0
    total_count = 0
    first_trace_id = None
    last_trace_id = None
    last_summary: dict[str, Any] = {}

    while True:
        page_body = {**request_body, "page": page_no}
        response = requests.post(
            url,
            json=page_body,
            headers={"accessToken": access_token},
            timeout=timeout_seconds,
        )
        request_count += 1
        last_summary = summarize_response(response)
        if not response.ok or last_summary.get("business_code") not in (0, 200):
            return {
                **last_summary,
                "data_summary": {
                    "total": total_count,
                    "required_pages": None,
                    "requested_pages": request_count,
                    "row_count": row_count,
                    "complete": False,
                },
            }

        page_summary = last_summary.get("data_summary") or {}
        page_total = page_summary.get("total")
        page_row_count = page_summary.get("row_count")
        if not isinstance(page_total, int) or not isinstance(page_row_count, int):
            raise ValueError("分页响应缺少有效的 data.total 或 data.rows")

        total_count = page_total
        row_count += page_row_count
        trace_id = last_summary.get("trace_id")
        first_trace_id = first_trace_id or trace_id
        last_trace_id = trace_id
        if page_no * page_size >= total_count:
            break

        # 官方默认每秒 5 次，完整分页测试按 0.2 秒间隔执行。
        time.sleep(0.2)
        page_no += 1

    required_pages = max(1, math.ceil(total_count / page_size))
    complete = row_count == total_count and request_count == required_pages
    return {
        "http_status": last_summary.get("http_status"),
        "business_code": last_summary.get("business_code"),
        "messages": last_summary.get("messages"),
        "first_trace_id": first_trace_id,
        "last_trace_id": last_trace_id,
        "data_summary": {
            "total": total_count,
            "required_pages": required_pages,
            "requested_pages": request_count,
            "row_count": row_count,
            "complete": complete,
        },
    }


def main() -> int:
    """获取凭证并执行一次退货订单分页请求。"""
    try:
        args = parse_args()
        request_body = build_request_body(args)
        settings = load_settings()
        auth_client = JijiaAuthClient(settings, timeout_seconds=args.timeout_seconds)
        token = auth_client.get_access_token()
        api_client = JijiaApiClient(settings, timeout_seconds=args.timeout_seconds)
        url = api_client.request_url({"path": API_PATH})

        if args.all_pages:
            if args.page != 1:
                raise ValueError("all-pages 模式必须从第 1 页开始")
            response_summary = request_all_pages(
                url,
                request_body,
                token.value,
                args.timeout_seconds,
            )
        else:
            response = requests.post(
                url,
                json=request_body,
                headers={"accessToken": token.value},
                timeout=args.timeout_seconds,
            )
            response_summary = summarize_response(response)
        result = {
            "method": "POST",
            "path": API_PATH,
            "request_body": request_body,
            **response_summary,
        }
        # ASCII JSON 可避免 PowerShell 终端再次破坏中文错误信息。
        print(json.dumps(result, ensure_ascii=True))
        successful = result.get("business_code") in (0, 200)
        if args.all_pages:
            successful = successful and bool(
                (result.get("data_summary") or {}).get("complete")
            )
        return 0 if successful else 1
    except (ValueError, requests.RequestException) as error:
        print(
            json.dumps(
                {
                    "error_type": type(error).__name__,
                    "error": "请求未完成，请检查参数、网络或本地鉴权配置",
                },
                ensure_ascii=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
