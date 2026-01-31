"""
Supabase client service.

Handles all database operations via Supabase Python client.
This is the primary data layer for referrals (appointments), calls, and flags (alerts).

NOTE: The schema uses 'referrals' table but we expose it as 'appointments' to the frontend.
We transform data to match frontend expectations.
"""

import os
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def transform_referral_to_appointment(referral: dict) -> dict:
    """
    Transform a referral record from DB schema to frontend appointment format.
    
    DB Schema (referrals):
        - patient_name, patient_phone, patient_email (embedded)
        - scheduled_date (TIMESTAMPTZ)
        - status: PENDING, SCHEDULED, ATTENDED, MISSED, NEEDS_REBOOK, ESCALATED, COMPLETED, CANCELLED
        - specialist_type, condition, urgency
        
    Frontend expects:
        - id, patient_id (or patient object), scheduled_at, status (lowercase)
        - patient: { id, first_name, last_name, phone, email }
    """
    if not referral:
        return None
    
    # Parse patient name into first/last
    patient_name = referral.get('patient_name', 'Unknown Patient')
    name_parts = patient_name.strip().split(' ', 1)
    first_name = name_parts[0] if name_parts else 'Unknown'
    last_name = name_parts[1] if len(name_parts) > 1 else ''
    
    # Create synthetic patient object (since patient info is embedded in referrals)
    patient_phone = referral.get('patient_phone')
    patient_email = referral.get('patient_email')
    
    patient = {
        'id': referral.get('id'),  # Use referral ID as patient ID for now
        'first_name': first_name,
        'last_name': last_name,
        'phone': patient_phone if patient_phone else None,  # Convert empty string to None
        'email': patient_email if patient_email else None,  # Convert empty string to None
        'date_of_birth': referral.get('patient_dob'),
        'created_at': referral.get('created_at'),
        'updated_at': referral.get('updated_at'),
    }
    
    # Map status to lowercase for frontend
    status_map = {
        'PENDING': 'scheduled',
        'SCHEDULED': 'scheduled',
        'ATTENDED': 'completed',
        'MISSED': 'missed',
        'NEEDS_REBOOK': 'rescheduled',
        'ESCALATED': 'missed',
        'COMPLETED': 'completed',
        'CANCELLED': 'cancelled',
    }
    db_status = referral.get('status', 'PENDING')
    frontend_status = status_map.get(db_status, db_status.lower())
    
    return {
        'id': referral.get('id'),
        'patient_id': referral.get('id'),  # Use referral ID as patient reference
        'patient': patient,
        'scheduled_at': referral.get('scheduled_date'),
        'appointment_type': referral.get('specialist_type', 'General'),
        'status': frontend_status,
        'notes': referral.get('notes'),
        'condition': referral.get('condition'),
        'urgency': referral.get('urgency'),
        'is_high_risk': referral.get('is_high_risk', False),
        'duration_minutes': 30,  # Default duration
        'google_event_id': referral.get('calendar_event_id'),
        'created_at': referral.get('created_at'),
        'updated_at': referral.get('updated_at'),
        # Keep original fields for backend use
        'patient_name': patient_name,
        'patient_phone': referral.get('patient_phone'),
        'patient_email': referral.get('patient_email'),
    }


