from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.auth import ALGORITHM, JWT_SECRET, decode_access_token


@pytest.mark.parametrize("missing", ["sub", "exp", "type"])
def test_required_token_claims(missing):
    claims = {
        "sub": "patient",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
        "type": "access",
    }
    claims.pop(missing)
    token = jwt.encode(claims, JWT_SECRET, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as error:
        decode_access_token(token)
    assert error.value.status_code == 401


def test_other_signing_algorithms_are_rejected():
    token = jwt.encode(
        {"sub": "patient", "exp": 9999999999, "type": "access"}, "", algorithm="none"
    )
    with pytest.raises(HTTPException) as error:
        decode_access_token(token)
    assert error.value.status_code == 401
