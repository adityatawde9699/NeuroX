"""Add consent, privacy-request, audit, and location-sharing records."""

from alembic import op
import sqlalchemy as sa

revision = "20260909_003"
down_revision = "20260907_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("safety_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "location_sharing_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.create_table(
        "consent_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("purpose", sa.String(48), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("notice_version", sa.String(32), nullable=False),
        sa.Column(
            "recorded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consent_records_patient_id", "consent_records", ["patient_id"])
    op.create_index("ix_consent_records_purpose", "consent_records", ["purpose"])
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("request_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_privacy_requests_patient_id", "privacy_requests", ["patient_id"]
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_patient_id", "audit_events", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_patient_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_privacy_requests_patient_id", table_name="privacy_requests")
    op.drop_table("privacy_requests")
    op.drop_index("ix_consent_records_purpose", table_name="consent_records")
    op.drop_index("ix_consent_records_patient_id", table_name="consent_records")
    op.drop_table("consent_records")
    with op.batch_alter_table("safety_settings") as batch_op:
        batch_op.drop_column("location_sharing_enabled")
