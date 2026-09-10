import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = (
        f"sqlite:///{Path(tempfile.gettempdir()) / f'neurox-phase7-{uuid4().hex}.sqlite3'}"
    )

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def patient_headers(client):
    response = client.post(
        "/auth/login",
        json={"email": "maya@neurox.demo", "password": "NeuroXDemo!2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_human_override_wins_over_adaptive_rule(client, patient_headers):
    set_override = client.put(
        "/patients/maya-demo/personalization/override",
        headers=patient_headers,
        json={"difficulty_level": 1},
    )
    assert set_override.status_code == 200
    event_id = f"phase7-{uuid4().hex}"
    result = client.post("/activities/memory-match/complete", headers=patient_headers, json={
        "user_id": "maya-demo", "activity_id": "memory-match", "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(), "accuracy": 1.0, "response_time": 2.0,
        "attempts": 1, "completion_status": "completed", "difficulty_level": 2, "event_id": event_id,
    })
    assert result.status_code == 200
    assert result.json()["next_difficulty"] == 1
    assert "selected" in result.json()["message"].lower()
    client.put("/patients/maya-demo/personalization/override", headers=patient_headers, json={"difficulty_level": None})


def test_withdrawn_consent_keeps_activity_level(client, patient_headers):
    client.put("/patients/me/privacy/consents", headers=patient_headers, json={
        "purpose": "personalization", "granted": False,
    })
    for _ in range(3):
        now = datetime.now(timezone.utc).isoformat()
        response = client.post("/activities/memory-match/complete", headers=patient_headers, json={
            "user_id": "maya-demo", "activity_id": "memory-match",
            "started_at": now, "completed_at": now, "accuracy": 1,
            "response_time": 2, "attempts": 1, "completion_status": "completed",
            "difficulty_level": 2, "event_id": uuid4().hex,
        })
        assert response.status_code == 200, response.text
        assert response.json()["next_difficulty"] == 2
        assert "off" in response.json()["message"]


def test_report_rejects_reversed_dates(client, patient_headers):
    response = client.get(
        "/patients/maya-demo/reports/activity",
        headers=patient_headers,
        params={"from": "2026-09-10T12:00:00Z", "to": "2026-09-09T12:00:00Z"},
    )
    assert response.status_code == 422


def test_report_declares_truncation(client, patient_headers):
    response = client.get(
        "/patients/maya-demo/reports/activity", headers=patient_headers,
        params={"limit": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["truncated"] is True
    assert data["summary"]["sessions"] == 1
    assert "generatedAt" in data
    assert "offlineCreated" in data["series"][0]
