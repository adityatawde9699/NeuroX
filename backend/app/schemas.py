# ===================================
#  Imports
# ===================================
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator

# ===================================
#  User Roles
# ===================================
class Role(str, Enum):
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    HEALTHCARE_WORKER = "HEALTHCARE_WORKER"
    ADMIN = "ADMIN"

# ===================================
#  Authentication Schemas
# ===================================
# Login Request
class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)

# Sign in request for registration
class RegisterRequest(LoginRequest):
    name: str = Field(min_length=2, max_length=80)
    role: Role = Role.CAREGIVER

    @field_validator("role")
    @classmethod
    def public_registration_role(cls, role: Role) -> Role:
        if role not in {Role.PATIENT, Role.CAREGIVER}:
            raise ValueError("Public registration supports patient and caregiver accounts only.")
        return role

# Sign in request using Google
class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20)

# Authnetication response containing tokens and user information
class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

# Refresh request containing the refresh token
class RefreshRequest(BaseModel):
    refresh_token: str

# Activity Completion schema representing the completion of an activity by a user
class ActivityCompletion(BaseModel):
    user_id: str
    activity_id: str
    started_at: datetime
    completed_at: datetime
    accuracy: float = Field(ge=0, le=1)
    response_time: float = Field(gt=0)
    attempts: int = Field(ge=1)
    completion_status: str
    difficulty_level: int = Field(ge=1, le=5)
    offline_created: bool = False
    event_id: str

# Starting Activity
class ActivityStart(BaseModel):
    user_id: str
    difficulty_level: int = Field(ge=1, le=5)
    started_at: datetime
    event_id: str = Field(min_length=8, max_length=64)
    offline_created: bool = False

# Create Reminder
class ReminderCreate(BaseModel):
    patient_id: str
    type: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    scheduled_time: datetime
    repeat_rule: str | None = Field(default=None, max_length=64)
    enabled: bool = True

# Update Reminder
class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    scheduled_time: datetime | None = None
    repeat_rule: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None
    completed: bool | None = None

# Emergency Contact Schemas
class EmergencyContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=32)
    relationship: str = Field(min_length=2, max_length=64)
    priority: int = Field(default=1, ge=1, le=10)

# Update Emergency Contact
class EmergencyContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    relationship: str | None = Field(default=None, min_length=2, max_length=64)
    priority: int | None = Field(default=None, ge=1, le=10)
    active: bool | None = None

# Safety configuration
class SafetySettingsUpdate(BaseModel):
    safe_zone_name: str | None = Field(default=None, min_length=2, max_length=80)
    safe_zone_latitude: float | None = Field(default=None, ge=-90, le=90)
    safe_zone_longitude: float | None = Field(default=None, ge=-180, le=180)
    safe_zone_radius_m: int | None = Field(default=None, ge=50, le=5000)
    expected_return_at: datetime | None = None
    expected_return_note: str | None = Field(default=None, max_length=160)
    late_return_grace_minutes: int | None = Field(default=None, ge=0, le=180)

# Patient location update
class LocationUpdateCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=5000)
    connection_state: str = Field(default="online", min_length=2, max_length=24)
    captured_at: datetime

# Patient SOS event
class SOSEventCreate(BaseModel):
    message: str = Field(
        default="I need help. Please check on me.",
        min_length=2,
        max_length=255,
    )
    location_update_id: str | None = None

# Alert acknowledgement
class SafetyAcknowledgement(BaseModel):
    note: str | None = Field(default=None, max_length=160)

class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)

# Offline mutation envelope shared by Android and the sync endpoint.
class SyncEventRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    event_type: str = Field(min_length=3, max_length=48)
    patient_id: str = Field(min_length=1, max_length=36)
    payload: dict
