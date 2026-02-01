"""
Emails router.

Provides endpoints to send transactional emails to patients and view email logs.
Integrates with SendGrid for email delivery and Supabase for logging.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import (
    EmailLogCreate,
    EmailLogResponse,
    EmailType,
    EmailStatus
)
from services import get_supabase_client, get_email_service

router = APIRouter()


@router.get("/", response_model=List[EmailLogResponse])
async def list_email_logs(
    referral_id: Optional[UUID] = Query(None, description="Filter by referral"),
    status: Optional[EmailStatus] = Query(None, description="Filter by email status"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    List email logs with optional filters.

    Used to view email history for referrals.
    """
    db = get_supabase_client()

    if referral_id:
        emails = await db.get_email_logs_by_referral(referral_id)
        return emails[:limit]
    elif status and status == EmailStatus.PENDING:
        emails = await db.get_pending_emails(limit)
        return emails
    else:
        # Return empty list or implement general listing
        # TODO: Implement general email listing with filters
        return []


@router.post("/send", response_model=EmailLogResponse, status_code=status.HTTP_201_CREATED)
async def send_email(email_request: EmailLogCreate):
    """
    Send an email to a patient.

    Workflow:
    1. Create email_log record in database (status: pending)
    2. Fetch referral details
    3. Send email via SendGrid
    4. Update email_log with SendGrid message_id and status
    5. Return email log record
    """
    db = get_supabase_client()
    email_service = get_email_service()

    # Verify referral exists
    referral = await db.get_referral(email_request.referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {email_request.referral_id} not found"
        )

    # Create email log record
    email_data = {
        "referral_id": str(email_request.referral_id),
        "email_type": email_request.email_type.value,
        "recipient_email": email_request.recipient_email,
        "subject": email_request.subject,
        "status": EmailStatus.PENDING.value,
        "calendar_invite_attached": email_request.calendar_invite_attached
    }
    email_log = await db.create_email_log(email_data)

    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email log record"
        )

    try:
        # Prepare context based on email type
        context = {
            "patient_name": referral["patient_name"],
            "specialist_type": referral.get("specialist_type", "specialist"),
            "condition": referral.get("condition", ""),
            "urgency": referral.get("urgency", "ROUTINE"),
            "scheduled_date": None
        }

        # Parse scheduled_date if present
        if referral.get("scheduled_date"):
            try:
                context["scheduled_date"] = datetime.fromisoformat(referral["scheduled_date"].replace('Z', '+00:00'))
            except:
                pass

        # Send email based on type
        result = None
        if email_request.email_type == EmailType.REFERRAL_CREATED:
            result = await email_service.send_referral_created_email(
                to_email=email_request.recipient_email,
                patient_name=context["patient_name"],
                specialist_type=context["specialist_type"],
                condition=context["condition"],
                urgency=context["urgency"],
                scheduled_date=context["scheduled_date"]
            )
        elif email_request.email_type == EmailType.APPOINTMENT_REMINDER:
            if context["scheduled_date"]:
                result = await email_service.send_appointment_reminder_email(
                    to_email=email_request.recipient_email,
                    patient_name=context["patient_name"],
                    appointment_datetime=context["scheduled_date"],
                    specialist_type=context["specialist_type"]
                )
        elif email_request.email_type == EmailType.APPOINTMENT_CONFIRMED:
            if context["scheduled_date"]:
                result = await email_service.send_appointment_confirmed_email(
                    to_email=email_request.recipient_email,
                    patient_name=context["patient_name"],
                    appointment_datetime=context["scheduled_date"],
                    specialist_type=context["specialist_type"],
                    calendar_attached=email_request.calendar_invite_attached
                )
        elif email_request.email_type == EmailType.FOLLOW_UP:
            result = await email_service.send_follow_up_email(
                to_email=email_request.recipient_email,
                patient_name=context["patient_name"],
                specialist_type=context["specialist_type"],
                scheduled_date=context["scheduled_date"]
            )

        if not result or not result.get("success"):
            raise Exception(result.get("error", "Unknown error") if result else "Email service returned no result")

        # Update email log with success
        await db.update_email_log(
            email_log["id"],
            {
                "status": EmailStatus.SENT.value,
                "sendgrid_message_id": result.get("message_id"),
                "sent_at": datetime.now().isoformat()
            }
        )

        # Refresh and return
        updated_log = await db.get_email_log(email_log["id"]) if hasattr(db, 'get_email_log') else email_log
        return updated_log if updated_log else email_log

    except Exception as e:
        # Update email log as failed
        await db.update_email_log(
            email_log["id"],
            {
                "status": EmailStatus.FAILED.value,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.get("/{email_id}", response_model=EmailLogResponse)
async def get_email_log(email_id: UUID):
    """Get a specific email log by ID."""
    db = get_supabase_client()

    # Fetch email log directly from table
    try:
        result = db.client.table("email_logs").select("*").eq("id", str(email_id)).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
    except Exception as e:
        print(f"Error getting email log {email_id}: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Email log {email_id} not found"
    )


@router.post("/send-bulk", status_code=status.HTTP_202_ACCEPTED)
async def send_bulk_emails(email_type: EmailType, referral_ids: List[UUID]):
    """
    Queue bulk emails for multiple referrals.

    This endpoint creates email log records in pending status.
    A background worker would process these asynchronously.

    For now, this is a placeholder for future implementation.
    """
    db = get_supabase_client()
    created_count = 0

    for referral_id in referral_ids:
        referral = await db.get_referral(referral_id)
        if not referral or not referral.get("patient_email"):
            continue

        email_data = {
            "referral_id": str(referral_id),
            "email_type": email_type.value,
            "recipient_email": referral["patient_email"],
            "subject": f"{email_type.value.replace('_', ' ').title()}",
            "status": EmailStatus.PENDING.value,
            "calendar_invite_attached": False
        }

        result = await db.create_email_log(email_data)
        if result:
            created_count += 1

    return {
        "message": f"Queued {created_count} emails for sending",
        "queued_count": created_count,
        "total_requested": len(referral_ids)
    }
