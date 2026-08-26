import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.v1 import auth, invitations, users
from backend.app.core.config import get_web_settings
from backend.app.core.errors import ApiError


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时验证生产安全配置，配置错误时拒绝提供服务。"""
    get_web_settings()
    yield


def create_app(validate_settings: bool = True) -> FastAPI:
    """创建不执行同步任务的 FastAPI 管理服务。"""
    app = FastAPI(
        title="积加数据同步 Web 服务",
        version="0.1.0",
        lifespan=lifespan if validate_settings else None,
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith("/api/v1/auth"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                },
                "requestId": request.state.request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数不正确",
                    "details": error.errors(),
                },
                "requestId": request.state.request_id,
            },
        )

    @app.get("/health/live")
    def health_live(request: Request) -> dict[str, object]:
        return {"data": {"status": "ok"}, "requestId": request.state.request_id}

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(invitations.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    return app


app = create_app()
