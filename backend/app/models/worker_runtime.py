from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class WorkerRuntime(TimestampMixin, Base):
    """按实例保存同步 Worker 的在线心跳和当前任务。"""

    __tablename__ = "worker_runtime"
    __table_args__ = (
        CheckConstraint(
            "status IN ('idle', 'running', 'stopped')",
            name="ck_worker_runtime_status",
        ),
    )

    worker_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_job.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime())
