"""
Slack Integration for ag3ntwerk.

Provides team messaging, channel management, and notifications.

Requirements:
    - pip install slack-sdk

Slack is ideal for:
    - Agent announcements and updates
    - Team coordination and messaging
    - Automated notifications and alerts
    - Channel monitoring and summarization
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Configuration for Slack integration."""

    bot_token: str = ""
    app_token: str = ""  # For socket mode
    signing_secret: str = ""
    default_channel: str = ""
    rate_limit_delay: float = 1.0


@dataclass
class SlackUser:
    """Represents a Slack user."""

    id: str
    name: str
    real_name: str = ""
    email: str = ""
    is_bot: bool = False
    is_admin: bool = False
    avatar_url: str = ""


@dataclass
class SlackChannel:
    """Represents a Slack channel."""

    id: str
    name: str
    is_private: bool = False
    is_archived: bool = False
    topic: str = ""
    purpose: str = ""
    member_count: int = 0
    created: Optional[datetime] = None


@dataclass
class SlackMessage:
    """Represents a Slack message."""

    text: str
    channel: str
    user: Optional[str] = None
    timestamp: Optional[str] = None
    thread_ts: Optional[str] = None
    blocks: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    reactions: List[Dict[str, Any]] = field(default_factory=list)
    reply_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SlackReaction:
    """Represents a reaction to a message."""

    name: str
    count: int
    users: List[str] = field(default_factory=list)


