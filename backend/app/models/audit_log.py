from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class AuditLog(TimestampMixin, Base):
    """记录敏感业务写操作和完整原始 JSON 访问事件。"""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_log_created", "created_at"),
        Index(
            "idx_audit_log_account_action",
            "jijia_account_id",
            "action",
            "created_at",
        ),
        Index("idx_audit_log_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    jijia_account_id: Mapped[int | None] = mapped_column(ForeignKey("jijia_account.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100))
    request_id: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    changes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON())
