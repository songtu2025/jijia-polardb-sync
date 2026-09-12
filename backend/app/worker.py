import logging
import os
import socket
from threading import Event
from typing import Protocol
from uuid import uuid4

from app.sync_lock import SyncTaskLockUnavailable
from backend.app.core.config import get_web_settings
from backend.app.core.database import SessionLocal, engine
from backend.app.core.service_lifecycle import install_shutdown_handlers
from backend.app.core.service_logging import configure_service_logging
from backend.app.services.runtime_startup_service import validate_runtime_startup
from backend.app.services.sync_worker import CoreSyncExecutor, SyncWorker

logger = logging.getLogger(__name__)


def resolve_worker_name(configured_name: str) -> str:
    """优先使用配置名；本地无配置时用主机名和 PID 避免实例冲突。"""
    if name := configured_name.strip():
        return name
    process_suffix = f"-{os.getpid()}"
    host_name = socket.gethostname()[: 50 - len(process_suffix)]
    return f"{host_name}{process_suffix}"


def create_worker_instance_id(worker_name: str) -> str:
    """为每次启动生成唯一所有权代次，长度不超过数据库字段限制。"""
    return f"{worker_name}:{uuid4().hex}"


class WorkerLoop(Protocol):
    def start_runtime(self) -> None: ...

    def heartbeat_runtime(self) -> None: ...

    def stop_runtime(self) -> None: ...

    def recover_stale_jobs(self) -> int: ...

    def run_once(self) -> int | None: ...


def build_worker() -> SyncWorker:
    """创建数据库队列 Worker，不包含定时任务生成器。"""
    settings = get_web_settings()
    worker_name = resolve_worker_name(settings.worker_name)
    return SyncWorker(
        SessionLocal,
        CoreSyncExecutor(engine, settings),
        create_worker_instance_id(worker_name),
        heartbeat_interval_seconds=settings.worker_heartbeat_seconds,
        stale_after_seconds=settings.worker_stale_minutes * 60,
        recovery_lock_engine=engine,
        track_runtime=True,
        worker_name=worker_name,
        sync_lock_scope=settings.sync_lock_scope,
    )


def run_worker_loop(
    worker: WorkerLoop,
    stop_event: Event,
    *,
    poll_seconds: float,
) -> None:
    """只消费数据库队列，在停止信号后安全排空当前任务。"""
    while not stop_event.is_set():
        worker.heartbeat_runtime()
        try:
            worker.recover_stale_jobs()
        except SyncTaskLockUnavailable:
            logger.warning("已有同步进程运行，等待失联恢复锁")
            stop_event.wait(poll_seconds)
            continue
        if stop_event.is_set():
            break
        if worker.run_once() is None:
            stop_event.wait(poll_seconds)


def main() -> int:
    """运行一个 Worker 实例；异常退出非零，并始终释放数据库连接池。"""
    configure_service_logging()
    exit_code = 0
    worker: SyncWorker | None = None
    try:
        settings = get_web_settings()
        configure_service_logging(settings.log_level)
        validate_runtime_startup(settings, engine)
        stop_event = Event()
        install_shutdown_handlers(stop_event, "Worker")
        worker = build_worker()
        worker.start_runtime()
        run_worker_loop(
            worker,
            stop_event,
            poll_seconds=settings.worker_poll_seconds,
        )
    except KeyboardInterrupt:
        logger.info("Worker 收到键盘停止请求")
    except Exception as error:
        logger.error("Worker 运行失败: error_type=%s", type(error).__name__)
        exit_code = 1
    finally:
        if worker is not None:
            try:
                worker.stop_runtime()
            except Exception as error:
                logger.error("Worker 停止状态写入失败: error_type=%s", type(error).__name__)
                exit_code = 1
        try:
            engine.dispose()
        except Exception as error:
            logger.error("数据库连接池释放失败: error_type=%s", type(error).__name__)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
