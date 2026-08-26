from typing import Any

from fastapi import Request


def success_response(request: Request, data: Any) -> dict[str, Any]:
    """生成统一成功响应并附带请求标识。"""
    return {"data": data, "requestId": request.state.request_id}
