"""Add caregiver preferences, privacy review, and immutable audit triggers."""

from alembic import op
import sqlalchemy as sa

revision = "20260910_006"
down_revision = "20260910_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caregiver_settings",
        sa.Column(
            "caregiver_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("notify_sos", sa.Boolean(), nullable=False),
        sa.Column("notify_safety_alerts", sa.Boolean(), nullable=False),
        sa.Column("notify_reminders", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("privacy_requests") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by", sa.String(36), nullable=True))
        batch_op.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_privacy_requests_reviewed_by_users",
            "users",
            ["reviewed_by"],
            ["id"],
        )
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit_events are append-only'; END; $$"
        )
        op.execute(
            "CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation()"
        )
    elif dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER audit_events_append_only ON audit_events")
        op.execute("DROP FUNCTION reject_audit_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER audit_events_no_delete")
        op.execute("DROP TRIGGER audit_events_no_update")
    with op.batch_alter_table("privacy_requests") as batch_op:
        batch_op.drop_constraint(
            "fk_privacy_requests_reviewed_by_users", type_="foreignkey"
        )
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
    op.drop_table("caregiver_settings")
