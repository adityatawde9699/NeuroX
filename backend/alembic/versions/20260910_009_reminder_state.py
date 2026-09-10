"""Add local-time reminder acknowledgement and snooze state."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_009"
down_revision = "20260910_008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(24), nullable=False, server_default="upcoming"))
        batch_op.add_column(sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("timezone_name", sa.String(64), nullable=False, server_default="Asia/Kolkata"))


def downgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.drop_column("timezone_name")
        batch_op.drop_column("acknowledged_at")
        batch_op.drop_column("snoozed_until")
        batch_op.drop_column("status")
