"""
Webhooks router.

Handles incoming webhooks from external services:
- ElevenLabs: Call completion events with outcomes

IMPORTANT: Webhook endpoints must:
1. Verify request authenticity (signature validation)
2. Respond quickly (do heavy processing async)
3. Be idempotent (same webhook may be delivered multiple times)
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header, status, BackgroundTasks

from models.schemas import (
    ElevenLabsWebhookPayload,
    WebhookResponse,
    CallStatus,
    CallOutcome,
    FlagPriority
)
from services import get_supabase_client, get_elevenlabs_service, get_calendar_service

router = APIRouter()


@router.post("/elevenlabs", response_model=WebhookResponse)
async def handle_elevenlabs_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature")
):
    """
    Handle ElevenLabs call completion webhook.
    
    WORKFLOW:
    1. Verify webhook signature
    2. Parse payload and find our call attempt record
    3. Update call attempt with outcome
    4. Based on outcome:
       - SUCCESS (rescheduled): Update appointment + sync calendar
       - FAILURE (declined/no-answer): Create nurse follow-up flag
    
    IMPORTANT: This endpoint should respond quickly.
    Heavy processing is done in background tasks.
    
    Expected Payload (verify against ElevenLabs docs):
    {
        "call_id": "elevenlabs-call-uuid",
        "status": "completed" | "failed" | "no_answer",
        "outcome": "rescheduled" | "declined" | "voicemail" | "callback_requested",
        "new_appointment_time": "2026-02-01T14:00:00Z",  // If rescheduled
        "transcript": "...",
        "duration_seconds": 120,
        "metadata": {
            "appointment_id": "our-appointment-uuid",
            "call_attempt_id": "our-call-attempt-uuid"
        }
    }
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    elevenlabs = get_elevenlabs_service()
    if not elevenlabs.verify_webhook_signature(body, x_webhook_signature or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse payload
    try:
        payload_dict = await request.json()
        payload = ElevenLabsWebhookPayload(**payload_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    
    # Find our call attempt record
    db = get_supabase_client()
    call_attempt = await db.get_call_by_elevenlabs_id(payload.call_id)
    
    if not call_attempt:
        # Log but don't fail - might be a duplicate or test
        print(f"Unknown ElevenLabs call_id: {payload.call_id}")
        return WebhookResponse(success=True, message="Call not found, ignoring")
    
    # Schedule background processing
    background_tasks.add_task(
        process_call_outcome,
        call_attempt=call_attempt,
        payload=payload
    )
    
    # Respond immediately
    return WebhookResponse(success=True, message="Webhook received, processing")


async def process_call_outcome(call_attempt: dict, payload: ElevenLabsWebhookPayload):
    """
    Background task to process call outcome.
    
    Handles:
    - Updating call attempt record
    - Rescheduling appointment (if successful)
    - Creating follow-up flag (if failed)
    - Syncing to Google Calendar (if rescheduled)
    """
    db = get_supabase_client()
    
    # Map ElevenLabs status to our status
    status_map = {
        "completed": CallStatus.COMPLETED.value,
        "failed": CallStatus.FAILED.value,
        "no_answer": CallStatus.NO_ANSWER.value
    }
    
    outcome_map = {
        "rescheduled": CallOutcome.RESCHEDULED.value,
        "declined": CallOutcome.DECLINED.value,
        "voicemail": CallOutcome.VOICEMAIL.value,
        "callback_requested": CallOutcome.CALLBACK_REQUESTED.value,
        "invalid_number": CallOutcome.INVALID_NUMBER.value
    }
    
    # Update call attempt record
    call_update = {
        "status": status_map.get(payload.status, CallStatus.COMPLETED.value),
        "outcome": outcome_map.get(payload.outcome) if payload.outcome else None,
        "ended_at": datetime.utcnow().isoformat(),
        "transcript": payload.transcript
    }
    
    await db.update_call_attempt(call_attempt["id"], call_update)
    
    appointment_id = call_attempt["appointment_id"]
    patient_id = call_attempt["patient_id"]
    
    # Handle based on outcome
    if payload.outcome == "rescheduled" and payload.new_appointment_time:
        # SUCCESS: Patient agreed to reschedule
        await handle_successful_reschedule(
            appointment_id=appointment_id,
            new_datetime=payload.new_appointment_time,
            patient_id=patient_id
        )
    else:
        # FAILURE: Need nurse follow-up
        await create_follow_up_flag(
            appointment_id=appointment_id,
            patient_id=patient_id,
            call_outcome=payload.outcome or payload.status,
            transcript=payload.transcript
        )


async def handle_successful_reschedule(
    appointment_id: str,
    new_datetime: datetime,
    patient_id: str
):
    """
    Handle successful rescheduling by AI agent.
    
    1. Update appointment in Supabase
    2. Update/create Google Calendar event
    """
    db = get_supabase_client()
    calendar = get_calendar_service()
    
    # Update appointment
    appointment = await db.reschedule_appointment(
        appointment_id,
        new_datetime,
        reason="Rescheduled via automated call"
    )
    
    if not appointment:
        print(f"Failed to reschedule appointment {appointment_id}")
        return
    
    # Get patient details for calendar
    patient = await db.get_patient(patient_id)
    patient_name = f"{patient['first_name']} {patient['last_name']}"
    
    # Update or create calendar event
    try:
        if appointment.get("google_event_id"):
            await calendar.update_appointment_event(
                google_event_id=appointment["google_event_id"],
                scheduled_at=new_datetime,
                patient_name=patient_name,
                send_update=True
            )
        else:
            result = await calendar.create_appointment_event(
                appointment_id=appointment_id,
                patient_name=patient_name,
                patient_email=patient.get("email"),
                appointment_type=appointment.get("appointment_type", "Appointment"),
                scheduled_at=new_datetime,
                duration_minutes=appointment.get("duration_minutes", 30),
                send_invite=True
            )
            # Save Google event ID
            await db.update_appointment(
                appointment_id,
                {"google_event_id": result["google_event_id"]}
            )
        
        print(f"Successfully rescheduled appointment {appointment_id} to {new_datetime}")
        
    except Exception as e:
        print(f"Failed to sync calendar for appointment {appointment_id}: {e}")


async def create_follow_up_flag(
    appointment_id: str,
    patient_id: str,
    call_outcome: str,
    transcript: Optional[str] = None
):
    """
    Create a nurse follow-up flag after failed reschedule attempt.
    
    The nurse will see this flag on their dashboard and can
    manually follow up with the patient.
    """
    db = get_supabase_client()
    
    # Determine priority based on outcome
    priority_map = {
        "declined": FlagPriority.HIGH.value,
        "no_answer": FlagPriority.MEDIUM.value,
        "voicemail": FlagPriority.MEDIUM.value,
        "callback_requested": FlagPriority.HIGH.value,
        "invalid_number": FlagPriority.URGENT.value,
        "failed": FlagPriority.HIGH.value
    }
    
    # Build description
    description_parts = [
        f"Automated call outcome: {call_outcome}",
        "Patient needs manual follow-up to reschedule missed appointment."
    ]
    
    if transcript:
        description_parts.append(f"\nCall transcript:\n{transcript[:500]}...")
    
    flag_data = {
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "title": f"Follow-up needed: {call_outcome.replace('_', ' ').title()}",
        "description": "\n".join(description_parts),
        "priority": priority_map.get(call_outcome, FlagPriority.MEDIUM.value),
        "status": "open"
    }
    
    await db.create_flag(flag_data)
    print(f"Created follow-up flag for patient {patient_id}, appointment {appointment_id}")


# Optional: Health check endpoint for webhook URL validation
@router.get("/elevenlabs")
async def elevenlabs_webhook_verify():
    """
    GET endpoint for webhook URL verification.
    
    Some services ping the webhook URL to verify it's valid
    before allowing registration.
    """
    return {"status": "ok", "service": "elevenlabs-webhook"}
