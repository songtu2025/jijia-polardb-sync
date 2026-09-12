"""新增积加账号和账号接口策略。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_jijia_account_and_policy"
down_revision: str | None = "0001_identity_and_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只新增 M2 表，不修改现有同步表或历史数据。"""
    op.create_table(
        "jijia_account",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("masked_app_id", sa.String(length=40), nullable=False),
        sa.Column("encrypted_app_id", sa.String(length=1024), nullable=True),
        sa.Column("encrypted_app_key", sa.String(length=1024), nullable=True),
        sa.Column(
            "credential_source",
            sa.Enum("encrypted", "environment_legacy", name="credential_source", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending_verification",
                "active",
                "verification_failed",
                "inactive",
                name="jijia_account_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_verify_error", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_code", name="uk_jijia_account_code"),
    )
    op.create_table(
        "account_api_policy",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jijia_account_id", sa.Integer(), nullable=False),
        sa.Column("api_code", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "schedule_mode",
            sa.Enum("manual_only", "daily", "cron", name="schedule_mode", native_enum=False),
            nullable=False,
        ),
        sa.Column("schedule_expr", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "window_mode",
            sa.Enum(
                "checkpoint",
                "lookback_days",
                "start_date",
                name="window_mode",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("lookback_days", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["jijia_account_id"], ["jijia_account.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jijia_account_id",
            "api_code",
            name="uk_account_api_policy_account_api",
        ),
    )


def downgrade() -> None:
    """回退时只删除本迁移新增的两张表。"""
    op.drop_table("account_api_policy")
    op.drop_table("jijia_account")
