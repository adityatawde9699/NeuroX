import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# DATABASE_URL is set by conftest.py before this module is imported.
# We record the path so the module-level client fixture can clean it up.
_DB_PATH = Path(os.environ["DATABASE_URL"].replace("sqlite:///", ""))

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


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


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Language-config endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_language_config_is_public_and_returns_required_fields(client):
    """GET /language-config must be accessible without authentication and must
    include every field required by the Android LanguageConfig model."""
    resp = client.get("/language-config")
    assert resp.status_code == 200
    configs = resp.json()
    assert isinstance(configs, list)
    assert len(configs) >= 2

    required_fields = {"languageCode", "languageName", "speechSupported", "ttsSupported"}
    for config in configs:
        missing = required_fields - set(config.keys())
        assert not missing, f"Language config for {config.get('languageCode')} missing fields: {missing}"

    # Assamese must be present as the primary patient language for the demo.
    assamese = next((c for c in configs if c["languageCode"] == "as-IN"), None)
    assert assamese is not None, "Assamese (as-IN) language config is missing"
    assert assamese["speechSupported"] is True
    assert assamese["ttsSupported"] is False, "Assamese TTS is not yet available"
    assert assamese["ttsFallbackNote"] is not None, "Assamese config must include a ttsFallbackNote"

    # English must be present and fully supported.
    english = next((c for c in configs if c["languageCode"] == "en-IN"), None)
    assert english is not None, "English (en-IN) language config is missing"
    assert english["speechSupported"] is True
    assert english["ttsSupported"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Cross-patient authorization: report, alerts, location-updates
# ─────────────────────────────────────────────────────────────────────────────


def _stranger_headers(client) -> dict:
    """Register a fresh caregiver with no patient assignment."""
    email = f"stranger-p7-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={"name": "Stranger Caregiver", "email": email, "password": "Testing!2026"},
    )
    assert reg.status_code == 201
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


def test_unrelated_caregiver_cannot_read_activity_report(client):
    assert client.get("/patients/maya-demo/reports/activity", headers=_stranger_headers(client)).status_code == 403


def test_unrelated_caregiver_cannot_read_alerts(client):
    assert client.get("/patients/maya-demo/alerts", headers=_stranger_headers(client)).status_code == 403


def test_unrelated_caregiver_cannot_read_location_updates(client):
    assert client.get("/patients/maya-demo/location-updates", headers=_stranger_headers(client)).status_code == 403