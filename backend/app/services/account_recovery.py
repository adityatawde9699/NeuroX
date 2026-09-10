"""One-time email verification and password recovery workflows."""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth import JWT_SECRET, hash_password
from app.database import get_db
from app.models import AccountToken, AuditEvent, RefreshSession, User
from app.schemas import (
    EmailVerificationConfirm,
    PasswordResetConfirm,
    PasswordResetRequest,
    PhoneVerificationConfirm,
    PhoneVerificationRequest,
    Role,
)
from app.services.account_delivery import send_account_link, send_phone_code
from app.services.authentication import authenticated_user

logger = logging.getLogger("neurox.account_delivery")
VERIFY_TTL = timedelta(hours=24)
RESET_TTL = timedelta(hours=1)
PHONE_TTL = timedelta(minutes=10)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _phone_digest(user_id: str, code: str) -> str:
    return hmac.new(
        JWT_SECRET.encode(), f"{user_id}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def request_phone_verification(
    request: PhoneVerificationRequest,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(User.phone_number == request.phone_number, User.id != user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This phone number is already in use."
        )
    now = datetime.now(timezone.utc)
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == "phone_verification",
            AccountToken.consumed_at.is_(None),
        )
        .values(consumed_at=now),
        execution_options={"synchronize_session": False},
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        AccountToken(
            user_id=user.id,
            purpose="phone_verification",
            token_hash=_phone_digest(user.id, code),
            expires_at=now + PHONE_TTL,
            created_at=now,
        )
    )
    user.phone_number = request.phone_number
    user.phone_verified = False
    db.commit()
    try:
        send_phone_code(request.phone_number, code)
    except Exception as exc:
        logger.error(
            "Phone verification delivery failed",
            extra={"event": "phone_delivery_failed"},
        )
        raise HTTPException(
            status_code=503,
            detail="Verification message delivery is temporarily unavailable.",
        ) from exc
    return {"message": "A verification code was sent if delivery succeeded."}


def confirm_phone_verification(
    request: PhoneVerificationConfirm,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(AccountToken)
        .filter(
            AccountToken.user_id == user.id,
            AccountToken.purpose == "phone_verification",
            AccountToken.token_hash == _phone_digest(user.id, request.code),
            AccountToken.consumed_at.is_(None),
        )
        .first()
    )
    if not record or _as_utc(record.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, detail="This verification code is invalid or expired."
        )
    record.consumed_at = datetime.now(timezone.utc)
    user.phone_verified = True
    db.add(
        AuditEvent(
            patient_id=user.id if user.role == Role.PATIENT.value else None,
            actor_id=user.id,
            action="auth.phone_verified",
            target_id=user.id,
            metadata_json={},
        )
    )
    db.commit()
    return {"verified": True}


def _issue(user: User, purpose: str, ttl: timedelta, db: Session) -> str:
    issued_at = datetime.now(timezone.utc)
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.consumed_at.is_(None),
        )
        .values(consumed_at=issued_at),
        execution_options={"synchronize_session": False},
    )
    token = secrets.token_urlsafe(32)
    db.add(
        AccountToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=_digest(token),
            expires_at=issued_at + ttl,
            created_at=issued_at,
        )
    )
    db.commit()
    return token


def request_email_verification(
    user: User = Depends(authenticated_user), db: Session = Depends(get_db)
):
    if user.email_verified:
        return {"message": "This email address is already verified."}
    token = _issue(user, "email_verification", VERIFY_TTL, db)
    try:
        send_account_link(user.email, "email_verification", token)
    except Exception as exc:
        logger.exception("email_verification_delivery_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email delivery is temporarily unavailable.",
        ) from exc
    return {
        "message": "If delivery succeeds, a verification email will arrive shortly."
    }


def request_password_reset(
    request: PasswordResetRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email.strip().lower()).first()
    if user:
        token = _issue(user, "password_reset", RESET_TTL, db)
        try:
            send_account_link(user.email, "password_reset", token)
        except Exception:
            # Keep the public response identical for existing and unknown accounts.
            logger.exception("password_reset_delivery_failed")
    return {
        "message": "If an account exists for that email, a reset link will arrive shortly."
    }


def _valid_token(token: str, purpose: str, db: Session) -> AccountToken:
    record = (
        db.query(AccountToken)
        .filter(
            AccountToken.token_hash == _digest(token),
            AccountToken.purpose == purpose,
            AccountToken.consumed_at.is_(None),
        )
        .first()
    )
    if not record or _as_utc(record.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This link is invalid or expired.")
    return record


def confirm_email_verification(
    request: EmailVerificationConfirm, db: Session = Depends(get_db)
):
    record = _valid_token(request.token, "email_verification", db)
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This link is invalid or expired.")
    record.consumed_at = datetime.now(timezone.utc)
    user.email_verified = True
    db.add(
        AuditEvent(
            patient_id=user.id if user.role == Role.PATIENT.value else None,
            actor_id=user.id,
            action="auth.email_verified",
            target_id=user.id,
            metadata_json={},
        )
    )
    db.commit()
    return {"verified": True}


def confirm_password_reset(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
):
    record = _valid_token(request.token, "password_reset", db)
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This link is invalid or expired.")
    changed_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(request.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.consumed_at = changed_at
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == "password_reset",
            AccountToken.consumed_at.is_(None),
        )
        .values(consumed_at=changed_at),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked.is_(False))
        .values(
            revoked=True,
            revoked_at=changed_at,
            revoke_reason="password_reset",
        ),
        execution_options={"synchronize_session": False},
    )
    db.add(
        AuditEvent(
            patient_id=user.id if user.role == Role.PATIENT.value else None,
            actor_id=user.id,
            action="auth.password_reset",
            target_id=user.id,
            metadata_json={},
        )
    )
    db.commit()
    return {"reset": True}
