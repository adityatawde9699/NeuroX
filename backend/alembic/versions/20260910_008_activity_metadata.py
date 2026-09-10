"""Add Phase 3 activity provenance and accessibility metadata."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_008"
down_revision = "20260910_007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("activity_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "content_version",
                sa.String(32),
                nullable=False,
                server_default="legacy",
            )
        )
        batch_op.add_column(
            sa.Column("interruptions", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "accessibility_mode",
                sa.String(32),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.add_column(
            sa.Column(
                "app_version", sa.String(32), nullable=False, server_default="unknown"
            )
        )
        batch_op.add_column(
            sa.Column(
                "model_version",
                sa.String(32),
                nullable=False,
                server_default="adaptive-v1",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("activity_sessions") as batch_op:
        batch_op.drop_column("model_version")
        batch_op.drop_column("app_version")
        batch_op.drop_column("accessibility_mode")
        batch_op.drop_column("interruptions")
        batch_op.drop_column("content_version")
