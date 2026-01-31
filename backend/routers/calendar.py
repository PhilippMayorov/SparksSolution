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


@router.post("/sync/{referral_id}", response_model=CalendarEventResponse)
async def sync_referral_to_calendar(referral_id: UUID):
    """
    Sync a single referral to Google Calendar.
    
    Creates a new event if one doesn't exist,
    or updates the existing event if it does.
    
    Returns the Google Calendar event details.
    """
    db = get_supabase_client()
    calendar = get_calendar_service()
    
    # Get referral with patient details
    referral = await db.get_referral(referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )
    
    # Patient info is stored directly in referral
    patient_name = referral.get("patient_name", "Patient")
    patient_email = referral.get("patient_email")
    
    try:
        if referral.get("calendar_event_id"):
            # Update existing event
            result = await calendar.update_appointment_event(
                google_event_id=referral["calendar_event_id"],
                scheduled_at=referral["scheduled_date"],
                duration_minutes=30,
                appointment_type="Specialist Referral",
                patient_name=patient_name,
                notes=referral.get("notes"),
                send_update=True
            )
        else:
            # Create new event
            result = await calendar.create_appointment_event(
                appointment_id=referral_id,
                patient_name=patient_name,
                patient_email=patient_email,
                appointment_type="Specialist Referral",
                scheduled_at=referral["scheduled_date"],
                duration_minutes=30,
                notes=referral.get("notes"),
                send_invite=True
            )
            
            # Save Google event ID to referral
            await db.update_referral(
                referral_id,
                {"calendar_event_id": result["google_event_id"]}
            )
        
        # Update calendar sync record
        sync_data = {
            "referral_id": str(referral_id),
            "google_event_id": result["google_event_id"],
            "last_synced_at": "now()",
            "status": "synced"
        }
        
        existing_sync = await db.get_calendar_sync(referral_id)
        if existing_sync:
            await db.update_calendar_sync(referral_id, sync_data)
        else:
            await db.create_calendar_sync(sync_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync to calendar: {str(e)}"
        )


@router.get("/sync-status/{referral_id}", response_model=CalendarSyncStatus)
async def get_sync_status(referral_id: UUID):
    """
    Get the calendar sync status for a referral.
    
    Shows whether the referral is synced to Google Calendar
    and when it was last updated.
    """
    db = get_supabase_client()
    
    referral = await db.get_referral(referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )
    
    sync_record = await db.get_calendar_sync(referral_id)
    
    return {
        "appointment_id": referral_id,
        "synced": bool(referral.get("calendar_event_id")),
        "google_event_id": referral.get("calendar_event_id"),
        "last_synced_at": sync_record.get("calendar_invite_sent") if sync_record else None,
        "error": None
    }


@router.delete("/event/{referral_id}")
async def remove_calendar_event(referral_id: UUID):
    """
    Remove a Google Calendar event for a referral.
    
    Used when a referral is cancelled.
    """
    db = get_supabase_client()
    calendar = get_calendar_service()
    
    referral = await db.get_referral(referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )
    
    if not referral.get("calendar_event_id"):
        return {"message": "No calendar event to remove"}
    
    try:
        await calendar.cancel_event(
            referral["calendar_event_id"],
            send_cancellation=True
        )
        
        # Clear event ID from referral
        await db.update_referral(referral_id, {"calendar_event_id": None})
        
        # Update sync record
        await db.update_calendar_sync(referral_id, {
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
async def bulk_sync_referrals(referral_ids: List[UUID] = None):
    """
    Sync multiple referrals to Google Calendar.
    
    If no IDs provided, syncs all unsynced referrals.
    
    TODO: Implement batch processing for large numbers.
    """
    db = get_supabase_client()
    
    # TODO: Implement bulk sync logic
    # - Get all referrals without google_event_id
    # - Create events in batches
    # - Handle rate limiting
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bulk sync not yet implemented"
    )
