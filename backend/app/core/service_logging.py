import logging
from typing import TextIO

SERVICE_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class _RemoveExceptionDetails(logging.Filter):
    """禁止服务日志处理器输出异常正文和堆栈。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def configure_service_logging(
    level: str = "INFO",
    *,
    stream: TextIO | None = None,
) -> None:
    """把项目日志写到标准错误，由 systemd journal 统一收集。"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(stream)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(SERVICE_LOG_FORMAT))
    handler.addFilter(_RemoveExceptionDetails())

    # 只接管项目命名空间，避免第三方库在 INFO 级别输出 URL 或请求上下文。
    for logger_name in ("backend", "app"):
        project_logger = logging.getLogger(logger_name)
        project_logger.handlers = [handler]
        project_logger.setLevel(log_level)
        project_logger.propagate = False
