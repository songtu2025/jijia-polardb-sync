from collections.abc import Callable
from time import sleep
from typing import TypeVar

T = TypeVar("T")


def retry_call(func: Callable[[], T], retries: int = 3, delay_seconds: float = 1.0) -> T:
    """用固定间隔重试一个无参函数。

    同步引擎会在外层记录真实尝试次数和失败上下文；这里保持简单，只负责
    多次调用和最终抛出最后一次异常。
    """
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as error:
            last_error = error
            if attempt < retries:
                sleep(delay_seconds)
    assert last_error is not None
    raise last_error
