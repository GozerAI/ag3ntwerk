"""
ICS (iCalendar) generator for ag3ntwerk.

Generates RFC 5545 compliant .ics files for calendar event invites.
Used by the meeting intelligence pipeline to send action item reminders
as email attachments that any calendar client can import.

No external dependencies — pure string formatting.

Usage:
    from ag3ntwerk.integrations.communication.ics_generator import generate_ics

    ics_bytes = generate_ics(
        title="Follow up on Q2 budget proposal",
        description="Action item from product sync meeting",
        start=datetime(2026, 3, 25, 14, 0),
        end=datetime(2026, 3, 25, 14, 30),
    )
    # Attach ics_bytes to an email as "reminder.ics"
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4


def _format_dt(dt: datetime) -> str:
    """Format datetime to iCalendar UTC format (YYYYMMDDTHHMMSSZ)."""
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt
    return utc_dt.strftime("%Y%m%dT%H%M%SZ")


def _escape_text(text: str) -> str:
    """Escape special characters for iCalendar text fields."""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\n", "\\n")
    return text


def _fold_line(line: str) -> str:
    """Fold long lines per RFC 5545 (max 75 octets)."""
    if len(line.encode("utf-8")) <= 75:
        return line
    result = []
    current = ""
    for char in line:
        test = current + char
        if len(test.encode("utf-8")) > 75:
            result.append(current)
            current = " " + char  # continuation line starts with space
        else:
            current = test
    if current:
        result.append(current)
    return "\r\n".join(result)


def generate_ics(
    title: str,
    description: str,
    start: datetime,
    end: datetime,
    attendees: Optional[List[str]] = None,
    uid: Optional[str] = None,
    location: str = "",
    reminder_minutes: int = 30,
) -> bytes:
    """
    Generate an RFC 5545 compliant .ics file.

    Args:
        title: Event title/summary
        description: Event description
        start: Event start time
        end: Event end time
        attendees: List of attendee email addresses
        uid: Unique event identifier (auto-generated if None)
        location: Event location
        reminder_minutes: Minutes before event to trigger alarm

    Returns:
        UTF-8 encoded .ics file content
    """
    uid = uid or f"{uuid4()}@ag3ntwerk"
    now = _format_dt(datetime.now(timezone.utc))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ag3ntwerk//Meeting Intelligence//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{_format_dt(start)}",
        f"DTEND:{_format_dt(end)}",
        _fold_line(f"SUMMARY:{_escape_text(title)}"),
        _fold_line(f"DESCRIPTION:{_escape_text(description)}"),
    ]

    if location:
        lines.append(_fold_line(f"LOCATION:{_escape_text(location)}"))

    if attendees:
        for email in attendees:
            lines.append(
                f"ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{email}"
            )

    # Add alarm/reminder
    if reminder_minutes > 0:
        lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT%dM" % reminder_minutes,
            "ACTION:DISPLAY",
            _fold_line(f"DESCRIPTION:{_escape_text(title)}"),
            "END:VALARM",
        ])

    lines.extend([
        "END:VEVENT",
        "END:VCALENDAR",
    ])

    return "\r\n".join(lines).encode("utf-8")
