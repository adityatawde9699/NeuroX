"""
Phase 8 - Synchronization tests.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

if "DATABASE_URL" not in os.environ:
    _tmp = Path(tempfile.gettempdir())
    os.environ["DATABASE_URL"] = (
        f"sqlite:///{_tmp / f'neurox-sync-{uuid4().hex}.sqlite3'}"
    )

from app.main import app  # noqa: E402
from app.database import engine
from app.models import CaregiverPatientAssignment

_PATIENT_EMAIL = "maya@neurox.demo"
_PATIENT_PASSWORD = "NeuroXDemo!2026"
_CAREGIVER_EMAIL = "anita@neurox.demo"
_CAREGIVER_PASSWORD = "NeuroXDemo!2026"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def patient_headers(client):
    resp = client.post(
        "/auth/login",
        json={"email": _PATIENT_EMAIL, "password": _PATIENT_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def caregiver_headers(client):
    resp = client.post(
        "/auth/login",
        json={"email": _CAREGIVER_EMAIL, "password": _CAREGIVER_PASSWORD},
    )
    if resp.status_code != 200:
        uid = uuid4().hex[:8]
        client.post(
            "/auth/register",
            json={
                "name": f"CaregiverSync {uid}",
                "email": f"caregiver-sync-{uid}@neurox.test",
                "password": "SyncTest!1234",
                "role": "CAREGIVER",
            },
        )
        resp = client.post(
            "/auth/login",
            json={
                "email": f"caregiver-sync-{uid}@neurox.test",
                "password": "SyncTest!1234",
            },
        )
        assert resp.status_code == 200
        user_id = resp.json()["user"]["id"]
        with Session(engine) as db:
            db.add(
                CaregiverPatientAssignment(caregiver_id=user_id, patient_id="maya-demo")
            )
            db.commit()
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _activity_event(event_id):
    now = datetime.now(timezone.utc)
    return {
        "event_id": event_id,
        "event_type": "activity_completion",
        "patient_id": "maya-demo",
        "payload": {
            "event_id": event_id,
            "user_id": "maya-demo",
            "activity_id": "memory-match",
            "accuracy": 0.85,
            "response_time": 12.0,
            "attempts": 2,
            "difficulty_level": 2,
            "started_at": (now - timedelta(minutes=5)).isoformat(),
            "completed_at": now.isoformat(),
            "completion_status": "completed",
        },
    }


def _sos_event(event_id, message="I need help."):
    return {
        "event_id": event_id,
        "event_type": "sos_event",
        "patient_id": "maya-demo",
        "payload": {
            "message": message,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def test_sync_activity_completion_creates_session(client, patient_headers):
    event_id = f"evt-{uuid4().hex}"
    resp = client.post(
        "/sync/events", json=[_activity_event(event_id)], headers=patient_headers
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["results"][0]["status"] == "accepted"


def test_sync_duplicate_event_is_idempotent(client, patient_headers):
    event_id = f"idem-{uuid4().hex}"
    event = [_activity_event(event_id)]
    event[0]["payload"]["activity_id"] = "object-recall"
    first = client.post("/sync/events", json=event, headers=patient_headers)
    second = client.post("/sync/events", json=event, headers=patient_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["results"][0]["status"] == "duplicate"


def test_sync_envelope_accepts_offline_metadata(client, patient_headers):
    event_id = f"meta-{uuid4().hex}"
    event = _activity_event(event_id)
    event.update({
        "schema_version": 1,
        "device_time": datetime.now(timezone.utc).isoformat(),
        "attempt_count": 3,
        "origin": "android",
    })
    response = client.post("/sync/events", json=[event], headers=patient_headers)
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["status"] == "accepted"


def test_sync_sos_event_appears_in_safety(client, patient_headers, caregiver_headers):
    event_id = f"sos-{uuid4().hex}"
    resp = client.post(
        "/sync/events", json=[_sos_event(event_id)], headers=patient_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["status"] == "accepted"

    safety = client.get("/patients/maya-demo/safety", headers=caregiver_headers)
    assert safety.status_code == 200
    sos_events = safety.json().get("sosEvents", [])
    assert len(sos_events) >= 1


def test_location_update_accepted(client, patient_headers):
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/patients/maya-demo/location-updates",
        json={
            "latitude": 26.1447,
            "longitude": 91.7364,
            "accuracy_m": 10,
            "connection_state": "online",
            "captured_at": now.isoformat(),
        },
        headers=patient_headers,
    )
    assert resp.status_code == 201, resp.text


def test_unrelated_caregiver_cannot_sync_for_patient(client):
    uid = uuid4().hex[:8]
    reg = client.post(
        "/auth/register",
        json={
            "name": f"Intruder {uid}",
            "email": f"intruder-{uid}@neurox.test",
            "password": "IntruderPass!123",
            "role": "CAREGIVER",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]

    event = [_activity_event(f"bad-{uuid4().hex}")]
    resp = client.post(
        "/sync/events",
        json=event,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 200:
        assert resp.json()["results"][0]["status"] == "rejected"
        assert (
            "not assigned to this patient"
            in resp.json()["results"][0]["detail"].lower()
        )
    else:
        assert resp.status_code == 403
