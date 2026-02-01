"""
Flags router.

Manages nurse follow-up flags for patients who need attention.
Flags are created automatically when:
- A call attempt fails to reschedule
- Manual review is needed
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import (
    FlagCreate,
    FlagUpdate,
    FlagResponse,
    FlagStatus,
    FlagPriority
)
from services import get_supabase_client

router = APIRouter()


@router.get("/", response_model=List[FlagResponse])
async def list_flags(
    status: Optional[FlagStatus] = Query(None, description="Filter by status"),
    priority: Optional[FlagPriority] = Query(None, description="Filter by priority"),
    patient_id: Optional[UUID] = Query(None, description="Filter by patient"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List flags with optional filters.
    
    Used by nurse dashboard to show items requiring follow-up.
    Default sorting: priority (desc), then created_at (desc)
    """
    db = get_supabase_client()
    
    if status:
        flags = await db.get_flags(status=status.value)
    else:
        flags = await db.get_flags()
    
    # TODO: Add priority and patient_id filtering
    return flags


@router.get("/open", response_model=List[FlagResponse])
async def list_open_flags():
    """
    Get all open flags for the nurse dashboard.
    
    This is the primary endpoint for the Flags page,
    showing all items that need nurse attention.
    """
    db = get_supabase_client()
    return await db.get_open_flags()


@router.post("/", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(flag: FlagCreate):
    """
    Create a new flag for nurse follow-up.
    
    Flags can be created:
    - Automatically by webhook handler when call fails
    - Manually by nurse for any patient concern
    """
    db = get_supabase_client()
    
    # Verify patient exists
    patient = await db.get_patient(flag.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {flag.patient_id} not found"
        )
    
    # Verify appointment exists if provided
    if flag.appointment_id:
        appointment = await db.get_appointment(flag.appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {flag.appointment_id} not found"
            )
    
    flag_data = flag.model_dump()
    flag_data["patient_id"] = str(flag.patient_id)
    flag_data["appointment_id"] = str(flag.appointment_id) if flag.appointment_id else None
    flag_data["status"] = FlagStatus.OPEN.value
    
    created = await db.create_flag(flag_data)
    
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create flag"
        )
    
    return created


@router.get("/{flag_id}", response_model=FlagResponse)
async def get_flag(flag_id: UUID):
    """Get a specific flag by ID."""
    db = get_supabase_client()
    
    # TODO: Implement get_flag method in supabase_client
    flags = await db.get_flags()
    flag = next((f for f in flags if f["id"] == str(flag_id)), None)
    
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )
    
    return flag


@router.patch("/{flag_id}", response_model=FlagResponse)
async def update_flag(flag_id: UUID, updates: FlagUpdate):
    """
    Update a flag.
    
    For resolving flags, prefer the /resolve endpoint.
    """
    db = get_supabase_client()
    
    update_data = updates.model_dump(exclude_unset=True)
    updated = await db.update_flag(flag_id, update_data)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )
    
    return updated


@router.post("/{flag_id}/resolve", response_model=FlagResponse)
async def resolve_flag(
    flag_id: UUID,
    resolution_notes: Optional[str] = None,
    resolved_by: Optional[UUID] = None  # TODO: Get from auth
):
    """
    Mark a flag as resolved.
    
    Called when nurse has addressed the follow-up item.
    Typically after:
    - Successful manual call to patient
    - Appointment rescheduled through other means
    - Issue no longer relevant
    """
    db = get_supabase_client()
    
    # TODO: Get resolved_by from authenticated user
    if not resolved_by:
        resolved_by = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
    
    resolved = await db.resolve_flag(flag_id, resolved_by, resolution_notes)
    
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )
    
    return resolved


@router.post("/{flag_id}/dismiss", response_model=FlagResponse)
async def dismiss_flag(flag_id: UUID, reason: Optional[str] = None):
    """
    Dismiss a flag without resolving it.
    
    Used when flag is no longer relevant or was created in error.
    """
    db = get_supabase_client()
    
    updates = {
        "status": FlagStatus.DISMISSED.value,
        "resolution_notes": reason
    }
    
    updated = await db.update_flag(flag_id, updates)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )
    
    return updated
