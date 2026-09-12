"""为逻辑任务最新执行查询增加索引。"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_sync_job_task_index"
down_revision: str | None = "0008_sync_job_market_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只增加非唯一索引，不改写任务数据。"""
    op.create_index(
        "idx_sync_job_task_execution",
        "sync_job",
        ["task_no", "id"],
        unique=False,
    )


def downgrade() -> None:
    """移除逻辑任务执行索引，不触碰任务数据。"""
    op.drop_index("idx_sync_job_task_execution", table_name="sync_job")
