"""冻结同步任务选择的店铺站点范围。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_sync_job_market_scope"
down_revision: str | None = "0007_sync_job_config_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """空值沿用全部店铺，已有任务行为保持不变。"""
    with op.batch_alter_table("sync_job") as batch_op:
        batch_op.add_column(sa.Column("market_ids_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """移除任务店铺范围，不触碰同步业务数据。"""
    with op.batch_alter_table("sync_job") as batch_op:
        batch_op.drop_column("market_ids_json")
