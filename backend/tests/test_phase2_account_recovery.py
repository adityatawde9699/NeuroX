from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import AccountToken, AuditEvent, User
from app.services import account_recovery, authentication


def account(prefix: str) -> dict[str, str]:
    return {
        "name": "Recovery User",
        "email": f"{prefix}-{uuid4().hex}@neurox.test",
        "password": "Recovery!123",
    }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_email_verification_token_is_hashed_one_time_and_enforced(monkeypatch):
    delivered: list[str] = []
    monkeypatch.setattr(authentication, "REQUIRE_EMAIL_VERIFICATION", True)
    monkeypatch.setattr(
        account_recovery,
        "send_account_link",
        lambda _email, purpose, token: delivered.append(f"{purpose}:{token}"),
    )
    with TestClient(app) as client:
        credentials = account("verify")
        registered = client.post("/api/v1/auth/register", json=credentials).json()
        assert (
            client.get(
                "/api/v1/auth/me", headers=auth(registered["access_token"])
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": credentials["email"],
                    "password": credentials["password"],
                },
            ).status_code
            == 403
        )
        requested = client.post(
            "/api/v1/auth/email-verification/request",
            headers=auth(registered["access_token"]),
        )
        assert requested.status_code == 200
        raw_token = delivered.pop().split(":", 1)[1]
        with SessionLocal() as db:
            stored = (
                db.query(AccountToken).filter_by(purpose="email_verification").all()
            )
            record = next(
                item for item in stored if item.user_id == registered["user"]["id"]
            )
            assert record.token_hash != raw_token
            assert len(record.token_hash) == 64

        confirmed = client.post(
            "/api/v1/auth/email-verification/confirm", json={"token": raw_token}
        )
        assert confirmed.json() == {"verified": True}
        assert (
            client.post(
                "/api/v1/auth/email-verification/confirm", json={"token": raw_token}
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": credentials["email"],
                    "password": credentials["password"],
                },
            ).status_code
            == 200
        )


def test_unverified_browser_registration_does_not_set_refresh_cookie(monkeypatch):
    monkeypatch.setattr(authentication, "REQUIRE_EMAIL_VERIFICATION", True)
    with TestClient(app) as client:
        response = client.post(
            "/auth/browser/register",
            headers={"Origin": "http://localhost:5173"},
            json=account("browser-unverified"),
        )
        assert response.status_code == 200
        assert response.json()["user"]["emailVerified"] is False
        assert "set-cookie" not in response.headers
        assert client.cookies.get("neurox_refresh") is None


def test_password_reset_is_non_enumerating_one_time_and_revokes_sessions(monkeypatch):
    delivered: list[str] = []
    monkeypatch.setattr(
        account_recovery,
        "send_account_link",
        lambda _email, purpose, token: delivered.append(f"{purpose}:{token}"),
    )
    with TestClient(app) as client:
        credentials = account("reset")
        registered = client.post("/api/v1/auth/register", json=credentials).json()
        known = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": credentials["email"]},
        )
        unknown = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": f"unknown-{uuid4().hex}@neurox.test"},
        )
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()
        raw_token = delivered.pop().split(":", 1)[1]

        reset = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "RecoveryNew!456"},
        )
        assert reset.json() == {"reset": True}
        assert (
            client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": raw_token, "new_password": "AnotherNew!789"},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": registered["refresh_token"]},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": credentials["email"],
                    "password": credentials["password"],
                },
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": credentials["email"], "password": "RecoveryNew!456"},
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            user = db.query(User).filter_by(email=credentials["email"]).one()
            assert (
                db.query(AuditEvent)
                .filter_by(actor_id=user.id, action="auth.password_reset")
                .count()
                == 1
            )


def test_expired_reset_link_is_rejected(monkeypatch):
    delivered: list[str] = []
    monkeypatch.setattr(
        account_recovery,
        "send_account_link",
        lambda _email, _purpose, token: delivered.append(token),
    )
    with TestClient(app) as client:
        credentials = account("expired-reset")
        client.post("/api/v1/auth/register", json=credentials)
        client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": credentials["email"]},
        )
        raw_token = delivered.pop()
        with SessionLocal() as db:
            user = db.query(User).filter_by(email=credentials["email"]).one()
            record = (
                db.query(AccountToken)
                .filter_by(user_id=user.id, purpose="password_reset")
                .one()
            )
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        assert (
            client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": raw_token, "new_password": "RecoveryNew!456"},
            ).status_code
            == 400
        )


def test_phone_verification_code_is_hashed_expiring_and_one_time(monkeypatch):
    delivered: list[str] = []
    monkeypatch.setattr(
        account_recovery,
        "send_phone_code",
        lambda phone, code: delivered.append(f"{phone}:{code}"),
    )
    with TestClient(app) as client:
        registered = client.post("/api/v1/auth/register", json=account("phone")).json()
        headers = auth(registered["access_token"])
        requested = client.post(
            "/api/v1/auth/phone-verification/request",
            headers=headers,
            json={"phone_number": "+919876543210"},
        )
        assert requested.status_code == 200
        raw_code = delivered.pop().rsplit(":", 1)[1]
        with SessionLocal() as db:
            user = db.get(User, registered["user"]["id"])
            record = (
                db.query(AccountToken)
                .filter_by(user_id=user.id, purpose="phone_verification")
                .one()
            )
            assert record.token_hash != raw_code
            assert user.phone_verified is False

        confirmed = client.post(
            "/api/v1/auth/phone-verification/confirm",
            headers=headers,
            json={"code": raw_code},
        )
        assert confirmed.json() == {"verified": True}
        assert (
            client.post(
                "/api/v1/auth/phone-verification/confirm",
                headers=headers,
                json={"code": raw_code},
            ).status_code
            == 400
        )
