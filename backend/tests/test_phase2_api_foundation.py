from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_v1_contract_has_stable_core_operations():
    schema = app.openapi()
    required = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/patients/me",
        "/api/v1/activities",
        "/api/v1/sync/events",
        "/api/v1/patients/me/privacy",
    }
    assert required <= set(schema["paths"])
    operations = [
        operation["operationId"]
        for path in schema["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "delete", "patch"}
    ]
    assert len(operations) == len(set(operations))


def test_v1_auth_and_readiness_are_operational():
    with TestClient(app) as client:
        email = f"v1-{uuid4().hex}@neurox.test"
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Version One",
                "email": email,
                "password": "VersionOne!123",
                "role": "CAREGIVER",
            },
        )
        assert registered.status_code == 201
        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert client.get("/ready").json() == {
            "status": "ready",
            "database": "available",
        }


def test_errors_have_correlation_ids_without_breaking_detail_clients():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"X-Request-ID": "phase2-test"}
        )
        assert response.status_code == 401
        assert response.headers["X-Request-ID"] == "phase2-test"
        assert response.json()["detail"] == "Sign in is required."
        assert response.json()["error"] == {
            "code": "http_401",
            "message": "Sign in is required.",
            "requestId": "phase2-test",
        }
        invalid = client.post(
            "/api/v1/auth/login",
            json={},
            headers={"X-Request-ID": "invalid id with spaces"},
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "validation_error"
        assert invalid.headers["X-Request-ID"] != "invalid id with spaces"


def test_paginated_queries_validate_bounds():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Pagination Patient",
                "email": f"page-{uuid4().hex}@neurox.test",
                "password": "Pagination!123",
                "role": "PATIENT",
            },
        ).json()
        response = client.get(
            f"/api/v1/patients/{registered['user']['id']}/reminders?limit=101&offset=-1",
            headers={"Authorization": f"Bearer {registered['access_token']}"},
        )
        assert response.status_code == 422
