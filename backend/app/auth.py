"""Authentication primitives shared by route handlers."""

# ===================================
#  Imports
# ===================================
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

# ===================================
#  Constants for JWT and password hashing
# ===================================

ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")
APP_ENV = os.getenv("APP_ENV", "development").lower()
if APP_ENV in {"production", "staging"} and (
    JWT_SECRET == "development-only-change-me" or len(JWT_SECRET) < 32
):
    raise RuntimeError("JWT_SECRET must be a unique value of at least 32 characters outside development.")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    )

# Creating new Access Token using Refresh Token upon expiration
def create_refresh_token(user: Any, session_id: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user.id, "sid": session_id, "type": "refresh", "exp": expiry},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )

# Decoding Access Token to get user information
def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or has expired.",
        ) from exc
