"""Google Identity Services token verification adapter."""
# ===================================
#  Imports
# ===================================
import os
from fastapi import HTTPException, status

# ===================================
#  Authentication using Google Identity Services
# ===================================
def verify_google_credential(credential: str) -> dict[str, str]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )
    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        identity = id_token.verify_oauth2_token(
            credential, requests.Request(), client_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in could not be verified.",
        ) from exc
    if not identity.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A verified Google email is required.",
        )
    return {
        "google_subject": identity["sub"],
        "email": identity["email"],
        "name": identity.get("name", "Caregiver"),
    }
