"""
Calls router.

Manages outbound call attempts via ElevenLabs.
Provides endpoints to initiate calls and check call status.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import CallLogCreate, CallLogResponse, CallStatus
from services import get_supabase_client, get_elevenlabs_service

router = APIRouter()


@router.get("/", response_model=List[CallLogResponse])
async def list_call_logs(
    status: Optional[CallStatus] = Query(None, description="Filter by call status"),
    referral_id: Optional[UUID] = Query(None, description="Filter by referral"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    List call logs with optional filters.

    Used to view call history and pending calls.
    """
    db = get_supabase_client()

    if referral_id:
        calls = await db.get_calls_by_referral(referral_id)
    elif status and status == CallStatus.SCHEDULED:
        calls = await db.get_pending_calls()
    else:
        # TODO: Implement general call listing with filters
        calls = []

    return calls


@router.post("/initiate", response_model=CallLogResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(call_request: CallLogCreate):
    """
    Initiate an outbound call to a patient.

    Workflow:
    1. Create call_log record in database (status: scheduled)
    2. Fetch referral details
    3. Call ElevenLabs API to initiate outbound call
    4. Update call_log with Twilio call_sid
    5. Return call log record

    The ElevenLabs agent will:
    - Greet the patient
    - Explain the missed appointment
    - Attempt to schedule a new time
    - Report outcome via webhook
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()

    # Verify referral exists and is missed
    referral = await db.get_referral(call_request.referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral {call_request.referral_id} not found"
        )

    if referral.get("status") != "MISSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only initiate calls for missed referrals. Current status: {referral.get('status')}"
        )

    # Verify phone number exists
    if not call_request.phone_number:
        if not referral.get("patient_phone"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No phone number provided and referral has no patient_phone"
            )
        phone_number = referral["patient_phone"]
    else:
        phone_number = call_request.phone_number

    # Create call log record
    call_data = {
        "referral_id": str(call_request.referral_id),
        "call_type": call_request.call_type.value,
        "phone_number": phone_number,
        "status": CallStatus.SCHEDULED.value
    }
    call_log = await db.create_call_log(call_data)

    if not call_log:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create call log record"
        )

    try:
        # Initiate call via ElevenLabs
        elevenlabs_response = await elevenlabs.initiate_outbound_call(
            phone_number=phone_number,
            patient_name=referral["patient_name"],
            referral_id=call_request.referral_id,
            specialist_type=referral.get("specialist_type", "specialist"),
            original_datetime=referral.get("scheduled_date"),
            call_log_id=call_log["id"]
        )

        # Update call log with Twilio call SID
        await db.update_call_log(
            call_log["id"],
            {
                "twilio_call_sid": elevenlabs_response.get("call_sid"),
                "status": CallStatus.IN_PROGRESS.value,
                "scheduled_at": datetime.now().isoformat()
            }
        )

        # Refresh and return
        return await db.get_call_log(call_log["id"])

    except Exception as e:
        # Update call log as failed
        await db.update_call_log(
            call_log["id"],
            {"status": CallStatus.FAILED.value}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.get("/{call_id}", response_model=CallLogResponse)
async def get_call_log(call_id: UUID):
    """Get a specific call log by ID."""
    db = get_supabase_client()
    call = await db.get_call_log(call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call log {call_id} not found"
        )

    return call


@router.get("/{call_id}/status")
async def get_call_status(call_id: UUID):
    """
    Get real-time status of an ongoing call.

    Queries ElevenLabs/Twilio API for current call status.
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()

    call = await db.get_call_log(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call log {call_id} not found"
        )

    if not call.get("twilio_call_sid"):
        return {"status": call["status"], "message": "Call not yet initiated"}

    try:
        call_status = await elevenlabs.get_call_status(call["twilio_call_sid"])
        return {
            "status": call["status"],
            "call_status": call_status
        }
    except Exception as e:
        return {
            "status": call["status"],
            "error": str(e)
        }


@router.post("/{call_id}/cancel")
async def cancel_call(call_id: UUID):
    """
    Cancel an ongoing call.

    Only possible for calls in scheduled or in_progress status.
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()

    call = await db.get_call_log(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call log {call_id} not found"
        )

    if call["status"] not in [CallStatus.SCHEDULED.value, CallStatus.IN_PROGRESS.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel scheduled or in-progress calls"
        )

    # Cancel with ElevenLabs/Twilio if in progress
    if call.get("twilio_call_sid") and call["status"] == CallStatus.IN_PROGRESS.value:
        try:
            await elevenlabs.cancel_call(call["twilio_call_sid"])
        except Exception as e:
            print(f"Failed to cancel call: {e}")

    # Update our record
    await db.update_call_log(call_id, {"status": CallStatus.FAILED.value})

    return {"message": "Call cancelled"}
