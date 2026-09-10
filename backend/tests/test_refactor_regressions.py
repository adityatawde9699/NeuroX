"""Exercise shared authorization and handlers through both HTTP and sync."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine
from app.main import app
from app.models import CaregiverPatientAssignment, Patient


@pytest.fixture
def accounts():
    with TestClient(app) as client:
        identities = {}
        for name, role in [
            ("first", "PATIENT"),
            ("second", "PATIENT"),
            ("caregiver", "CAREGIVER"),
        ]:
            response = client.post(
                "/auth/register",
                json={
                    "name": name,
                    "email": f"{uuid4().hex}@neurox.test",
                    "password": "Regression!123",
                    "role": role,
                },
            )
            assert response.status_code == 201
            identities[name] = (
                response.json()["user"]["id"],
                {"Authorization": f"Bearer {response.json()['access_token']}"},
            )
        with Session(engine) as db:
            for name in ("first", "second"):
                db.add(Patient(user_id=identities[name][0], age=70))
                db.add(
                    CaregiverPatientAssignment(
                        caregiver_id=identities["caregiver"][0],
                        patient_id=identities[name][0],
                    )
                )
            db.commit()
        yield client, identities


def reminder(client, identity):
    patient_id, headers = identity
    response = client.post(
        "/reminders",
        headers=headers,
        json={
            "patient_id": patient_id,
            "type": "hydration",
            "title": "Water reminder",
            "scheduled_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_reminder_sync_and_replay_use_extracted_handler(accounts):
    client, identities = accounts
    patient_id, headers = identities["first"]
    reminder_id = reminder(client, identities["first"])
    event = {
        "event_id": str(uuid4()),
        "event_type": "reminder_update",
        "patient_id": patient_id,
        "payload": {"reminder_id": reminder_id, "changes": {"completed": True}},
    }
    first = client.post("/sync/events", headers=headers, json=[event])
    assert first.status_code == 200
    assert first.json()["results"][0]["status"] == "accepted"
    assert (
        client.get(f"/patients/{patient_id}/reminders", headers=headers).json()[0][
            "completed"
        ]
        is True
    )
    assert (
        client.post("/sync/events", headers=headers, json=[event]).json()["results"][0][
            "status"
        ]
        == "duplicate"
    )


def test_multi_patient_caregiver_cannot_misattribute_reminder_sync(accounts):
    client, identities = accounts
    first_id, _ = identities["first"]
    second_id, second_headers = identities["second"]
    reminder_id = reminder(client, identities["second"])
    event = {
        "event_id": str(uuid4()),
        "event_type": "reminder_update",
        "patient_id": first_id,
        "payload": {"reminder_id": reminder_id, "changes": {"completed": True}},
    }
    for _ in range(2):
        response = client.post(
            "/sync/events", headers=identities["caregiver"][1], json=[event]
        )
        assert response.json()["results"][0]["status"] == "rejected"
    assert (
        client.get(f"/patients/{second_id}/reminders", headers=second_headers).json()[
            0
        ]["completed"]
        is False
    )


def test_revoked_assignment_cannot_replay_prior_sync_result(accounts):
    client, identities = accounts
    patient_id, _ = identities["first"]
    caregiver_id, headers = identities["caregiver"]
    event = {
        "event_id": str(uuid4()),
        "event_type": "sos_event",
        "patient_id": patient_id,
        "payload": {"message": "Please check on me."},
    }
    assert (
        client.post("/sync/events", headers=headers, json=[event]).json()["results"][0][
            "status"
        ]
        == "accepted"
    )
    with Session(engine) as db:
        db.get(CaregiverPatientAssignment, (caregiver_id, patient_id)).active = False
        db.commit()
    result = client.post("/sync/events", headers=headers, json=[event]).json()[
        "results"
    ][0]
    assert result["status"] == "rejected"
    assert "result" not in result
    assert (
        client.get(f"/patients/{patient_id}/safety", headers=headers).status_code == 403
    )


def test_activity_event_ids_cannot_reveal_another_patients_session(accounts):
    client, identities = accounts
    first_id, first_headers = identities["first"]
    second_id, second_headers = identities["second"]
    payload = {
        "user_id": first_id,
        "difficulty_level": 2,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "event_id": str(uuid4()),
    }
    assert (
        client.post(
            "/activities/memory-match/start", headers=first_headers, json=payload
        ).status_code
        == 201
    )
    replay = client.post(
        "/activities/memory-match/start",
        headers=second_headers,
        json={**payload, "user_id": second_id},
    )
    assert replay.status_code == 403
    assert "session_id" not in replay.json()
    assert (
        client.post(
            "/activities/object-recall/start", headers=first_headers, json=payload
        ).status_code
        == 409
    )


def test_caregiver_cannot_record_own_activity_via_http_or_sync(accounts):
    client, identities = accounts
    caregiver_id, headers = identities["caregiver"]
    payload = {
        "user_id": caregiver_id,
        "difficulty_level": 2,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "event_id": str(uuid4()),
    }
    assert (
        client.post(
            "/activities/memory-match/start", headers=headers, json=payload
        ).status_code
        == 403
    )
    payload.update(
        activity_id="memory-match",
        completed_at=datetime.now(timezone.utc).isoformat(),
        accuracy=1,
        response_time=5,
        attempts=1,
        completion_status="completed",
    )
    assert (
        client.post(
            "/activities/memory-match/complete", headers=headers, json=payload
        ).status_code
        == 403
    )
    event = {
        "event_id": payload["event_id"],
        "event_type": "activity_completion",
        "patient_id": caregiver_id,
        "payload": payload,
    }
    assert (
        client.post("/sync/events", headers=headers, json=[event]).json()["results"][0][
            "status"
        ]
        == "rejected"
    )
