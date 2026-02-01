"""
Calls router.

Manages outbound call attempts via ElevenLabs.
Provides endpoints to initiate calls and check call status.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import CallAttemptCreate, CallAttemptResponse, CallStatus
from services import get_supabase_client, get_elevenlabs_service

router = APIRouter()


@router.get("/", response_model=List[CallAttemptResponse])
async def list_call_attempts(
    status: Optional[CallStatus] = Query(None, description="Filter by call status"),
    appointment_id: Optional[UUID] = Query(None, description="Filter by appointment"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    List call attempts with optional filters.
    
    Used to view call history and pending calls.
    """
    db = get_supabase_client()
    
    if status and status == CallStatus.PENDING:
        calls = await db.get_pending_calls()
    else:
        # TODO: Implement general call listing with filters
        calls = []
    
    return calls


@router.post("/initiate", response_model=CallAttemptResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(call_request: CallAttemptCreate):
    """
    Initiate an outbound call to a patient.
    
    Workflow:
    1. Create call_attempt record in database (status: pending)
    2. Fetch patient and appointment details
    3. Call ElevenLabs API to initiate outbound call
    4. Update call_attempt with ElevenLabs call_id
    5. Return call attempt record
    
    The ElevenLabs agent will:
    - Greet the patient
    - Explain the missed appointment
    - Attempt to schedule a new time
    - Report outcome via webhook
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()
    
    # Verify appointment exists and is missed
    appointment = await db.get_appointment(call_request.appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {call_request.appointment_id} not found"
        )
    
    if appointment.get("status") != "missed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only initiate calls for missed appointments"
        )
    
    # Get patient details
    patient = await db.get_patient(call_request.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {call_request.patient_id} not found"
        )
    
    # Create call attempt record
    call_data = {
        "appointment_id": str(call_request.appointment_id),
        "patient_id": str(call_request.patient_id),
        "status": CallStatus.PENDING.value
    }
    call_attempt = await db.create_call_attempt(call_data)
    
    if not call_attempt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create call attempt record"
        )
    
    try:
        # Initiate call via ElevenLabs
        elevenlabs_response = await elevenlabs.initiate_outbound_call(
            phone_number=patient["phone"],
            patient_name=f"{patient['first_name']} {patient['last_name']}",
            appointment_id=call_request.appointment_id,
            appointment_type=appointment.get("appointment_type", "appointment"),
            original_datetime=appointment["scheduled_at"],
            call_attempt_id=call_attempt["id"]
        )
        
        # Update call attempt with ElevenLabs call ID
        await db.update_call_attempt(
            call_attempt["id"],
            {
                "elevenlabs_call_id": elevenlabs_response.get("call_id"),
                "status": CallStatus.IN_PROGRESS.value,
                "started_at": "now()"
            }
        )
        
        # Refresh and return
        return await db.get_call_attempt(call_attempt["id"])
        
    except Exception as e:
        # Update call attempt as failed
        await db.update_call_attempt(
            call_attempt["id"],
            {"status": CallStatus.FAILED.value}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.get("/{call_id}", response_model=CallAttemptResponse)
async def get_call_attempt(call_id: UUID):
    """Get a specific call attempt by ID."""
    db = get_supabase_client()
    call = await db.get_call_attempt(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call attempt {call_id} not found"
        )
    
    return call


@router.get("/{call_id}/status")
async def get_call_status(call_id: UUID):
    """
    Get real-time status of an ongoing call.
    
    Queries ElevenLabs API for current call status.
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()
    
    call = await db.get_call_attempt(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call attempt {call_id} not found"
        )
    
    if not call.get("elevenlabs_call_id"):
        return {"status": call["status"], "message": "Call not yet initiated with ElevenLabs"}
    
    try:
        elevenlabs_status = await elevenlabs.get_call_status(call["elevenlabs_call_id"])
        return {
            "status": call["status"],
            "elevenlabs_status": elevenlabs_status
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
    
    Only possible for calls in pending or in_progress status.
    """
    db = get_supabase_client()
    elevenlabs = get_elevenlabs_service()
    
    call = await db.get_call_attempt(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call attempt {call_id} not found"
        )
    
    if call["status"] not in [CallStatus.PENDING.value, CallStatus.IN_PROGRESS.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending or in-progress calls"
        )
    
    # Cancel with ElevenLabs if in progress
    if call.get("elevenlabs_call_id") and call["status"] == CallStatus.IN_PROGRESS.value:
        try:
            await elevenlabs.cancel_call(call["elevenlabs_call_id"])
        except Exception as e:
            print(f"Failed to cancel ElevenLabs call: {e}")
    
    # Update our record
    await db.update_call_attempt(call_id, {"status": CallStatus.FAILED.value})
    
    return {"message": "Call cancelled"}
