"""Content-minimal append-only security and patient-data audit events."""

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record(
    db: Session,
    actor_id: str,
    action: str,
    patient_id: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            patient_id=patient_id,
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            metadata_json=metadata or {},
        )
    )
