from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import decode_access_token
from app.database import SessionLocal
from app.main import app
from app.models import AuditEvent, User


def credentials(prefix: str) -> dict[str, str]:
    return {
        "name": "Phase Two User",
        "email": f"{prefix}-{uuid4().hex}@neurox.test",
        "password": "PhaseTwo!123",
    }


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_failed_password_attempts_lock_and_then_recover_account():
    with TestClient(app) as client:
        account = credentials("lockout")
        assert client.post("/api/v1/auth/register", json=account).status_code == 201
        for _ in range(4):
            failed = client.post(
                "/api/v1/auth/login",
                json={"email": account["email"], "password": "Incorrect!123"},
            )
            assert failed.status_code == 401
        locked = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": "Incorrect!123"},
        )
        assert locked.status_code == 429
        assert int(locked.headers["Retry-After"]) > 0
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": account["email"], "password": account["password"]},
            ).status_code
            == 429
        )

        with SessionLocal() as db:
            user = db.query(User).filter(User.email == account["email"]).one()
            user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()

        recovered = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": account["password"]},
        )
        assert recovered.status_code == 200
        with SessionLocal() as db:
            user = db.query(User).filter(User.email == account["email"]).one()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None


def test_refresh_reuse_revokes_the_replacement_token_family():
    with TestClient(app) as client:
        account = credentials("reuse")
        original = client.post("/api/v1/auth/register", json=account).json()
        replacement = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original["refresh_token"]},
        )
        assert replacement.status_code == 200

        reused = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original["refresh_token"]},
        )
        assert reused.status_code == 401
        assert "reuse" in reused.json()["detail"].lower()
        assert (
            client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": replacement.json()["refresh_token"]},
            ).status_code
            == 401
        )

        with SessionLocal() as db:
            user = db.query(User).filter(User.email == account["email"]).one()
            event = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.actor_id == user.id,
                    AuditEvent.action == "auth.refresh_reuse_detected",
                )
                .one()
            )
            assert event.metadata_json == {}


def test_account_owner_can_list_and_revoke_sessions_only():
    with TestClient(app) as client:
        owner_account = credentials("session-owner")
        owner = client.post(
            "/api/v1/auth/register",
            json=owner_account,
            headers={"X-Client-Name": "NeuroX Android"},
        ).json()
        second = client.post(
            "/api/v1/auth/login",
            json={
                "email": owner_account["email"],
                "password": owner_account["password"],
            },
            headers={"X-Client-Name": "NeuroX Web"},
        ).json()
        other = client.post(
            "/api/v1/auth/register", json=credentials("session-other")
        ).json()

        listed = client.get(
            "/api/v1/auth/sessions", headers=bearer(owner["access_token"])
        )
        assert listed.status_code == 200
        assert len(listed.json()) == 2
        assert {item["device_name"] for item in listed.json()} == {
            "NeuroX Android",
            "NeuroX Web",
        }
        original_id = decode_access_token(owner["refresh_token"])["sid"]
        other_id = decode_access_token(other["refresh_token"])["sid"]
        assert (
            client.delete(
                f"/api/v1/auth/sessions/{other_id}",
                headers=bearer(owner["access_token"]),
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/auth/sessions/{original_id}",
                headers=bearer(owner["access_token"]),
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": owner["refresh_token"]},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": second["refresh_token"]},
            ).status_code
            == 200
        )


def test_password_change_revokes_every_refresh_session():
    with TestClient(app) as client:
        account = credentials("password-sessions")
        registered = client.post("/api/v1/auth/register", json=account).json()
        extra = client.post(
            "/api/v1/auth/login",
            json={"email": account["email"], "password": account["password"]},
        ).json()
        changed = client.put(
            "/api/v1/auth/me/password",
            headers=bearer(registered["access_token"]),
            json={
                "current_password": account["password"],
                "new_password": "PhaseTwoNew!456",
            },
        )
        assert changed.status_code == 200
        for token in (registered["refresh_token"], extra["refresh_token"]):
            assert (
                client.post(
                    "/api/v1/auth/refresh", json={"refresh_token": token}
                ).status_code
                == 401
            )
