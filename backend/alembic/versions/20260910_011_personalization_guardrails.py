"""add explainable personalization guardrails

Revision ID: 20260910_011
Revises: 20260910_010
"""

from alembic import op
import sqlalchemy as sa

revision = "20260910_011"
down_revision = "20260910_010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("personalization_override", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("last_difficulty_change_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("last_difficulty_change_at")
        batch.drop_column("personalization_override")
