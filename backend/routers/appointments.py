"""
Appointments router.

CRUD operations for patient appointments.
Handles scheduling, rescheduling, and status updates.
"""

from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentReschedule,
    AppointmentStatus
)
from services import get_supabase_client, get_calendar_service

router = APIRouter()


@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    patient_id: Optional[UUID] = Query(None, description="Filter by patient"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List appointments with optional filters.
    
    Used by the dashboard calendar view to show daily/weekly appointments.
    """
    db = get_supabase_client()
    
    if date:
        appointments = await db.get_appointments_by_date(datetime.combine(date, datetime.min.time()))
    elif status:
        appointments = await db.get_appointments_by_status(status.value)
    else:
        # Return all appointments when no filter is provided
        appointments = await db.get_all_appointments(limit=limit, offset=offset)
    
    return appointments


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(appointment: AppointmentCreate):
    """
    Create a new appointment.
    
    Since patients are embedded in referrals, we'll create a new referral
    with the appointment data. If patient_id is provided, we'll try to
    copy patient info from an existing referral.
    """
    try:

        db = get_supabase_client()

        # Create appointment in database
        appointment_data = appointment.model_dump(mode='json')

        # Sanitize phone number - remove spaces, dashes, parentheses
        if appointment_data.get("patient_phone"):
            phone = appointment_data["patient_phone"]
            # Remove common formatting characters
            sanitized_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            appointment_data["patient_phone"] = sanitized_phone if sanitized_phone else None

        appointment_data["status"] = AppointmentStatus.SCHEDULED.value

        # print("appointment_data:", appointment_data["status"])
        
        # Try to get existing patient info if patient_id is provided
        if appointment.patient_id:

            print("patient exists fetching existing patient info for ID:", appointment.patient_id)

            try:
                existing_patient = await db.get_patient(appointment.patient_id)

                print("existing_patient:", existing_patient)
                if existing_patient:
                    # Use existing patient info
                    appointment_data.update({
                        "patient_name": f"{existing_patient.get('first_name', '')} {existing_patient.get('last_name', '')}".strip(),
                        "patient_phone": existing_patient.get('phone', None),
                        "patient_email": existing_patient.get('email', None),
                        "patient_dob": existing_patient.get('date_of_birth', '2000-01-01'),
                    })
            except Exception as e:
                # If patient not found, we'll create a new one
                print(f"Error getting patient: {e}")
        

        # Set default patient info if not provided
        if not appointment_data.get("patient_name"):
            appointment_data.update({
                "patient_name": "New Patient",
                "patient_phone": None,
                "patient_email": None,
                "patient_dob": "2000-01-01",
                "health_card_number": f"TEMP-{appointment.patient_id}",
                "condition": "General consultation",
                "appointment_type": "OTHER",
                "urgency": "ROUTINE",
            })

        created = await db.create_appointment(appointment_data)
        
        if not created:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create appointment"
            )
        
        return created
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_appointment: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: UUID):
    """Get a specific appointment by ID."""
    db = get_supabase_client()
    appointment = await db.get_appointment(appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(appointment_id: UUID, updates: AppointmentUpdate):
    """
    Update an appointment.
    
    Use this for general updates. For rescheduling,
    prefer the /reschedule endpoint.
    """
    db = get_supabase_client()
    
    # Verify appointment exists
    existing = await db.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    update_data = updates.model_dump(exclude_unset=True)
    updated = await db.update_appointment(appointment_id, update_data)
    
    return updated


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(appointment_id: UUID, reschedule: AppointmentReschedule):
    """
    Reschedule an appointment to a new time.
    
    This endpoint:
    1. Updates the appointment in Supabase
    2. Updates the Google Calendar event (if exists)
    3. Sends updated invite to patient
    
    Called by:
    - Nurse manually rescheduling
    - Webhook handler when ElevenLabs agent successfully reschedules
    """
    db = get_supabase_client()
    
    # Verify appointment exists
    existing = await db.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    # Update appointment in database
    updated = await db.reschedule_appointment(
        appointment_id,
        reschedule.new_datetime,
        reschedule.reason
    )
    
    # Update Google Calendar event if it exists
    if existing.get("google_event_id"):
        try:
            calendar = get_calendar_service()
            await calendar.update_appointment_event(
                google_event_id=existing["google_event_id"],
                scheduled_at=reschedule.new_datetime,
                send_update=True
            )
        except Exception as e:
            # Log error but don't fail the reschedule
            print(f"Failed to update calendar event: {e}")
    
    return updated


@router.post("/{appointment_id}/mark-missed", response_model=AppointmentResponse)
async def mark_appointment_missed(appointment_id: UUID):
    """
    Mark an appointment as missed.
    
    This triggers the automated calling workflow:
    1. Mark appointment as missed
    2. Initiate ElevenLabs outbound call (via calls router)
    
    Typically called by a scheduled job checking for 
    appointments past their time without check-in.
    """
    db = get_supabase_client()
    
    existing = await db.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    updated = await db.mark_appointment_missed(appointment_id)
    
    # TODO: Automatically trigger outbound call
    # This could be done here or in a background task
    
    return updated


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(appointment_id: UUID):
    """
    Cancel an appointment.
    
    Updates status to cancelled and removes Google Calendar event.
    """
    db = get_supabase_client()
    
    existing = await db.get_appointment(appointment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    # Update status to cancelled
    await db.update_appointment(appointment_id, {"status": AppointmentStatus.CANCELLED.value})
    
    # Cancel Google Calendar event
    if existing.get("google_event_id"):
        try:
            calendar = get_calendar_service()
            await calendar.cancel_event(existing["google_event_id"])
        except Exception as e:
            print(f"Failed to cancel calendar event: {e}")
    
    return None