def transform_alert_to_flag(alert: dict, referral: dict = None) -> dict:
    """
    Transform an alert record from DB schema to frontend flag format.
    
    DB Schema (alerts):
        - referral_id, user_id, alert_type, message, is_read, is_dismissed
        
    Frontend expects:
        - id, patient_id, appointment_id, title, description, priority, status
        - patient: { first_name, last_name, phone }
        - appointment: { scheduled_at, appointment_type }
    """
    if not alert:
        return None
    
    # Map alert_type to priority
    priority_map = {
        'HIGH_RISK_ESCALATION': 'urgent',
        'MISSED_APPOINTMENT': 'high',
        'CALL_FAILED': 'high',
        'FOLLOW_UP_REQUIRED': 'medium',
        'GENERAL': 'low',
    }
    alert_type = alert.get('alert_type', 'GENERAL')
    priority = priority_map.get(alert_type, 'medium')
    
    # Determine status (is_read column may not exist, so just use is_dismissed)
    if alert.get('is_dismissed'):
        status = 'dismissed'
    else:
        status = 'open'
    
    # Get referral/patient info if available
    ref = referral or alert.get('referrals') or {}
    patient_name = ref.get('patient_name', 'Unknown Patient')
    name_parts = patient_name.split(' ', 1)
    
    patient = {
        'id': ref.get('id'),
        'first_name': name_parts[0] if name_parts else 'Unknown',
        'last_name': name_parts[1] if len(name_parts) > 1 else '',
        'phone': ref.get('patient_phone'),
        'email': ref.get('patient_email'),
    }
    
    appointment = transform_referral_to_appointment(ref) if ref else None
    
    return {
        'id': alert.get('id'),
        'patient_id': ref.get('id'),
        'appointment_id': ref.get('id'),
        'title': alert.get('message', 'Follow-up Required')[:200],
        'description': alert.get('message'),
        'reason': alert.get('message'),
        'flag_type': alert_type,
        'priority': priority,
        'status': status,
        'call_attempts': 3,  # Default; TODO: count from call_logs
        'patient': patient,
        'appointment': appointment,
        'created_by': alert.get('user_id'),
        'resolved_by': None,
        'resolved_at': None,
        'resolution_notes': None,
        'created_at': alert.get('created_at'),
        'updated_at': alert.get('created_at'),
    }


def transform_call_log_to_attempt(call_log: dict, referral: dict = None) -> dict:
    """Transform a call_log record to frontend call attempt format."""
    if not call_log:
        return None
    
    # Map status
    status_map = {
        'SCHEDULED': 'pending',
        'IN_PROGRESS': 'in_progress',
        'COMPLETED': 'completed',
        'FAILED': 'failed',
        'NO_ANSWER': 'no_answer',
        'VOICEMAIL': 'no_answer',
    }
    
    return {
        'id': call_log.get('id'),
        'appointment_id': call_log.get('referral_id'),
        'patient_id': call_log.get('referral_id'),
        'status': status_map.get(call_log.get('status'), 'pending'),
        'outcome': call_log.get('resolution', '').lower() if call_log.get('resolution') else None,
        'elevenlabs_call_id': call_log.get('twilio_call_sid'),
        'started_at': call_log.get('scheduled_at'),
        'ended_at': call_log.get('completed_at'),
        'transcript': call_log.get('transcript'),
        'duration_seconds': call_log.get('duration_seconds'),
        'created_at': call_log.get('created_at'),
    }


