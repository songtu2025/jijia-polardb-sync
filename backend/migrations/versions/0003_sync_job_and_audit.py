"""创建 M3 Worker 任务和审计日志表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sync_job_and_audit"
down_revision: str | None = "0002_jijia_account_and_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只创建 Web 任务表，不修改既有同步表。"""
    op.create_table(
        "sync_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_no", sa.String(length=64), nullable=False),
        sa.Column("jijia_account_id", sa.Integer(), nullable=False),
        sa.Column("api_code", sa.String(length=100), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("schedule_slot_key", sa.String(length=100), nullable=True),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("progress_json", sa.JSON(), nullable=True),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("sync_batch_no", sa.String(length=64), nullable=True),
        sa.Column("retry_of_job_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["jijia_account_id"], ["jijia_account.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["retry_of_job_id"], ["sync_job.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_no", name="uk_sync_job_job_no"),
        sa.UniqueConstraint("schedule_slot_key", name="uk_sync_job_schedule_slot"),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'retry', 'schedule')",
            name="ck_sync_job_trigger_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'success', 'partial_failed', 'failed')",
            name="ck_sync_job_status",
        ),
        sa.CheckConstraint(
            "job_type IN ('history_backfill', 'update_incremental', 'sync')",
            name="ck_sync_job_type",
        ),
    )
    op.create_index("idx_sync_job_status_created", "sync_job", ["status", "created_at"])
    op.create_index(
        "idx_sync_job_account_api_created",
        "sync_job",
        ["jijia_account_id", "api_code", "created_at"],
    )
    op.create_index("idx_sync_job_heartbeat", "sync_job", ["status", "heartbeat_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("jijia_account_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("changes_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["jijia_account_id"], ["jijia_account.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_log_created", "audit_log", ["created_at"])
    op.create_index(
        "idx_audit_log_account_action",
        "audit_log",
        ["jijia_account_id", "action", "created_at"],
    )
    op.create_index("idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"])


def downgrade() -> None:
    """拒绝删除已经被同步批次引用的任务和审计证据。"""
    raise RuntimeError("0003 downgrade is not supported; restore snapshot/PITR")
