# ===================================
#  Imports
# ===================================
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
import os
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.ai.personalization.adaptive_difficulty import (
    PerformanceInput,
    recommend_from_history,
)
from app.auth import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.database import Base, engine, get_db
from app.models import (
    ActivitySession,
    CaregiverPatientAssignment,
    EmergencyContact,
    LocationUpdate,
    Patient,
    RefreshSession,
    Reminder,
    SafetyAlert,
    SafetySettings,
    SOSEvent,
    SyncEvent,
    User,
)
from app.schemas import (
    ActivityCompletion,
    ActivityStart,
    AuthResponse,
    EmergencyContactCreate,
    EmergencyContactUpdate,
    GoogleLoginRequest,
    LoginRequest,
    LocationUpdateCreate,
    RefreshRequest,
    RegisterRequest,
    ReminderCreate,
    ReminderUpdate,
    Role,
    SafetyAcknowledgement,
    SafetySettingsUpdate,
    SOSEventCreate,
    SyncEventRequest,
    UserProfileUpdate,
    PasswordChangeRequest,
)
from app.services.google_auth import verify_google_credential

# ===================================
#  Application lifespan & seed data
# ===================================

def _seed_database() -> None:
    """Idempotent seed for demo data; runs once at startup."""
    if os.getenv("APP_ENV", "development").lower() == "development":
        Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        if not db.query(User).filter(User.email == "anita@neurox.demo").first():
            db.add(
                User(
                    id="caregiver-anita",
                    name="Anita Devi",
                    email="anita@neurox.demo",
                    role=Role.CAREGIVER.value,
                    password_hash=hash_password("NeuroXDemo!2026"),
                )
            )
            db.commit()
        if not db.query(User).filter(User.email == "maya@neurox.demo").first():
            db.add(
                User(
                    id="maya-demo",
                    name="Maya Devi",
                    email="maya@neurox.demo",
                    role=Role.PATIENT.value,
                    password_hash=hash_password("NeuroXDemo!2026"),
                )
            )
            db.commit()
        if not db.get(Patient, "maya-demo"):
            db.add(Patient(user_id="maya-demo", age=72, preferred_language="Assamese"))
        if (
            not db.query(CaregiverPatientAssignment)
            .filter_by(caregiver_id="caregiver-anita", patient_id="maya-demo")
            .first()
        ):
            db.add(
                CaregiverPatientAssignment(
                    caregiver_id="caregiver-anita", patient_id="maya-demo"
                )
            )
        db.commit()
        if not db.query(Reminder).filter(Reminder.patient_id == "maya-demo").first():
            today = datetime.now(timezone.utc).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
            db.add_all(
                [
                    Reminder(
                        patient_id="maya-demo",
                        type="medication",
                        title="Medication",
                        description="Take morning medicine",
                        scheduled_time=today,
                        repeat_rule="daily",
                        completed=True,
                    ),
                    Reminder(
                        patient_id="maya-demo",
                        type="hydration",
                        title="Hydration",
                        description="Have a glass of water",
                        scheduled_time=today + timedelta(hours=1, minutes=30),
                        repeat_rule="daily",
                    ),
                ]
            )
            db.commit()
        if not db.query(EmergencyContact).filter_by(patient_id="maya-demo").first():
            db.add_all(
                [
                    EmergencyContact(
                        patient_id="maya-demo",
                        name="Anita Devi",
                        phone="+91 98765 43210",
                        relationship="Primary caregiver",
                        priority=1,
                    ),
                    EmergencyContact(
                        patient_id="maya-demo",
                        name="Rohan Devi",
                        phone="+91 98765 43211",
                        relationship="Secondary caregiver",
                        priority=2,
                    ),
                ]
            )
        if not db.get(SafetySettings, "maya-demo"):
            db.add(
                SafetySettings(
                    patient_id="maya-demo",
                    safe_zone_name="Home safe zone",
                    safe_zone_latitude=26.1445,
                    safe_zone_longitude=91.7362,
                    safe_zone_radius_m=250,
                    expected_return_at=datetime.now(timezone.utc) + timedelta(hours=2),
                    expected_return_note="Evening walk",
                )
            )
        if not db.query(LocationUpdate).filter_by(patient_id="maya-demo").first():
            db.add(
                LocationUpdate(
                    patient_id="maya-demo",
                    latitude=26.1447,
                    longitude=91.7364,
                    accuracy_m=18,
                    connection_state="online",
                    captured_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                )
            )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _seed_database()
    yield


