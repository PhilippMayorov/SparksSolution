"""
Pydantic models for API request/response schemas.

These models define the data structures used throughout the API
for validation, serialization, and documentation.
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID


# ============ ENUMS ============

class ReferralStatus(str, Enum):
    """Possible states for a referral."""
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    ATTENDED = "ATTENDED"
    MISSED = "MISSED"
    NEEDS_REBOOK = "NEEDS_REBOOK"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SpecialistType(str, Enum):
    """Types of medical specialists."""
    CARDIOLOGY = "CARDIOLOGY"
    ORTHOPEDICS = "ORTHOPEDICS"
    NEUROLOGY = "NEUROLOGY"
    DERMATOLOGY = "DERMATOLOGY"
    OPHTHALMOLOGY = "OPHTHALMOLOGY"
    ENDOCRINOLOGY = "ENDOCRINOLOGY"
    PSYCHIATRY = "PSYCHIATRY"
    OTHER = "OTHER"


class Urgency(str, Enum):
    """Urgency levels for referrals."""
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


class UserRole(str, Enum):
    """User roles in the system."""
    NURSE = "NURSE"
    COORDINATOR = "COORDINATOR"
    ADMIN = "ADMIN"


class CallType(str, Enum):
    """Types of outbound calls."""
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    MISSED_APPOINTMENT_FOLLOWUP = "MISSED_APPOINTMENT_FOLLOWUP"
    HIGH_RISK_CHECKIN = "HIGH_RISK_CHECKIN"
    MANUAL_OUTREACH = "MANUAL_OUTREACH"


class CallStatus(str, Enum):
    """Possible states for a call attempt."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"
    VOICEMAIL = "VOICEMAIL"


class CallResolution(str, Enum):
    """Resolution/outcome of a call."""
    RESCHEDULED = "RESCHEDULED"
    LEFT_VOICEMAIL = "LEFT_VOICEMAIL"
    NO_ANSWER = "NO_ANSWER"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    DECLINED = "DECLINED"


class EmailType(str, Enum):
    """Types of emails."""
    REFERRAL_CREATED = "REFERRAL_CREATED"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"
    APPOINTMENT_RESCHEDULED = "APPOINTMENT_RESCHEDULED"
    FOLLOW_UP = "FOLLOW_UP"


class EmailStatus(str, Enum):
    """Email delivery status."""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"


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


class AlertType(str, Enum):
    """Types of alerts."""
    HIGH_RISK_ESCALATION = "HIGH_RISK_ESCALATION"
    OVERDUE_REFERRAL = "OVERDUE_REFERRAL"
    FAILED_CALL = "FAILED_CALL"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"


# ============ REFERRAL SCHEMAS ============

class ReferralBase(BaseModel):
    """Base referral fields."""
    patient_name: str = Field(..., min_length=1, max_length=255)
    patient_dob: date
    health_card_number: str = Field(..., min_length=1, max_length=50)
    patient_email: Optional[str] = Field(default=None)
    patient_phone: Optional[str] = Field(None, max_length=20)

    condition: str = Field(..., min_length=1)
    specialist_type: SpecialistType
    urgency: Urgency = Urgency.ROUTINE
    is_high_risk: bool = False

    referral_date: date
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator('patient_email', mode='before')
    @classmethod
    def validate_email(cls, v):
        """Convert empty strings to None for email field."""
        if v == '':
            return None
        return v


class ReferralCreate(ReferralBase):
    """Schema for creating a new referral."""
    created_by_id: UUID  # The nurse/user creating the referral


class ReferralUpdate(BaseModel):
    """Schema for updating a referral (all fields optional)."""
    patient_name: Optional[str] = None
    patient_dob: Optional[date] = None
    health_card_number: Optional[str] = None
    patient_email: Optional[str] = Field(default=None)
    patient_phone: Optional[str] = None

    condition: Optional[str] = None
    specialist_type: Optional[SpecialistType] = None
    urgency: Optional[Urgency] = None
    is_high_risk: Optional[bool] = None

    status: Optional[ReferralStatus] = None
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator('patient_email', mode='before')
    @classmethod
    def validate_email(cls, v):
        """Convert empty strings to None for email field."""
        if v == '':
            return None
        return v


class ReferralResponse(ReferralBase):
    """Schema for referral responses."""
    id: UUID
    status: ReferralStatus
    completed_date: Optional[datetime] = None

    # Email tracking
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None

    # Audit fields
    created_by_id: UUID
    updated_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReferralReschedule(BaseModel):
    """Schema for rescheduling a referral."""
    new_datetime: datetime
    reason: Optional[str] = None


