"""增加同步 Worker 运行心跳和任务领取索引。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_worker_runtime"
down_revision: str | None = "0005_sync_job_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只扩展 Web 任务控制域，不修改既有同步业务表。"""
    op.create_table(
        "worker_runtime",
        sa.Column("worker_name", sa.String(length=50), nullable=False),
        sa.Column("instance_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_job_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('idle', 'running', 'stopped')",
            name="ck_worker_runtime_status",
        ),
        sa.ForeignKeyConstraint(
            ["current_job_id"],
            ["sync_job.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("worker_name"),
    )
    op.create_index(
        "idx_sync_job_claim",
        "sync_job",
        ["status", "queued_at", "id"],
    )


def downgrade() -> None:
    """回退运行状态控制表；任务队列和业务数据保持不变。"""
    op.drop_index("idx_sync_job_claim", table_name="sync_job")
    op.drop_table("worker_runtime")
