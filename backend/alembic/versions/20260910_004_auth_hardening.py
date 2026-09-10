"""Add persistent login protection and refresh-session families."""

from alembic import op
import sqlalchemy as sa

revision = "20260910_004"
down_revision = "20260909_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
        )
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.add_column(sa.Column("family_id", sa.String(36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            )
        )
        batch_op.add_column(
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("revoke_reason", sa.String(32), nullable=True))
    op.execute("UPDATE refresh_sessions SET family_id = id WHERE family_id IS NULL")
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.alter_column("family_id", existing_type=sa.String(36), nullable=False)
        batch_op.create_index(
            "ix_refresh_sessions_family_id", ["family_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.drop_index("ix_refresh_sessions_family_id")
        batch_op.drop_column("revoke_reason")
        batch_op.drop_column("revoked_at")
        batch_op.drop_column("last_used_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("family_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
