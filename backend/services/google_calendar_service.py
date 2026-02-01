"""
Google Calendar API service.

Handles creating and updating calendar events for appointments.
Sends invites to patients when appointments are scheduled or rescheduled.

Setup:
1. Create Google Cloud project with Calendar API enabled
2. Create OAuth credentials or Service Account
3. For server-to-server: Use service account with domain-wide delegation
4. For user-specific: Implement OAuth flow and store refresh tokens
"""

import os
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()


class GoogleCalendarService:
    """
    Google Calendar integration service.
    
    Creates and manages calendar events for patient appointments.
    Can send email invites to patients and update events when rescheduled.
    """
    
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    
    def __init__(self):
        """
        Initialize Google Calendar service.
        
        Supports two authentication modes:
        1. Service Account (recommended for server-to-server)
        2. OAuth2 with refresh token (for user-delegated access)
        """
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.service = self._build_service()
    
    def _build_service(self):
        """Build the Google Calendar API service."""
        # Try service account first (recommended for production)
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        
        if service_account_file and os.path.exists(service_account_file):
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=self.SCOPES
            )
            # If using domain-wide delegation, impersonate a user
            delegate_email = os.getenv("GOOGLE_DELEGATE_EMAIL")
            if delegate_email:
                credentials = credentials.with_subject(delegate_email)
        else:
            # Fall back to OAuth2 with refresh token
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
            
            if not all([client_id, client_secret, refresh_token]):
                raise ValueError(
                    "Either GOOGLE_SERVICE_ACCOUNT_FILE or "
                    "GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN must be set"
                )
            
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES
            )
        
        return build("calendar", "v3", credentials=credentials)
    
    async def create_appointment_event(
        self,
        appointment_id: UUID,
        patient_name: str,
        patient_email: Optional[str],
        appointment_type: str,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        notes: Optional[str] = None,
        send_invite: bool = True
    ) -> dict:
        """
        Create a Google Calendar event for an appointment.
        
        Args:
            appointment_id: Internal appointment ID
            patient_name: Patient's name
            patient_email: Patient's email (for invite)
            appointment_type: Type of appointment
            scheduled_at: Appointment datetime
            duration_minutes: Duration in minutes
            notes: Optional notes/description
            send_invite: Whether to send email invite to patient
            
        Returns:
            dict with google_event_id and html_link
            
        Raises:
            HttpError: If Calendar API call fails
        """
        end_time = scheduled_at + timedelta(minutes=duration_minutes)
        
        event = {
            "summary": f"{appointment_type} - {patient_name}",
            "description": self._build_description(appointment_id, notes),
            "start": {
                "dateTime": scheduled_at.isoformat(),
                "timeZone": os.getenv("TIMEZONE", "America/New_York"),
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": os.getenv("TIMEZONE", "America/New_York"),
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 60},  # 1 hour before
                ],
            },
            # Extended properties to link back to our system
            "extendedProperties": {
                "private": {
                    "appointment_id": str(appointment_id),
                    "source": "nurse_appointment_system"
                }
            }
        }
        
        # Add patient as attendee if email provided
        if patient_email and send_invite:
            event["attendees"] = [
                {"email": patient_email, "displayName": patient_name}
            ]
        
        try:
            # sendUpdates controls email notifications
            send_updates = "all" if send_invite and patient_email else "none"
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                sendUpdates=send_updates
            ).execute()
            
            return {
                "google_event_id": created_event["id"],
                "html_link": created_event.get("htmlLink", ""),
                "status": created_event.get("status", "confirmed")
            }
            
        except HttpError as error:
            # TODO: Implement proper error handling and retry logic
            raise error
    
    async def update_appointment_event(
        self,
        google_event_id: str,
        scheduled_at: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        appointment_type: Optional[str] = None,
        patient_name: Optional[str] = None,
        notes: Optional[str] = None,
        send_update: bool = True
    ) -> dict:
        """
        Update an existing calendar event (e.g., when rescheduling).
        
        Args:
            google_event_id: The Google Calendar event ID
            scheduled_at: New datetime (if rescheduling)
            duration_minutes: New duration (if changing)
            appointment_type: Updated type
            patient_name: Patient name (for summary update)
            notes: Updated notes
            send_update: Whether to notify attendees of change
            
        Returns:
            Updated event details
        """
        try:
            # Fetch current event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()
            
            # Update fields if provided
            if scheduled_at:
                duration = duration_minutes or 30
                end_time = scheduled_at + timedelta(minutes=duration)
                event["start"]["dateTime"] = scheduled_at.isoformat()
                event["end"]["dateTime"] = end_time.isoformat()
            
            if appointment_type and patient_name:
                event["summary"] = f"{appointment_type} - {patient_name}"
            
            if notes:
                # Preserve appointment_id in description
                apt_id = event.get("extendedProperties", {}).get("private", {}).get("appointment_id", "")
                event["description"] = self._build_description(apt_id, notes)
            
            # Update the event
            send_updates = "all" if send_update else "none"
            
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                body=event,
                sendUpdates=send_updates
            ).execute()
            
            return {
                "google_event_id": updated_event["id"],
                "html_link": updated_event.get("htmlLink", ""),
                "status": updated_event.get("status", "confirmed")
            }
            
        except HttpError as error:
            raise error
    
    async def cancel_event(
        self, 
        google_event_id: str, 
        send_cancellation: bool = True
    ) -> bool:
        """
        Cancel (delete) a calendar event.
        
        Args:
            google_event_id: The Google Calendar event ID
            send_cancellation: Whether to notify attendees
            
        Returns:
            True if successfully cancelled
        """
        try:
            send_updates = "all" if send_cancellation else "none"
            
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                sendUpdates=send_updates
            ).execute()
            
            return True
            
        except HttpError as error:
            if error.resp.status == 404:
                # Event already deleted
                return True
            raise error
    
    async def get_event(self, google_event_id: str) -> Optional[dict]:
        """Get details of a calendar event."""
        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()
            return event
        except HttpError as error:
            if error.resp.status == 404:
                return None
            raise error
    
    def _build_description(self, appointment_id, notes: Optional[str] = None) -> str:
        """Build event description with appointment reference."""
        lines = [
            "Appointment scheduled via Nurse Appointment System",
            f"Appointment ID: {appointment_id}",
        ]
        if notes:
            lines.append(f"\nNotes: {notes}")
        return "\n".join(lines)


# Singleton instance
_calendar_service: Optional[GoogleCalendarService] = None


def get_calendar_service() -> GoogleCalendarService:
    """Get or create Google Calendar service singleton."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service
