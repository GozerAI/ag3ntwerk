"""
Communication Tool Definitions.

Tools for Slack, Email, Calendar, Discord, and Notion.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ParameterType,
)


class SendSlackMessageTool(BaseTool):
    """Send messages to Slack channels."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="send_slack_message",
            description="Send a message to a Slack channel or user",
            category=ToolCategory.COMMUNICATION,
            tags=["slack", "message", "chat", "notify"],
            examples=[
                "Send 'Hello team!' to #general",
                "Post project update to Slack",
                "Notify the team on Slack",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="channel",
                description="Channel name (e.g., #general) or user ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="message",
                description="Message text to send",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="thread_ts",
                description="Thread timestamp for replies",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        channel = kwargs.get("channel")
        message = kwargs.get("message")
        thread_ts = kwargs.get("thread_ts")

        try:
            from ag3ntwerk.integrations.communication.slack import SlackIntegration

            slack = SlackIntegration()
            result = await slack.send_message(
                channel=channel,
                text=message,
                thread_ts=thread_ts,
            )

            return ToolResult(
                success=True,
                data={
                    "message_id": result.get("ts"),
                    "channel": channel,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class SendEmailTool(BaseTool):
    """Send emails via SMTP or API."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="send_email",
            description="Send an email to one or more recipients",
            category=ToolCategory.COMMUNICATION,
            tags=["email", "send", "message", "notify"],
            examples=[
                "Send email to john@example.com",
                "Email the report to the team",
                "Send meeting notes via email",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="to",
                description="Recipient email address(es)",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="subject",
                description="Email subject line",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="body",
                description="Email body content",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="html",
                description="Whether body is HTML",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
            ToolParameter(
                name="cc",
                description="CC recipients",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        html = kwargs.get("html", False)
        cc = kwargs.get("cc")

        try:
            from ag3ntwerk.integrations.communication.email import EmailIntegration

            email = EmailIntegration()

            # Convert to list if string
            to_list = [to] if isinstance(to, str) else to
            cc_list = [cc] if cc and isinstance(cc, str) else cc

            result = await email.send(
                to=to_list,
                subject=subject,
                body=body,
                html=html,
                cc=cc_list,
            )

            return ToolResult(
                success=True,
                data={
                    "message_id": result.message_id,
                    "recipients": to_list,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class CreateCalendarEventTool(BaseTool):
    """Create calendar events."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_calendar_event",
            description="Create a calendar event or meeting",
            category=ToolCategory.COMMUNICATION,
            tags=["calendar", "meeting", "event", "schedule"],
            examples=[
                "Schedule a meeting for tomorrow at 2pm",
                "Create a team standup event",
                "Add a reminder to the calendar",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="title",
                description="Event title",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="start_time",
                description="Start time (ISO format)",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="end_time",
                description="End time (ISO format)",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="description",
                description="Event description",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="attendees",
                description="Attendee emails (comma-separated)",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="location",
                description="Event location or meeting link",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        description = kwargs.get("description", "")
        attendees = kwargs.get("attendees", "")
        location = kwargs.get("location", "")

        try:
            from ag3ntwerk.integrations.communication.calendar import CalendarIntegration
            from datetime import datetime

            calendar = CalendarIntegration()

            # Parse attendees
            attendee_list = [a.strip() for a in attendees.split(",")] if attendees else []

            event = await calendar.create_event(
                summary=title,
                start=datetime.fromisoformat(start_time),
                end=datetime.fromisoformat(end_time),
                description=description,
                attendees=attendee_list,
                location=location,
            )

            return ToolResult(
                success=True,
                data={
                    "event_id": event.id,
                    "title": title,
                    "start": start_time,
                    "end": end_time,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class SendDiscordMessageTool(BaseTool):
    """Send messages to Discord channels."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="send_discord_message",
            description="Send a message to a Discord channel",
            category=ToolCategory.COMMUNICATION,
            tags=["discord", "message", "chat"],
            examples=[
                "Post announcement to Discord",
                "Send update to #announcements",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="channel_id",
                description="Discord channel ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="content",
                description="Message content",
                param_type=ParameterType.STRING,
                required=True,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        channel_id = kwargs.get("channel_id")
        content = kwargs.get("content")

        try:
            from ag3ntwerk.integrations.communication.discord import DiscordIntegration

            discord = DiscordIntegration()
            message = await discord.send_message(
                channel_id=channel_id,
                content=content,
            )

            return ToolResult(
                success=True,
                data={
                    "message_id": message.id,
                    "channel_id": channel_id,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class CreateNotionPageTool(BaseTool):
    """Create pages in Notion."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_notion_page",
            description="Create a new page in Notion",
            category=ToolCategory.COMMUNICATION,
            tags=["notion", "page", "document", "wiki"],
            examples=[
                "Create a meeting notes page in Notion",
                "Add a new wiki page",
                "Create project documentation",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="parent_id",
                description="Parent page or database ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="title",
                description="Page title",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="content",
                description="Page content (markdown supported)",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        parent_id = kwargs.get("parent_id")
        title = kwargs.get("title")
        content = kwargs.get("content", "")

        try:
            from ag3ntwerk.integrations.communication.notion import NotionIntegration

            notion = NotionIntegration()
            page = await notion.create_page(
                parent_id=parent_id,
                title=title,
                content=content,
            )

            return ToolResult(
                success=True,
                data={
                    "page_id": page.id,
                    "title": title,
                    "url": page.url,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
