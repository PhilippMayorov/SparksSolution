"""
Calendar router.

Manages Google Calendar synchronization for appointments.
Provides endpoints to manually sync and check sync status.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from models.schemas import CalendarEventCreate, CalendarEventResponse, CalendarSyncStatus
from services import get_supabase_client, get_calendar_service

router = APIRouter()


@router.post("/sync/{appointment_id}", response_model=CalendarEventResponse)
async def sync_appointment_to_calendar(appointment_id: UUID):
    """
    Sync a single appointment to Google Calendar.
    
    Creates a new event if one doesn't exist,
    or updates the existing event if it does.
    
    Returns the Google Calendar event details.
    """
    db = get_supabase_client()
    calendar = get_calendar_service()
    
    # Get appointment with patient details
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    patient = appointment.get("patients")  # From join
    if not patient:
        patient = await db.get_patient(appointment["patient_id"])
    
    patient_name = f"{patient['first_name']} {patient['last_name']}"
    
    try:
        if appointment.get("google_event_id"):
            # Update existing event
            result = await calendar.update_appointment_event(
                google_event_id=appointment["google_event_id"],
                scheduled_at=appointment["scheduled_at"],
                duration_minutes=appointment.get("duration_minutes", 30),
                appointment_type=appointment.get("appointment_type"),
                patient_name=patient_name,
                notes=appointment.get("notes"),
                send_update=True
            )
        else:
            # Create new event
            result = await calendar.create_appointment_event(
                appointment_id=appointment_id,
                patient_name=patient_name,
                patient_email=patient.get("email"),
                appointment_type=appointment.get("appointment_type", "Appointment"),
                scheduled_at=appointment["scheduled_at"],
                duration_minutes=appointment.get("duration_minutes", 30),
                notes=appointment.get("notes"),
                send_invite=True
            )
            
            # Save Google event ID to appointment
            await db.update_appointment(
                appointment_id,
                {"google_event_id": result["google_event_id"]}
            )
        
        # Update calendar sync record
        sync_data = {
            "appointment_id": str(appointment_id),
            "google_event_id": result["google_event_id"],
            "last_synced_at": "now()",
            "status": "synced"
        }
        
        existing_sync = await db.get_calendar_sync(appointment_id)
        if existing_sync:
            await db.update_calendar_sync(appointment_id, sync_data)
        else:
            await db.create_calendar_sync(sync_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync to calendar: {str(e)}"
        )


@router.get("/sync-status/{appointment_id}", response_model=CalendarSyncStatus)
async def get_sync_status(appointment_id: UUID):
    """
    Get the calendar sync status for an appointment.
    
    Shows whether the appointment is synced to Google Calendar
    and when it was last updated.
    """
    db = get_supabase_client()
    
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    sync_record = await db.get_calendar_sync(appointment_id)
    
    return {
        "appointment_id": appointment_id,
        "synced": bool(appointment.get("google_event_id")),
        "google_event_id": appointment.get("google_event_id"),
        "last_synced_at": sync_record.get("last_synced_at") if sync_record else None,
        "error": sync_record.get("error") if sync_record else None
    }


@router.delete("/event/{appointment_id}")
async def remove_calendar_event(appointment_id: UUID):
    """
    Remove a Google Calendar event for an appointment.
    
    Used when an appointment is cancelled.
    """
    db = get_supabase_client()
    calendar = get_calendar_service()
    
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    if not appointment.get("google_event_id"):
        return {"message": "No calendar event to remove"}
    
    try:
        await calendar.cancel_event(
            appointment["google_event_id"],
            send_cancellation=True
        )
        
        # Clear event ID from appointment
        await db.update_appointment(appointment_id, {"google_event_id": None})
        
        # Update sync record
        await db.update_calendar_sync(appointment_id, {
            "status": "removed",
            "google_event_id": None
        })
        
        return {"message": "Calendar event removed"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove calendar event: {str(e)}"
        )


@router.post("/bulk-sync")
async def bulk_sync_appointments(appointment_ids: List[UUID] = None):
    """
    Sync multiple appointments to Google Calendar.
    
    If no IDs provided, syncs all unsynced appointments.
    
    TODO: Implement batch processing for large numbers.
    """
    db = get_supabase_client()
    
    # TODO: Implement bulk sync logic
    # - Get all appointments without google_event_id
    # - Create events in batches
    # - Handle rate limiting
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bulk sync not yet implemented"
    )
