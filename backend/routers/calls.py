"""
Calls router.

Manages outbound call attempts via ElevenLabs.
Provides endpoints to initiate calls and check call status.
"""

from fastapi import APIRouter, HTTPException, Query, status
import httpx
import os

router = APIRouter()

TWILIO_SERVICE_URL = "https://vehicles-forgot-terrain-magnificent.trycloudflare.com"

@router.post("/initiate")
async def initiate_call(request: dict):
    """
    Initiate outbound call via Twilio/ElevenLabs service
    """
    try:
        # Extract data from frontend format
        phone_number = request.get("phone_number")
        referral_id = request.get("referral_id")
        call_type = request.get("call_type", "MISSED_APPOINTMENT_FOLLOWUP")

        # For now, using placeholder data - replace with actual DB query

        # Format for Twilio/ElevenLabs service
        payload = {
            "phone_number": phone_number,
            "dynamic_variables": {
                "patient_name": "Parth Joshi",  # Get from referral data
                "patient_age": "19",  # Get from referral data
                "specialist_type": "Cardiologist",  # Get from referral data
                "cancelled_appointment_time": "Jan 20, 2026",  # Get from referral data
                "selected_time": "",
                "referral_id": referral_id,
                "call_type": call_type
            }
        }

        # Forward to Twilio service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TWILIO_SERVICE_URL}/make-call",
                json=payload
            )
            return response.json()

    except httpx.RequestError as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}