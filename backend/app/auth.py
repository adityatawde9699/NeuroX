"""Authentication primitives shared by route handlers."""

# ===================================
#  Imports
# ===================================
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import HTTPException, status
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from app.config import APP_ENV
from app.secrets import setting

# ===================================
#  Constants for JWT and password hashing
# ===================================

ALGORITHM = "HS256"
JWT_SECRET = setting("JWT_SECRET", "development-only-change-me")
JWT_KEY_ID = os.getenv("JWT_KEY_ID", "current")
JWT_PREVIOUS_SECRETS = [
    value.strip()
    for value in (setting("JWT_PREVIOUS_SECRETS", "") or "").split(",")
    if value.strip()
]
if APP_ENV in {"production", "staging"} and (
    JWT_SECRET in {"development-only-change-me", "replace-with-a-long-random-secret"}
    or len(JWT_SECRET) < 32
):
    raise RuntimeError(
        "JWT_SECRET must be a unique value of at least 32 characters outside development."
    )
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
if APP_ENV in {"production", "staging"} and BCRYPT_ROUNDS < 12:
    raise RuntimeError("BCRYPT_ROUNDS must be at least 12 outside development.")
password_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS
)


# Hashing Password
def hash_password(password: str) -> str:
    return password_context.hash(password)


# Verifying Password
def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


#  Creating Access Token to be used for authentication
def create_access_token(user: Any) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "type": "access",
            "exp": expiry,
        },
        JWT_SECRET,
        algorithm=ALGORITHM,
        headers={"kid": JWT_KEY_ID},
    )


# Creating new Access Token using Refresh Token upon expiration
def create_refresh_token(user: Any, session_id: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user.id, "sid": session_id, "type": "refresh", "exp": expiry},
        JWT_SECRET,
        algorithm=ALGORITHM,
        headers={"kid": JWT_KEY_ID},
    )


# Decoding Access Token to get user information
def decode_access_token(token: str) -> dict[str, Any]:
    last_error: InvalidTokenError | None = None
    for secret in [JWT_SECRET, *JWT_PREVIOUS_SECRETS]:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "exp", "type"]},
            )
        except InvalidTokenError as exc:
            last_error = exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Your session is invalid or has expired.",
    ) from last_error
