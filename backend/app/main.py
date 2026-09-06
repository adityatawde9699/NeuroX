# ===================================
#  Imports
# ===================================
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
    Patient,
    RefreshSession,
    Reminder,
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
    RefreshRequest,
    RegisterRequest,
    ReminderCreate,
    ReminderUpdate,
    Role,
)
from app.services.google_auth import verify_google_credential

# ===================================
#  API Application
# ===================================

app = FastAPI(
    title="NeuroX API",
    version="0.3.0",
    description="Supportive engagement APIs — not clinical diagnosis.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


@app.on_event("startup")
def initialise_database():
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

# User Profile
@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return public_user(user)

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

# Get a patient's safety status
@app.get("/patients/{patient_id}/safety")
def safety(patient_id: str, _: User = Depends(patient_access)):
    return {
        "status": "At Home • Safe",
        "gpsAccuracy": "±18 m",
        "lastUpdated": "2 minutes ago",
        "expectedReturn": "6:00 PM",
        "connection": "Online",
    }

# Sync events
@app.post("/sync/events")
def sync(events: list[dict], _: User = Depends(current_user)):
    return {
        "accepted": [event.get("event_id") for event in events],
        "syncedAt": datetime.now(timezone.utc),
    }