class SlackIntegration:
    """
    Integration with Slack for team communication.

    Provides messaging, channel management, and event handling.

    Example:
        integration = SlackIntegration(SlackConfig(
            bot_token="xoxb-...",
        ))

        # Send a message
        await integration.send_message(
            channel="#general",
            text="Hello from the CEO!",
        )

        # Read channel history
        messages = await integration.get_channel_history("#engineering")

        # React to a message
        await integration.add_reaction(message, "thumbsup")
    """

    def __init__(self, config: SlackConfig):
        """Initialize Slack integration."""
        self.config = config
        self._client = None
        self._async_client = None
        self._socket_client = None

    def _get_client(self):
        """Get synchronous Slack client."""
        if self._client is None:
            try:
                from slack_sdk import WebClient

                self._client = WebClient(token=self.config.bot_token)
            except ImportError:
                raise ImportError("slack-sdk not installed. Install with: pip install slack-sdk")
        return self._client

    def _get_async_client(self):
        """Get async Slack client."""
        if self._async_client is None:
            try:
                from slack_sdk.web.async_client import AsyncWebClient

                self._async_client = AsyncWebClient(token=self.config.bot_token)
            except ImportError:
                raise ImportError("slack-sdk not installed. Install with: pip install slack-sdk")
        return self._async_client

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        unfurl_links: bool = True,
        unfurl_media: bool = True,
    ) -> SlackMessage:
        """
        Send a message to a channel.

        Args:
            channel: Channel ID or name
            text: Message text
            thread_ts: Thread timestamp to reply to
            blocks: Block Kit blocks
            attachments: Legacy attachments
            unfurl_links: Unfurl URLs
            unfurl_media: Unfurl media

        Returns:
            Sent SlackMessage
        """
        client = self._get_async_client()

        response = await client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            blocks=blocks,
            attachments=attachments,
            unfurl_links=unfurl_links,
            unfurl_media=unfurl_media,
        )

        return SlackMessage(
            text=text,
            channel=response["channel"],
            timestamp=response["ts"],
            thread_ts=thread_ts,
            blocks=blocks,
            attachments=attachments,
        )

    async def send_dm(
        self,
        user: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> SlackMessage:
        """
        Send a direct message to a user.

        Args:
            user: User ID
            text: Message text
            blocks: Block Kit blocks

        Returns:
            Sent SlackMessage
        """
        client = self._get_async_client()

        # Open DM channel
        response = await client.conversations_open(users=[user])
        channel_id = response["channel"]["id"]

        return await self.send_message(channel_id, text, blocks=blocks)

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> SlackMessage:
        """
        Update an existing message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            text: New message text
            blocks: New Block Kit blocks

        Returns:
            Updated SlackMessage
        """
        client = self._get_async_client()

        response = await client.chat_update(
            channel=channel,
            ts=timestamp,
            text=text,
            blocks=blocks,
        )

        return SlackMessage(
            text=text,
            channel=channel,
            timestamp=timestamp,
            blocks=blocks,
        )

    async def delete_message(
        self,
        channel: str,
        timestamp: str,
    ) -> bool:
        """
        Delete a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp

        Returns:
            True if successful
        """
        client = self._get_async_client()
        await client.chat_delete(channel=channel, ts=timestamp)
        return True

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str,
    ) -> bool:
        """
        Add a reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            reaction: Reaction emoji name (without colons)

        Returns:
            True if successful
        """
        client = self._get_async_client()
        await client.reactions_add(
            channel=channel,
            timestamp=timestamp,
            name=reaction,
        )
        return True

    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> List[SlackMessage]:
        """
        Get message history from a channel.

        Args:
            channel: Channel ID or name
            limit: Maximum messages to retrieve
            oldest: Oldest message timestamp
            latest: Latest message timestamp

        Returns:
            List of SlackMessages
        """
        client = self._get_async_client()

        # Resolve channel name to ID if needed
        if channel.startswith("#"):
            channel = await self._resolve_channel_id(channel[1:])

        response = await client.conversations_history(
            channel=channel,
            limit=limit,
            oldest=oldest,
            latest=latest,
        )

        messages = []
        for msg in response.get("messages", []):
            messages.append(
                SlackMessage(
                    text=msg.get("text", ""),
                    channel=channel,
                    user=msg.get("user"),
                    timestamp=msg.get("ts"),
                    thread_ts=msg.get("thread_ts"),
                    blocks=msg.get("blocks"),
                    attachments=msg.get("attachments"),
                    reactions=[
                        {"name": r["name"], "count": r["count"]} for r in msg.get("reactions", [])
                    ],
                    reply_count=msg.get("reply_count", 0),
                )
            )

        return messages

    async def get_thread_replies(
        self,
        channel: str,
        thread_ts: str,
        limit: int = 100,
    ) -> List[SlackMessage]:
        """
        Get replies in a thread.

        Args:
            channel: Channel ID
            thread_ts: Parent message timestamp
            limit: Maximum replies to retrieve

        Returns:
            List of SlackMessages
        """
        client = self._get_async_client()

        response = await client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=limit,
        )

        messages = []
        for msg in response.get("messages", [])[1:]:  # Skip parent
            messages.append(
                SlackMessage(
                    text=msg.get("text", ""),
                    channel=channel,
                    user=msg.get("user"),
                    timestamp=msg.get("ts"),
                    thread_ts=thread_ts,
                )
            )

        return messages

    async def get_channels(
        self,
        exclude_archived: bool = True,
        types: str = "public_channel,private_channel",
    ) -> List[SlackChannel]:
        """
        Get list of channels.

        Args:
            exclude_archived: Exclude archived channels
            types: Channel types to include

        Returns:
            List of SlackChannels
        """
        client = self._get_async_client()

        channels = []
        cursor = None

        while True:
            response = await client.conversations_list(
                exclude_archived=exclude_archived,
                types=types,
                cursor=cursor,
            )

            for ch in response.get("channels", []):
                channels.append(
                    SlackChannel(
                        id=ch["id"],
                        name=ch["name"],
                        is_private=ch.get("is_private", False),
                        is_archived=ch.get("is_archived", False),
                        topic=ch.get("topic", {}).get("value", ""),
                        purpose=ch.get("purpose", {}).get("value", ""),
                        member_count=ch.get("num_members", 0),
                    )
                )

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return channels

    async def get_users(
        self,
        include_bots: bool = False,
    ) -> List[SlackUser]:
        """
        Get list of users.

        Args:
            include_bots: Include bot users

        Returns:
            List of SlackUsers
        """
        client = self._get_async_client()

        users = []
        cursor = None

        while True:
            response = await client.users_list(cursor=cursor)

            for user in response.get("members", []):
                if not include_bots and user.get("is_bot", False):
                    continue

                users.append(
                    SlackUser(
                        id=user["id"],
                        name=user.get("name", ""),
                        real_name=user.get("real_name", ""),
                        email=user.get("profile", {}).get("email", ""),
                        is_bot=user.get("is_bot", False),
                        is_admin=user.get("is_admin", False),
                        avatar_url=user.get("profile", {}).get("image_72", ""),
                    )
                )

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return users

    async def get_user_info(self, user_id: str) -> SlackUser:
        """Get information about a user."""
        client = self._get_async_client()
        response = await client.users_info(user=user_id)
        user = response["user"]

        return SlackUser(
            id=user["id"],
            name=user.get("name", ""),
            real_name=user.get("real_name", ""),
            email=user.get("profile", {}).get("email", ""),
            is_bot=user.get("is_bot", False),
            is_admin=user.get("is_admin", False),
            avatar_url=user.get("profile", {}).get("image_72", ""),
        )

    async def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
    ) -> List[SlackMessage]:
        """
        Search for messages.

        Args:
            query: Search query
            count: Number of results
            sort: Sort order (timestamp or score)

        Returns:
            List of matching SlackMessages
        """
        client = self._get_async_client()

        response = await client.search_messages(
            query=query,
            count=count,
            sort=sort,
        )

        messages = []
        for match in response.get("messages", {}).get("matches", []):
            messages.append(
                SlackMessage(
                    text=match.get("text", ""),
                    channel=match.get("channel", {}).get("id", ""),
                    user=match.get("user"),
                    timestamp=match.get("ts"),
                )
            )

        return messages

    async def upload_file(
        self,
        channels: Union[str, List[str]],
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        filename: str = "file",
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack.

        Args:
            channels: Channel(s) to share to
            file_path: Path to file
            content: File content (alternative to file_path)
            filename: Filename
            title: File title
            initial_comment: Comment to include

        Returns:
            File info dict
        """
        client = self._get_async_client()

        if isinstance(channels, str):
            channels = [channels]

        kwargs = {
            "channels": ",".join(channels),
            "filename": filename,
            "title": title,
            "initial_comment": initial_comment,
        }

        if file_path:
            kwargs["file"] = file_path
        elif content:
            kwargs["content"] = content

        response = await client.files_upload_v2(**kwargs)
        return response.get("file", {})

    async def create_channel(
        self,
        name: str,
        is_private: bool = False,
    ) -> SlackChannel:
        """
        Create a new channel.

        Args:
            name: Channel name
            is_private: Create as private channel

        Returns:
            Created SlackChannel
        """
        client = self._get_async_client()

        response = await client.conversations_create(
            name=name,
            is_private=is_private,
        )

        ch = response["channel"]
        return SlackChannel(
            id=ch["id"],
            name=ch["name"],
            is_private=is_private,
        )

    async def invite_to_channel(
        self,
        channel: str,
        users: List[str],
    ) -> bool:
        """
        Invite users to a channel.

        Args:
            channel: Channel ID
            users: List of user IDs

        Returns:
            True if successful
        """
        client = self._get_async_client()
        await client.conversations_invite(channel=channel, users=users)
        return True

    async def set_channel_topic(
        self,
        channel: str,
        topic: str,
    ) -> bool:
        """Set a channel's topic."""
        client = self._get_async_client()
        await client.conversations_setTopic(channel=channel, topic=topic)
        return True

    async def _resolve_channel_id(self, name: str) -> str:
        """Resolve channel name to ID."""
        channels = await self.get_channels()
        for ch in channels:
            if ch.name == name:
                return ch.id
        raise ValueError(f"Channel not found: {name}")

    def build_blocks(self) -> "BlockBuilder":
        """Get a Block Kit builder."""
        return BlockBuilder()


class BlockBuilder:
    """Helper class for building Slack Block Kit blocks."""

    def __init__(self):
        self.blocks = []

    def add_section(
        self,
        text: str,
        accessory: Optional[Dict] = None,
    ) -> "BlockBuilder":
        """Add a section block."""
        block = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        }
        if accessory:
            block["accessory"] = accessory
        self.blocks.append(block)
        return self

    def add_header(self, text: str) -> "BlockBuilder":
        """Add a header block."""
        self.blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": text},
            }
        )
        return self

    def add_divider(self) -> "BlockBuilder":
        """Add a divider block."""
        self.blocks.append({"type": "divider"})
        return self

    def add_context(self, elements: List[str]) -> "BlockBuilder":
        """Add a context block."""
        self.blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": el} for el in elements],
            }
        )
        return self

    def add_image(
        self,
        url: str,
        alt_text: str,
        title: Optional[str] = None,
    ) -> "BlockBuilder":
        """Add an image block."""
        block = {
            "type": "image",
            "image_url": url,
            "alt_text": alt_text,
        }
        if title:
            block["title"] = {"type": "plain_text", "text": title}
        self.blocks.append(block)
        return self

    def add_actions(self, elements: List[Dict]) -> "BlockBuilder":
        """Add an actions block."""
        self.blocks.append(
            {
                "type": "actions",
                "elements": elements,
            }
        )
        return self

    def add_button(
        self,
        text: str,
        action_id: str,
        value: str = "",
        style: Optional[str] = None,
    ) -> Dict:
        """Create a button element (for use in actions)."""
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
            "value": value,
        }
        if style:
            button["style"] = style
        return button

    def build(self) -> List[Dict]:
        """Build and return the blocks."""
        return self.blocks
