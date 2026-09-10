from uuid import uuid4

from fastapi.testclient import TestClient

from app import rate_limit
from app.main import app


def test_login_rate_limit_uses_hashed_client_key(monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit, "APP_ENV", "test")
    rate_limit.clear_local_limits()
    with TestClient(app) as client:
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"missing-{uuid4().hex}@neurox.test",
                    "password": "NotAReal!123",
                },
            )
            assert response.status_code == 401
        limited = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"missing-{uuid4().hex}@neurox.test",
                "password": "NotAReal!123",
            },
        )
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0
        assert limited.json()["error"]["code"] == "http_429"
        assert all("testclient" not in key for key in rate_limit._memory_windows)
