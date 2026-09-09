from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import CaregiverPatientAssignment
from app.database import SessionLocal


def register(client, role, name):
    email = f"{role.lower()}-{uuid4().hex}@neurox.test"
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "Phase1Test!123", "role": role},
    )
    assert response.status_code == 201
    return response.json()


def headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_patient_can_control_consent_location_and_caregiver_access():
    with TestClient(app) as client:
        patient = register(client, "PATIENT", "Privacy Patient")
        caregiver = register(client, "CAREGIVER", "Privacy Caregiver")
        with SessionLocal() as db:
            db.add(
                CaregiverPatientAssignment(
                    caregiver_id=caregiver["user"]["id"],
                    patient_id=patient["user"]["id"],
                )
            )
            db.commit()
        patient_headers = headers(patient)
        patient_id = patient["user"]["id"]
        caregiver_id = caregiver["user"]["id"]

        assert (
            client.post(
                f"/patients/{patient_id}/location-updates",
                headers=patient_headers,
                json={
                    "latitude": 26.1,
                    "longitude": 91.7,
                    "accuracy_m": 10,
                    "captured_at": "2026-09-09T00:00:00Z",
                },
            ).status_code
            == 403
        )
        enabled = client.put(
            "/patients/me/privacy/location-sharing",
            headers=patient_headers,
            json={"enabled": True},
        )
        assert enabled.status_code == 200
        assert (
            client.post(
                f"/patients/{patient_id}/location-updates",
                headers=patient_headers,
                json={
                    "latitude": 26.1,
                    "longitude": 91.7,
                    "accuracy_m": 10,
                    "captured_at": "2026-09-09T00:00:00Z",
                },
            ).status_code
            == 201
        )
        assert client.get(
            f"/patients/{patient_id}/location-updates", headers=headers(caregiver)
        ).json()
        assert (
            client.put(
                "/patients/me/privacy/location-sharing",
                headers=patient_headers,
                json={"enabled": False},
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/patients/{patient_id}/location-updates", headers=headers(caregiver)
            ).json()
            == []
        )
        consent = client.put(
            "/patients/me/privacy/consents",
            headers=patient_headers,
            json={
                "purpose": "personalization",
                "granted": False,
                "notice_version": "test-v1",
            },
        )
        assert consent.status_code == 200
        assert (
            client.get("/patients/me/privacy", headers=patient_headers).json()[
                "consents"
            ]["personalization"]["granted"]
            is False
        )
        assert (
            client.get("/patients/me/caregivers", headers=patient_headers).json()[0][
                "id"
            ]
            == caregiver_id
        )
        assert (
            client.delete(
                f"/patients/me/caregivers/{caregiver_id}", headers=patient_headers
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/patients/{patient_id}/safety", headers=headers(caregiver)
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/patients/me/privacy/export", headers=patient_headers
            ).status_code
            == 200
        )
        deletion = client.post(
            "/patients/me/privacy/deletion-request", headers=patient_headers
        )
        assert deletion.status_code == 202
        assert (
            client.post(
                "/patients/me/privacy/deletion-request", headers=patient_headers
            ).json()["requestId"]
            == deletion.json()["requestId"]
        )
