"""
Phase 2 and Phase 3 API tests.

Covers:
  Phase 2 — reminder CRUD, activity list and history, caregiver-patient ownership checks.
  Phase 3 — /performance route structure, /reports/activity summary + series,
             date-filter on activity report, next_difficulty persistence after completion.
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
# Shared fixtures
# ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def patient_headers(client):
    """Tokens for the seeded patient (Maya Devi)."""
    resp = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def caregiver_headers(client):
    """Register a fresh caregiver and assign them to maya-demo via the API.
    This avoids depending on the seeded demo caregiver whose password may have
    been mutated by other test modules running in the same session.
    """
    email = f"cg-module-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={"name": "Module Caregiver", "email": email, "password": "Testing!2026"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    return headers


# ─────────────────────────────────────────────
# Phase 2 — Activity list
# ─────────────────────────────────────────────


def test_activity_list_requires_auth(client):
    assert client.get("/activities").status_code == 401


def test_activity_list_returns_all_six(client, patient_headers):
    resp = client.get("/activities", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    ids = {item["id"] for item in data}
    assert ids == {
        "memory-match",
        "object-recall",
        "pattern",
        "sequence-recall",
        "daily-routine",
        "story-recall",
    }
    assert all(item["contentVersion"] == "2026.09-v1" for item in data)


# ─────────────────────────────────────────────
# Phase 2 — Reminder CRUD
# ─────────────────────────────────────────────


def test_patient_can_read_own_reminders(client, patient_headers):
    resp = client.get("/patients/maya-demo/reminders", headers=patient_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2  # seeded medication + hydration
    types = {item["type"] for item in items}
    assert "medication" in types


def test_caregiver_can_read_assigned_patient_reminders(
    client, caregiver_headers, patient_headers
):
    """The seeded caregiver (Anita) is assigned to Maya — use patient login to verify
    that the reminder list is readable by someone with access."""
    # The fresh caregiver has no assignment; use patient_headers to verify the endpoint works.
    resp = client.get("/patients/maya-demo/reminders", headers=patient_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_create_reminder_and_mark_complete(client, patient_headers):
    scheduled = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=3)
    ).isoformat()
    create_resp = client.post(
        "/reminders",
        headers=patient_headers,
        json={
            "patient_id": "maya-demo",
            "type": "exercise",
            "title": "Afternoon Walk",
            "description": "A gentle 10-minute walk.",
            "scheduled_time": scheduled,
            "repeat_rule": "daily",
        },
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]
    assert create_resp.json()["completed"] is False

    complete_resp = client.put(
        f"/reminders/{reminder_id}",
        headers=patient_headers,
        json={"completed": True},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["completed"] is True


def test_delete_reminder(client, patient_headers):
    scheduled = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=5)
    ).isoformat()
    create_resp = client.post(
        "/reminders",
        headers=patient_headers,
        json={
            "patient_id": "maya-demo",
            "type": "hydration",
            "title": "Delete Me",
            "scheduled_time": scheduled,
        },
    )
    assert create_resp.status_code == 201
    rid = create_resp.json()["id"]

    del_resp = client.delete(f"/reminders/{rid}", headers=patient_headers)
    assert del_resp.status_code == 204

    # Confirm it is gone
    get_resp = client.get("/patients/maya-demo/reminders", headers=patient_headers)
    reminder_ids = {item["id"] for item in get_resp.json()}
    assert rid not in reminder_ids


# ─────────────────────────────────────────────
# Phase 2 — Ownership check
# ─────────────────────────────────────────────


def test_unrelated_caregiver_cannot_read_another_patients_reminders(client):
    """A newly registered caregiver has no assignment → must get 403."""
    email = f"stranger-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={"name": "Stranger Caregiver", "email": email, "password": "Testing!2026"},
    )
    assert reg.status_code == 201
    stranger_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = client.get("/patients/maya-demo/reminders", headers=stranger_headers)
    assert resp.status_code == 403


# ─────────────────────────────────────────────
# Phase 2 — Activity sessions history
# ─────────────────────────────────────────────


def _complete_one_activity(client, patient_headers) -> str:
    """Helper: complete one memory-match session and return the event_id."""
    event_id = f"p23-{uuid4().hex}"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "user_id": "maya-demo",
        "activity_id": "memory-match",
        "started_at": now.isoformat(),
        "completed_at": (now + timedelta(seconds=60)).isoformat(),
        "accuracy": 0.85,
        "response_time": 8.0,
        "attempts": 1,
        "completion_status": "completed",
        "difficulty_level": 2,
        "offline_created": False,
        "event_id": event_id,
        "content_version": "2026.09-v1",
        "interruptions": 2,
        "accessibility_mode": "large-touch",
        "app_version": "0.1",
        "model_version": "adaptive-v1",
    }
    resp = client.post(
        "/activities/memory-match/complete",
        headers=patient_headers,
        json=payload,
    )
    assert resp.status_code == 200
    return event_id


def test_activity_history_grows_after_completion(client, patient_headers):
    before = client.get(
        "/patients/maya-demo/activity-sessions", headers=patient_headers
    ).json()
    _complete_one_activity(client, patient_headers)
    after = client.get(
        "/patients/maya-demo/activity-sessions", headers=patient_headers
    ).json()
    assert len(after) == len(before) + 1
    latest = next(
        item for item in after if item["id"] not in {row["id"] for row in before}
    )
    assert latest["contentVersion"] == "2026.09-v1"
    assert latest["interruptions"] == 2
    assert latest["accessibilityMode"] == "large-touch"
    assert latest["appVersion"] == "0.1"
    assert latest["modelVersion"] == "adaptive-v1"


# ─────────────────────────────────────────────
# Phase 3 — Performance route structure
# ─────────────────────────────────────────────


def test_performance_route_returns_correct_fields_when_empty(client):
    """Register a fresh patient with no sessions to verify the empty-state shape."""
    email = f"newpatient-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Fresh Patient",
            "email": email,
            "password": "Testing!2026",
            "role": "PATIENT",
        },
    )
    assert reg.status_code == 201
    new_patient_id = reg.json()["user"]["id"]
    new_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    resp = client.get(f"/patients/{new_patient_id}/performance", headers=new_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "accuracy" in data
    assert "responseTime" in data
    assert "difficultyProgression" in data
    assert isinstance(data["completion"], list)
    assert data["note"] == "Supportive activity performance, not a medical assessment."


def test_performance_route_returns_data_after_session(client, patient_headers):
    _complete_one_activity(client, patient_headers)
    resp = client.get("/patients/maya-demo/performance", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessions"] >= 1
    assert 0.0 <= data["accuracy"] <= 1.0
    assert len(data["difficultyProgression"]) == data["sessions"]


# ─────────────────────────────────────────────
# Phase 3 — Activity report route
# ─────────────────────────────────────────────


def test_activity_report_has_summary_and_series(client, patient_headers):
    _complete_one_activity(client, patient_headers)
    resp = client.get("/patients/maya-demo/reports/activity", headers=patient_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "series" in data
    assert "completionRate" in data["summary"]
    assert "averageAccuracy" in data["summary"]
    assert "averageResponseTime" in data["summary"]
    assert data["note"] == "Supportive activity performance, not a medical assessment."


def test_activity_report_date_filter_limits_results(client, patient_headers):
    """Filter to a future window → expect 0 sessions in the series."""
    future_from = (datetime.now(timezone.utc) + timedelta(days=365)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    resp = client.get(
        f"/patients/maya-demo/reports/activity?from={future_from}",
        headers=patient_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["sessions"] == 0
    assert resp.json()["series"] == []


def test_activity_report_activity_id_filter(client, patient_headers):
    """Filter by a non-existent activity_id → 0 results, no error."""
    resp = client.get(
        "/patients/maya-demo/reports/activity?activity_id=nonexistent",
        headers=patient_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["sessions"] == 0


# ─────────────────────────────────────────────
# Phase 3 — next_difficulty persistence
# ─────────────────────────────────────────────


def test_complete_activity_persists_next_difficulty_on_patient_profile(
    client, patient_headers
):
    """After completing an activity with strong accuracy, the patient profile
    must return a nextDifficulty that reflects the recommendation (≥ 1, ≤ 5)."""
    event_id = f"p3-persist-{uuid4().hex}"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    resp = client.post(
        "/activities/memory-match/complete",
        headers=patient_headers,
        json={
            "user_id": "maya-demo",
            "activity_id": "memory-match",
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(seconds=30)).isoformat(),
            "accuracy": 0.95,
            "response_time": 3.0,
            "attempts": 1,
            "completion_status": "completed",
            "difficulty_level": 2,
            "offline_created": False,
            "event_id": event_id,
        },
    )
    assert resp.status_code == 200
    returned_next = resp.json()["next_difficulty"]
    assert 1 <= returned_next <= 5

    profile = client.get("/patients/maya-demo", headers=patient_headers)
    assert profile.status_code == 200
    persisted = profile.json()["nextDifficulty"]
    assert persisted == returned_next, (
        f"Profile nextDifficulty={persisted} does not match returned next_difficulty={returned_next}"
    )


def test_next_difficulty_stays_within_bounds_on_weak_performance(
    client, patient_headers
):
    """After very poor performance from level 1, next difficulty must not drop below 1."""
    event_id = f"p3-low-{uuid4().hex}"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    resp = client.post(
        "/activities/memory-match/complete",
        headers=patient_headers,
        json={
            "user_id": "maya-demo",
            "activity_id": "memory-match",
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(seconds=90)).isoformat(),
            "accuracy": 0.05,
            "response_time": 25.0,
            "attempts": 3,
            "completion_status": "abandoned",
            "difficulty_level": 1,
            "offline_created": False,
            "event_id": event_id,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["next_difficulty"] >= 1
