from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.user import enum_values


class ScheduleMode(StrEnum):
    MANUAL_ONLY = "manual_only"
    DAILY = "daily"
    CRON = "cron"


class WindowMode(StrEnum):
    CHECKPOINT = "checkpoint"
    LOOKBACK_DAYS = "lookback_days"
    START_DATE = "start_date"


class AccountApiPolicy(TimestampMixin, Base):
    """保存单个积加账号对官方接口目录的运行策略。"""

    __tablename__ = "account_api_policy"
    __table_args__ = (
        UniqueConstraint("jijia_account_id", "api_code", name="uk_account_api_policy_account_api"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jijia_account_id: Mapped[int] = mapped_column(ForeignKey("jijia_account.id"), nullable=False)
    api_code: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_mode: Mapped[ScheduleMode] = mapped_column(
        Enum(ScheduleMode, native_enum=False, length=20, values_callable=enum_values),
        nullable=False,
    )
    schedule_expr: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")
    window_mode: Mapped[WindowMode | None] = mapped_column(
        Enum(WindowMode, native_enum=False, length=20, values_callable=enum_values)
    )
    lookback_days: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date())
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
