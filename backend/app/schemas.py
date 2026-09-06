# ===================================
#  Imports
# ===================================
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

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
