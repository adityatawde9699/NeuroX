"""Cross-patient authorization checks for every patient-data API domain."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(client: TestClient, email: str, password: str = "NeuroXDemo!2026") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def patient_headers(client):
    return auth(client, "maya@neurox.demo")


@pytest.fixture(scope="module")
def stranger_headers(client):
    email = f"matrix-{uuid4().hex}@neurox.test"
    response = client.post(
        "/auth/register",
        json={
            "name": "Unassigned Caregiver",
            "email": email,
            "password": "MatrixTest!123",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def owned_records(client, patient_headers):
    contact = client.post(
        "/patients/maya-demo/emergency-contacts",
        headers=patient_headers,
        json={
            "name": "Matrix Contact",
            "phone": "+91 90000 12345",
            "relationship": "Family",
            "priority": 4,
        },
    )
    assert contact.status_code == 201, contact.text
    reminder = client.post(
        "/reminders",
        headers=patient_headers,
        json={
            "patient_id": "maya-demo",
            "type": "hydration",
            "title": "Matrix Reminder",
            "scheduled_time": (
                datetime.now(timezone.utc) + timedelta(hours=2)
            ).isoformat(),
        },
    )
    assert reminder.status_code == 201, reminder.text
    return {"contact": contact.json()["id"], "reminder": reminder.json()["id"]}


@pytest.mark.parametrize(
    "path",
    [
        "/patients/maya-demo/emergency-contacts",
        "/patients/maya-demo/reminders",
        "/patients/maya-demo/activity-sessions",
        "/patients/maya-demo/performance",
        "/patients/maya-demo/reports/activity",
        "/patients/maya-demo/alerts",
        "/patients/maya-demo/location-updates",
        "/patients/maya-demo/safety",
    ],
)
def test_unassigned_caregiver_cannot_read_patient_domains(
    client, stranger_headers, path
):
    assert client.get(path, headers=stranger_headers).status_code == 403


def test_unassigned_caregiver_cannot_create_or_change_contacts(
    client, patient_headers, stranger_headers, owned_records
):
    before = client.get(
        "/patients/maya-demo/emergency-contacts", headers=patient_headers
    ).json()
    create = client.post(
        "/patients/maya-demo/emergency-contacts",
        headers=stranger_headers,
        json={
            "name": "Intruder Contact",
            "phone": "+91 90000 99999",
            "relationship": "Unknown",
        },
    )
    update = client.put(
        f"/patients/maya-demo/emergency-contacts/{owned_records['contact']}",
        headers=stranger_headers,
        json={"active": False},
    )
    assert create.status_code == update.status_code == 403
    assert (
        client.get(
            "/patients/maya-demo/emergency-contacts", headers=patient_headers
        ).json()
        == before
    )


def test_unassigned_caregiver_cannot_create_change_or_delete_reminders(
    client, patient_headers, stranger_headers, owned_records
):
    before = client.get("/patients/maya-demo/reminders", headers=patient_headers).json()
    create = client.post(
        "/reminders",
        headers=stranger_headers,
        json={
            "patient_id": "maya-demo",
            "type": "appointment",
            "title": "Unauthorized reminder",
            "scheduled_time": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        },
    )
    update = client.put(
        f"/reminders/{owned_records['reminder']}",
        headers=stranger_headers,
        json={"completed": True},
    )
    delete = client.delete(
        f"/reminders/{owned_records['reminder']}", headers=stranger_headers
    )
    assert create.status_code == update.status_code == delete.status_code == 403
    assert (
        client.get("/patients/maya-demo/reminders", headers=patient_headers).json()
        == before
    )


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("put", "/patients/maya-demo/safety/settings", {"safe_zone_radius_m": 999}),
        (
            "post",
            "/patients/maya-demo/location-updates",
            {
                "latitude": 26.1,
                "longitude": 91.7,
                "accuracy_m": 10,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
        ("post", "/patients/maya-demo/sos-events", {"message": "Unauthorized event"}),
        (
            "post",
            "/patients/maya-demo/safety-alerts/not-found/acknowledge",
            {"note": "Unauthorized"},
        ),
        (
            "post",
            "/patients/maya-demo/sos-events/not-found/acknowledge",
            {"note": "Unauthorized"},
        ),
    ],
)
def test_unassigned_caregiver_cannot_mutate_safety_domain(
    client, stranger_headers, method, path, payload
):
    assert (
        client.request(method, path, headers=stranger_headers, json=payload).status_code
        == 403
    )


@pytest.mark.parametrize(
    "path",
    [
        "/activities/memory-match/start",
        "/activities/memory-match/complete",
    ],
)
def test_caregivers_cannot_submit_patient_activity_sessions(
    client, stranger_headers, path
):
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": "maya-demo",
        "difficulty_level": 2,
        "started_at": now.isoformat(),
        "event_id": f"matrix-{uuid4().hex}",
    }
    if path.endswith("/complete"):
        payload.update(
            {
                "activity_id": "memory-match",
                "completed_at": (now + timedelta(seconds=30)).isoformat(),
                "accuracy": 0.8,
                "response_time": 5,
                "attempts": 1,
                "completion_status": "completed",
            }
        )
    assert client.post(path, headers=stranger_headers, json=payload).status_code == 403