# ===================================
#  API Application
# ===================================

app = FastAPI(
    title="NeuroX API",
    version="0.3.0",
    description="Supportive engagement APIs — not clinical diagnosis.",
    lifespan=lifespan,
)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACTIVITIES = [
    {
        "id": "memory-match",
        "title": "Memory Match",
        "description": "Match two familiar objects.",
        "difficulty": 2,
    },
    {
        "id": "object-recall",
        "title": "Remember the Objects",
        "description": "Look, listen, then remember.",
        "difficulty": 2,
    },
    {
        "id": "pattern",
        "title": "Pattern Completion",
        "description": "Choose what comes next.",
        "difficulty": 2,
    },
]



# ===================================
#  Getter
# ===================================
#  Public User Data
def public_user(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


# Public Reminder
def public_reminder(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "patientId": reminder.patient_id,
        "type": reminder.type,
        "title": reminder.title,
        "description": reminder.description,
        "scheduledTime": reminder.scheduled_time,
        "repeatRule": reminder.repeat_rule,
        "enabled": reminder.enabled,
        "completed": reminder.completed,
    }


# Patient Data
def public_patient(patient: Patient, user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": patient.age,
        "preferredLanguage": patient.preferred_language,
        "nextDifficulty": patient.next_difficulty,
    }


# Patient Emergency Contact Data
def public_contact(contact: EmergencyContact) -> dict:
    return {
        "id": contact.id,
        "patientId": contact.patient_id,
        "name": contact.name,
        "phone": contact.phone,
        "relationship": contact.relationship,
        "priority": contact.priority,
        "active": contact.active,
    }

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def minutes_ago(value: datetime, now_value: datetime | None = None) -> int:
    now_value = now_value or datetime.now(timezone.utc)
    return max(0, round((now_value - as_utc(value)).total_seconds() / 60))

def human_freshness(value: datetime) -> str:
    minutes = minutes_ago(value)
    if minutes < 1:
        return "just now"
    if minutes == 1:
        return "1 minute ago"
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"

def distance_meters(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    earth_radius_m = 6371000
    d_lat = radians(lat_b - lat_a)
    d_lng = radians(lng_b - lng_a)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lng / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(a))

def active_contacts(patient_id: str, db: Session) -> list[EmergencyContact]:
    return (
        db.query(EmergencyContact)
        .filter_by(patient_id=patient_id, active=True)
        .order_by(EmergencyContact.priority)
        .all()
    )

def contact_for_priority(patient_id: str, priority: int, db: Session) -> dict | None:
    contacts = active_contacts(patient_id, db)
    if not contacts:
        return None
    chosen = next((contact for contact in contacts if contact.priority >= priority), contacts[-1])
    return public_contact(chosen)

def public_safety_settings(settings: SafetySettings | None) -> dict:
    if not settings:
        return {
            "safeZoneName": "Home safe zone",
            "safeZoneLatitude": None,
            "safeZoneLongitude": None,
            "safeZoneRadiusM": 250,
            "expectedReturnAt": None,
            "expectedReturnNote": None,
            "lateReturnGraceMinutes": 10,
        }
    return {
        "safeZoneName": settings.safe_zone_name,
        "safeZoneLatitude": settings.safe_zone_latitude,
        "safeZoneLongitude": settings.safe_zone_longitude,
        "safeZoneRadiusM": settings.safe_zone_radius_m,
        "expectedReturnAt": settings.expected_return_at,
        "expectedReturnNote": settings.expected_return_note,
        "lateReturnGraceMinutes": settings.late_return_grace_minutes,
        "updatedAt": settings.updated_at,
    }

def public_location(location: LocationUpdate | None) -> dict | None:
    if not location:
        return None
    age_minutes = minutes_ago(location.captured_at)
    is_online = location.connection_state.lower() == "online" and age_minutes <= 5
    return {
        "id": location.id,
        "patientId": location.patient_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracyM": location.accuracy_m,
        "connectionState": "online" if is_online else "offline",
        "capturedAt": location.captured_at,
        "receivedAt": location.received_at,
        "freshness": human_freshness(location.captured_at),
        "label": "Current location" if is_online else "Last known location",
    }

def public_alert(alert: SafetyAlert, db: Session) -> dict:
    return {
        "id": alert.id,
        "patientId": alert.patient_id,
        "type": alert.type,
        "severity": alert.severity,
        "status": alert.status,
        "message": alert.message,
        "createdAt": alert.created_at,
        "acknowledgedAt": alert.acknowledged_at,
        "acknowledgedBy": alert.acknowledged_by,
        "escalatedToPriority": alert.escalated_to_priority,
        "escalatedContact": contact_for_priority(alert.patient_id, alert.escalated_to_priority, db),
    }

def public_sos(event: SOSEvent, db: Session) -> dict:
    return {
        "id": event.id,
        "patientId": event.patient_id,
        "message": event.message,
        "status": event.status,
        "createdAt": event.created_at,
        "acknowledgedAt": event.acknowledged_at,
        "acknowledgedBy": event.acknowledged_by,
        "escalatedToPriority": event.escalated_to_priority,
        "escalatedContact": contact_for_priority(event.patient_id, event.escalated_to_priority, db),
        "workflowNote": "NeuroX SOS notifies configured caregivers. It does not contact government or emergency services directly.",
    }

def latest_location(patient_id: str, db: Session) -> LocationUpdate | None:
    return (
        db.query(LocationUpdate)
        .filter_by(patient_id=patient_id)
        .order_by(LocationUpdate.captured_at.desc())
        .first()
    )

def open_alert_exists(patient_id: str, alert_type: str, db: Session) -> bool:
    return (
        db.query(SafetyAlert)
        .filter_by(patient_id=patient_id, type=alert_type, status="open")
        .first()
        is not None
    )

def ensure_alert(
    patient_id: str,
    alert_type: str,
    severity: str,
    message: str,
    db: Session,
    location_update_id: str | None = None,
) -> SafetyAlert | None:
    if open_alert_exists(patient_id, alert_type, db):
        return None
    alert = SafetyAlert(
        patient_id=patient_id,
        type=alert_type,
        severity=severity,
        message=message,
        location_update_id=location_update_id,
    )
    db.add(alert)
    return alert

def evaluate_safety(patient_id: str, db: Session) -> None:
    settings = db.get(SafetySettings, patient_id)
    location = latest_location(patient_id, db)
    now_value = datetime.now(timezone.utc)
    if settings and location and settings.safe_zone_latitude is not None and settings.safe_zone_longitude is not None:
        distance = distance_meters(
            settings.safe_zone_latitude,
            settings.safe_zone_longitude,
            location.latitude,
            location.longitude,
        )
        if distance > settings.safe_zone_radius_m + location.accuracy_m:
            ensure_alert(
                patient_id,
                "safe_zone_exit",
                "high",
                f"Location appears outside {settings.safe_zone_name}. Accuracy +/- {round(location.accuracy_m)} m.",
                db,
                location.id,
            )
    if settings and settings.expected_return_at:
        due_at = as_utc(settings.expected_return_at) + timedelta(
            minutes=settings.late_return_grace_minutes
        )
        if now_value > due_at:
            ensure_alert(
                patient_id,
                "late_return",
                "high",
                "Expected return time has passed and no caregiver acknowledgement is recorded.",
                db,
                location.id if location else None,
            )
    escalation_cutoff = now_value - timedelta(minutes=3)
    for item in (
        db.query(SafetyAlert)
        .filter_by(patient_id=patient_id, status="open")
        .all()
    ):
        if item.escalated_to_priority == 1 and as_utc(item.created_at) <= escalation_cutoff:
            item.escalated_to_priority = 2
            item.escalated_at = now_value
    for item in (
        db.query(SOSEvent)
        .filter_by(patient_id=patient_id, status="open")
        .all()
    ):
        if item.escalated_to_priority == 1 and as_utc(item.created_at) <= escalation_cutoff:
            item.escalated_to_priority = 2
            item.escalated_at = now_value
    db.commit()


# ===================================
#  Session Management
# ===================================


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

# User Authentication and Authorization
def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in is required.")
    payload = decode_access_token(authorization.removeprefix("Bearer "))
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="An access token is required.")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user