class ReferralSchedule(BaseModel):
    """Schema for scheduling a pending referral."""
    scheduled_date: datetime
    notes: Optional[str] = None


# ============ USER SCHEMAS ============

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.NURSE
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user responses."""
    id: UUID
    email: EmailStr
    role: UserRole
    first_name: str
    last_name: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============ CALL LOG SCHEMAS ============

class CallLogCreate(BaseModel):
    """Schema for initiating a call."""
    referral_id: UUID
    call_type: CallType = CallType.MISSED_APPOINTMENT_FOLLOWUP
    phone_number: str


class CallLogResponse(BaseModel):
    """Schema for call log responses."""
    id: UUID
    referral_id: UUID
    call_type: CallType
    phone_number: str
    status: CallStatus
    resolution: Optional[CallResolution] = None
    selected_proposal_id: Optional[UUID] = None
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = None
    twilio_call_sid: Optional[str] = None
    recording_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ EMAIL LOG SCHEMAS ============

class EmailLogCreate(BaseModel):
    """Schema for creating an email log."""
    referral_id: UUID
    email_type: EmailType
    recipient_email: EmailStr
    subject: str
    calendar_invite_attached: bool = False


class EmailLogResponse(BaseModel):
    """Schema for email log responses."""
    id: UUID
    referral_id: UUID
    email_type: EmailType
    recipient_email: EmailStr
    subject: str
    status: EmailStatus
    sendgrid_message_id: Optional[str] = None
    error_message: Optional[str] = None
    calendar_invite_attached: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ FLAG SCHEMAS ============

class FlagBase(BaseModel):
    """Base flag fields."""
    referral_id: UUID
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    priority: FlagPriority = FlagPriority.MEDIUM


class FlagCreate(FlagBase):
    """Schema for creating a flag."""
    created_by_id: Optional[UUID] = None  # Optional for system-generated flags


class FlagUpdate(BaseModel):
    """Schema for updating a flag."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[FlagPriority] = None
    status: Optional[FlagStatus] = None
    resolved_by_id: Optional[UUID] = None
    resolution_notes: Optional[str] = None


class PatientInfo(BaseModel):
    """Minimal patient info for flag responses."""
    first_name: str
    last_name: str


class AppointmentInfo(BaseModel):
    """Minimal appointment info for flag responses."""
    scheduled_date: Optional[datetime] = None
    status: Optional[str] = None


class ReferralInfo(BaseModel):
    """Referral info embedded in flag response."""
    id: Optional[UUID] = None
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class FlagResponse(FlagBase):
    """Schema for flag responses."""
    id: UUID
    status: FlagStatus
    created_by_id: Optional[UUID] = None
    resolved_by_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientInfo] = None
    appointment: Optional[AppointmentInfo] = None
    referrals: Optional[ReferralInfo] = None

    class Config:
        from_attributes = True


# ============ ALERT SCHEMAS ============

class AlertBase(BaseModel):
    """Base alert fields."""
    referral_id: Optional[UUID] = None
    user_id: Optional[UUID] = None  # Null = broadcast to all users
    alert_type: AlertType
    message: str


class AlertCreate(AlertBase):
    """Schema for creating an alert."""
    pass


class AlertResponse(AlertBase):
    """Schema for alert responses."""
    id: UUID
    is_dismissed: bool
    dismissed_at: Optional[datetime] = None
    created_at: datetime

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
    referral_id: UUID
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
    referral_id: UUID
    synced: bool
    google_event_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    error: Optional[str] = None


# ============ DASHBOARD SCHEMAS ============

class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_active: int
    pending_count: int
    scheduled_count: int
    missed_count: int
    escalated_count: int
    high_risk_active: int
    scheduled_this_week: int
    overdue_pending: int
    unread_alerts: int
    emails_pending: int


class StatusHistoryResponse(BaseModel):
    """Schema for status history responses."""
    id: UUID
    referral_id: UUID
    status: ReferralStatus
    changed_by_id: UUID
    changed_at: datetime
    note: Optional[str] = None

    class Config:
        from_attributes = True


class SpecialistCalendarResponse(BaseModel):
    """Schema for specialist calendar responses."""
    id: UUID
    specialist_type: SpecialistType
    external_calendar_id: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentProposalStatus(str, Enum):
    """Status of an appointment proposal."""
    PROPOSED = "PROPOSED"
    HELD = "HELD"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONFIRMED = "CONFIRMED"


class AppointmentProposalResponse(BaseModel):
    """Schema for appointment proposal responses."""
    id: UUID
    referral_id: UUID
    proposed_start: datetime
    proposed_end: datetime
    status: AppointmentProposalStatus
    hold_expires_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
