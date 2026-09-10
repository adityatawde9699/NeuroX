"""Phase 3 reminder acknowledgement, offline-safe state, and medication guardrails."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import AuditEvent, CaregiverPatientAssignment


def register(client: TestClient, role: str, name: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": f"phase3-{uuid4().hex}@neurox.test",
            "password": "Phase3Test!123",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(identity: dict) -> dict:
    return {"Authorization": f"Bearer {identity['access_token']}"}


def test_medication_schedule_requires_caregiver_but_patient_controls_status():
    with TestClient(app) as client:
        patient = register(client, "PATIENT", "Reminder Patient")
        caregiver = register(client, "CAREGIVER", "Reminder Caregiver")
        patient_id = patient["user"]["id"]
        caregiver_id = caregiver["user"]["id"]
        with SessionLocal() as db:
            db.add(
                CaregiverPatientAssignment(
                    caregiver_id=caregiver_id,
                    patient_id=patient_id,
                )
            )
            db.commit()

        payload = {
            "patient_id": patient_id,
            "type": "medication",
            "title": "Check care plan",
            "scheduled_time": "2026-09-11T09:00:00+05:30",
            "repeat_rule": "daily",
            "timezone_name": "Asia/Kolkata",
        }
        denied = client.post("/reminders", headers=headers(patient), json=payload)
        assert denied.status_code == 403
        assert "caregiver" in denied.json()["detail"].lower()

        created = client.post("/reminders", headers=headers(caregiver), json=payload)
        assert created.status_code == 201, created.text
        reminder_id = created.json()["id"]
        assert created.json()["status"] == "upcoming"
        assert created.json()["timezoneName"] == "Asia/Kolkata"

        schedule_change = client.put(
            f"/reminders/{reminder_id}",
            headers=headers(patient),
            json={"scheduled_time": "2026-09-11T10:00:00+05:30"},
        )
        assert schedule_change.status_code == 403

        missing_time = client.put(
            f"/reminders/{reminder_id}",
            headers=headers(patient),
            json={"status": "snoozed"},
        )
        assert missing_time.status_code == 422

        snoozed = client.put(
            f"/reminders/{reminder_id}",
            headers=headers(patient),
            json={
                "status": "snoozed",
                "snoozed_until": "2026-09-11T09:10:00+05:30",
            },
        )
        assert snoozed.status_code == 200, snoozed.text
        assert snoozed.json()["status"] == "snoozed"
        assert snoozed.json()["completed"] is False
        assert snoozed.json()["acknowledgedAt"] is not None

        done = client.put(
            f"/reminders/{reminder_id}",
            headers=headers(patient),
            json={"status": "done"},
        )
        assert done.status_code == 200, done.text
        assert done.json()["status"] == "done"
        assert done.json()["completed"] is True
        assert done.json()["snoozedUntil"] is None

        confirmed = client.put(
            f"/reminders/{reminder_id}",
            headers=headers(caregiver),
            json={"repeat_rule": "weekly"},
        )
        assert confirmed.status_code == 200, confirmed.text
        with SessionLocal() as db:
            audits = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.actor_id == caregiver_id,
                    AuditEvent.action == "reminder.medication_schedule_confirmed",
                    AuditEvent.target_id == reminder_id,
                )
                .order_by(AuditEvent.occurred_at)
                .all()
            )
            assert [audit.metadata_json for audit in audits] == [
                {"fields": ["created"]},
                {"fields": ["repeat_rule"]},
            ]


def test_non_medication_reminder_can_be_marked_missed():
    with TestClient(app) as client:
        patient = register(client, "PATIENT", "Activity Reminder Patient")
        created = client.post(
            "/reminders",
            headers=headers(patient),
            json={
                "patient_id": patient["user"]["id"],
                "type": "hydration",
                "title": "Have some water",
                "scheduled_time": "2026-09-11T10:00:00Z",
            },
        )
        assert created.status_code == 201, created.text
        missed = client.put(
            f"/reminders/{created.json()['id']}",
            headers=headers(patient),
            json={"status": "missed"},
        )
        assert missed.status_code == 200, missed.text
        assert missed.json()["status"] == "missed"
        assert missed.json()["completed"] is False


def test_invalid_time_zone_is_rejected():
    with TestClient(app) as client:
        patient = register(client, "PATIENT", "Timezone Patient")
        response = client.post(
            "/reminders",
            headers=headers(patient),
            json={
                "patient_id": patient["user"]["id"],
                "type": "appointment",
                "title": "Appointment",
                "scheduled_time": "2026-09-11T10:00:00Z",
                "timezone_name": "Mars/Olympus",
            },
        )
        assert response.status_code == 422


def test_medication_type_cannot_bypass_confirmation_with_different_casing():
    with TestClient(app) as client:
        patient = register(client, "PATIENT", "Type Validation Patient")
        response = client.post(
            "/reminders",
            headers=headers(patient),
            json={
                "patient_id": patient["user"]["id"],
                "type": "Medication",
                "title": "Unsafe casing",
                "scheduled_time": "2026-09-11T10:00:00Z",
            },
        )
        assert response.status_code == 422