# ===================================
#  Caregiver Access Control
# ===================================

# Caregiver Access Control
def caregiver_only(user: User = Depends(current_user)) -> User:
    if user.role not in {Role.CAREGIVER.value, Role.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Caregiver access is required.")
    return user

# Caregiver's Access to Patient Data
def can_access_patient(user: User, patient_id: str, db: Session) -> bool:
    if user.role == Role.ADMIN.value or user.id == patient_id:
        return True
    return (
        db.query(CaregiverPatientAssignment)
        .filter_by(caregiver_id=user.id, patient_id=patient_id, active=True)
        .first()
        is not None
    )

# ===================================
#  Patient Access Control
# ===================================

def patient_access(patient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    return user

# ===================================
#  Language Capability Registry (Phase 4)
# ===================================

LANGUAGE_CONFIG = [
    {
        "languageCode": "en-IN",
        "languageName": "English",
        "speechSupported": True,
        "ttsSupported": True,
        "ttsFallbackNote": None,
        "bhashinSupported": False,
        "bhashinNote": None,
    },
    {
        "languageCode": "as-IN",
        "languageName": "Assamese",
        "speechSupported": True,
        "ttsSupported": False,
        "ttsFallbackNote": "Voice guides will use English until an Assamese voice pack is installed.",
        "bhashinSupported": True,
        "bhashinNote": "Enhanced Assamese speech recognition is available via BHASHINI. Configure a BHASHINI API key to activate it.",
    },
    {
        "languageCode": "hi-IN",
        "languageName": "Hindi",
        "speechSupported": True,
        "ttsSupported": True,
        "ttsFallbackNote": None,
        "bhashinSupported": True,
        "bhashinNote": "Enhanced Hindi speech recognition is available via BHASHINI.",
    },
]

# ===================================
#  API Endpoints
# ===================================

# Health Check
@app.get("/health")
def health():
    return {"status": "ok"}

# Language config — public, no auth required
@app.get("/language-config")
def language_config():
    """Return the static language capability registry.
    The app never claims speech support for a language not present here.
    """
    return LANGUAGE_CONFIG

#  User Registration

@app.post("/auth/register", response_model=AuthResponse, status_code=201)
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
@app.post("/auth/login", response_model=AuthResponse)
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
@app.post("/auth/google", response_model=AuthResponse)
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
@app.post("/auth/refresh", response_model=AuthResponse)
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
    token_session.revoked = True
    db.commit()
    return session_for(user, db)


@app.post("/auth/logout")
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
@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


@app.put("/auth/me")
def update_current_user(request: UserProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = request.name.strip()
    db.commit()
    db.refresh(user)
    return public_user(user)


@app.put("/auth/me/password")
def update_current_password(request: PasswordChangeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.password_hash or not verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")
    user.password_hash = hash_password(request.new_password)
    db.commit()
    return {"updated": True}

# Patient Profile
@app.get("/patients/me")
def my_patient(user: User = Depends(current_user), db: Session = Depends(get_db)):
    patient = db.get(Patient, user.id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return public_patient(patient, user)

# 
@app.get("/patients/{patient_id}")
def patient(
    patient_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    patient_user = db.get(User, patient_id)
    patient_profile = db.get(Patient, patient_id)
    if (
        not patient_user
        or not patient_profile
        or not can_access_patient(user, patient_id, db)
    ):
        raise HTTPException(status_code=404, detail="Patient not found.")
    return public_patient(patient_profile, patient_user)

#  
@app.get("/caregivers/me/patients")
def assigned_patients(
    user: User = Depends(caregiver_only), db: Session = Depends(get_db)
):
    assignments = (
        db.query(CaregiverPatientAssignment)
        .filter_by(caregiver_id=user.id, active=True)
        .all()
    )
    return [
        public_patient(db.get(Patient, item.patient_id), db.get(User, item.patient_id))
        for item in assignments
    ]

#  get emergency contacts for a patient
@app.get("/patients/{patient_id}/emergency-contacts")
def emergency_contacts(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    return [
        public_contact(item)
        for item in db.query(EmergencyContact)
        .filter_by(patient_id=patient_id, active=True)
        .order_by(EmergencyContact.priority)
        .all()
    ]

# create an emergency contact for a patient
@app.post("/patients/{patient_id}/emergency-contacts", status_code=201)
def create_emergency_contact(
    patient_id: str,
    request: EmergencyContactCreate,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    contact = EmergencyContact(patient_id=patient_id, **request.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return public_contact(contact)

# update an emergency contact
@app.put("/patients/{patient_id}/emergency-contacts/{contact_id}")
def update_emergency_contact(
    patient_id: str,
    contact_id: str,
    request: EmergencyContactUpdate,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(EmergencyContact)
        .filter_by(id=contact_id, patient_id=patient_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found.")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return public_contact(contact)

# Get a list of available activities
@app.get("/activities")
def activities(_: User = Depends(current_user)):
    return ACTIVITIES

# Get a list of reminders
@app.get("/patients/{patient_id}/reminders")
def reminders(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    return [
        public_reminder(item)
        for item in db.query(Reminder)
        .filter(Reminder.patient_id == patient_id)
        .order_by(Reminder.scheduled_time)
        .all()
    ]

# Create a reminder
@app.post("/reminders", status_code=201)
def create_reminder(
    request: ReminderCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, request.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    reminder = Reminder(**request.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return public_reminder(reminder)

# Update a reminder
@app.put("/reminders/{reminder_id}")
def update_reminder(
    reminder_id: str,
    request: ReminderUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    if not can_access_patient(user, reminder.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    db.commit()
    db.refresh(reminder)
    return public_reminder(reminder)

# Delete a reminder
@app.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    reminder = db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    if not can_access_patient(user, reminder.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    db.delete(reminder)
    db.commit()

# Start an activity to do
@app.post("/activities/{activity_id}/start", status_code=201)
def start_activity(
    activity_id: str,
    session: ActivityStart,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not any(activity["id"] == activity_id for activity in ACTIVITIES):
        raise HTTPException(status_code=404, detail="Activity not found.")
    if session.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Activity user does not match the signed-in account.",
        )
    existing = (
        db.query(ActivitySession)
        .filter(ActivitySession.event_id == session.event_id)
        .first()
    )
    if existing:
        return {
            "session_id": existing.id,
            "event_id": existing.event_id,
            "status": existing.completion_status,
            "duplicate": True,
        }
    activity_session = ActivitySession(
        event_id=session.event_id,
        user_id=user.id,
        activity_id=activity_id,
        started_at=session.started_at,
        difficulty_level=session.difficulty_level,
        offline_created=session.offline_created,
    )
    db.add(activity_session)
    db.commit()
    db.refresh(activity_session)
    return {
        "session_id": activity_session.id,
        "event_id": activity_session.event_id,
        "status": "started",
        "duplicate": False,
    }

# Activity Completion
@app.post("/activities/{activity_id}/complete")
def complete_activity(
    activity_id: str,
    session: ActivityCompletion,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not any(activity["id"] == activity_id for activity in ACTIVITIES):
        raise HTTPException(status_code=404, detail="Activity not found.")
    if session.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Activity user does not match the signed-in account.",
        )
    activity_session = (
        db.query(ActivitySession)
        .filter(ActivitySession.event_id == session.event_id)
        .first()
    )
    if activity_session and activity_session.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="Activity event belongs to another account."
        )
    if not activity_session:
        activity_session = ActivitySession(
            event_id=session.event_id,
            user_id=user.id,
            activity_id=activity_id,
            started_at=session.started_at,
            difficulty_level=session.difficulty_level,
            offline_created=session.offline_created,
        )
        db.add(activity_session)
    activity_session.completed_at = session.completed_at
    activity_session.accuracy = session.accuracy
    activity_session.response_time = session.response_time
    activity_session.attempts = session.attempts
    activity_session.completion_status = session.completion_status
    db.commit()
    history_rows = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == user.id,
            ActivitySession.activity_id == activity_id,
            ActivitySession.completed_at.is_not(None),
            ActivitySession.event_id != session.event_id,
        )
        .order_by(ActivitySession.completed_at.desc())
        .limit(4)
        .all()
    )
    current = PerformanceInput(
        session.accuracy,
        session.response_time,
        1 if session.completion_status == "completed" else 0,
        session.difficulty_level,
    )
    history = [
        PerformanceInput(
            item.accuracy or 0,
            item.response_time or 30,
            1 if item.completion_status == "completed" else 0,
            item.difficulty_level,
        )
        for item in reversed(history_rows)
    ]
    next_level, score = recommend_from_history(current, history)
    # Persist the recommended next difficulty so the Android app can hydrate it
    # from the patient profile without re-computing on every launch.
    patient_row = db.get(Patient, user.id)
    if patient_row:
        patient_row.next_difficulty = next_level
        db.commit()
    return {
        "saved": True,
        "event_id": session.event_id,
        "next_difficulty": next_level,
        "performance_score": score,
        "message": "Your next activity is adjusted to your performance.",
    }

# Get a patient's activity history
@app.get("/patients/{patient_id}/activity-sessions")
def activity_history(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    sessions = (
        db.query(ActivitySession)
        .filter(ActivitySession.user_id == patient_id)
        .order_by(ActivitySession.started_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": item.id,
            "activityId": item.activity_id,
            "startedAt": item.started_at,
            "completedAt": item.completed_at,
            "accuracy": item.accuracy,
            "responseTime": item.response_time,
            "attempts": item.attempts,
            "status": item.completion_status,
            "difficulty": item.difficulty_level,
        }
        for item in sessions
    ]

# Get a patient's activity performance
@app.get("/patients/{patient_id}/performance")
def performance(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    sessions = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == patient_id,
            ActivitySession.completed_at.is_not(None),
        )
        .order_by(ActivitySession.completed_at.asc())
        .limit(30)
        .all()
    )
    if not sessions:
        return {
            "patientId": patient_id,
            "note": "Supportive activity performance, not a medical assessment.",
            "accuracy": 0,
            "responseTime": 0,
            "difficulty": 2,
            "completion": [],
            "accuracyScores": [],
            "responseTimes": [],
            "difficultyProgression": [],
            "sessions": 0,
        }
    return {
        "patientId": patient_id,
        "note": "Supportive activity performance, not a medical assessment.",
        "accuracy": round(
            sum(item.accuracy or 0 for item in sessions) / len(sessions), 2
        ),
        "responseTime": round(
            sum(item.response_time or 0 for item in sessions) / len(sessions), 2
        ),
        "difficulty": round(
            sum(item.difficulty_level for item in sessions) / len(sessions), 1
        ),
        "completion": [
            round((1 if item.completion_status == "completed" else 0) * 100)
            for item in sessions
        ],
        "accuracyScores": [round((item.accuracy or 0) * 100) for item in sessions],
        "responseTimes": [item.response_time or 0 for item in sessions],
        "difficultyProgression": [item.difficulty_level for item in sessions],
        "sessions": len(sessions),
    }


@app.get("/patients/{patient_id}/reports/activity")
def activity_report(
    patient_id: str,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    activity_id: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    query = db.query(ActivitySession).filter(ActivitySession.user_id == patient_id)
    if from_date:
        query = query.filter(ActivitySession.started_at >= from_date)
    if to_date:
        query = query.filter(ActivitySession.started_at <= to_date)
    if activity_id:
        query = query.filter(ActivitySession.activity_id == activity_id)
    sessions = query.filter(ActivitySession.completed_at.is_not(None)).order_by(ActivitySession.started_at.asc()).limit(limit).all()
    completion_rate = sum(item.completion_status == "completed" for item in sessions) / len(sessions) if sessions else 0
    return {
        "patientId": patient_id,
        "summary": {
            "sessions": len(sessions),
            "completionRate": round(completion_rate, 2),
            "averageAccuracy": round(sum(item.accuracy or 0 for item in sessions) / len(sessions), 2) if sessions else 0,
            "averageResponseTime": round(sum(item.response_time or 0 for item in sessions) / len(sessions), 2) if sessions else 0,
            "averageDifficulty": round(sum(item.difficulty_level for item in sessions) / len(sessions), 2) if sessions else 0,
        },
        "series": [
            {"date": item.completed_at, "completionRate": 1 if item.completion_status == "completed" else 0, "accuracy": item.accuracy or 0, "responseTime": item.response_time or 0, "difficulty": item.difficulty_level}
            for item in sessions
        ],
        "note": "Supportive activity performance, not a medical assessment.",
    }


@app.get("/patients/{patient_id}/alerts")
def alert_history(
    patient_id: str,
    alert_status: str = Query(default="open", alias="status", pattern="^(open|acknowledged|all)$"),
    severity: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    alert_query = db.query(SafetyAlert).filter(SafetyAlert.patient_id == patient_id)
    sos_query = db.query(SOSEvent).filter(SOSEvent.patient_id == patient_id)
    if alert_status != "all":
        alert_query = alert_query.filter(SafetyAlert.status == alert_status)
        sos_query = sos_query.filter(SOSEvent.status == alert_status)
    if severity:
        alert_query = alert_query.filter(SafetyAlert.severity == severity)
    alerts = [{**public_alert(item, db), "kind": "safety_alert"} for item in alert_query.order_by(SafetyAlert.created_at.desc()).limit(limit).all()]
    alerts.extend({**public_sos(item, db), "kind": "sos"} for item in sos_query.order_by(SOSEvent.created_at.desc()).limit(limit).all())
    return sorted(alerts, key=lambda item: item["createdAt"], reverse=True)[:limit]


@app.get("/patients/{patient_id}/location-updates")
def location_history(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    locations = db.query(LocationUpdate).filter_by(patient_id=patient_id).order_by(LocationUpdate.captured_at.desc()).limit(limit).all()
    return [public_location(item) for item in locations]

# Get a patient's safety status
@app.get("/patients/{patient_id}/safety")
def safety(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    evaluate_safety(patient_id, db)
    location = latest_location(patient_id, db)
    settings = db.get(SafetySettings, patient_id)
    alerts = (
        db.query(SafetyAlert)
        .filter_by(patient_id=patient_id, status="open")
        .order_by(SafetyAlert.created_at.desc())
        .all()
    )
    sos_events = (
        db.query(SOSEvent)
        .filter_by(patient_id=patient_id, status="open")
        .order_by(SOSEvent.created_at.desc())
        .all()
    )
    location_data = public_location(location)
    status_text = "Needs acknowledgement" if alerts or sos_events else "No open safety alerts"
    if location_data and location_data["connectionState"] == "offline":
        status_text = f"{status_text} - showing last known location"
    return {
        "patientId": patient_id,
        "status": status_text,
        "location": location_data,
        "settings": public_safety_settings(settings),
        "contacts": [public_contact(item) for item in active_contacts(patient_id, db)],
        "alerts": [public_alert(item, db) for item in alerts],
        "sosEvents": [public_sos(item, db) for item in sos_events],
        "workflowNote": "Safety support is permission-aware caregiver coordination. SOS notifies configured caregivers and does not contact government or emergency services directly.",
    }

# Configure patient safety settings
@app.put("/patients/{patient_id}/safety/settings")
def update_safety_settings(
    patient_id: str,
    request: SafetySettingsUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    settings = db.get(SafetySettings, patient_id)
    if not settings:
        settings = SafetySettings(patient_id=patient_id)
        db.add(settings)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    evaluate_safety(patient_id, db)
    db.refresh(settings)
    return public_safety_settings(settings)

# Save a patient location update
@app.post("/patients/{patient_id}/location-updates", status_code=201)
def create_location_update(
    patient_id: str,
    request: LocationUpdateCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    location = LocationUpdate(patient_id=patient_id, **request.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    evaluate_safety(patient_id, db)
    return public_location(location)

# Create an SOS caregiver workflow event
@app.post("/patients/{patient_id}/sos-events", status_code=201)
def create_sos_event(
    patient_id: str,
    request: SOSEventCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    event = SOSEvent(patient_id=patient_id, **request.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    evaluate_safety(patient_id, db)
    return public_sos(event, db)

# Acknowledge an SOS event
@app.post("/patients/{patient_id}/sos-events/{event_id}/acknowledge")
def acknowledge_sos_event(
    patient_id: str,
    event_id: str,
    _: SafetyAcknowledgement,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    event = db.get(SOSEvent, event_id)
    if not event or event.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="SOS event not found.")
    event.status = "acknowledged"
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by = user.id
    db.commit()
    db.refresh(event)
    return public_sos(event, db)

# Acknowledge a safety alert
@app.post("/patients/{patient_id}/safety-alerts/{alert_id}/acknowledge")
def acknowledge_safety_alert(
    patient_id: str,
    alert_id: str,
    _: SafetyAcknowledgement,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    alert = db.get(SafetyAlert, alert_id)
    if not alert or alert.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Safety alert not found.")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.id
    db.commit()
    db.refresh(alert)
    return public_alert(alert, db)

# Process one offline mutation against the same persistence models as online APIs.
def apply_sync_event(event: SyncEventRequest, user: User, db: Session) -> dict:
    if not can_access_patient(user, event.patient_id, db):
        raise HTTPException(status_code=403, detail="You are not assigned to this patient.")

    if event.event_type == "activity_completion":
        payload = ActivityCompletion.model_validate(event.payload)
        if payload.event_id != event.event_id:
            raise HTTPException(status_code=422, detail="Activity event IDs must match.")
        if payload.user_id != user.id or payload.user_id != event.patient_id:
            raise HTTPException(status_code=403, detail="Activity user does not match the event patient.")
        result = complete_activity(payload.activity_id, payload, user, db)
    elif event.event_type == "reminder_update":
        reminder_id = event.payload.get("reminder_id")
        if not isinstance(reminder_id, str):
            raise HTTPException(status_code=422, detail="reminder_id is required.")
        payload = ReminderUpdate.model_validate(event.payload.get("changes", {}))
        result = update_reminder(reminder_id, payload, user, db)
    elif event.event_type == "location_update":
        payload = LocationUpdateCreate.model_validate(event.payload)
        latest = latest_location(event.patient_id, db)
        if latest and as_utc(payload.captured_at) <= as_utc(latest.captured_at):
            raise HTTPException(
                status_code=409,
                detail="Location update is older than the latest stored location.",
            )
        result = create_location_update(event.patient_id, payload, user, db)
    elif event.event_type == "safety_settings_update":
        payload = SafetySettingsUpdate.model_validate(event.payload)
        result = update_safety_settings(event.patient_id, payload, user, db)
    elif event.event_type == "sos_event":
        payload = SOSEventCreate.model_validate(event.payload)
        result = create_sos_event(event.patient_id, payload, user, db)
    else:
        raise HTTPException(status_code=422, detail=f"Unsupported sync event type: {event.event_type}")
    return {"event_id": event.event_id, "status": "accepted", "result": result}


@app.post("/sync/events")
def sync(events: list[SyncEventRequest], user: User = Depends(current_user), db: Session = Depends(get_db)):
    results = []
    for event in events:
        existing = db.get(SyncEvent, event.event_id)
        if existing:
            if (
                existing.user_id != user.id
                or existing.patient_id != event.patient_id
                or existing.event_type != event.event_type
                or existing.payload != event.payload
            ):
                results.append(
                    {
                        "event_id": event.event_id,
                        "status": "conflict",
                        "detail": "Event ID is already associated with different event data.",
                    }
                )
                continue
            results.append({"event_id": event.event_id, "status": "duplicate", "result": existing.result})
            continue
        try:
            processed = apply_sync_event(event, user, db)
            record = SyncEvent(
                event_id=event.event_id,
                user_id=user.id,
                patient_id=event.patient_id,
                event_type=event.event_type,
                payload=event.payload,
                status="accepted",
                result=jsonable_encoder(processed["result"]),
            )
            db.add(record)
            db.commit()
            results.append(processed)
        except (HTTPException, ValidationError) as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc, HTTPException) else "Invalid sync event payload."
            status_text = "conflict" if isinstance(exc, HTTPException) and exc.status_code == 409 else "rejected"
            record = SyncEvent(
                event_id=event.event_id,
                user_id=user.id,
                patient_id=event.patient_id,
                event_type=event.event_type,
                payload=event.payload,
                status=status_text,
                result={"detail": detail},
            )
            db.add(record)
            db.commit()
            results.append({"event_id": event.event_id, "status": status_text, "detail": detail})
    return {"results": results, "syncedAt": datetime.now(timezone.utc)}
