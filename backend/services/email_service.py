"""
Email service using SendGrid.

Handles sending transactional emails to patients for referral notifications,
appointment confirmations, reminders, and follow-ups.

Uses Jinja2 templates for professional HTML emails.
"""

import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

from models.schemas import EmailType

load_dotenv()


class EmailService:
    """
    SendGrid email service for transactional emails.

    Renders HTML templates and sends emails via SendGrid API.
    Supports all email types defined in EmailType enum.
    """

    def __init__(self):
        """Initialize with SendGrid credentials from environment."""
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "Clinic Notification System")
        self.reply_to_email = os.getenv("SENDGRID_REPLY_TO_EMAIL", self.from_email)

        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY must be set in environment")
        if not self.from_email:
            raise ValueError("SENDGRID_FROM_EMAIL must be set in environment")

        self.client = SendGridAPIClient(self.api_key)

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def _get_template_name(self, email_type: EmailType) -> str:
        """Map EmailType to template filename."""
        template_map = {
            EmailType.REFERRAL_CREATED: "referral_created.html",
            EmailType.APPOINTMENT_REMINDER: "appointment_reminder.html",
            EmailType.APPOINTMENT_CONFIRMED: "appointment_confirmed.html",
            EmailType.APPOINTMENT_RESCHEDULED: "appointment_rescheduled.html",
            EmailType.FOLLOW_UP: "follow_up.html",
        }
        return template_map.get(email_type, "base.html")

    def _render_template(
        self,
        email_type: EmailType,
        context: Dict[str, Any]
    ) -> str:
        """
        Render email template with context variables.

        Args:
            email_type: Type of email to render
            context: Template context variables

        Returns:
            Rendered HTML string
        """
        template_name = self._get_template_name(email_type)
        template = self.jinja_env.get_template(template_name)

        # Add default context variables
        default_context = {
            "clinic_name": self.from_name,
            "contact_email": self.reply_to_email,
        }
        merged_context = {**default_context, **context}

        return template.render(**merged_context)

    def _generate_ical_content(
        self,
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        patient_email: Optional[str] = None
    ) -> str:
        """
        Generate iCal/ICS calendar invite content.

        Args:
            summary: Event title
            description: Event description
            start_time: Appointment start time
            end_time: Appointment end time
            location: Optional location
            patient_email: Optional attendee email

        Returns:
            iCal formatted string (RFC 5545)
        """
        # Generate unique UID for the event
        uid = f"{uuid4()}@{self.from_email.split('@')[1]}"

        # Format datetime in iCal format (YYYYMMDDTHHMMSS)
        dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        dtstart = start_time.strftime("%Y%m%dT%H%M%S")
        dtend = end_time.strftime("%Y%m%dT%H%M%S")

        # Build iCal content
        ical_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            f"PRODID:-//{self.from_name}//Appointment System//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
        ]

        if location:
            ical_lines.append(f"LOCATION:{location}")

        # Add organizer
        ical_lines.append(f"ORGANIZER;CN={self.from_name}:mailto:{self.from_email}")

        # Add attendee if provided
        if patient_email:
            ical_lines.append(f"ATTENDEE;RSVP=TRUE;CN=Patient:mailto:{patient_email}")

        # Add reminder (24 hours before)
        ical_lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT24H",
            "ACTION:DISPLAY",
            "DESCRIPTION:Appointment Reminder",
            "END:VALARM",
        ])

        ical_lines.extend([
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "END:VEVENT",
            "END:VCALENDAR"
        ])

        return "\r\n".join(ical_lines)

    def _create_ical_attachment(
        self,
        appointment_datetime: datetime,
        specialist_type: str,
        patient_name: str,
        patient_email: Optional[str] = None,
        location: Optional[str] = None,
        duration_minutes: int = 60
    ) -> Dict[str, str]:
        """
        Create an iCal attachment for email.

        Args:
            appointment_datetime: Appointment start time
            specialist_type: Type of specialist
            patient_name: Patient's name
            patient_email: Patient's email for RSVP
            location: Appointment location
            duration_minutes: Appointment duration in minutes

        Returns:
            Dictionary with attachment data for SendGrid
        """
        # Calculate end time
        end_time = appointment_datetime + timedelta(minutes=duration_minutes)

        # Generate iCal content
        summary = f"{specialist_type} Appointment - {patient_name}"
        description = f"Specialist appointment for {patient_name}\\n\\nPlease arrive 15 minutes early."

        ical_content = self._generate_ical_content(
            summary=summary,
            description=description,
            start_time=appointment_datetime,
            end_time=end_time,
            location=location,
            patient_email=patient_email
        )

        # Encode to base64 for email attachment
        ical_base64 = base64.b64encode(ical_content.encode('utf-8')).decode('utf-8')

        return {
            'content': ical_base64,
            'filename': 'appointment.ics',
            'type': 'text/calendar',
            'disposition': 'attachment'
        }

    async def send_email(
        self,
        to_email: str,
        subject: str,
        email_type: EmailType,
        context: Dict[str, Any],
        attachments: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Send an email using SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            email_type: Type of email (determines template)
            context: Template variables for rendering
            attachments: Optional list of attachments

        Returns:
            dict with status and message_id

        Raises:
            Exception: If sending fails
        """
        try:
            # Render HTML content
            html_content = self._render_template(email_type, context)

            # Create message
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )

            # Set reply-to
            if self.reply_to_email:
                message.reply_to = self.reply_to_email

            # Add attachments if provided
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment(
                        FileContent(attachment_data.get('content')),
                        FileName(attachment_data.get('filename')),
                        FileType(attachment_data.get('type', 'application/octet-stream')),
                        Disposition('attachment')
                    )
                    message.add_attachment(attachment)

            # Send email
            response = self.client.send(message)

            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get('X-Message-Id'),
                "message": "Email sent successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send email: {str(e)}"
            }

    async def send_referral_created_email(
        self,
        to_email: str,
        patient_name: str,
        specialist_type: str,
        condition: str,
        urgency: str,
        scheduled_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Send email when a referral is created."""
        context = {
            "patient_name": patient_name,
            "specialist_type": specialist_type,
            "condition": condition,
            "urgency": urgency,
            "scheduled_date": scheduled_date.strftime("%A, %B %d, %Y at %I:%M %p") if scheduled_date else None
        }

        return await self.send_email(
            to_email=to_email,
            subject=f"Referral Created - {specialist_type}",
            email_type=EmailType.REFERRAL_CREATED,
            context=context
        )

    async def send_appointment_reminder_email(
        self,
        to_email: str,
        patient_name: str,
        appointment_datetime: datetime,
        specialist_type: str,
        location: Optional[str] = None,
        attach_calendar: bool = False
    ) -> Dict[str, Any]:
        """
        Send appointment reminder email.

        Args:
            to_email: Recipient email
            patient_name: Patient's name
            appointment_datetime: Appointment date and time
            specialist_type: Type of specialist
            location: Optional appointment location
            attach_calendar: Whether to attach iCal invite
        """
        context = {
            "patient_name": patient_name,
            "appointment_datetime": appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
            "specialist_type": specialist_type,
            "location": location
        }

        # Create iCal attachment if requested
        attachments = None
        if attach_calendar:
            ical_attachment = self._create_ical_attachment(
                appointment_datetime=appointment_datetime,
                specialist_type=specialist_type,
                patient_name=patient_name,
                patient_email=to_email,
                location=location
            )
            attachments = [ical_attachment]

        return await self.send_email(
            to_email=to_email,
            subject=f"Appointment Reminder - {appointment_datetime.strftime('%B %d')}",
            email_type=EmailType.APPOINTMENT_REMINDER,
            context=context,
            attachments=attachments
        )

    async def send_appointment_confirmed_email(
        self,
        to_email: str,
        patient_name: str,
        appointment_datetime: datetime,
        specialist_type: str,
        location: Optional[str] = None,
        attach_calendar: bool = True
    ) -> Dict[str, Any]:
        """
        Send appointment confirmation email with optional calendar invite.

        Args:
            to_email: Recipient email
            patient_name: Patient's name
            appointment_datetime: Appointment date and time
            specialist_type: Type of specialist
            location: Optional appointment location
            attach_calendar: Whether to attach iCal invite (default: True)
        """
        # Create iCal attachment if requested
        attachments = None
        if attach_calendar:
            ical_attachment = self._create_ical_attachment(
                appointment_datetime=appointment_datetime,
                specialist_type=specialist_type,
                patient_name=patient_name,
                patient_email=to_email,
                location=location
            )
            attachments = [ical_attachment]

        context = {
            "patient_name": patient_name,
            "appointment_datetime": appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
            "specialist_type": specialist_type,
            "location": location,
            "calendar_attached": attach_calendar
        }

        return await self.send_email(
            to_email=to_email,
            subject=f"Appointment Confirmed - {specialist_type}",
            email_type=EmailType.APPOINTMENT_CONFIRMED,
            context=context,
            attachments=attachments
        )

    async def send_appointment_rescheduled_email(
        self,
        to_email: str,
        patient_name: str,
        new_datetime: datetime,
        specialist_type: str,
        old_datetime: Optional[datetime] = None,
        location: Optional[str] = None,
        reason: Optional[str] = None,
        attach_calendar: bool = True
    ) -> Dict[str, Any]:
        """
        Send appointment rescheduled email with updated calendar invite.

        Args:
            to_email: Recipient email
            patient_name: Patient's name
            new_datetime: New appointment date and time
            specialist_type: Type of specialist
            old_datetime: Previous appointment date and time
            location: Optional appointment location
            reason: Optional reason for rescheduling
            attach_calendar: Whether to attach updated iCal invite (default: True)
        """
        # Create iCal attachment for new appointment time
        attachments = None
        if attach_calendar:
            ical_attachment = self._create_ical_attachment(
                appointment_datetime=new_datetime,
                specialist_type=specialist_type,
                patient_name=patient_name,
                patient_email=to_email,
                location=location
            )
            attachments = [ical_attachment]

        context = {
            "patient_name": patient_name,
            "new_datetime": new_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
            "old_datetime": old_datetime.strftime("%A, %B %d, %Y at %I:%M %p") if old_datetime else None,
            "specialist_type": specialist_type,
            "location": location,
            "reason": reason
        }

        return await self.send_email(
            to_email=to_email,
            subject=f"Appointment Rescheduled - {specialist_type}",
            email_type=EmailType.APPOINTMENT_RESCHEDULED,
            context=context,
            attachments=attachments
        )

    async def send_follow_up_email(
        self,
        to_email: str,
        patient_name: str,
        specialist_type: str,
        scheduled_date: Optional[datetime] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send follow-up email."""
        context = {
            "patient_name": patient_name,
            "specialist_type": specialist_type,
            "scheduled_date": scheduled_date.strftime("%A, %B %d, %Y at %I:%M %p") if scheduled_date else None,
            "message": message
        }

        return await self.send_email(
            to_email=to_email,
            subject=f"Follow-Up - {specialist_type} Referral",
            email_type=EmailType.FOLLOW_UP,
            context=context
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
