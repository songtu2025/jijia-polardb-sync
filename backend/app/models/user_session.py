from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class UserSession(TimestampMixin, Base):
    """保存服务端 Session 和 CSRF 摘要，不保存原始令牌。"""

    __tablename__ = "user_session"
    __table_args__ = (Index("idx_user_session_user_revoked", "user_id", "revoked_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    session_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime())
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent_summary: Mapped[str | None] = mapped_column(String(255))
