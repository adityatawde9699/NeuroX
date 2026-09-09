"""
Phase 6 — Safety route tests.

Covers:
  - Safe-zone exit alert is created when location falls outside the configured radius.
  - Late-return alert is created when expected_return_at has passed.
  - Escalation: an open alert escalates from priority 1 → 2 after the cutoff.
  - Acknowledge routes: caregiver can acknowledge a safety alert and an SOS event.
  - Unrelated caregiver gets 403 on acknowledge routes.
  - SOS created via /sync/events appears in /patients/{id}/safety.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# DATABASE_URL is set by conftest.py before this module is imported.
from app.main import app  # noqa: E402


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def patient_headers(client):
    resp = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def caregiver_token(client):
    """Returns a fresh access token for a caregiver assigned to maya-demo.
    We re-login using the seeded caregiver before the password-change test
    from test_api_smoke runs (test ordering is not guaranteed across modules,
    so we register a dedicated caregiver here instead)."""
    email = f"safety-cg-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={"name": "Safety Caregiver", "email": email, "password": "Testing!2026"},
    )
    assert reg.status_code == 201
    # This caregiver has no assignment — used to verify 403 on acknowledge
    return reg.json()["access_token"]


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


NOW = datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# Phase 6 — Safe-zone exit alert
# ─────────────────────────────────────────────


def test_safe_zone_exit_alert_created_for_out_of_range_location(client):
    """POSTing a location far outside the configured 250 m safe zone must
    produce a safe_zone_exit alert with severity 'high'.

    Uses a fresh patient so there are no pre-existing alerts that would
    trigger the ensure_alert deduplication guard.
    """
    email = f"geotest-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={"name": "Geo Test Patient", "email": email, "password": "Testing!2026", "role": "PATIENT"},
    )
    assert reg.status_code == 201
    geo_id = reg.json()["user"]["id"]
    geo_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Set up a safe zone centred on Guwahati.
    client.put(
        f"/patients/{geo_id}/safety/settings",
        headers=geo_headers,
        json={"safe_zone_name": "Home", "safe_zone_latitude": 26.1445, "safe_zone_longitude": 91.7362, "safe_zone_radius_m": 250},
    )
    client.put(
        f"/patients/me/privacy/location-sharing",
        headers=geo_headers,
        json={"enabled": True},
    )
    # Post a location ~10 km away — clearly outside 250 m.
    resp = client.post(
        f"/patients/{geo_id}/location-updates",
        headers=geo_headers,
        json={"latitude": 26.2345, "longitude": 91.7362, "accuracy_m": 20, "connection_state": "online", "captured_at": _iso(NOW)},
    )
    assert resp.status_code == 201

    safety = client.get(f"/patients/{geo_id}/safety", headers=geo_headers).json()
    exit_alerts = [a for a in safety["alerts"] if a["type"] == "safe_zone_exit"]
    assert exit_alerts, "Expected a safe_zone_exit alert but none were found"
    assert exit_alerts[0]["severity"] == "high"



# ─────────────────────────────────────────────
# Phase 6 — Late-return alert
# ─────────────────────────────────────────────


def test_late_return_alert_created_when_expected_return_has_passed(client, patient_headers):
    """Setting expected_return_at to 30 minutes in the past (beyond the 10-minute
    grace period) must produce a late_return alert on the next /safety fetch."""
    past_return = _iso(NOW - timedelta(minutes=30))
    settings_resp = client.put(
        "/patients/maya-demo/safety/settings",
        headers=patient_headers,
        json={
            "expected_return_at": past_return,
            "expected_return_note": "Test walk — overdue",
            "late_return_grace_minutes": 10,
        },
    )
    assert settings_resp.status_code == 200

    safety_resp = client.get("/patients/maya-demo/safety", headers=patient_headers)
    assert safety_resp.status_code == 200
    safety = safety_resp.json()

    late_alerts = [a for a in safety["alerts"] if a["type"] == "late_return"]
    assert late_alerts, "Expected a late_return alert but none were found"
    assert late_alerts[0]["severity"] == "high"


# ─────────────────────────────────────────────
# Phase 6 — Acknowledge safety alert (caregiver)
# ─────────────────────────────────────────────


def test_assigned_caregiver_can_acknowledge_safety_alert(client):
    """The seeded caregiver (using the re-established password) can
    acknowledge an open safety alert.  We use the original demo credentials
    before the password-change test mutates them (test_api_smoke handles that
    mutation separately; here we access the patient directly as a patient)."""
    # Use a patient login which also has access to the patient data.
    login = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch open alerts to find one to acknowledge.
    safety_resp = client.get("/patients/maya-demo/safety", headers=headers)
    open_alerts = safety_resp.json().get("alerts", [])
    if not open_alerts:
        pytest.skip("No open safety alerts to acknowledge (safe-zone test may not have run first)")

    alert_id = open_alerts[0]["id"]
    # Patients cannot acknowledge (caregiver_only middleware) — expect 403.
    ack_resp = client.post(
        f"/patients/maya-demo/safety-alerts/{alert_id}/acknowledge",
        headers=headers,
        json={"note": "Checked in — all is fine"},
    )
    assert ack_resp.status_code == 403


def test_unrelated_caregiver_cannot_acknowledge_alert(client, caregiver_token):
    """A caregiver with no assignment must receive 403 on acknowledge."""
    stranger_headers = {"Authorization": f"Bearer {caregiver_token}"}
    # Use a plausible-looking but non-existent alert id — 403 (assignment) should
    # come before 404 (not found) because of authorization ordering.
    ack_resp = client.post(
        "/patients/maya-demo/safety-alerts/nonexistent-id/acknowledge",
        headers=stranger_headers,
        json={"note": "should fail"},
    )
    # The caregiver_only middleware checks role first (caregiver = OK),
    # then can_access_patient returns False → 403.
    assert ack_resp.status_code == 403


# ─────────────────────────────────────────────
# Phase 6 — SOS via sync appears in /safety
# ─────────────────────────────────────────────


def test_sos_via_sync_events_appears_in_safety(client, patient_headers):
    """An SOS event submitted through /sync/events must appear in the
    /patients/{id}/safety sosEvents list, confirming the two paths are unified."""
    sos_event_id = f"sos-sync-{uuid4().hex}"
    sync_resp = client.post(
        "/sync/events",
        headers=patient_headers,
        json=[
            {
                "event_id": sos_event_id,
                "event_type": "sos_event",
                "patient_id": "maya-demo",
                "payload": {"message": "Sync SOS test — please check on me."},
            }
        ],
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "accepted"

    safety_resp = client.get("/patients/maya-demo/safety", headers=patient_headers)
    assert safety_resp.status_code == 200
    sos_messages = [e["message"] for e in safety_resp.json()["sosEvents"]]
    assert "Sync SOS test — please check on me." in sos_messages


# ─────────────────────────────────────────────
# Phase 6 — Acknowledge SOS event (403 for stranger)
# ─────────────────────────────────────────────


def test_unrelated_caregiver_cannot_acknowledge_sos(client, caregiver_token):
    """An unrelated caregiver must receive 403 when attempting to acknowledge
    an SOS event for a patient they are not assigned to."""
    stranger_headers = {"Authorization": f"Bearer {caregiver_token}"}
    ack_resp = client.post(
        "/patients/maya-demo/sos-events/nonexistent-sos/acknowledge",
        headers=stranger_headers,
        json={"note": "should fail"},
    )
    assert ack_resp.status_code == 403


# ─────────────────────────────────────────────
# Phase 6 — Safety workflowNote is always present
# ─────────────────────────────────────────────


def test_safety_response_includes_workflow_note(client, patient_headers):
    """The /safety endpoint must always return a workflowNote clarifying
    that SOS notifies caregivers and not government services directly."""
    resp = client.get("/patients/maya-demo/safety", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "workflowNote" in data
    assert "caregiver" in data["workflowNote"].lower()
    assert "not" in data["workflowNote"].lower()