class SupabaseClient:
    """
    Supabase database client wrapper.
    
    Provides typed methods for all database operations.
    Uses Supabase service role key for server-side operations.
    """
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client: Client = create_client(url, key)
    
    # ============ PATIENTS (via referrals) ============
    # Note: Patient info is embedded in referrals table
    
    async def get_patient(self, patient_id: UUID) -> Optional[dict]:
        """
        Get a patient by ID.
        Since patients are embedded in referrals, we fetch the referral and extract patient info.
        """
        try:
            result = self.client.table("referrals").select("*").eq("id", str(patient_id)).single().execute()
            if result.data:
                ref = result.data
                name_parts = ref.get('patient_name', 'Unknown').split(' ', 1)
                return {
                    'id': ref.get('id'),
                    'first_name': name_parts[0],
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'phone': ref.get('patient_phone'),
                    'email': ref.get('patient_email'),
                    'date_of_birth': ref.get('patient_dob'),
                }
        except Exception:
            pass
        return None
    
    # ============ APPOINTMENTS (via referrals) ============
    
    async def create_appointment(self, appointment_data: dict) -> dict:
        """
        Create a new appointment (referral).
        
        Frontend sends:
            patient_id, scheduled_at, appointment_type, notes
            
        We need to create a referral with this data.
        """
        # Get a real user ID from the database for created_by_id
        try:
            users_result = self.client.table('users').select('id').limit(1).execute()
            if users_result.data:
                default_user_id = users_result.data[0]['id']
            else:
                raise Exception("No users found in database")
        except Exception:
            # Fallback to a known user ID or create one
            default_user_id = 'f13fab2f-74d6-489b-a58e-80307f589fdb'  # Use the known user ID
        
        referral_data = {
            'patient_name': appointment_data.get('patient_name', 'New Patient'),
            'patient_phone': appointment_data.get('patient_phone') or '',
            'patient_email': appointment_data.get('patient_email') or '',
            'patient_dob': appointment_data.get('patient_dob', '2000-01-01'),
            'health_card_number': appointment_data.get('health_card_number', f'TEMP-{uuid4().hex[:8]}'),
            'condition': appointment_data.get('condition', 'General Checkup'),
            'specialist_type': (appointment_data.get('appointment_type') or 'OTHER').upper(),
            'urgency': appointment_data.get('urgency', 'ROUTINE'),
            'status': 'SCHEDULED',
            'scheduled_date': appointment_data.get('scheduled_at'),
            'referral_date': datetime.utcnow().date().isoformat(),
            'notes': appointment_data.get('notes'),
            'created_by_id': appointment_data.get('created_by_id', default_user_id),
        }
        
        result = self.client.table("referrals").insert(referral_data).execute()
        if result.data:
            return transform_referral_to_appointment(result.data[0])
        return None
    
    async def get_appointment(self, appointment_id: UUID) -> Optional[dict]:
        """Get an appointment (referral) by ID."""
        try:
            result = (
                self.client.table("referrals")
                .select("*")
                .eq("id", str(appointment_id))
                .single()
                .execute()
            )
            return transform_referral_to_appointment(result.data) if result.data else None
        except Exception:
            return None
    
    async def get_appointments_by_date(self, date: datetime) -> List[dict]:
        """Get all appointments for a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        result = (
            self.client.table("referrals")
            .select("*")
            .gte("scheduled_date", start_of_day.isoformat())
            .lte("scheduled_date", end_of_day.isoformat())
            .order("scheduled_date")
            .execute()
        )
        return [transform_referral_to_appointment(r) for r in (result.data or [])]
    
    async def get_appointments_by_status(self, status: str) -> List[dict]:
        """Get all appointments with a specific status."""
        # Map frontend status to DB status
        status_map = {
            'scheduled': ['PENDING', 'SCHEDULED'],
            'missed': ['MISSED', 'ESCALATED'],
            'completed': ['ATTENDED', 'COMPLETED'],
            'cancelled': ['CANCELLED'],
            'rescheduled': ['NEEDS_REBOOK'],
        }
        db_statuses = status_map.get(status.lower(), [status.upper()])
        
        result = (
            self.client.table("referrals")
            .select("*")
            .in_("status", db_statuses)
            .order("scheduled_date", desc=True)
            .execute()
        )
        return [transform_referral_to_appointment(r) for r in (result.data or [])]
    
    async def get_all_appointments(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get all appointments with pagination."""
        result = (
            self.client.table("referrals")
            .select("*")
            .order("scheduled_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [transform_referral_to_appointment(r) for r in (result.data or [])]
    
    async def update_appointment(self, appointment_id: UUID, updates: dict) -> Optional[dict]:
        """Update an appointment (referral)."""
        # Transform frontend field names to DB field names
        db_updates = {}
        
        if 'scheduled_at' in updates:
            db_updates['scheduled_date'] = updates['scheduled_at']
        if 'status' in updates:
            # Map frontend status to DB status
            status_map = {
                'scheduled': 'SCHEDULED',
                'missed': 'MISSED',
                'completed': 'COMPLETED',
                'cancelled': 'CANCELLED',
                'rescheduled': 'NEEDS_REBOOK',
            }
            db_updates['status'] = status_map.get(updates['status'].lower(), updates['status'].upper())
        if 'notes' in updates:
            db_updates['notes'] = updates['notes']
        if 'appointment_type' in updates:
            db_updates['specialist_type'] = updates['appointment_type'].upper()
            
        db_updates['updated_at'] = datetime.utcnow().isoformat()
        
        result = (
            self.client.table("referrals")
            .update(db_updates)
            .eq("id", str(appointment_id))
            .execute()
        )
        return transform_referral_to_appointment(result.data[0]) if result.data else None
    
    async def mark_appointment_missed(self, appointment_id: UUID) -> Optional[dict]:
        """Mark an appointment as missed."""
        return await self.update_appointment(appointment_id, {"status": "missed"})
    
    async def reschedule_appointment(
        self, 
        appointment_id: UUID, 
        new_datetime: datetime,
        reason: Optional[str] = None
    ) -> Optional[dict]:
        """Reschedule an appointment to a new time."""
        updates = {
            'scheduled_date': new_datetime.isoformat(),
            'status': 'SCHEDULED',  # Reset to scheduled
            'notes': reason,
            'updated_at': datetime.utcnow().isoformat(),
        }
        result = (
            self.client.table("referrals")
            .update(updates)
            .eq("id", str(appointment_id))
            .execute()
        )
        return transform_referral_to_appointment(result.data[0]) if result.data else None
    
    # ============ CALL ATTEMPTS (via call_logs) ============
    
    async def create_call_attempt(self, call_data: dict) -> dict:
        """Create a new call attempt record."""
        # Get referral to get phone number
        referral_id = call_data.get('appointment_id') or call_data.get('referral_id')
        referral = await self.get_appointment(referral_id)
        
        call_log_data = {
            'referral_id': str(referral_id),
            'call_type': 'MISSED_APPOINTMENT_FOLLOWUP',
            'phone_number': referral.get('patient_phone') if referral else '',
            'status': 'SCHEDULED',
        }
        
        result = self.client.table("call_logs").insert(call_log_data).execute()
        return transform_call_log_to_attempt(result.data[0]) if result.data else None
    
    async def get_call_attempt(self, call_id: UUID) -> Optional[dict]:
        """Get a call attempt by ID."""
        try:
            result = (
                self.client.table("call_logs")
                .select("*, referrals(*)")
                .eq("id", str(call_id))
                .single()
                .execute()
            )
            if result.data:
                referral = result.data.pop('referrals', None)
                return transform_call_log_to_attempt(result.data, referral)
        except Exception:
            pass
        return None
    
    async def get_call_by_elevenlabs_id(self, elevenlabs_call_id: str) -> Optional[dict]:
        """Get a call attempt by ElevenLabs/Twilio call ID."""
        try:
            result = (
                self.client.table("call_logs")
                .select("*, referrals(*)")
                .eq("twilio_call_sid", elevenlabs_call_id)
                .single()
                .execute()
            )
            if result.data:
                referral = result.data.pop('referrals', None)
                return transform_call_log_to_attempt(result.data, referral)
        except Exception:
            pass
        return None
    
    async def update_call_attempt(self, call_id: UUID, updates: dict) -> Optional[dict]:
        """Update a call attempt record."""
        # Transform field names
        db_updates = {}
        if 'status' in updates:
            status_map = {
                'pending': 'SCHEDULED',
                'in_progress': 'IN_PROGRESS',
                'completed': 'COMPLETED',
                'failed': 'FAILED',
                'no_answer': 'NO_ANSWER',
            }
            db_updates['status'] = status_map.get(updates['status'].lower(), updates['status'].upper())
        if 'elevenlabs_call_id' in updates:
            db_updates['twilio_call_sid'] = updates['elevenlabs_call_id']
        if 'started_at' in updates:
            db_updates['scheduled_at'] = updates['started_at']
        if 'ended_at' in updates:
            db_updates['completed_at'] = updates['ended_at']
        if 'transcript' in updates:
            db_updates['transcript'] = updates['transcript']
        if 'outcome' in updates:
            db_updates['resolution'] = updates['outcome'].upper()
            
        result = (
            self.client.table("call_logs")
            .update(db_updates)
            .eq("id", str(call_id))
            .execute()
        )
        return transform_call_log_to_attempt(result.data[0]) if result.data else None
    
    async def get_pending_calls(self) -> List[dict]:
        """Get all pending call attempts."""
        result = (
            self.client.table("call_logs")
            .select("*, referrals(*)")
            .in_("status", ["SCHEDULED", "IN_PROGRESS"])
            .execute()
        )
        calls = []
        for row in (result.data or []):
            referral = row.pop('referrals', None)
            calls.append(transform_call_log_to_attempt(row, referral))
        return calls
    
    # ============ FLAGS (via alerts) ============
    
    async def create_flag(self, flag_data: dict) -> dict:
        """Create a new flag (alert) for nurse follow-up."""
        alert_data = {
            'referral_id': str(flag_data.get('patient_id') or flag_data.get('appointment_id')),
            'user_id': str(flag_data.get('created_by')) if flag_data.get('created_by') else None,
            'alert_type': (flag_data.get('flag_type') or 'FOLLOW_UP_REQUIRED').upper(),
            'message': flag_data.get('description') or flag_data.get('title') or 'Follow-up required',
            'is_dismissed': False,
        }
        
        result = self.client.table("alerts").insert(alert_data).execute()
        if result.data:
            # Fetch the referral to include in response
            referral_data = await self.get_appointment(alert_data['referral_id'])
            return transform_alert_to_flag(result.data[0], referral_data)
        return None
    
    async def get_flags(self, status: Optional[str] = None) -> List[dict]:
        """Get all flags (alerts), optionally filtered by status."""
        query = self.client.table("alerts").select("*, referrals(*)")
        
        if status:
            if status == 'open':
                query = query.eq("is_dismissed", False)
            elif status == 'resolved' or status == 'dismissed':
                query = query.eq("is_dismissed", True)
        
        result = query.order("created_at", desc=True).execute()
        
        flags = []
        for row in (result.data or []):
            referral = row.pop('referrals', None)
            flags.append(transform_alert_to_flag(row, referral))
        return flags
    
    async def get_open_flags(self) -> List[dict]:
        """Get all open flags for nurse dashboard."""
        return await self.get_flags(status='open')
    
    async def update_flag(self, flag_id: UUID, updates: dict) -> Optional[dict]:
        """Update a flag (alert)."""
        db_updates = {}
        
        if 'status' in updates:
            status = updates['status'].lower()
            if status in ['dismissed', 'resolved']:
                db_updates['is_dismissed'] = True
            elif status == 'open':
                db_updates['is_dismissed'] = False
        
        if 'resolution_notes' in updates:
            db_updates['message'] = updates.get('resolution_notes')
            
        result = (
            self.client.table("alerts")
            .update(db_updates)
            .eq("id", str(flag_id))
            .execute()
        )
        if result.data:
            return transform_alert_to_flag(result.data[0])
        return None
    
    async def resolve_flag(
        self, 
        flag_id: UUID, 
        resolved_by: UUID, 
        resolution_notes: Optional[str] = None
    ) -> Optional[dict]:
        """Mark a flag as resolved."""
        updates = {
            'is_dismissed': True,
        }
        result = (
            self.client.table("alerts")
            .update(updates)
            .eq("id", str(flag_id))
            .execute()
        )
        if result.data:
            return transform_alert_to_flag(result.data[0])
        return None
    
    # ============ USERS ============
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email."""
        try:
            result = (
                self.client.table("users")
                .select("*")
                .eq("email", email)
                .single()
                .execute()
            )
            return result.data
        except Exception:
            return None
    
    async def create_user(self, user_data: dict) -> Optional[dict]:
        """Create a new user."""
        result = self.client.table("users").insert(user_data).execute()
        return result.data[0] if result.data else None


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
