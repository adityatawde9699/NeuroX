"""store offline synchronization envelope metadata

Revision ID: 20260910_010
Revises: 20260910_009
"""

from alembic import op
import sqlalchemy as sa


revision = "20260910_010"
down_revision = "20260910_009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sync_events") as batch:
        batch.add_column(sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("device_time", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("origin", sa.String(length=32), nullable=False, server_default="android"))


def downgrade() -> None:
    with op.batch_alter_table("sync_events") as batch:
        batch.drop_column("origin")
        batch.drop_column("attempt_count")
        batch.drop_column("device_time")
        batch.drop_column("schema_version")
