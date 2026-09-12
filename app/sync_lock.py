import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal, TypeAlias

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

SYNC_TASK_LOCK_NAME = "jijia_polardb_sync_task"
ACCOUNT_SYNC_TASK_LOCK_PREFIX = "jijia_polardb_sync_account:"
MYSQL_NAMED_LOCK_MAX_BYTES = 64
SyncLockScope: TypeAlias = Literal["global", "account"]


class SyncTaskLockUnavailable(RuntimeError):
    """表示已有同步任务持有目标互斥锁。"""


def sync_task_lock_name(
    scope: SyncLockScope = "global",
    account_id: int | None = None,
) -> str:
    """生成不包含凭据等敏感信息的稳定同步锁键。"""
    if scope == "global":
        return SYNC_TASK_LOCK_NAME
    if scope != "account":
        raise ValueError("不支持的同步锁范围")
    if isinstance(account_id, bool) or account_id is None or account_id <= 0:
        raise ValueError("账号锁需要有效的账号 ID")
    lock_name = f"{ACCOUNT_SYNC_TASK_LOCK_PREFIX}{account_id}"
    if len(lock_name.encode("utf-8")) > MYSQL_NAMED_LOCK_MAX_BYTES:
        raise ValueError("账号同步锁键超过 MySQL 长度限制")
    return lock_name


@contextmanager
def sync_task_lock(
    engine: Any,
    logger: logging.Logger | None = None,
    *,
    scope: SyncLockScope = "global",
    account_id: int | None = None,
) -> Iterator[None]:
    """在 MySQL 连接上按配置范围持有同步锁直到任务结束。

    SQLite 仅用于本地隔离测试，不支持 MySQL named lock，因此直接放行。
    """
    lock_name = sync_task_lock_name(scope, account_id)
    engine_dialect = getattr(getattr(engine, "dialect", None), "name", None)
    if engine_dialect == "sqlite":
        yield
        return

    task_logger = logger or logging.getLogger(__name__)
    connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    lock_acquired = False
    try:
        result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 0)"),
            {"lock_name": lock_name},
        ).scalar()
        if result == 0:
            raise SyncTaskLockUnavailable("同步任务锁已被占用")
        if result != 1:
            raise RuntimeError("获取同步任务锁失败")
        lock_acquired = True
        yield
    finally:
        if lock_acquired:
            try:
                connection.execute(
                    text("SELECT RELEASE_LOCK(:lock_name)"),
                    {"lock_name": lock_name},
                )
            except SQLAlchemyError as error:
                task_logger.warning(
                    "release sync task lock failed: lock=%s error_type=%s",
                    lock_name,
                    type(error).__name__,
                )
        connection.close()
