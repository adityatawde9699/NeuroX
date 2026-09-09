from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import authentication

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def sign_in(client):
    credentials = {"email": f"browser-{uuid4().hex}@neurox.test", "password": "BrowserTest!123"}
    assert client.post("/auth/register", json={**credentials, "name": "Browser User"}).status_code == 201
    return client.post("/auth/browser/login", json=credentials, headers=ORIGIN)


def test_browser_cookie_rotation_and_logout(client):
    login = sign_in(client)
    assert login.status_code == 200
    assert "refresh_token" not in login.json()
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/auth/browser" in cookie
    assert login.headers["cache-control"] == "no-store"
    old_token = client.cookies.get("neurox_refresh")
    refreshed = client.post("/auth/browser/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert "refresh_token" not in refreshed.json()
    assert client.cookies.get("neurox_refresh") != old_token
    assert client.post("/auth/refresh", json={"refresh_token": old_token}).status_code == 401
    current_token = client.cookies.get("neurox_refresh")
    assert client.post("/auth/browser/logout", headers=ORIGIN).status_code == 200
    assert client.cookies.get("neurox_refresh") is None
    assert client.post("/auth/refresh", json={"refresh_token": current_token}).status_code == 401


def test_browser_registration_creates_caregiver_cookie_session(client):
    response = client.post(
        "/auth/browser/register",
        headers=ORIGIN,
        json={
            "name": "New Caregiver",
            "email": f"new-caregiver-{uuid4().hex}@neurox.test",
            "password": "BrowserTest!123",
            "role": "CAREGIVER",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "CAREGIVER"
    assert "refresh_token" not in response.json()
    assert "HttpOnly" in response.headers["set-cookie"]


@pytest.mark.parametrize("origin", [None, "https://untrusted.example", "null"])
def test_browser_endpoints_require_trusted_origin(client, origin):
    headers = {"Origin": origin} if origin else {}
    for endpoint in ("login", "register", "google", "refresh", "logout"):
        response = client.post(f"/auth/browser/{endpoint}", headers=headers, json={
            "email": "x@example.com", "password": "Password!123", "credential": "x" * 30,
        })
        assert response.status_code == 403
        assert "set-cookie" not in response.headers


def test_deployed_cookie_is_secure(client, monkeypatch):
    monkeypatch.setattr(authentication, "APP_ENV", "production")
    assert "Secure" in sign_in(client).headers["set-cookie"]


def test_missing_cookie_cannot_refresh(client):
    assert client.post("/auth/browser/refresh", headers=ORIGIN).status_code == 401


def test_non_development_startup_never_seeds_demo_accounts(monkeypatch):
    from app import seed as main
    monkeypatch.setenv("APP_ENV", "production")
    def forbidden(*args, **kwargs):
        raise AssertionError("Production startup must not seed or create tables")
    monkeypatch.setattr(main, "Session", forbidden)
    monkeypatch.setattr(main.Base.metadata, "create_all", forbidden)
    main._seed_database()
