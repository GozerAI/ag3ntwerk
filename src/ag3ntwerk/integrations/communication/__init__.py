"""
Communication Integrations for ag3ntwerk.

This package provides integrations with communication platforms:
- Slack: Team messaging and notifications
- Discord: Community and team communication
- Email: IMAP/SMTP email handling
- Calendar: Google/Outlook calendar management
- Notion: Knowledge base and documentation
"""

from ag3ntwerk.integrations.communication.slack import (
    SlackIntegration,
    SlackConfig,
    SlackMessage,
    SlackChannel,
)
from ag3ntwerk.integrations.communication.discord import (
    DiscordIntegration,
    DiscordConfig,
    DiscordMessage,
)
from ag3ntwerk.integrations.communication.email import (
    EmailIntegration,
    EmailConfig,
    EmailMessage,
    EmailFilter,
)
from ag3ntwerk.integrations.communication.calendar import (
    CalendarIntegration,
    CalendarConfig,
    CalendarEvent,
    CalendarProvider,
)
from ag3ntwerk.integrations.communication.notion import (
    NotionIntegration,
    NotionConfig,
    NotionPage,
    NotionDatabase,
)

__all__ = [
    "SlackIntegration",
    "SlackConfig",
    "SlackMessage",
    "SlackChannel",
    "DiscordIntegration",
    "DiscordConfig",
    "DiscordMessage",
    "EmailIntegration",
    "EmailConfig",
    "EmailMessage",
    "EmailFilter",
    "CalendarIntegration",
    "CalendarConfig",
    "CalendarEvent",
    "CalendarProvider",
    "NotionIntegration",
    "NotionConfig",
    "NotionPage",
    "NotionDatabase",
]
