"""
ElevenLabs Conversational AI service.

Handles outbound calling via ElevenLabs API for automated appointment rescheduling.
The agent calls patients who have missed appointments and attempts to reschedule.

Flow:
1. Backend triggers call via initiate_outbound_call()
2. ElevenLabs agent converses with patient
3. On completion, ElevenLabs sends webhook to our /api/webhooks/elevenlabs endpoint
4. Webhook handler processes outcome and updates appointment status
"""

import os
import httpx
from typing import Optional
from uuid import UUID
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


class ElevenLabsService:
    """
    ElevenLabs Conversational AI integration service.
    
    Uses ElevenLabs API to initiate outbound calls for appointment rescheduling.
    The agent is pre-configured in ElevenLabs dashboard with appropriate prompts.
    """
    
    # ElevenLabs API base URL
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self):
        """Initialize with API credentials from environment."""
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        self.webhook_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000") + "/api/webhooks/elevenlabs"
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY must be set")
        if not self.agent_id:
            raise ValueError("ELEVENLABS_AGENT_ID must be set")
        
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def initiate_outbound_call(
        self,
        phone_number: str,
        patient_name: str,
        appointment_id: UUID,
        appointment_type: str,
        original_datetime: datetime,
        call_attempt_id: UUID
    ) -> dict:
        """
        Initiate an outbound call to reschedule a missed appointment.
        
        Args:
            phone_number: Patient's phone number in E.164 format (+1234567890)
            patient_name: Patient's name for personalized greeting
            appointment_id: ID of the missed appointment
            appointment_type: Type of appointment (e.g., "follow-up", "check-up")
            original_datetime: Original scheduled datetime
            call_attempt_id: Our internal call attempt ID for tracking
            
        Returns:
            dict with call_id and status from ElevenLabs
            
        Raises:
            httpx.HTTPError: If API call fails
            
        NOTE: The actual ElevenLabs API endpoint and payload structure 
        should be verified against their documentation. This is a placeholder
        based on typical conversational AI patterns.
        """
        # TODO: Verify actual ElevenLabs outbound calling API endpoint
        # This is a placeholder structure - adjust based on actual API docs
        
        payload = {
            "agent_id": self.agent_id,
            "phone_number": phone_number,
            "webhook_url": self.webhook_url,
            # Dynamic variables passed to the agent's prompt
            "dynamic_variables": {
                "patient_name": patient_name,
                "appointment_type": appointment_type,
                "original_date": original_datetime.strftime("%A, %B %d"),
                "original_time": original_datetime.strftime("%I:%M %p"),
            },
            # Metadata returned in webhook for our tracking
            "metadata": {
                "appointment_id": str(appointment_id),
                "call_attempt_id": str(call_attempt_id),
                "source": "nurse_appointment_system"
            }
        }
        
        async with httpx.AsyncClient() as client:
            # TODO: Update endpoint URL based on actual ElevenLabs API
            response = await client.post(
                f"{self.BASE_URL}/convai/agents/{self.agent_id}/call",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_call_status(self, call_id: str) -> dict:
        """
        Get the current status of an ongoing or completed call.
        
        Args:
            call_id: ElevenLabs call ID
            
        Returns:
            Call status and details
        """
        # TODO: Implement based on actual ElevenLabs API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/convai/calls/{call_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def cancel_call(self, call_id: str) -> dict:
        """
        Cancel an ongoing call.
        
        Args:
            call_id: ElevenLabs call ID
            
        Returns:
            Cancellation confirmation
        """
        # TODO: Implement based on actual ElevenLabs API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/convai/calls/{call_id}/cancel",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook came from ElevenLabs.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from webhook header
            
        Returns:
            True if signature is valid
            
        TODO: Implement actual signature verification based on ElevenLabs docs.
        This is critical for security in production.
        """
        webhook_secret = os.getenv("WEBHOOK_SECRET")
        if not webhook_secret:
            # In development, skip verification
            return True
        
        # TODO: Implement HMAC verification
        # import hmac
        # import hashlib
        # expected = hmac.new(
        #     webhook_secret.encode(),
        #     payload,
        #     hashlib.sha256
        # ).hexdigest()
        # return hmac.compare_digest(expected, signature)
        
        return True  # Placeholder - implement in production!


# Singleton instance
_elevenlabs_service: Optional[ElevenLabsService] = None


def get_elevenlabs_service() -> ElevenLabsService:
    """Get or create ElevenLabs service singleton."""
    global _elevenlabs_service
    if _elevenlabs_service is None:
        _elevenlabs_service = ElevenLabsService()
    return _elevenlabs_service
