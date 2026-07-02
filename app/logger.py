import logging
from pathlib import Path


def setup_logging(log_dir: str | Path = "logs", level: str = "INFO") -> None:
    """初始化控制台和文件日志。

    同步服务通常由 cron 或 systemd 调度，文件日志用于事后排查；控制台日志
    方便本地手动运行时直接观察结果。
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(log_dir) / "sync.log", encoding="utf-8"),
        ],
    )
