from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    HEALTHCARE_WORKER = "HEALTHCARE_WORKER"
    ADMIN = "ADMIN"


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)

class RegisterRequest(LoginRequest):
    name: str = Field(min_length=2, max_length=80)
    role: Role = Role.CAREGIVER

class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20)

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str


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
