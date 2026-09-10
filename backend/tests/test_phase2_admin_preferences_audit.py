from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import AuditEvent, Patient, User


def register(client: TestClient, role: str) -> dict:
    suffix = uuid4().hex
    return client.post(
        "/api/v1/auth/register",
        json={
            "name": f"{role.title()} User",
            "email": f"{role.lower()}-{suffix}@neurox.test",
            "password": "AdminFlow!123",
            "role": role,
        },
    ).json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def admin_headers() -> dict[str, str]:
    with SessionLocal() as db:
        admin = User(
            name="Platform Administrator",
            email=f"admin-{uuid4().hex}@neurox.test",
            role="ADMIN",
            password_hash=hash_password("AdminFlow!123"),
            email_verified=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return headers(create_access_token(admin))


def test_admin_assignment_and_privacy_review_are_authorized_and_audited():
    with TestClient(app) as client:
        caregiver = register(client, "CAREGIVER")
        patient = register(client, "PATIENT")
        with SessionLocal() as db:
            db.add(Patient(user_id=patient["user"]["id"], age=70))
            db.commit()
        assignment = {
            "caregiver_id": caregiver["user"]["id"],
            "patient_id": patient["user"]["id"],
        }
        assert (
            client.post(
                "/api/v1/admin/assignments",
                json=assignment,
                headers=headers(caregiver["access_token"]),
            ).status_code
            == 403
        )
        admin = admin_headers()
        assert (
            client.post(
                "/api/v1/admin/assignments", json=assignment, headers=admin
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/v1/patients/{patient['user']['id']}",
                headers=headers(caregiver["access_token"]),
            ).status_code
            == 200
        )

        deletion = client.post(
            "/api/v1/patients/me/privacy/deletion-request",
            headers=headers(patient["access_token"]),
        ).json()
        reviewed = client.put(
            f"/api/v1/admin/privacy-requests/{deletion['requestId']}",
            headers=admin,
            json={"status": "approved"},
        )
        assert reviewed.json()["status"] == "approved"
        events = client.get(
            f"/api/v1/admin/audit-events?patient_id={patient['user']['id']}",
            headers=admin,
        ).json()
        actions = {event["action"] for event in events}
        assert "caregiver_assignment.created" in actions
        assert "privacy_request.approved" in actions
        assert "patient_data.accessed" in actions

        assert (
            client.delete(
                f"/api/v1/admin/assignments/{caregiver['user']['id']}/{patient['user']['id']}",
                headers=admin,
            ).status_code
            == 200
        )


def test_caregiver_controls_availability_and_notification_preferences():
    with TestClient(app) as client:
        caregiver = register(client, "CAREGIVER")
        caregiver_auth = headers(caregiver["access_token"])
        defaults = client.get(
            "/api/v1/caregivers/me/preferences", headers=caregiver_auth
        )
        assert defaults.json()["available"] is True
        updated = client.put(
            "/api/v1/caregivers/me/preferences",
            headers=caregiver_auth,
            json={"available": False, "notify_reminders": False},
        )
        assert updated.json()["available"] is False
        assert updated.json()["notifyReminders"] is False


def test_audit_events_cannot_be_changed_or_deleted_through_orm():
    with SessionLocal() as db:
        user = User(
            name="Audit Actor",
            email=f"audit-{uuid4().hex}@neurox.test",
            role="ADMIN",
            email_verified=True,
        )
        db.add(user)
        db.flush()
        event = AuditEvent(
            actor_id=user.id,
            action="audit.test_created",
            metadata_json={},
        )
        db.add(event)
        db.commit()
        event.action = "tampered"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()
        event = db.query(AuditEvent).first()
        db.delete(event)
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
