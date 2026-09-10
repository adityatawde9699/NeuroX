"""Background maintenance worker for bounded authentication data retention."""

import logging
import os
import signal
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_

from app.audit import record
from app.database import SessionLocal
from app.models import (
    AccountToken,
    ActivitySession,
    CaregiverPatientAssignment,
    ConsentRecord,
    EmergencyContact,
    LocationUpdate,
    Patient,
    PrivacyRequest,
    RefreshSession,
    Reminder,
    SafetyAlert,
    SafetySettings,
    SOSEvent,
    SyncEvent,
    User,
)

logger = logging.getLogger("neurox.worker")
stopping = False


def run_maintenance() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    token_cutoff = now - timedelta(
        days=int(os.getenv("ACCOUNT_TOKEN_RETENTION_DAYS", "7"))
    )
    session_cutoff = now - timedelta(
        days=int(os.getenv("SESSION_RETENTION_DAYS", "30"))
    )
    with SessionLocal() as db:
        completed_deletions = _process_approved_deletions(db, now)
        tokens = db.execute(
            delete(AccountToken).where(
                or_(
                    AccountToken.expires_at < token_cutoff,
                    AccountToken.consumed_at < token_cutoff,
                )
            )
        ).rowcount
        sessions = db.execute(
            delete(RefreshSession).where(
                RefreshSession.revoked.is_(True),
                RefreshSession.revoked_at < session_cutoff,
            )
        ).rowcount
        db.commit()
    return {
        "privacy_deletions_completed": completed_deletions,
        "account_tokens_deleted": tokens,
        "refresh_sessions_deleted": sessions,
    }


def _process_approved_deletions(db, now: datetime) -> int:
    requests = (
        db.query(PrivacyRequest)
        .filter_by(request_type="deletion", status="approved")
        .all()
    )
    for request in requests:
        patient_id = request.patient_id
        db.execute(delete(SafetyAlert).where(SafetyAlert.patient_id == patient_id))
        db.execute(delete(SOSEvent).where(SOSEvent.patient_id == patient_id))
        db.execute(
            delete(LocationUpdate).where(LocationUpdate.patient_id == patient_id)
        )
        db.execute(
            delete(CaregiverPatientAssignment).where(
                CaregiverPatientAssignment.patient_id == patient_id
            )
        )
        db.execute(
            delete(EmergencyContact).where(EmergencyContact.patient_id == patient_id)
        )
        db.execute(
            delete(SafetySettings).where(SafetySettings.patient_id == patient_id)
        )
        db.execute(delete(Reminder).where(Reminder.patient_id == patient_id))
        db.execute(delete(ActivitySession).where(ActivitySession.user_id == patient_id))
        db.execute(delete(SyncEvent).where(SyncEvent.patient_id == patient_id))
        db.execute(delete(ConsentRecord).where(ConsentRecord.patient_id == patient_id))
        db.execute(delete(AccountToken).where(AccountToken.user_id == patient_id))
        db.execute(delete(RefreshSession).where(RefreshSession.user_id == patient_id))
        db.execute(delete(Patient).where(Patient.user_id == patient_id))
        user = db.get(User, patient_id)
        if user:
            user.name = "Deleted account"
            user.email = f"deleted-{user.id}@invalid.neurox"
            user.role = "DELETED"
            user.password_hash = None
            user.google_subject = None
            user.email_verified = False
        request.status = "completed"
        request.reviewed_at = request.reviewed_at or now
        record(
            db,
            actor_id=request.reviewed_by or patient_id,
            patient_id=patient_id,
            action="privacy_request.completed",
            target_id=request.id,
            metadata={"request_type": "deletion"},
        )
    return len(requests)


def _stop(*_args) -> None:
    global stopping
    stopping = True


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    interval = max(60, int(os.getenv("MAINTENANCE_INTERVAL_SECONDS", "3600")))
    while not stopping:
        try:
            result = run_maintenance()
            logger.info("Maintenance completed counts=%s", result)
        except Exception:
            logger.exception("Maintenance cycle failed")
        for _ in range(interval):
            if stopping:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
