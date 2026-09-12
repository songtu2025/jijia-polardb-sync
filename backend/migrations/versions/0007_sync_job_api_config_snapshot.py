"""冻结同步任务使用的接口配置版本。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_sync_job_config_snapshot"
down_revision: str | None = "0006_worker_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只扩展 Web 任务表，既有历史任务允许没有配置快照。"""
    with op.batch_alter_table("sync_job") as batch_op:
        batch_op.add_column(sa.Column("api_config_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("api_config_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("api_config_snapshot_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """仅移除任务配置快照，不触碰同步业务数据。"""
    with op.batch_alter_table("sync_job") as batch_op:
        batch_op.drop_column("api_config_snapshot_json")
        batch_op.drop_column("api_config_hash")
        batch_op.drop_column("api_config_version")
