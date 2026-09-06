import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


TEST_DATABASE = Path("/tmp") / f"neurox-test-{uuid4().hex}.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

    TEST_DATABASE.unlink(missing_ok=True)


def test_health_and_seeded_demo_data(client):
    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    login_response = client.post(
        "/auth/login",
        json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "anita@neurox.demo"


def test_registration_protected_identity_and_refresh_rotation(client):
    email = f"phase1-{uuid4().hex}@example.com"
    credentials = {"name": "Phase One", "email": email, "password": "Testing!2026"}

    register_response = client.post("/auth/register", json=credentials)
    assert register_response.status_code == 201
    tokens = register_response.json()

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

    duplicate_response = client.post("/auth/register", json=credentials)
    assert duplicate_response.status_code == 409

    refresh_response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    rotated_token = refresh_response.json()["refresh_token"]
    assert rotated_token != tokens["refresh_token"]

    reused_response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused_response.status_code == 401


def test_logout_revokes_refresh_session(client):
    login_response = client.post(
        "/auth/login",
        json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    refresh_token = login_response.json()["refresh_token"]
    logout_response = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200
    assert logout_response.json() == {"loggedOut": True}
    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_sync_persists_and_deduplicates_activity_completion(client):
    login_response = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    token = login_response.json()["access_token"]
    event_id = f"sync-{uuid4().hex}"
    event = {
        "event_id": event_id,
        "event_type": "activity_completion",
        "patient_id": "maya-demo",
        "payload": {
            "user_id": "maya-demo",
            "activity_id": "memory-match",
            "started_at": "2026-09-07T10:00:00Z",
            "completed_at": "2026-09-07T10:01:00Z",
            "accuracy": 0.9,
            "response_time": 12,
            "attempts": 1,
            "completion_status": "completed",
            "difficulty_level": 2,
            "offline_created": True,
            "event_id": event_id,
        },
    }
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post("/sync/events", json=[event], headers=headers)
    assert first_response.status_code == 200
    assert first_response.json()["results"][0]["status"] == "accepted"

    duplicate_response = client.post("/sync/events", json=[event], headers=headers)
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["results"][0]["status"] == "duplicate"


def test_sync_rejects_invalid_payload_without_server_error(client):
    login_response = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    token = login_response.json()["access_token"]
    response = client.post(
        "/sync/events",
        headers={"Authorization": f"Bearer {token}"},
        json=[
            {
                "event_id": f"sync-{uuid4().hex}",
                "event_type": "location_update",
                "patient_id": "maya-demo",
                "payload": {"latitude": 999},
            }
        ],
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "rejected"


def test_sync_persists_location_and_sos_events(client):
    login_response = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    location_id = f"sync-{uuid4().hex}"
    sos_id = f"sync-{uuid4().hex}"
    response = client.post(
        "/sync/events",
        headers=headers,
        json=[
            {
                "event_id": location_id,
                "event_type": "location_update",
                "patient_id": "maya-demo",
                "payload": {
                    "latitude": 26.1447,
                    "longitude": 91.7364,
                    "accuracy_m": 18,
                    "connection_state": "offline",
                    "captured_at": "2026-09-07T10:00:00Z",
                },
            },
            {
                "event_id": sos_id,
                "event_type": "sos_event",
                "patient_id": "maya-demo",
                "payload": {"message": "Please check on me."},
            },
        ],
    )
    assert response.status_code == 200
    assert [item["status"] for item in response.json()["results"]] == ["accepted", "accepted"]
    safety_response = client.get("/patients/maya-demo/safety", headers=headers)
    assert safety_response.status_code == 200
    safety = safety_response.json()
    assert safety["location"]["connectionState"] == "offline"
    assert any(item["message"] == "Please check on me." for item in safety["sosEvents"])


def test_sync_rejects_stale_location_as_conflict(client):
    login_response = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    token = login_response.json()["access_token"]
    response = client.post(
        "/sync/events",
        headers={"Authorization": f"Bearer {token}"},
        json=[
            {
                "event_id": f"sync-{uuid4().hex}",
                "event_type": "location_update",
                "patient_id": "maya-demo",
                "payload": {
                    "latitude": 26.1,
                    "longitude": 91.7,
                    "accuracy_m": 20,
                    "connection_state": "offline",
                    "captured_at": "2020-01-01T00:00:00Z",
                },
            }
        ],
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "conflict"


def test_phase7_report_alert_and_location_routes_are_protected(client):
    login = client.post("/auth/login", json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/patients/maya-demo/reports/activity", headers=headers).status_code == 200
    assert client.get("/patients/maya-demo/alerts", headers=headers).status_code == 200
    assert client.get("/patients/maya-demo/location-updates", headers=headers).status_code == 200

    patient_login = client.post("/auth/login", json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"})
    patient_headers = {"Authorization": f"Bearer {patient_login.json()['access_token']}"}
    assert client.get("/patients/maya-demo/reports/activity", headers=patient_headers).status_code == 200


def test_caregiver_profile_update_route(client):
    login = client.post("/auth/login", json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.put("/auth/me", headers=headers, json={"name": "Anita Devi"})
    assert response.status_code == 200
    assert response.json()["name"] == "Anita Devi"


def test_emergency_contact_create_update_and_deactivate(client):
    login = client.post("/auth/login", json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post(
        "/patients/maya-demo/emergency-contacts",
        headers=headers,
        json={"name": "Rita Devi", "phone": "+91 90000 00000", "relationship": "Neighbor", "priority": 3},
    )
    assert created.status_code == 201
    contact_id = created.json()["id"]
    updated = client.put(
        f"/patients/maya-demo/emergency-contacts/{contact_id}",
        headers=headers,
        json={"priority": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["priority"] == 2
    deactivated = client.put(
        f"/patients/maya-demo/emergency-contacts/{contact_id}",
        headers=headers,
        json={"active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False


def test_caregiver_password_change_requires_current_password(client):
    login = client.post("/auth/login", json={"email": "anita@neurox.demo", "password": "NeuroXDemo!2026"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    invalid = client.put("/auth/me/password", headers=headers, json={"current_password": "wrong-pass", "new_password": "NewNeuroX!2026"})
    assert invalid.status_code == 400
    changed = client.put("/auth/me/password", headers=headers, json={"current_password": "NeuroXDemo!2026", "new_password": "NewNeuroX!2026"})
    assert changed.status_code == 200
    assert client.post("/auth/login", json={"email": "anita@neurox.demo", "password": "NewNeuroX!2026"}).status_code == 200