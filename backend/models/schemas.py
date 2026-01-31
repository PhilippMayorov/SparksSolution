"""
Pydantic models for API request/response schemas.

These models define the data structures used throughout the API
for validation, serialization, and documentation.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# ============ ENUMS ============

class AppointmentStatus(str, Enum):
    """Possible states for an appointment."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    MISSED = "missed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CallStatus(str, Enum):
    """Possible states for a call attempt."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class CallOutcome(str, Enum):
    """Outcome of a completed call."""
    RESCHEDULED = "rescheduled"
    DECLINED = "declined"
    VOICEMAIL = "voicemail"
    CALLBACK_REQUESTED = "callback_requested"
    INVALID_NUMBER = "invalid_number"


class FlagPriority(str, Enum):
    """Priority levels for flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FlagStatus(str, Enum):
    """Status of a flag."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ============ PATIENT SCHEMAS ============

class PatientBase(BaseModel):
    """Base patient fields."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(default='', max_length=100)  # Allow empty last name
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")  # E.164 format
    date_of_birth: Optional[datetime] = None


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating a patient (all fields optional)."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None


class PatientResponse(PatientBase):
    """Schema for patient responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ APPOINTMENT SCHEMAS ============

class AppointmentBase(BaseModel):
    """Base appointment fields."""
    patient_id: Optional[UUID] = None  # Made optional since patients are embedded in referrals
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)
    appointment_type: str = Field(..., max_length=100)
    notes: Optional[str] = None
    # Additional fields for new patient creation
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""
    pass


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    appointment_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[AppointmentStatus] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment responses."""
    id: UUID
    status: AppointmentStatus
    google_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling an appointment."""
    new_datetime: datetime
    reason: Optional[str] = None


# ============ CALL ATTEMPT SCHEMAS ============

class CallAttemptCreate(BaseModel):
    """Schema for initiating a call."""
    appointment_id: UUID
    patient_id: UUID


class CallAttemptResponse(BaseModel):
    """Schema for call attempt responses."""
    id: UUID
    appointment_id: UUID
    patient_id: UUID
    status: CallStatus
    outcome: Optional[CallOutcome] = None
    elevenlabs_call_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    transcript: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ FLAG SCHEMAS ============

class FlagBase(BaseModel):
    """Base flag fields."""
    patient_id: UUID
    appointment_id: Optional[UUID] = None
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    priority: FlagPriority = FlagPriority.MEDIUM


class FlagCreate(FlagBase):
    """Schema for creating a flag."""
    pass


class FlagUpdate(BaseModel):
    """Schema for updating a flag."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[FlagPriority] = None
    status: Optional[FlagStatus] = None
    resolved_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None


class FlagResponse(FlagBase):
    """Schema for flag responses."""
    id: UUID
    status: FlagStatus
    created_by: Optional[UUID] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientResponse] = None
    appointment: Optional[AppointmentResponse] = None

    class Config:
        from_attributes = True


# ============ WEBHOOK SCHEMAS ============

class ElevenLabsWebhookPayload(BaseModel):
    """
    Schema for ElevenLabs webhook callbacks.
    
    NOTE: This structure is based on expected ElevenLabs callback format.
    TODO: Verify actual payload structure from ElevenLabs documentation.
    """
    call_id: str
    status: str  # "completed", "failed", "no_answer"
    outcome: Optional[str] = None  # "rescheduled", "declined", etc.
    new_appointment_time: Optional[datetime] = None  # If rescheduled
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[dict] = None  # Custom metadata we passed when initiating


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    success: bool
    message: str


# ============ CALENDAR SCHEMAS ============

class CalendarEventCreate(BaseModel):
    """Schema for creating a Google Calendar event."""
    appointment_id: UUID
    summary: str
    description: Optional[str] = None
    attendee_email: Optional[EmailStr] = None


class CalendarEventResponse(BaseModel):
    """Schema for calendar event responses."""
    google_event_id: str
    html_link: str
    status: str


class CalendarSyncStatus(BaseModel):
    """Schema for calendar sync status."""
    appointment_id: UUID
    synced: bool
    google_event_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    error: Optional[str] = None


# ============ AUTH SCHEMAS ============

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user responses."""
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============ DASHBOARD SCHEMAS ============

class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_appointments_today: int
    missed_appointments: int
    pending_calls: int
    open_flags: int
    upcoming_appointments: List[AppointmentResponse]
