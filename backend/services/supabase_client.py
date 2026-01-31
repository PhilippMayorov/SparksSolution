"""
Supabase client service.

Handles all database operations via Supabase Python client.
This is the primary data layer for patients, appointments, calls, and flags.
"""

import os
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


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
    
    # ============ PATIENTS ============
    
    async def create_patient(self, patient_data: dict) -> dict:
        """
        Create a new patient record.
        
        Args:
            patient_data: Patient information including name, phone, email
            
        Returns:
            Created patient record with ID
        """
        # TODO: Implement patient creation
        result = self.client.table("patients").insert(patient_data).execute()
        return result.data[0] if result.data else None
    
    async def get_patient(self, patient_id: UUID) -> Optional[dict]:
        """Get a patient by ID."""
        result = self.client.table("patients").select("*").eq("id", str(patient_id)).single().execute()
        return result.data
    
    async def get_patients(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get all patients with pagination."""
        result = self.client.table("patients").select("*").range(offset, offset + limit - 1).execute()
        return result.data or []
    
    async def update_patient(self, patient_id: UUID, updates: dict) -> Optional[dict]:
        """Update a patient record."""
        result = self.client.table("patients").update(updates).eq("id", str(patient_id)).execute()
        return result.data[0] if result.data else None
    
    # ============ APPOINTMENTS ============
    
    async def create_appointment(self, appointment_data: dict) -> dict:
        """
        Create a new appointment.
        
        Args:
            appointment_data: Appointment details including patient_id, scheduled_at, type
            
        Returns:
            Created appointment record
        """
        # TODO: Validate patient exists
        # TODO: Check for scheduling conflicts
        result = self.client.table("appointments").insert(appointment_data).execute()
        return result.data[0] if result.data else None
    
    async def get_appointment(self, appointment_id: UUID) -> Optional[dict]:
        """Get an appointment by ID with patient details."""
        result = (
            self.client.table("appointments")
            .select("*, patients(*)")
            .eq("id", str(appointment_id))
            .single()
            .execute()
        )
        return result.data
    
    async def get_appointments_by_date(self, date: datetime) -> List[dict]:
        """Get all appointments for a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        result = (
            self.client.table("appointments")
            .select("*, patients(*)")
            .gte("scheduled_at", start_of_day.isoformat())
            .lte("scheduled_at", end_of_day.isoformat())
            .order("scheduled_at")
            .execute()
        )
        return result.data or []
    
    async def get_appointments_by_status(self, status: str) -> List[dict]:
        """Get all appointments with a specific status."""
        result = (
            self.client.table("appointments")
            .select("*, patients(*)")
            .eq("status", status)
            .execute()
        )
        return result.data or []
    
    async def update_appointment(self, appointment_id: UUID, updates: dict) -> Optional[dict]:
        """Update an appointment."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = (
            self.client.table("appointments")
            .update(updates)
            .eq("id", str(appointment_id))
            .execute()
        )
        return result.data[0] if result.data else None
    
    async def mark_appointment_missed(self, appointment_id: UUID) -> Optional[dict]:
        """Mark an appointment as missed. Called when appointment time passes without check-in."""
        return await self.update_appointment(appointment_id, {"status": "missed"})
    
    async def reschedule_appointment(
        self, 
        appointment_id: UUID, 
        new_datetime: datetime,
        reason: Optional[str] = None
    ) -> Optional[dict]:
        """
        Reschedule an appointment to a new time.
        
        Args:
            appointment_id: ID of appointment to reschedule
            new_datetime: New scheduled datetime
            reason: Optional reason for rescheduling
            
        Returns:
            Updated appointment record
        """
        updates = {
            "scheduled_at": new_datetime.isoformat(),
            "status": "rescheduled",
            "notes": reason
        }
        return await self.update_appointment(appointment_id, updates)
    
    # ============ CALL ATTEMPTS ============
    
    async def create_call_attempt(self, call_data: dict) -> dict:
        """Create a new call attempt record."""
        result = self.client.table("call_attempts").insert(call_data).execute()
        return result.data[0] if result.data else None
    
    async def get_call_attempt(self, call_id: UUID) -> Optional[dict]:
        """Get a call attempt by ID."""
        result = (
            self.client.table("call_attempts")
            .select("*, appointments(*), patients(*)")
            .eq("id", str(call_id))
            .single()
            .execute()
        )
        return result.data
    
    async def get_call_by_elevenlabs_id(self, elevenlabs_call_id: str) -> Optional[dict]:
        """Get a call attempt by ElevenLabs call ID (for webhook processing)."""
        result = (
            self.client.table("call_attempts")
            .select("*, appointments(*), patients(*)")
            .eq("elevenlabs_call_id", elevenlabs_call_id)
            .single()
            .execute()
        )
        return result.data
    
    async def update_call_attempt(self, call_id: UUID, updates: dict) -> Optional[dict]:
        """Update a call attempt record."""
        result = (
            self.client.table("call_attempts")
            .update(updates)
            .eq("id", str(call_id))
            .execute()
        )
        return result.data[0] if result.data else None
    
    async def get_pending_calls(self) -> List[dict]:
        """Get all pending call attempts."""
        result = (
            self.client.table("call_attempts")
            .select("*, appointments(*), patients(*)")
            .eq("status", "pending")
            .execute()
        )
        return result.data or []
    
    # ============ FLAGS ============
    
    async def create_flag(self, flag_data: dict) -> dict:
        """Create a new flag for nurse follow-up."""
        result = self.client.table("flags").insert(flag_data).execute()
        return result.data[0] if result.data else None
    
    async def get_flags(self, status: Optional[str] = None) -> List[dict]:
        """Get all flags, optionally filtered by status."""
        query = self.client.table("flags").select("*, patients(*), appointments(*)")
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("priority", desc=True).order("created_at", desc=True).execute()
        return result.data or []
    
    async def get_open_flags(self) -> List[dict]:
        """Get all open flags for nurse dashboard."""
        return await self.get_flags(status="open")
    
    async def update_flag(self, flag_id: UUID, updates: dict) -> Optional[dict]:
        """Update a flag."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = self.client.table("flags").update(updates).eq("id", str(flag_id)).execute()
        return result.data[0] if result.data else None
    
    async def resolve_flag(
        self, 
        flag_id: UUID, 
        resolved_by: UUID, 
        resolution_notes: Optional[str] = None
    ) -> Optional[dict]:
        """Mark a flag as resolved."""
        updates = {
            "status": "resolved",
            "resolved_by": str(resolved_by),
            "resolved_at": datetime.utcnow().isoformat(),
            "resolution_notes": resolution_notes
        }
        return await self.update_flag(flag_id, updates)
    
    # ============ CALENDAR SYNC ============
    
    async def create_calendar_sync(self, sync_data: dict) -> dict:
        """Create a calendar sync record."""
        result = self.client.table("calendar_sync").insert(sync_data).execute()
        return result.data[0] if result.data else None
    
    async def get_calendar_sync(self, appointment_id: UUID) -> Optional[dict]:
        """Get calendar sync status for an appointment."""
        result = (
            self.client.table("calendar_sync")
            .select("*")
            .eq("appointment_id", str(appointment_id))
            .single()
            .execute()
        )
        return result.data
    
    async def update_calendar_sync(self, appointment_id: UUID, updates: dict) -> Optional[dict]:
        """Update calendar sync record."""
        result = (
            self.client.table("calendar_sync")
            .update(updates)
            .eq("appointment_id", str(appointment_id))
            .execute()
        )
        return result.data[0] if result.data else None
    
    # ============ USERS ============
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("email", email)
            .single()
            .execute()
        )
        return result.data


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
