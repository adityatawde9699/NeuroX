"""Native token authentication and browser cookie sessions."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Depends, Header, HTTPException, Request, Response
from sqlalchemy import update
from sqlalchemy.orm import Session
from app.auth import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import APP_ENV, CORS_ORIGINS
from app.database import get_db
from app.models import RefreshSession, User
from app.schemas import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    Role,
    UserProfileUpdate,
    PasswordChangeRequest,
)
from app.services.google_auth import verify_google_credential


def public_user(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def session_for(user: User, db: Session) -> AuthResponse:
    session_id = str(uuid4())
    db.add(
        RefreshSession(
            id=session_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user, session_id),
        user=public_user(user),
    )


def current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in is required.")
    payload = decode_access_token(authorization.removeprefix("Bearer "))
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="An access token is required.")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409, detail="An account already exists for this email."
        )
    user = User(
        name=request.name.strip(),
        email=email,
        role=request.role.value,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return session_for(user, db)


# User Login
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.strip().lower()).first()
    if (
        not user
        or not user.password_hash
        or not verify_password(request.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return session_for(user, db)


# Google Login
def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    identity = verify_google_credential(request.credential)
    user = db.query(User).filter(User.email == identity["email"]).first()
    if not user:
        user = User(
            name=identity["name"],
            email=identity["email"],
            role=Role.CAREGIVER.value,
            google_subject=identity["google_subject"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.google_subject not in {None, identity["google_subject"]}:
        raise HTTPException(
            status_code=409, detail="This email is linked to another Google account."
        )
    elif not user.google_subject:
        user.google_subject = identity["google_subject"]
        db.commit()
    return session_for(user, db)


# User Session Refresh
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="A refresh token is required.")
    token_session = db.get(RefreshSession, payload.get("sid"))
    if (
        not token_session
        or token_session.revoked
        or token_session.expires_at.replace(tzinfo=timezone.utc)
        < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=401, detail="Your session has expired. Please sign in again."
        )
    user = db.get(User, token_session.user_id)
    if not user or payload.get("sub") != token_session.user_id:
        raise HTTPException(status_code=401, detail="Account not found.")
    # Only one concurrent request may consume this refresh session. Issuing the
    # replacement and revoking the previous session commit together below.
    claimed = db.execute(
        update(RefreshSession)
        .where(RefreshSession.id == token_session.id, RefreshSession.revoked.is_(False))
        .values(revoked=True),
        execution_options={"synchronize_session": False},
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=401, detail="This refresh session has already been used."
        )
    return session_for(user, db)


def logout(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="A refresh token is required.")
    token_session = db.get(RefreshSession, payload.get("sid"))
    if token_session:
        token_session.revoked = True
        db.commit()
    return {"loggedOut": True}


# User Profile
def me(user: User = Depends(current_user)):
    return public_user(user)


def update_current_user(
    request: UserProfileUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    user.name = request.name.strip()
    db.commit()
    db.refresh(user)
    return public_user(user)


def update_current_password(
    request: PasswordChangeRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not user.password_hash or not verify_password(
        request.current_password, user.password_hash
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")
    user.password_hash = hash_password(request.new_password)
    db.commit()
    return {"updated": True}


COOKIE_NAME = "neurox_refresh"
COOKIE_PATH = "/auth/browser"


def browser_origin(request: Request) -> None:
    # Check even login: CORS alone does not prevent login/logout CSRF.
    if request.headers.get("origin") not in CORS_ORIGINS:
        raise HTTPException(
            status_code=403, detail="This browser origin is not allowed."
        )


def browser_session(data: AuthResponse, response: Response) -> dict:
    response.set_cookie(
        COOKIE_NAME,
        data.refresh_token,
        httponly=True,
        secure=APP_ENV != "development",
        samesite="strict",
        path=COOKIE_PATH,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.headers["Cache-Control"] = "no-store"
    return {
        "access_token": data.access_token,
        "token_type": data.token_type,
        "user": data.user,
    }


def browser_login(
    body: LoginRequest, response: Response, db: Session = Depends(get_db)
):
    return browser_session(login(body, db), response)


def browser_google(
    body: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)
):
    return browser_session(google_login(body, db), response)


def browser_refresh(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return browser_session(refresh(RefreshRequest(refresh_token=token), db), response)


def browser_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            logout(RefreshRequest(refresh_token=token), db)
        except HTTPException as error:
            if error.status_code != 401:
                raise
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=APP_ENV != "development",
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"loggedOut": True}
