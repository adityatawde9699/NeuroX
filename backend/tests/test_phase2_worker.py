from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.database import Base, SessionLocal, engine
from app.models import (
    AccountToken,
    AuditEvent,
    Patient,
    PrivacyRequest,
    RefreshSession,
    Reminder,
    User,
)
from app.worker import run_maintenance


@pytest.fixture(scope="module", autouse=True)
def schema():
    Base.metadata.create_all(engine)


def test_maintenance_removes_only_expired_retained_auth_records(monkeypatch):
    monkeypatch.setenv("ACCOUNT_TOKEN_RETENTION_DAYS", "7")
    monkeypatch.setenv("SESSION_RETENTION_DAYS", "30")
    now = datetime.now(timezone.utc)
    user_id = str(uuid4())
    old_token_id = str(uuid4())
    current_token_id = str(uuid4())
    old_session_id = str(uuid4())
    current_session_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            User(
                id=user_id, name="Retention", email=f"{user_id}@test", role="CAREGIVER"
            )
        )
        db.add_all(
            [
                AccountToken(
                    id=old_token_id,
                    user_id=user_id,
                    purpose="password_reset",
                    token_hash=uuid4().hex + uuid4().hex,
                    expires_at=now - timedelta(days=8),
                    created_at=now - timedelta(days=9),
                ),
                AccountToken(
                    id=current_token_id,
                    user_id=user_id,
                    purpose="password_reset",
                    token_hash=uuid4().hex + uuid4().hex,
                    expires_at=now + timedelta(minutes=30),
                    created_at=now,
                ),
                RefreshSession(
                    id=old_session_id,
                    user_id=user_id,
                    family_id=old_session_id,
                    expires_at=now - timedelta(days=40),
                    revoked=True,
                    revoked_at=now - timedelta(days=31),
                ),
                RefreshSession(
                    id=current_session_id,
                    user_id=user_id,
                    family_id=current_session_id,
                    expires_at=now + timedelta(days=1),
                    revoked=False,
                ),
            ]
        )
        db.commit()
    result = run_maintenance()
    assert result["account_tokens_deleted"] == 1
    assert result["refresh_sessions_deleted"] == 1
    with SessionLocal() as db:
        assert db.get(AccountToken, old_token_id) is None
        assert db.get(AccountToken, current_token_id) is not None
        assert db.get(RefreshSession, old_session_id) is None
        assert db.get(RefreshSession, current_session_id) is not None


def test_approved_deletion_is_executed_transactionally():
    now = datetime.now(timezone.utc)
    patient_id = str(uuid4())
    admin_id = str(uuid4())
    request_id = str(uuid4())
    with SessionLocal() as db:
        db.add_all(
            [
                User(
                    id=patient_id,
                    name="Delete Me",
                    email=f"delete-{patient_id}@test",
                    role="PATIENT",
                    password_hash="password-hash",
                ),
                User(
                    id=admin_id,
                    name="Privacy Admin",
                    email=f"admin-{admin_id}@test",
                    role="ADMIN",
                ),
                Patient(user_id=patient_id, age=70),
                Reminder(
                    patient_id=patient_id,
                    type="hydration",
                    title="Drink water",
                    scheduled_time=now,
                ),
                PrivacyRequest(
                    id=request_id,
                    patient_id=patient_id,
                    request_type="deletion",
                    status="approved",
                    reviewed_by=admin_id,
                    reviewed_at=now,
                ),
            ]
        )
        db.commit()
    result = run_maintenance()
    assert result["privacy_deletions_completed"] == 1
    with SessionLocal() as db:
        user = db.get(User, patient_id)
        assert user.role == "DELETED"
        assert user.name == "Deleted account"
        assert user.password_hash is None
        assert db.get(Patient, patient_id) is None
        assert db.query(Reminder).filter_by(patient_id=patient_id).count() == 0
        assert db.get(PrivacyRequest, request_id).status == "completed"
        assert (
            db.query(AuditEvent)
            .filter_by(patient_id=patient_id, action="privacy_request.completed")
            .count()
            == 1
        )
