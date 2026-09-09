"""Fail closed on unknown environments and unsafe deployed origins."""
import os
from urllib.parse import urlsplit

APP_ENV = os.getenv("APP_ENV", "development").lower()
if APP_ENV not in {"development", "test", "staging", "production"}:
    raise RuntimeError("APP_ENV must be development, test, staging, or production.")

CORS_ORIGINS = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
if APP_ENV in {"staging", "production"}:
    if not os.getenv("CORS_ORIGINS") or not CORS_ORIGINS:
        raise RuntimeError("Explicit HTTPS CORS_ORIGINS are required outside development.")
    for origin in CORS_ORIGINS:
        parsed = urlsplit(origin)
        if (parsed.scheme != "https" or not parsed.hostname or "*" in origin or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment):
            raise RuntimeError("CORS_ORIGINS must contain exact HTTPS origins without paths or credentials.")
