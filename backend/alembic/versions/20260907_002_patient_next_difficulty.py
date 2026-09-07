"""Add next_difficulty to patients table (Phase 3 personalization)."""

from alembic import op
import sqlalchemy as sa

revision = "20260907_002"
down_revision = "20260907_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(
            sa.Column("next_difficulty", sa.Integer(), nullable=False, server_default="2")
        )


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_column("next_difficulty")
