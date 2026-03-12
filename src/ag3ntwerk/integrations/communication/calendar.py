"""
Calendar Integration for ag3ntwerk.

Provides calendar management for Google Calendar and Outlook.

Requirements:
    - Google: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    - Outlook: pip install O365

Calendar is ideal for:
    - Agent scheduling
    - Meeting management
    - Availability checking
    - Automated reminders
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class CalendarProvider(str, Enum):
    """Supported calendar providers."""

    GOOGLE = "google"
    OUTLOOK = "outlook"
    CALDAV = "caldav"


class EventStatus(str, Enum):
    """Event status."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ResponseStatus(str, Enum):
    """Attendee response status."""

    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needsAction"


@dataclass
class CalendarConfig:
    """Configuration for calendar integration."""

    provider: CalendarProvider = CalendarProvider.GOOGLE

    # Google-specific
    google_credentials_file: str = ""
    google_token_file: str = ""

    # Outlook-specific
    outlook_client_id: str = ""
    outlook_client_secret: str = ""

    # CalDAV-specific
    caldav_url: str = ""
    caldav_username: str = ""
    caldav_password: str = ""

    # General
    default_calendar_id: str = "primary"
    timezone: str = "UTC"


@dataclass
class Attendee:
    """Represents a calendar event attendee."""

    email: str
    name: str = ""
    response_status: ResponseStatus = ResponseStatus.NEEDS_ACTION
    is_organizer: bool = False
    is_optional: bool = False


@dataclass
class CalendarEvent:
    """Represents a calendar event."""

    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    attendees: List[Attendee] = field(default_factory=list)
    status: EventStatus = EventStatus.CONFIRMED
    is_all_day: bool = False
    recurrence: Optional[str] = None  # RRULE string
    reminders: List[int] = field(default_factory=list)  # Minutes before
    conference_link: str = ""
    event_id: Optional[str] = None
    calendar_id: str = "primary"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> timedelta:
        """Get event duration."""
        return self.end - self.start


@dataclass
class Calendar:
    """Represents a calendar."""

    id: str
    name: str
    description: str = ""
    color: str = ""
    is_primary: bool = False
    is_owner: bool = True
    timezone: str = "UTC"


@dataclass
class FreeBusy:
    """Represents free/busy information."""

    start: datetime
    end: datetime
    status: str = "busy"


