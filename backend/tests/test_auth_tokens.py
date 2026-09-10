"""
Phase 8 - Authentication tests.

Covers:
  - Login returns tokens and user payload.
  - Wrong password returns 401.
  - Valid JWT reaches a protected endpoint (/auth/me).
  - Invalid token is rejected with 401.
  - Refresh endpoint issues a new access token.
  - Logout revokes the refresh token so subsequent refresh fails.
  - An unrelated caregiver cannot access another patient (403/404).

NOTE: All fixtures use freshly registered test users so this module
      is independent of demo-data state set by other test modules.
"""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if "DATABASE_URL" not in os.environ:
    _tmp = Path(tempfile.gettempdir())
    os.environ["DATABASE_URL"] = (
        f"sqlite:///{_tmp / f'neurox-auth-{uuid4().hex}.sqlite3'}"
    )

from app.main import app  # noqa: E402

_TEST_EMAIL = f"caregiver-auth-{uuid4().hex[:8]}@neurox.test"
_TEST_PASSWORD = "AuthTest!9876"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        # Register a fresh caregiver for this module.
        test_client.post(
            "/auth/register",
            json={
                "name": "Auth Tester",
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
            },
        )
        yield test_client


@pytest.fixture(scope="module")
def caregiver_tokens(client):
    """Log in as the module-scoped test caregiver and return tokens."""
    resp = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# -------------------------------------------------------
# Login
# -------------------------------------------------------


def test_login_returns_tokens_and_user(client, caregiver_tokens):
    data = caregiver_tokens
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == _TEST_EMAIL


def test_login_wrong_password_returns_401(client):
    resp = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = client.post(
        "/auth/login",
        json={"email": "nobody@neurox.test", "password": "doesnotmatter"},
    )
    assert resp.status_code == 401


@pytest.mark.parametrize("role", ["ADMIN", "HEALTHCARE_WORKER", "admin", "UNKNOWN"])
def test_public_registration_rejects_privileged_roles(client, role):
    email = f"forbidden-{uuid4().hex}@neurox.test"
    response = client.post(
        "/auth/register",
        json={
            "name": "Untrusted Registration",
            "email": email,
            "password": _TEST_PASSWORD,
            "role": role,
        },
    )
    assert response.status_code == 422
    assert (
        client.post(
            "/auth/login",
            json={
                "email": email,
                "password": _TEST_PASSWORD,
            },
        ).status_code
        == 401
    )


@pytest.mark.parametrize("role", ["PATIENT", "CAREGIVER"])
def test_public_registration_accepts_supported_roles(client, role):
    response = client.post(
        "/auth/register",
        json={
            "name": "Supported Registration",
            "email": f"allowed-{uuid4().hex}@neurox.test",
            "password": _TEST_PASSWORD,
            "role": role,
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    assert (
        client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        ).json()["role"]
        == role
    )


# -------------------------------------------------------
# Protected endpoints
# -------------------------------------------------------


def test_auth_me_with_valid_token(client, caregiver_tokens):
    resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {caregiver_tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == _TEST_EMAIL


def test_auth_me_with_no_token_returns_403(client):
    resp = client.get("/auth/me")
    assert resp.status_code in (401, 403)


def test_auth_me_with_garbage_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage-token"})
    assert resp.status_code == 401


# -------------------------------------------------------
# Refresh
# -------------------------------------------------------


def test_refresh_issues_new_access_token(client, caregiver_tokens):
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": caregiver_tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    new_data = resp.json()
    # A new access token must be present in the response.
    assert "access_token" in new_data
    assert new_data["token_type"] == "bearer"


def test_refresh_with_garbage_token_returns_401(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401


# -------------------------------------------------------
# Logout + revocation
# -------------------------------------------------------


def test_logout_then_refresh_fails(client):
    """A refresh token used for logout must then be rejected."""
    uid = uuid4().hex[:8]
    email = f"logout-test-{uid}@neurox.test"
    reg = client.post(
        "/auth/register",
        json={
            "name": f"Logout Tester {uid}",
            "email": email,
            "password": "Logout!9876",
        },
    )
    assert reg.status_code == 201, reg.text
    tokens = reg.json()

    # Logout
    logout_resp = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 200

    # Now refresh should fail.
    refresh_resp = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code in (401, 403)


# -------------------------------------------------------
# Caregiver ownership
# -------------------------------------------------------


def test_unrelated_caregiver_cannot_read_patient(client):
    """A caregiver not assigned to maya-demo must get 403 or 404."""
    uid = uuid4().hex[:8]
    reg = client.post(
        "/auth/register",
        json={
            "name": f"Stranger {uid}",
            "email": f"stranger-{uid}@neurox.test",
            "password": "StrangerPass!123",
        },
    )
    # /auth/register returns 201 Created.
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/patients/maya-demo", headers=headers)
    # Backend returns 403 (forbidden) or 404 (not found) for non-assigned caregivers.
    assert resp.status_code in (403, 404)
