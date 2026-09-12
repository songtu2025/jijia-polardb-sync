import logging
import signal
from threading import Event
from types import FrameType

logger = logging.getLogger(__name__)


def install_shutdown_handlers(stop_event: Event, service_name: str) -> None:
    """收到停止信号时通知常驻服务结束当前安全窗口。"""

    def request_stop(signal_number: int, _frame: FrameType | None) -> None:
        logger.info(
            "%s 收到停止信号: signal=%s",
            service_name,
            signal.Signals(signal_number).name,
        )
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_stop)