class CalendarIntegration:
    """
    Integration with calendar services.

    Supports Google Calendar, Outlook, and CalDAV.

    Example:
        integration = CalendarIntegration(CalendarConfig(
            provider=CalendarProvider.GOOGLE,
            google_credentials_file="credentials.json",
        ))

        # Get upcoming events
        events = await integration.get_events(
            start=datetime.now(),
            end=datetime.now() + timedelta(days=7),
        )

        # Create an event
        event = await integration.create_event(CalendarEvent(
            title="Team Meeting",
            start=datetime(2024, 1, 15, 10, 0),
            end=datetime(2024, 1, 15, 11, 0),
            attendees=[Attendee(email="team@example.com")],
        ))

        # Check availability
        free_busy = await integration.get_free_busy(
            emails=["user1@example.com", "user2@example.com"],
            start=datetime.now(),
            end=datetime.now() + timedelta(days=1),
        )
    """

    def __init__(self, config: CalendarConfig):
        """Initialize calendar integration."""
        self.config = config
        self._service = None

    async def _get_google_service(self):
        """Get Google Calendar service."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import json
            import os
        except ImportError:
            raise ImportError(
                "Google Calendar dependencies not installed. Install with: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        creds = None

        if os.path.exists(self.config.google_token_file):
            token_path = self.config.google_token_file
            try:
                with open(token_path, "r") as token:
                    token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except (json.JSONDecodeError, ValueError, KeyError):
                # Legacy pickle token or corrupted file -- remove and re-authenticate
                logger.warning(
                    "Token file '%s' is not valid JSON (possibly legacy pickle format). "
                    "Deleting and re-authenticating.",
                    token_path,
                )
                os.remove(token_path)
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.google_credentials_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            with open(self.config.google_token_file, "w") as token:
                token.write(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    async def _get_outlook_service(self):
        """Get Outlook Calendar service."""
        if self._service is not None:
            return self._service

        try:
            from O365 import Account
        except ImportError:
            raise ImportError("O365 not installed. Install with: pip install O365")

        credentials = (
            self.config.outlook_client_id,
            self.config.outlook_client_secret,
        )
        account = Account(credentials)

        if not account.is_authenticated:
            account.authenticate(scopes=["basic", "calendar_all"])

        self._service = account.schedule()
        return self._service

    async def get_calendars(self) -> List[Calendar]:
        """Get list of calendars."""
        if self.config.provider == CalendarProvider.GOOGLE:
            return await self._get_google_calendars()
        elif self.config.provider == CalendarProvider.OUTLOOK:
            return await self._get_outlook_calendars()
        else:
            raise NotImplementedError(f"Provider {self.config.provider} not implemented")

    async def _get_google_calendars(self) -> List[Calendar]:
        """Get Google calendars."""
        service = await self._get_google_service()
        loop = asyncio.get_running_loop()

        def _fetch():
            result = service.calendarList().list().execute()
            return result.get("items", [])

        items = await loop.run_in_executor(None, _fetch)

        calendars = []
        for item in items:
            calendars.append(
                Calendar(
                    id=item["id"],
                    name=item.get("summary", ""),
                    description=item.get("description", ""),
                    color=item.get("backgroundColor", ""),
                    is_primary=item.get("primary", False),
                    is_owner=item.get("accessRole") == "owner",
                    timezone=item.get("timeZone", "UTC"),
                )
            )

        return calendars

    async def _get_outlook_calendars(self) -> List[Calendar]:
        """Get Outlook calendars."""
        schedule = await self._get_outlook_service()

        calendars = []
        for cal in schedule.list_calendars():
            calendars.append(
                Calendar(
                    id=cal.calendar_id,
                    name=cal.name,
                    is_primary=cal.is_default,
                )
            )

        return calendars

    async def get_events(
        self,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
        max_results: int = 100,
    ) -> List[CalendarEvent]:
        """
        Get events in a time range.

        Args:
            start: Start datetime
            end: End datetime
            calendar_id: Calendar ID (default: primary)
            max_results: Maximum events to return

        Returns:
            List of CalendarEvents
        """
        calendar_id = calendar_id or self.config.default_calendar_id

        if self.config.provider == CalendarProvider.GOOGLE:
            return await self._get_google_events(start, end, calendar_id, max_results)
        elif self.config.provider == CalendarProvider.OUTLOOK:
            return await self._get_outlook_events(start, end, calendar_id, max_results)
        else:
            raise NotImplementedError(f"Provider {self.config.provider} not implemented")

    async def _get_google_events(
        self,
        start: datetime,
        end: datetime,
        calendar_id: str,
        max_results: int,
    ) -> List[CalendarEvent]:
        """Get events from Google Calendar."""
        service = await self._get_google_service()
        loop = asyncio.get_running_loop()

        def _fetch():
            result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start.isoformat() + "Z",
                    timeMax=end.isoformat() + "Z",
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return result.get("items", [])

        items = await loop.run_in_executor(None, _fetch)

        events = []
        for item in items:
            # Parse start/end times
            start_data = item.get("start", {})
            end_data = item.get("end", {})

            if "dateTime" in start_data:
                event_start = datetime.fromisoformat(start_data["dateTime"].replace("Z", "+00:00"))
                event_end = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00"))
                is_all_day = False
            else:
                event_start = datetime.fromisoformat(start_data.get("date", ""))
                event_end = datetime.fromisoformat(end_data.get("date", ""))
                is_all_day = True

            # Parse attendees
            attendees = []
            for att in item.get("attendees", []):
                attendees.append(
                    Attendee(
                        email=att.get("email", ""),
                        name=att.get("displayName", ""),
                        response_status=ResponseStatus(att.get("responseStatus", "needsAction")),
                        is_organizer=att.get("organizer", False),
                        is_optional=att.get("optional", False),
                    )
                )

            # Parse reminders
            reminders = []
            reminder_data = item.get("reminders", {})
            if not reminder_data.get("useDefault", True):
                for r in reminder_data.get("overrides", []):
                    reminders.append(r.get("minutes", 0))

            events.append(
                CalendarEvent(
                    title=item.get("summary", ""),
                    start=event_start,
                    end=event_end,
                    description=item.get("description", ""),
                    location=item.get("location", ""),
                    attendees=attendees,
                    status=EventStatus(item.get("status", "confirmed")),
                    is_all_day=is_all_day,
                    recurrence=(
                        item.get("recurrence", [None])[0] if item.get("recurrence") else None
                    ),
                    reminders=reminders,
                    conference_link=item.get("hangoutLink", ""),
                    event_id=item.get("id"),
                    calendar_id=calendar_id,
                )
            )

        return events

    async def _get_outlook_events(
        self,
        start: datetime,
        end: datetime,
        calendar_id: str,
        max_results: int,
    ) -> List[CalendarEvent]:
        """Get events from Outlook Calendar."""
        schedule = await self._get_outlook_service()
        calendar = schedule.get_calendar(calendar_id)

        query = calendar.new_query("start").greater_equal(start)
        query.chain("and").on_attribute("end").less_equal(end)

        events = []
        for event in calendar.get_events(query=query, limit=max_results):
            attendees = [
                Attendee(
                    email=att.address,
                    name=att.name or "",
                )
                for att in event.attendees
            ]

            events.append(
                CalendarEvent(
                    title=event.subject,
                    start=event.start,
                    end=event.end,
                    description=event.body or "",
                    location=event.location.get("displayName", "") if event.location else "",
                    attendees=attendees,
                    is_all_day=event.is_all_day,
                    event_id=event.event_id,
                    calendar_id=calendar_id,
                )
            )

        return events

    async def create_event(
        self,
        event: CalendarEvent,
    ) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            event: CalendarEvent to create

        Returns:
            Created CalendarEvent with ID
        """
        if self.config.provider == CalendarProvider.GOOGLE:
            return await self._create_google_event(event)
        elif self.config.provider == CalendarProvider.OUTLOOK:
            return await self._create_outlook_event(event)
        else:
            raise NotImplementedError(f"Provider {self.config.provider} not implemented")

    async def _create_google_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create event in Google Calendar."""
        service = await self._get_google_service()
        loop = asyncio.get_running_loop()

        body = {
            "summary": event.title,
            "description": event.description,
            "location": event.location,
            "status": event.status.value,
        }

        if event.is_all_day:
            body["start"] = {"date": event.start.strftime("%Y-%m-%d")}
            body["end"] = {"date": event.end.strftime("%Y-%m-%d")}
        else:
            body["start"] = {
                "dateTime": event.start.isoformat(),
                "timeZone": self.config.timezone,
            }
            body["end"] = {
                "dateTime": event.end.isoformat(),
                "timeZone": self.config.timezone,
            }

        if event.attendees:
            body["attendees"] = [
                {"email": a.email, "displayName": a.name, "optional": a.is_optional}
                for a in event.attendees
            ]

        if event.recurrence:
            body["recurrence"] = [event.recurrence]

        if event.reminders:
            body["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in event.reminders],
            }

        def _create():
            return (
                service.events()
                .insert(
                    calendarId=event.calendar_id or self.config.default_calendar_id,
                    body=body,
                    conferenceDataVersion=1,
                )
                .execute()
            )

        result = await loop.run_in_executor(None, _create)

        event.event_id = result.get("id")
        event.conference_link = result.get("hangoutLink", "")

        return event

    async def _create_outlook_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create event in Outlook Calendar."""
        schedule = await self._get_outlook_service()
        calendar = schedule.get_calendar(event.calendar_id or self.config.default_calendar_id)

        new_event = calendar.new_event()
        new_event.subject = event.title
        new_event.body = event.description
        new_event.start = event.start
        new_event.end = event.end
        new_event.is_all_day = event.is_all_day

        if event.location:
            new_event.location = event.location

        for attendee in event.attendees:
            new_event.attendees.add(attendee.email)

        new_event.save()
        event.event_id = new_event.event_id

        return event

    async def update_event(
        self,
        event: CalendarEvent,
    ) -> CalendarEvent:
        """Update an existing event."""
        if not event.event_id:
            raise ValueError("Event must have an ID to update")

        if self.config.provider == CalendarProvider.GOOGLE:
            return await self._update_google_event(event)
        elif self.config.provider == CalendarProvider.OUTLOOK:
            return await self._update_outlook_event(event)
        else:
            raise NotImplementedError(f"Provider {self.config.provider} not implemented")

    async def _update_google_event(self, event: CalendarEvent) -> CalendarEvent:
        """Update event in Google Calendar."""
        service = await self._get_google_service()
        loop = asyncio.get_running_loop()

        body = {
            "summary": event.title,
            "description": event.description,
            "location": event.location,
        }

        if event.is_all_day:
            body["start"] = {"date": event.start.strftime("%Y-%m-%d")}
            body["end"] = {"date": event.end.strftime("%Y-%m-%d")}
        else:
            body["start"] = {"dateTime": event.start.isoformat(), "timeZone": self.config.timezone}
            body["end"] = {"dateTime": event.end.isoformat(), "timeZone": self.config.timezone}

        if event.attendees:
            body["attendees"] = [{"email": a.email} for a in event.attendees]

        def _update():
            return (
                service.events()
                .update(
                    calendarId=event.calendar_id or self.config.default_calendar_id,
                    eventId=event.event_id,
                    body=body,
                )
                .execute()
            )

        await loop.run_in_executor(None, _update)
        return event

    async def _update_outlook_event(self, event: CalendarEvent) -> CalendarEvent:
        """Update event in Outlook Calendar."""
        schedule = await self._get_outlook_service()
        calendar = schedule.get_calendar(event.calendar_id or self.config.default_calendar_id)

        outlook_event = calendar.get_event(event.event_id)
        outlook_event.subject = event.title
        outlook_event.body = event.description
        outlook_event.start = event.start
        outlook_event.end = event.end
        outlook_event.save()

        return event

    async def delete_event(
        self,
        event_id: str,
        calendar_id: Optional[str] = None,
    ) -> bool:
        """Delete an event."""
        calendar_id = calendar_id or self.config.default_calendar_id

        if self.config.provider == CalendarProvider.GOOGLE:
            service = await self._get_google_service()
            loop = asyncio.get_running_loop()

            def _delete():
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id,
                ).execute()

            await loop.run_in_executor(None, _delete)

        elif self.config.provider == CalendarProvider.OUTLOOK:
            schedule = await self._get_outlook_service()
            calendar = schedule.get_calendar(calendar_id)
            event = calendar.get_event(event_id)
            event.delete()

        return True

    async def get_free_busy(
        self,
        emails: List[str],
        start: datetime,
        end: datetime,
    ) -> Dict[str, List[FreeBusy]]:
        """
        Get free/busy information for multiple users.

        Args:
            emails: List of email addresses
            start: Start datetime
            end: End datetime

        Returns:
            Dict mapping email to list of busy periods
        """
        if self.config.provider == CalendarProvider.GOOGLE:
            return await self._get_google_free_busy(emails, start, end)
        else:
            raise NotImplementedError(f"Free/busy not implemented for {self.config.provider}")

    async def _get_google_free_busy(
        self,
        emails: List[str],
        start: datetime,
        end: datetime,
    ) -> Dict[str, List[FreeBusy]]:
        """Get free/busy from Google Calendar."""
        service = await self._get_google_service()
        loop = asyncio.get_running_loop()

        body = {
            "timeMin": start.isoformat() + "Z",
            "timeMax": end.isoformat() + "Z",
            "items": [{"id": email} for email in emails],
        }

        def _query():
            return service.freebusy().query(body=body).execute()

        result = await loop.run_in_executor(None, _query)

        free_busy = {}
        for email in emails:
            calendar_data = result.get("calendars", {}).get(email, {})
            busy_periods = []

            for busy in calendar_data.get("busy", []):
                busy_periods.append(
                    FreeBusy(
                        start=datetime.fromisoformat(busy["start"].replace("Z", "+00:00")),
                        end=datetime.fromisoformat(busy["end"].replace("Z", "+00:00")),
                    )
                )

            free_busy[email] = busy_periods

        return free_busy

    async def find_available_slots(
        self,
        emails: List[str],
        start: datetime,
        end: datetime,
        duration_minutes: int = 30,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Find available time slots for a group.

        Args:
            emails: List of attendee emails
            start: Start of search range
            end: End of search range
            duration_minutes: Required slot duration

        Returns:
            List of (start, end) tuples for available slots
        """
        free_busy = await self.get_free_busy(emails, start, end)

        # Merge all busy periods
        all_busy = []
        for periods in free_busy.values():
            all_busy.extend(periods)

        # Sort by start time
        all_busy.sort(key=lambda x: x.start)

        # Find gaps
        duration = timedelta(minutes=duration_minutes)
        available = []
        current = start

        for busy in all_busy:
            if busy.start > current and busy.start - current >= duration:
                available.append((current, busy.start))
            current = max(current, busy.end)

        if end > current and end - current >= duration:
            available.append((current, end))

        return available
