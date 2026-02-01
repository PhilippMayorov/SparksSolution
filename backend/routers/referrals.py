"""
Referrals router.

CRUD operations for patient referrals.
Handles creation, scheduling, rescheduling, and status updates.
"""

from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status # type: ignore

from models.schemas import (
    ReferralCreate,
    ReferralUpdate,
    ReferralResponse,
    ReferralReschedule,
    ReferralSchedule,
    ReferralStatus,
    SpecialistType,
    DashboardStats,
    StatusHistoryResponse,
    EmailType,
    EmailStatus
)
from services import get_supabase_client, get_email_service

router = APIRouter()


@router.get("/", response_model=List[ReferralResponse])
async def list_referrals(
    date: Optional[date] = Query(None, description="Filter by scheduled date (YYYY-MM-DD)"),
    status: Optional[ReferralStatus] = Query(None, description="Filter by status"),
    specialist_type: Optional[SpecialistType] = Query(None, description="Filter by specialist type"),
    is_high_risk: Optional[bool] = Query(None, description="Filter by high risk flag"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List referrals with optional filters.

    Used by the dashboard to show daily/weekly referrals and calendar view.
    """
    db = get_supabase_client()

    if date:
        # Get referrals scheduled for specific date
        referrals = await db.get_referrals_by_date(date)
    elif status:
        # Get referrals by status
        referrals = await db.get_referrals_by_status(status.value)
    else:
        # Get all referrals with filters
        referrals = await db.get_referrals(
            limit=limit,
            offset=offset,
            specialist_type=specialist_type.value if specialist_type else None,
            is_high_risk=is_high_risk
        )

    return referrals


@router.post("/", response_model=ReferralResponse, status_code=status.HTTP_201_CREATED)
async def create_referral(referral: ReferralCreate):
    """
    Create a new referral.

    Creates a patient referral record with status PENDING.
    After creation, can be scheduled via the /schedule endpoint.
    """
    db = get_supabase_client()

    try:
        # Convert Pydantic model to dict
        referral_data = referral.model_dump()

        # Convert enums to strings
        referral_data["specialist_type"] = referral.specialist_type.value
        referral_data["urgency"] = referral.urgency.value
        referral_data["status"] = ReferralStatus.PENDING.value
        referral_data["created_by_id"] = str(referral.created_by_id)

        # Convert date to string
        referral_data["referral_date"] = referral.referral_date.isoformat()
        if referral.patient_dob:
            referral_data["patient_dob"] = referral.patient_dob.isoformat()
        if referral.scheduled_date:
            referral_data["scheduled_date"] = referral.scheduled_date.isoformat()

        print(f"DEBUG: Attempting to create referral with data: {referral_data}")

        # Try to create the referral
        created = await db.create_referral(referral_data)

        # Optionally send referral created email to patient
        if created.get("patient_email"):
            try:
                email_service = get_email_service()
                scheduled_datetime = None
                if created.get("scheduled_date"):
                    try:
                        scheduled_datetime = datetime.fromisoformat(created["scheduled_date"].replace('Z', '+00:00'))
                    except:
                        pass

                email_result = await email_service.send_referral_created_email(
                    to_email=created["patient_email"],
                    patient_name=created["patient_name"],
                    specialist_type=created["specialist_type"],
                    condition=created["condition"],
                    urgency=created["urgency"],
                    scheduled_date=scheduled_datetime
                )

                # Log the email
                if email_result.get("success"):
                    email_log_data = {
                        "referral_id": str(created["id"]),
                        "email_type": EmailType.REFERRAL_CREATED.value,
                        "recipient_email": created["patient_email"],
                        "subject": f"Referral Created - {created['specialist_type']}",
                        "status": EmailStatus.SENT.value,
                        "sendgrid_message_id": email_result.get("message_id"),
                        "calendar_invite_attached": False,
                        "sent_at": datetime.now().isoformat()
                    }
                    await db.create_email_log(email_log_data)
            except Exception as e:
                # Don't fail referral creation if email fails
                print(f"Failed to send referral created email: {e}")

        return created
        
    except Exception as e:
        error_detail = str(e)
        print(f"Error in create_referral: {error_detail}")
        import traceback
        traceback.print_exc()
        
        # Check if it's a foreign key constraint error
        if "created_by_id" in error_detail or "users" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID. Ensure the user exists in the system. Error: {error_detail}"
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create referral: {error_detail}"
        )


@router.get("/{referral_id}", response_model=ReferralResponse)
async def get_referral(referral_id: UUID):
    """Get a specific referral by ID."""
    db = get_supabase_client()
    referral = await db.get_referral(referral_id)

    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    return referral


@router.patch("/{referral_id}", response_model=ReferralResponse)
async def update_referral(referral_id: UUID, updates: ReferralUpdate):
    """
    Update a referral.

    For scheduling, prefer the /schedule endpoint.
    For rescheduling, prefer the /reschedule endpoint.
    """
    db = get_supabase_client()

    # Verify referral exists
    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    update_data = updates.model_dump(exclude_unset=True)

    # Convert enums to strings
    if "specialist_type" in update_data and update_data["specialist_type"]:
        update_data["specialist_type"] = update_data["specialist_type"].value
    if "urgency" in update_data and update_data["urgency"]:
        update_data["urgency"] = update_data["urgency"].value
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    # Convert dates to strings
    if "patient_dob" in update_data and update_data["patient_dob"]:
        update_data["patient_dob"] = update_data["patient_dob"].isoformat()
    if "scheduled_date" in update_data and update_data["scheduled_date"]:
        update_data["scheduled_date"] = update_data["scheduled_date"].isoformat()
    if "completed_date" in update_data and update_data["completed_date"]:
        update_data["completed_date"] = update_data["completed_date"].isoformat()

    updated = await db.update_referral(referral_id, update_data)

    return updated


@router.post("/{referral_id}/schedule", response_model=ReferralResponse)
async def schedule_referral(referral_id: UUID, schedule_data: ReferralSchedule):
    """
    Schedule a pending referral.

    Sets the scheduled_date and updates status to SCHEDULED.
    """
    db = get_supabase_client()

    # Verify referral exists and is pending
    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    if existing.get("status") not in ["PENDING", "NEEDS_REBOOK"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only schedule PENDING or NEEDS_REBOOK referrals. Current status: {existing.get('status')}"
        )

    # Update referral
    updates = {
        "scheduled_date": schedule_data.scheduled_date.isoformat(),
        "status": ReferralStatus.SCHEDULED.value
    }

    if schedule_data.notes:
        # Append to existing notes
        old_notes = existing.get("notes", "")
        updates["notes"] = f"{old_notes}\n\nScheduled: {schedule_data.notes}".strip()

    updated = await db.update_referral(referral_id, updates)

    # Send email confirmation to patient
    if updated.get("patient_email"):
        try:
            email_service = get_email_service()
            # Send email with calendar invite attached
            email_result = await email_service.send_appointment_confirmed_email(
                to_email=updated["patient_email"],
                patient_name=updated["patient_name"],
                appointment_datetime=schedule_data.scheduled_date,
                specialist_type=updated["specialist_type"],
                location=None,  # TODO: Get location from referral or settings
                attach_calendar=True  # Always attach calendar invite for confirmations
            )

            # Log the email in database
            if email_result.get("success"):
                email_log_data = {
                    "referral_id": str(referral_id),
                    "email_type": EmailType.APPOINTMENT_CONFIRMED.value,
                    "recipient_email": updated["patient_email"],
                    "subject": f"Appointment Confirmed - {updated['specialist_type']}",
                    "status": EmailStatus.SENT.value,
                    "sendgrid_message_id": email_result.get("message_id"),
                    "calendar_invite_attached": True,  # iCal invite attached
                    "sent_at": datetime.now().isoformat()
                }
                await db.create_email_log(email_log_data)
            else:
                # Log failed email
                email_log_data = {
                    "referral_id": str(referral_id),
                    "email_type": EmailType.APPOINTMENT_CONFIRMED.value,
                    "recipient_email": updated["patient_email"],
                    "subject": f"Appointment Confirmed - {updated['specialist_type']}",
                    "status": EmailStatus.FAILED.value,
                    "error_message": email_result.get("error", "Unknown error"),
                    "calendar_invite_attached": False
                }
                await db.create_email_log(email_log_data)
        except Exception as e:
            # Don't fail the whole request if email fails
            print(f"Failed to send confirmation email: {e}")

    return updated


@router.post("/{referral_id}/reschedule", response_model=ReferralResponse)
async def reschedule_referral(referral_id: UUID, reschedule: ReferralReschedule):
    """
    Reschedule a referral to a new time.

    This endpoint:
    1. Updates the referral scheduled_date in Supabase
    2. Sends updated invite to patient

    Called by:
    - Nurse manually rescheduling
    - Webhook handler when ElevenLabs agent successfully reschedules
    """
    db = get_supabase_client()

    # Verify referral exists
    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    # Reschedule in database
    old_datetime = None
    if existing.get("scheduled_date"):
        try:
            old_datetime = datetime.fromisoformat(existing["scheduled_date"].replace('Z', '+00:00'))
        except:
            pass

    updated = await db.reschedule_referral(
        referral_id,
        reschedule.new_datetime,
        reschedule.reason
    )

    # Send rescheduled email notification
    if updated.get("patient_email"):
        try:
            email_service = get_email_service()
            # Send email with updated calendar invite
            email_result = await email_service.send_appointment_rescheduled_email(
                to_email=updated["patient_email"],
                patient_name=updated["patient_name"],
                new_datetime=reschedule.new_datetime,
                specialist_type=updated["specialist_type"],
                old_datetime=old_datetime,
                location=None,  # TODO: Get location from referral or settings
                reason=reschedule.reason,
                attach_calendar=True  # Always attach updated calendar invite for reschedules
            )

            # Log the email
            if email_result.get("success"):
                email_log_data = {
                    "referral_id": str(referral_id),
                    "email_type": EmailType.APPOINTMENT_RESCHEDULED.value,
                    "recipient_email": updated["patient_email"],
                    "subject": f"Appointment Rescheduled - {updated['specialist_type']}",
                    "status": EmailStatus.SENT.value,
                    "sendgrid_message_id": email_result.get("message_id"),
                    "calendar_invite_attached": True,  # Updated iCal invite attached
                    "sent_at": datetime.now().isoformat()
                }
                await db.create_email_log(email_log_data)
        except Exception as e:
            print(f"Failed to send reschedule email: {e}")

    return updated


@router.post("/{referral_id}/mark-missed", response_model=ReferralResponse)
async def mark_referral_missed(referral_id: UUID):
    """
    Mark a referral as missed.

    This triggers the automated calling workflow:
    1. Mark referral as missed
    2. Create call log for outbound call

    Typically called by a scheduled job checking for
    referrals past their scheduled_date without check-in.
    """
    db = get_supabase_client()

    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    updated = await db.mark_referral_missed(referral_id)

    # TODO: Automatically trigger outbound call
    # This could be done here or in a background task

    return updated


@router.post("/{referral_id}/mark-attended", response_model=ReferralResponse)
async def mark_referral_attended(referral_id: UUID):
    """
    Mark a referral as attended/completed.

    Called when patient successfully attends the appointment.
    """
    db = get_supabase_client()

    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    updates = {
        "status": ReferralStatus.ATTENDED.value,
        "completed_date": datetime.now().isoformat()
    }

    updated = await db.update_referral(referral_id, updates)

    return updated


@router.delete("/{referral_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_referral(referral_id: UUID):
    """
    Cancel a referral.

    Updates status to cancelled.
    """
    db = get_supabase_client()

    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    # Update status to cancelled
    await db.cancel_referral(referral_id)

    return None


@router.get("/{referral_id}/history", response_model=List[StatusHistoryResponse])
async def get_referral_history(referral_id: UUID):
    """
    Get status change history for a referral.

    Shows all status transitions with timestamps and user who made the change.
    """
    db = get_supabase_client()

    # Verify referral exists
    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    history = await db.get_status_history(referral_id)

    return history


@router.get("/{referral_id}/communications")
async def get_referral_communications(referral_id: UUID):
    """
    Get all communications (calls + emails) for a referral.

    Returns combined log of all call attempts and email sends.
    """
    db = get_supabase_client()

    # Verify referral exists
    existing = await db.get_referral(referral_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {referral_id} not found"
        )

    # Get call logs and email logs
    calls = await db.get_calls_by_referral(referral_id)
    emails = await db.get_email_logs_by_referral(referral_id)

    return {
        "referral_id": str(referral_id),
        "calls": calls,
        "emails": emails
    }


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get dashboard statistics.

    Calls the database function to get aggregated stats:
    - Total active referrals
    - Counts by status
    - Overdue referrals
    - High risk active
    - Unread alerts
    - Pending emails
    """
    db = get_supabase_client()

    stats = await db.get_dashboard_stats()

    if not stats:
        # Return zeros if function fails
        return {
            "total_active": 0,
            "pending_count": 0,
            "scheduled_count": 0,
            "missed_count": 0,
            "escalated_count": 0,
            "high_risk_active": 0,
            "scheduled_this_week": 0,
            "overdue_pending": 0,
            "unread_alerts": 0,
            "emails_pending": 0
        }

    return stats


@router.get("/overdue/list")
async def get_overdue_referrals(days_threshold: int = Query(14, ge=1, le=90)):
    """
    Get overdue referrals.

    Uses database function to find referrals that are:
    - PENDING and older than days_threshold
    - SCHEDULED with past scheduled_date but not ATTENDED
    - NEEDS_REBOOK and not updated in 7 days
    """
    db = get_supabase_client()

    overdue = await db.get_overdue_referrals(days_threshold)

    return overdue
