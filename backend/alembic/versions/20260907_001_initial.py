"""Frozen initial schema: do not import evolving application metadata."""

from alembic import op
import sqlalchemy as sa

revision = "20260907_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("activity_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("response_time", sa.Float(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("completion_status", sa.String(length=32), nullable=False),
        sa.Column("difficulty_level", sa.Integer(), nullable=False),
        sa.Column("offline_created", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_sessions_event_id"),
        "activity_sessions",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_activity_sessions_user_id"),
        "activity_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repeat_rule", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminders_patient_id"), "reminders", ["patient_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("google_subject", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_subject"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "caregiver_patient_assignments",
        sa.Column("caregiver_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caregiver_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("caregiver_id", "patient_id"),
    )
    op.create_table(
        "emergency_contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_emergency_contacts_patient_id"),
        "emergency_contacts",
        ["patient_id"],
        unique=False,
    )
    op.create_table(
        "location_updates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=False),
        sa.Column("connection_state", sa.String(length=24), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_location_updates_patient_id"),
        "location_updates",
        ["patient_id"],
        unique=False,
    )
    op.create_table(
        "patients",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("preferred_language", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_refresh_sessions_user_id"),
        "refresh_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "safety_settings",
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("safe_zone_name", sa.String(length=80), nullable=False),
        sa.Column("safe_zone_latitude", sa.Float(), nullable=True),
        sa.Column("safe_zone_longitude", sa.Float(), nullable=True),
        sa.Column("safe_zone_radius_m", sa.Integer(), nullable=False),
        sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_return_note", sa.String(length=160), nullable=True),
        sa.Column("late_return_grace_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("patient_id"),
    )
    op.create_table(
        "sync_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        op.f("ix_sync_events_patient_id"), "sync_events", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_sync_events_user_id"), "sync_events", ["user_id"], unique=False
    )
    op.create_table(
        "safety_alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=36), nullable=True),
        sa.Column("escalated_to_priority", sa.Integer(), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_update_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["location_update_id"],
            ["location_updates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_safety_alerts_patient_id"),
        "safety_alerts",
        ["patient_id"],
        unique=False,
    )
    op.create_table(
        "sos_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=36), nullable=True),
        sa.Column("escalated_to_priority", sa.Integer(), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_update_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["location_update_id"],
            ["location_updates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sos_events_patient_id"), "sos_events", ["patient_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(op.f("ix_sos_events_patient_id"), table_name="sos_events")
    op.drop_table("sos_events")
    op.drop_index(op.f("ix_safety_alerts_patient_id"), table_name="safety_alerts")
    op.drop_table("safety_alerts")
    op.drop_index(op.f("ix_sync_events_user_id"), table_name="sync_events")
    op.drop_index(op.f("ix_sync_events_patient_id"), table_name="sync_events")
    op.drop_table("sync_events")
    op.drop_table("safety_settings")
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_table("patients")
    op.drop_index(op.f("ix_location_updates_patient_id"), table_name="location_updates")
    op.drop_table("location_updates")
    op.drop_index(
        op.f("ix_emergency_contacts_patient_id"), table_name="emergency_contacts"
    )
    op.drop_table("emergency_contacts")
    op.drop_table("caregiver_patient_assignments")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_reminders_patient_id"), table_name="reminders")
    op.drop_table("reminders")
    op.drop_index(op.f("ix_activity_sessions_user_id"), table_name="activity_sessions")
    op.drop_index(op.f("ix_activity_sessions_event_id"), table_name="activity_sessions")
    op.drop_table("activity_sessions")
    # ### end Alembic commands ###
