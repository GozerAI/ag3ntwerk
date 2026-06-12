"""Tests for ICS (iCalendar) generator."""

import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.integrations.communication.ics_generator import (
    generate_ics,
    _format_dt,
    _escape_text,
    _fold_line,
)


# ============================================================
# Helper formatting
# ============================================================


class TestFormatDt:
    def test_utc_datetime(self):
        dt = datetime(2026, 3, 25, 14, 30, 0, tzinfo=timezone.utc)
        assert _format_dt(dt) == "20260325T143000Z"

    def test_naive_datetime(self):
        dt = datetime(2026, 1, 1, 0, 0, 0)
        assert _format_dt(dt) == "20260101T000000Z"

    def test_offset_datetime(self):
        est = timezone(timedelta(hours=-5))
        dt = datetime(2026, 3, 25, 10, 0, 0, tzinfo=est)
        # 10:00 EST = 15:00 UTC
        assert _format_dt(dt) == "20260325T150000Z"


class TestEscapeText:
    def test_semicolons(self):
        assert _escape_text("a;b") == "a\\;b"

    def test_commas(self):
        assert _escape_text("a,b") == "a\\,b"

    def test_newlines(self):
        assert _escape_text("a\nb") == "a\\nb"

    def test_backslashes(self):
        assert _escape_text("a\\b") == "a\\\\b"

    def test_combined(self):
        assert _escape_text("a;b,c\nd\\e") == "a\\;b\\,c\\nd\\\\e"

    def test_plain_text_unchanged(self):
        assert _escape_text("Hello World") == "Hello World"


class TestFoldLine:
    def test_short_line_unchanged(self):
        line = "SHORT"
        assert _fold_line(line) == "SHORT"

    def test_exactly_75_bytes(self):
        line = "A" * 75
        assert _fold_line(line) == line

    def test_long_line_folded(self):
        line = "A" * 100
        folded = _fold_line(line)
        assert "\r\n " in folded
        # Unfolded result should reconstruct original
        unfolded = folded.replace("\r\n ", "")
        assert unfolded == line


# ============================================================
# ICS Generation
# ============================================================


class TestGenerateIcs:
    def _parse_ics(self, ics_bytes: bytes) -> str:
        return ics_bytes.decode("utf-8")

    def test_basic_event(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics(
            title="Test Event",
            description="A test event",
            start=start,
            end=end,
        ))
        assert "BEGIN:VCALENDAR" in ics
        assert "END:VCALENDAR" in ics
        assert "BEGIN:VEVENT" in ics
        assert "END:VEVENT" in ics
        assert "SUMMARY:Test Event" in ics
        assert "DESCRIPTION:A test event" in ics
        assert "DTSTART:20260325T140000Z" in ics
        assert "DTEND:20260325T143000Z" in ics

    def test_returns_bytes(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        result = generate_ics("Test", "Desc", start, end)
        assert isinstance(result, bytes)

    def test_vcalendar_headers(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end))
        assert "VERSION:2.0" in ics
        assert "PRODID:-//ag3ntwerk//Meeting Intelligence//EN" in ics
        assert "METHOD:REQUEST" in ics

    def test_custom_uid(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end, uid="custom-123@test"))
        assert "UID:custom-123@test" in ics

    def test_auto_uid(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end))
        assert "UID:" in ics
        assert "@ag3ntwerk" in ics

    def test_with_attendees(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics(
            "T", "D", start, end,
            attendees=["alice@example.com", "bob@example.com"],
        ))
        assert "mailto:alice@example.com" in ics
        assert "mailto:bob@example.com" in ics
        assert "ROLE=REQ-PARTICIPANT" in ics

    def test_no_attendees(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end))
        assert "ATTENDEE" not in ics

    def test_with_location(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics(
            "T", "D", start, end, location="Conference Room A",
        ))
        assert "LOCATION:Conference Room A" in ics

    def test_alarm_present(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end, reminder_minutes=15))
        assert "BEGIN:VALARM" in ics
        assert "TRIGGER:-PT15M" in ics
        assert "ACTION:DISPLAY" in ics

    def test_no_alarm_when_zero(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end, reminder_minutes=0))
        assert "BEGIN:VALARM" not in ics

    def test_special_characters_escaped(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics(
            title="Review; Plan, Act",
            description="Line1\nLine2",
            start=start,
            end=end,
        ))
        assert "\\;" in ics
        assert "\\," in ics
        assert "\\n" in ics

    def test_crlf_line_endings(self):
        start = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        ics = self._parse_ics(generate_ics("T", "D", start, end))
        # ICS standard requires CRLF
        assert "\r\n" in ics
