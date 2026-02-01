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


def transform_flag_response(flag_data: dict) -> dict:
    """
    Transform flag data from Supabase to include patient and appointment info.

    Args:
        flag_data: Raw flag data from database with referrals join

    Returns:
        Transformed flag data ready for FlagResponse model
    """
    # Keep referral data for frontend access
    referral = flag_data.get("referrals", None)

    # Make sure we preserve the referrals object in the response
    if referral:
        flag_data["referrals"] = referral
        
        # Add flattened patient info for backwards compatibility
        patient_name = referral.get("patient_name", "")
        if patient_name:
            parts = patient_name.strip().split(None, 1)
            flag_data["patient"] = {
                "first_name": parts[0] if parts else "",
                "last_name": parts[1] if len(parts) > 1 else ""
            }

        # Add appointment info
        if referral.get("scheduled_date"):
            flag_data["appointment"] = {
                "scheduled_date": referral["scheduled_date"],
                "status": referral.get("status")
            }
    else:
        # If no referral data, ensure referrals key exists (for consistency)
        flag_data["referrals"] = None

    return flag_data


@router.get("/", response_model=List[FlagResponse])
async def list_flags(
    status: Optional[FlagStatus] = Query(None, description="Filter by status"),
    priority: Optional[FlagPriority] = Query(None, description="Filter by priority"),
    referral_id: Optional[UUID] = Query(None, description="Filter by referral"),
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

    # Filter by priority if specified
    if priority:
        flags = [f for f in flags if f.get("priority") == priority.value]

    # Filter by referral_id if specified
    if referral_id:
        flags = [f for f in flags if f.get("referral_id") == str(referral_id)]

    # Transform flags to include patient/appointment data
    transformed_flags = [transform_flag_response(dict(flag)) for flag in flags]

    return transformed_flags[offset:offset + limit]


@router.get("/open", response_model=List[FlagResponse])
async def list_open_flags():
    """
    Get all open flags for the nurse dashboard.

    This is the primary endpoint for the Flags page,
    showing all items that need nurse attention.
    """
    db = get_supabase_client()
    flags = await db.get_open_flags()

    # Transform flags to include patient/appointment data
    return [transform_flag_response(dict(flag)) for flag in flags]


@router.post("/", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(flag: FlagCreate):
    """
    Create a new flag for nurse follow-up.

    Flags can be created:
    - Automatically by webhook handler when call fails
    - Manually by nurse for any referral concern
    """
    db = get_supabase_client()

    # Verify referral exists
    referral = await db.get_referral(flag.referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {flag.referral_id} not found"
        )

    flag_data = flag.model_dump()
    flag_data["referral_id"] = str(flag.referral_id)
    if flag_data.get("created_by_id"):
        flag_data["created_by_id"] = str(flag_data["created_by_id"])
    flag_data["status"] = "open"
    flag_data["priority"] = flag.priority.value

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

    flag = await db.get_flag(flag_id)

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )

    return transform_flag_response(dict(flag))


@router.patch("/{flag_id}", response_model=FlagResponse)
async def update_flag(flag_id: UUID, updates: FlagUpdate):
    """
    Update a flag.

    For resolving flags, prefer the /resolve endpoint.
    """
    db = get_supabase_client()

    update_data = updates.model_dump(exclude_unset=True)
    # Convert enum values to strings if present
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]
    if "priority" in update_data and update_data["priority"]:
        update_data["priority"] = update_data["priority"].value if hasattr(update_data["priority"], "value") else update_data["priority"]

    updated = await db.update_flag(flag_id, update_data)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )

    # Fetch the updated flag with referral data
    flag = await db.get_flag(flag_id)
    return transform_flag_response(dict(flag))


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

    # Fetch the updated flag with referral data
    flag = await db.get_flag(flag_id)
    return transform_flag_response(dict(flag))


@router.post("/{flag_id}/dismiss", response_model=FlagResponse)
async def dismiss_flag(flag_id: UUID, reason: Optional[str] = None):
    """
    Dismiss a flag without resolving it.

    Used when flag is no longer relevant or was created in error.
    """
    db = get_supabase_client()

    updates = {
        "status": "dismissed",
        "resolution_notes": reason
    }

    updated = await db.update_flag(flag_id, updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag {flag_id} not found"
        )

    # Fetch the updated flag with referral data
    flag = await db.get_flag(flag_id)
    return transform_flag_response(dict(flag))
