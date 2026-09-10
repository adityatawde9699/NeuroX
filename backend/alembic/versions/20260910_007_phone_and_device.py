"""Add phone verification and session device labels."""

from alembic import op
import sqlalchemy as sa

revision = "20260910_007"
down_revision = "20260910_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("phone_number", sa.String(16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "phone_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_unique_constraint("uq_users_phone_number", ["phone_number"])
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "device_name",
                sa.String(80),
                nullable=False,
                server_default="Unknown client",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.drop_column("device_name")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_phone_number", type_="unique")
        batch_op.drop_column("phone_verified")
        batch_op.drop_column("phone_number")
