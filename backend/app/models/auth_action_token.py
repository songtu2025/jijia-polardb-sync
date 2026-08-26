from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class AuthActionToken(TimestampMixin, Base):
    """保存邀请令牌摘要及单次使用状态。"""

    __tablename__ = "auth_action_token"
    __table_args__ = (Index("idx_auth_action_token_email_purpose", "email", "purpose"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False, default="invitation")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
