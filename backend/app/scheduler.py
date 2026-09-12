import logging
from threading import Event
from typing import Protocol

from backend.app.core.config import get_web_settings
from backend.app.core.database import SessionLocal, engine
from backend.app.core.service_lifecycle import install_shutdown_handlers
from backend.app.core.service_logging import configure_service_logging
from backend.app.services.runtime_startup_service import validate_runtime_startup
from backend.app.services.scheduler import SyncScheduler

logger = logging.getLogger(__name__)


class SchedulerLoop(Protocol):
    def enqueue_due_jobs(self) -> int: ...


def build_scheduler() -> SyncScheduler:
    """创建只负责生成到期队列任务的 Scheduler。"""
    return SyncScheduler(SessionLocal, get_web_settings())


def run_scheduler_loop(
    scheduler: SchedulerLoop,
    stop_event: Event,
    *,
    poll_seconds: float,
) -> None:
    """启动后立即扫描，并按固定间隔持续生成到期任务。"""
    while not stop_event.is_set():
        scheduler.enqueue_due_jobs()
        stop_event.wait(max(poll_seconds, 0.01))


def main() -> int:
    """运行唯一 Scheduler；异常退出非零，并始终释放数据库连接池。"""
    configure_service_logging()
    exit_code = 0
    try:
        settings = get_web_settings()
        configure_service_logging(settings.log_level)
        validate_runtime_startup(settings, engine)
        stop_event = Event()
        install_shutdown_handlers(stop_event, "Scheduler")
        run_scheduler_loop(
            build_scheduler(),
            stop_event,
            poll_seconds=settings.worker_poll_seconds,
        )
    except KeyboardInterrupt:
        logger.info("Scheduler 收到键盘停止请求")
    except Exception as error:
        logger.error("Scheduler 运行失败: error_type=%s", type(error).__name__)
        exit_code = 1
    finally:
        try:
            engine.dispose()
        except Exception as error:
            logger.error("数据库连接池释放失败: error_type=%s", type(error).__name__)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
