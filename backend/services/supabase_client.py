"""
Supabase client service.

Handles all database operations via Supabase Python client.
This is the primary data layer for referrals, users, calls, emails, and flags.
"""

import os
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timezone

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class SupabaseClient:
    """
    Supabase database client wrapper.

    Provides typed methods for all database operations.
    Uses Supabase service role key for server-side operations.
    """

    def __init__(self):
        """Initialize Supabase client with environment variables."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.client: Client = create_client(url, key)

    # ============ REFERRALS ============

    async def create_referral(self, referral_data: dict) -> Optional[dict]:
        """
        Create a new referral record.

        Args:
            referral_data: Referral information including patient details, condition, specialist type

        Returns:
            Created referral record with ID
            
        Raises:
            Exception: If database operation fails
        """
        try:
            print(f"Creating referral with data: {referral_data}")
            result = self.client.table("referrals").insert(referral_data).execute()
            print(f"Referral created successfully: {result.data}")
            return result.data[0] if result.data else None
        except Exception as e:
            error_msg = f"Error creating referral: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            raise Exception(error_msg) from e

    async def get_referral(self, referral_id: UUID) -> Optional[dict]:
        """
        Get a referral by ID.

        Args:
            referral_id: UUID of the referral

        Returns:
            Referral record or None
        """
        try:
            result = self.client.table("referrals").select("*").eq("id", str(referral_id)).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting referral {referral_id}: {e}")
            return None

    async def get_referrals(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        specialist_type: Optional[str] = None,
        is_high_risk: Optional[bool] = None,
        created_by_id: Optional[UUID] = None
    ) -> List[dict]:
        """
        Get referrals with optional filters and pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Filter by referral status
            specialist_type: Filter by specialist type
            is_high_risk: Filter by high risk flag
            created_by_id: Filter by creator user ID

        Returns:
            List of referral records
        """
        try:
            query = self.client.table("referrals").select("*")

            if status:
                query = query.eq("status", status)
            if specialist_type:
                query = query.eq("specialist_type", specialist_type)
            if is_high_risk is not None:
                query = query.eq("is_high_risk", is_high_risk)
            if created_by_id:
                query = query.eq("created_by_id", str(created_by_id))

            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting referrals: {e}")
            return []

    async def get_referrals_by_status(self, status: str) -> List[dict]:
        """
        Get all referrals with a specific status.

        Args:
            status: Referral status (PENDING, SCHEDULED, MISSED, etc.)

        Returns:
            List of referrals
        """
        try:
            result = (
                self.client.table("referrals")
                .select("*")
                .eq("status", status)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting referrals by status {status}: {e}")
            return []

    async def get_referrals_by_date(self, target_date: date) -> List[dict]:
        """
        Get all referrals scheduled for a specific date.

        Args:
            target_date: Date to filter scheduled referrals

        Returns:
            List of scheduled referrals
        """
        try:
            # Convert date to datetime range
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())

            result = (
                self.client.table("referrals")
                .select("*")
                .gte("scheduled_date", start_of_day.isoformat())
                .lte("scheduled_date", end_of_day.isoformat())
                .order("scheduled_date")
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting referrals by date {target_date}: {e}")
            return []

    async def update_referral(self, referral_id: UUID, updates: dict) -> Optional[dict]:
        """
        Update a referral record.

        Args:
            referral_id: UUID of the referral
            updates: Dictionary of fields to update

        Returns:
            Updated referral record or None
        """
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            result = (
                self.client.table("referrals")
                .update(updates)
                .eq("id", str(referral_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating referral {referral_id}: {e}")
            return None

    async def reschedule_referral(
        self,
        referral_id: UUID,
        new_datetime: datetime,
        reason: Optional[str] = None
    ) -> Optional[dict]:
        """
        Reschedule a referral to a new time.

        Args:
            referral_id: ID of referral to reschedule
            new_datetime: New scheduled datetime
            reason: Optional reason for rescheduling

        Returns:
            Updated referral record
        """
        updates = {
            "scheduled_date": new_datetime.isoformat(),
            "status": "SCHEDULED",
        }
        if reason:
            # Append to notes
            existing = await self.get_referral(referral_id)
            if existing:
                old_notes = existing.get("notes", "")
                updates["notes"] = f"{old_notes}\n\nRescheduled: {reason}".strip()

        return await self.update_referral(referral_id, updates)

    async def mark_referral_missed(self, referral_id: UUID) -> Optional[dict]:
        """
        Mark a referral as missed.

        Args:
            referral_id: ID of referral to mark as missed

        Returns:
            Updated referral record
        """
        return await self.update_referral(referral_id, {"status": "MISSED"})

    async def cancel_referral(self, referral_id: UUID) -> Optional[dict]:
        """
        Cancel a referral.

        Args:
            referral_id: ID of referral to cancel

        Returns:
            Updated referral record
        """
        return await self.update_referral(referral_id, {"status": "CANCELLED"})

    # ============ USERS ============

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """
        Get a user by email address.

        Args:
            email: User's email

        Returns:
            User record or None
        """
        try:
            result = (
                self.client.table("users")
                .select("*")
                .eq("email", email)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting user by email {email}: {e}")
            return None

    async def get_user(self, user_id: UUID) -> Optional[dict]:
        """Get a user by ID."""
        try:
            result = (
                self.client.table("users")
                .select("*")
                .eq("id", str(user_id))
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_data: dict) -> Optional[dict]:
        """
        Create a new user account.

        Args:
            user_data: User information (email, password_hash, role, first_name, last_name)

        Returns:
            Created user record
        """
        try:
            result = self.client.table("users").insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    async def update_user_last_login(self, user_id: UUID) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: ID of user
        """
        try:
            self.client.table("users").update({
                "last_login": datetime.now(timezone.utc).isoformat()
            }).eq("id", str(user_id)).execute()
        except Exception as e:
            print(f"Error updating last login for user {user_id}: {e}")

    # ============ CALL LOGS ============

    async def create_call_log(self, call_data: dict) -> Optional[dict]:
        """
        Create a new call log record.

        Args:
            call_data: Call information (referral_id, call_type, phone_number, status)

        Returns:
            Created call log record
        """
        try:
            result = self.client.table("call_logs").insert(call_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating call log: {e}")
            return None

    async def get_call_log(self, call_id: UUID) -> Optional[dict]:
        """
        Get a call log by ID.

        Args:
            call_id: UUID of the call log

        Returns:
            Call log record or None
        """
        try:
            result = (
                self.client.table("call_logs")
                .select("*")
                .eq("id", str(call_id))
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting call log {call_id}: {e}")
            return None

    async def get_call_by_twilio_sid(self, twilio_call_sid: str) -> Optional[dict]:
        """
        Get a call log by Twilio Call SID (for webhook processing).

        Args:
            twilio_call_sid: Twilio's call SID

        Returns:
            Call log record or None
        """
        try:
            result = (
                self.client.table("call_logs")
                .select("*")
                .eq("twilio_call_sid", twilio_call_sid)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting call by Twilio SID {twilio_call_sid}: {e}")
            return None

    async def update_call_log(self, call_id: UUID, updates: dict) -> Optional[dict]:
        """
        Update a call log record.

        Args:
            call_id: UUID of the call log
            updates: Dictionary of fields to update

        Returns:
            Updated call log record
        """
        try:
            result = (
                self.client.table("call_logs")
                .update(updates)
                .eq("id", str(call_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating call log {call_id}: {e}")
            return None

    async def get_pending_calls(self) -> List[dict]:
        """
        Get all pending call logs.

        Returns:
            List of pending calls
        """
        try:
            result = (
                self.client.table("call_logs")
                .select("*")
                .eq("status", "SCHEDULED")
                .order("scheduled_at")
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting pending calls: {e}")
            return []

    async def get_calls_by_referral(self, referral_id: UUID) -> List[dict]:
        """
        Get all call logs for a specific referral.

        Args:
            referral_id: UUID of the referral

        Returns:
            List of call logs
        """
        try:
            result = (
                self.client.table("call_logs")
                .select("*")
                .eq("referral_id", str(referral_id))
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting calls for referral {referral_id}: {e}")
            return []

    # ============ EMAIL LOGS ============

    async def create_email_log(self, email_data: dict) -> Optional[dict]:
        """
        Create a new email log record.

        Args:
            email_data: Email information (referral_id, email_type, recipient, subject, status)

        Returns:
            Created email log record
        """
        try:
            result = self.client.table("email_logs").insert(email_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating email log: {e}")
            return None

    async def get_email_logs_by_referral(self, referral_id: UUID) -> List[dict]:
        """
        Get all email logs for a specific referral.

        Args:
            referral_id: UUID of the referral

        Returns:
            List of email logs
        """
        try:
            result = (
                self.client.table("email_logs")
                .select("*")
                .eq("referral_id", str(referral_id))
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting emails for referral {referral_id}: {e}")
            return []

    async def get_pending_emails(self, limit: int = 50) -> List[dict]:
        """
        Get pending emails from the queue.

        Args:
            limit: Maximum number of emails to fetch

        Returns:
            List of pending email logs
        """
        try:
            result = (
                self.client.table("email_logs")
                .select("*")
                .eq("status", "PENDING")
                .order("created_at")
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting pending emails: {e}")
            return []

    async def update_email_log(self, email_id: UUID, updates: dict) -> Optional[dict]:
        """
        Update an email log record.

        Args:
            email_id: UUID of the email log
            updates: Dictionary of fields to update

        Returns:
            Updated email log record
        """
        try:
            result = (
                self.client.table("email_logs")
                .update(updates)
                .eq("id", str(email_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating email log {email_id}: {e}")
            return None

    # ============ FLAGS ============

    async def create_flag(self, flag_data: dict) -> Optional[dict]:
        """
        Create a new flag for nurse follow-up.

        Args:
            flag_data: Flag information (referral_id, title, description, priority)

        Returns:
            Created flag record
        """
        try:
            result = self.client.table("flags").insert(flag_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating flag: {e}")
            return None

    async def get_flag(self, flag_id: UUID) -> Optional[dict]:
        """
        Get a specific flag by ID with referral and patient data.

        Args:
            flag_id: UUID of the flag

        Returns:
            Flag record with joined referral/patient data or None
        """
        try:
            result = (
                self.client.table("flags")
                .select("*, referrals(id, patient_name, patient_dob, patient_phone, patient_email, scheduled_date, status)")
                .eq("id", str(flag_id))
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting flag {flag_id}: {e}")
            return None

    async def get_flags(self, status: Optional[str] = None) -> List[dict]:
        """
        Get all flags, optionally filtered by status.

        Args:
            status: Filter by flag status (open, resolved, dismissed)

        Returns:
            List of flags with referral/patient data
        """
        try:
            # Priority order: urgent > high > medium > low
            # We'll order by CASE to get correct ordering
            query = self.client.table("flags").select("*, referrals(id, patient_name, patient_dob, patient_phone, patient_email, scheduled_date, status)")

            if status:
                query = query.eq("status", status)

            # Order: urgent first, then high, then medium, then low, then by created_at desc
            result = query.order("created_at", desc=True).execute()

            # Sort in Python to ensure correct priority order
            if result.data:
                priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
                result.data.sort(key=lambda x: (priority_order.get(x.get("priority", "low"), 4), -datetime.fromisoformat(x["created_at"].replace('Z', '+00:00')).timestamp()))

            return result.data or []
        except Exception as e:
            print(f"Error getting flags: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def get_open_flags(self) -> List[dict]:
        """
        Get all open flags for nurse dashboard.

        Returns:
            List of open flags with referral/patient data
        """
        return await self.get_flags(status="open")

    async def update_flag(self, flag_id: UUID, updates: dict) -> Optional[dict]:
        """
        Update a flag.

        Args:
            flag_id: UUID of the flag
            updates: Dictionary of fields to update

        Returns:
            Updated flag record
        """
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            result = self.client.table("flags").update(updates).eq("id", str(flag_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating flag {flag_id}: {e}")
            return None

    async def resolve_flag(
        self,
        flag_id: UUID,
        resolved_by_id: UUID,
        resolution_notes: Optional[str] = None
    ) -> Optional[dict]:
        """
        Mark a flag as resolved.

        Args:
            flag_id: UUID of the flag
            resolved_by_id: UUID of user resolving the flag
            resolution_notes: Optional notes about the resolution

        Returns:
            Updated flag record
        """
        updates = {
            "status": "resolved",
            "resolved_by_id": str(resolved_by_id),
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_notes": resolution_notes
        }
        return await self.update_flag(flag_id, updates)

    # ============ STATUS HISTORY ============

    async def get_status_history(self, referral_id: UUID) -> List[dict]:
        """
        Get status change history for a referral.

        Args:
            referral_id: UUID of the referral

        Returns:
            List of status history records
        """
        try:
            result = (
                self.client.table("status_history")
                .select("*")
                .eq("referral_id", str(referral_id))
                .order("changed_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting status history for referral {referral_id}: {e}")
            return []

    async def create_status_history(self, history_data: dict) -> Optional[dict]:
        """
        Create a status history record.

        Note: This is usually handled automatically by database triggers,
        but can be called manually if needed.

        Args:
            history_data: History information (referral_id, status, changed_by_id, note)

        Returns:
            Created history record
        """
        try:
            result = self.client.table("status_history").insert(history_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating status history: {e}")
            return None

    # ============ SPECIALIST CALENDARS ============

    async def get_specialist_calendar(self, specialist_type: str) -> Optional[dict]:
        """
        Get the active calendar for a specialist type.

        Args:
            specialist_type: Type of specialist (CARDIOLOGY, ORTHOPEDICS, etc.)

        Returns:
            Specialist calendar record or None
        """
        try:
            result = (
                self.client.table("specialist_calendars")
                .select("*")
                .eq("specialist_type", specialist_type)
                .eq("is_active", True)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting specialist calendar for {specialist_type}: {e}")
            return None

    async def get_all_specialist_calendars(self) -> List[dict]:
        """
        Get all active specialist calendars.

        Returns:
            List of specialist calendar records
        """
        try:
            result = (
                self.client.table("specialist_calendars")
                .select("*")
                .eq("is_active", True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting all specialist calendars: {e}")
            return []

    # ============ APPOINTMENT PROPOSALS ============

    async def create_appointment_proposal(self, proposal_data: dict) -> Optional[dict]:
        """
        Create an appointment proposal (time slot option).

        Args:
            proposal_data: Proposal information (referral_id, proposed_start, proposed_end, status)

        Returns:
            Created proposal record
        """
        try:
            result = self.client.table("appointment_proposals").insert(proposal_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating appointment proposal: {e}")
            return None

    async def get_proposals_by_referral(self, referral_id: UUID) -> List[dict]:
        """
        Get all appointment proposals for a referral.

        Args:
            referral_id: UUID of the referral

        Returns:
            List of proposal records
        """
        try:
            result = (
                self.client.table("appointment_proposals")
                .select("*")
                .eq("referral_id", str(referral_id))
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Error getting proposals for referral {referral_id}: {e}")
            return []

    async def update_proposal_status(self, proposal_id: UUID, status: str) -> Optional[dict]:
        """
        Update the status of an appointment proposal.

        Args:
            proposal_id: UUID of the proposal
            status: New status (PROPOSED, HELD, ACCEPTED, REJECTED, EXPIRED, CONFIRMED)

        Returns:
            Updated proposal record
        """
        try:
            updates = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            result = (
                self.client.table("appointment_proposals")
                .update(updates)
                .eq("id", str(proposal_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating proposal {proposal_id}: {e}")
            return None

    # ============ DATABASE FUNCTIONS ============

    async def get_dashboard_stats(self) -> Optional[dict]:
        """
        Get dashboard statistics using database function.

        Returns:
            Dictionary with dashboard statistics
        """
        try:
            result = self.client.rpc("get_dashboard_stats").execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return None

    async def get_overdue_referrals(self, days_threshold: int = 14) -> List[dict]:
        """
        Get overdue referrals using database function.

        Args:
            days_threshold: Number of days to consider as overdue

        Returns:
            List of overdue referral records
        """
        try:
            result = self.client.rpc("get_overdue_referrals", {
                "days_threshold": days_threshold
            }).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting overdue referrals: {e}")
            return []

    # ============ CALENDAR SYNC ============

    async def get_calendar_sync(self, referral_id: UUID) -> Optional[dict]:
        """
        Get calendar sync status for a referral.

        Args:
            referral_id: UUID of the referral

        Returns:
            Calendar sync record or None
        """
        try:
            result = (
                self.client.table("referrals")
                .select("id, calendar_event_id, calendar_invite_sent, email_sent")
                .eq("id", str(referral_id))
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"Error getting calendar sync for referral {referral_id}: {e}")
            return None

    async def create_calendar_sync(self, sync_data: dict) -> Optional[dict]:
        """
        Create or record a calendar sync (updates referral with calendar event ID).

        Args:
            sync_data: Dictionary with referral_id and google_event_id

        Returns:
            Updated referral record
        """
        try:
            referral_id = sync_data.get("referral_id")
            updates = {
                "calendar_event_id": sync_data.get("google_event_id"),
                "calendar_invite_sent": True,
                "email_sent_at": datetime.now(timezone.utc).isoformat()
            }
            result = (
                self.client.table("referrals")
                .update(updates)
                .eq("id", str(referral_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating calendar sync: {e}")
            return None

    async def update_calendar_sync(self, referral_id: UUID, sync_data: dict) -> Optional[dict]:
        """
        Update calendar sync status for a referral.

        Args:
            referral_id: UUID of the referral
            sync_data: Dictionary with google_event_id and other sync fields

        Returns:
            Updated referral record
        """
        try:
            updates = {
                "calendar_event_id": sync_data.get("google_event_id"),
                "calendar_invite_sent": True
            }
            result = (
                self.client.table("referrals")
                .update(updates)
                .eq("id", str(referral_id))
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating calendar sync for referral {referral_id}: {e}")
            return None


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
