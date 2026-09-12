from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.user import enum_values


class JijiaAccountStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    VERIFICATION_FAILED = "verification_failed"
    INACTIVE = "inactive"


class CredentialSource(StrEnum):
    ENCRYPTED = "encrypted"
    ENVIRONMENT_LEGACY = "environment_legacy"


class JijiaAccount(TimestampMixin, Base):
    """保存积加开放平台账号及其加密凭证。"""

    __tablename__ = "jijia_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    masked_app_id: Mapped[str] = mapped_column(String(40), nullable=False)
    encrypted_app_id: Mapped[str | None] = mapped_column(String(1024))
    encrypted_app_key: Mapped[str | None] = mapped_column(String(1024))
    credential_source: Mapped[CredentialSource] = mapped_column(
        Enum(CredentialSource, native_enum=False, length=30, values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[JijiaAccountStatus] = mapped_column(
        Enum(JijiaAccountStatus, native_enum=False, length=30, values_callable=enum_values),
        nullable=False,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime())
    last_verify_error: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
