"""
Discord Integration for ag3ntwerk.

Provides community and team communication via Discord.

Requirements:
    - pip install discord.py

Discord is ideal for:
    - Community engagement
    - Team communication with voice support
    - Bot-based automation
    - Real-time notifications
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class DiscordConfig:
    """Configuration for Discord integration."""

    bot_token: str = ""
    application_id: str = ""
    default_guild: Optional[str] = None
    intents: List[str] = field(default_factory=lambda: ["messages", "guilds"])


@dataclass
class DiscordUser:
    """Represents a Discord user."""

    id: str
    name: str
    discriminator: str = ""
    avatar_url: str = ""
    is_bot: bool = False


@dataclass
class DiscordChannel:
    """Represents a Discord channel."""

    id: str
    name: str
    guild_id: str
    type: str = "text"  # text, voice, category, etc.
    topic: str = ""
    position: int = 0


@dataclass
class DiscordMessage:
    """Represents a Discord message."""

    content: str
    channel_id: str
    author: Optional[DiscordUser] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    embeds: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    reactions: List[Dict[str, Any]] = field(default_factory=list)
    reference: Optional[str] = None  # Reply reference


@dataclass
class DiscordEmbed:
    """Represents a Discord embed."""

    title: str = ""
    description: str = ""
    color: int = 0x5865F2  # Discord blurple
    url: str = ""
    timestamp: Optional[datetime] = None
    footer: Optional[Dict[str, str]] = None
    image: Optional[str] = None
    thumbnail: Optional[str] = None
    author: Optional[Dict[str, str]] = None
    fields: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Discord embed dict."""
        embed = {}
        if self.title:
            embed["title"] = self.title
        if self.description:
            embed["description"] = self.description
        if self.color:
            embed["color"] = self.color
        if self.url:
            embed["url"] = self.url
        if self.timestamp:
            embed["timestamp"] = self.timestamp.isoformat()
        if self.footer:
            embed["footer"] = self.footer
        if self.image:
            embed["image"] = {"url": self.image}
        if self.thumbnail:
            embed["thumbnail"] = {"url": self.thumbnail}
        if self.author:
            embed["author"] = self.author
        if self.fields:
            embed["fields"] = self.fields
        return embed

    def add_field(
        self,
        name: str,
        value: str,
        inline: bool = False,
    ) -> "DiscordEmbed":
        """Add a field to the embed."""
        self.fields.append(
            {
                "name": name,
                "value": value,
                "inline": inline,
            }
        )
        return self


class DiscordIntegration:
    """
    Integration with Discord for community communication.

    Provides messaging, channel management, and bot functionality.

    Example:
        integration = DiscordIntegration(DiscordConfig(
            bot_token="...",
        ))

        # Send a message
        await integration.send_message(
            channel_id="123456789",
            content="Hello from ag3ntwerk!",
        )

        # Send an embed
        embed = DiscordEmbed(
            title="Weekly Report",
            description="Here's what happened this week.",
            color=0x00FF00,
        )
        await integration.send_embed(channel_id, embed)
    """

    def __init__(self, config: DiscordConfig):
        """Initialize Discord integration."""
        self.config = config
        self._client = None
        self._http = None

    async def _get_client(self):
        """Get Discord client."""
        if self._client is None:
            try:
                import discord

                intents = discord.Intents.default()
                if "messages" in self.config.intents:
                    intents.message_content = True
                if "members" in self.config.intents:
                    intents.members = True

                self._client = discord.Client(intents=intents)
            except ImportError:
                raise ImportError("discord.py not installed. Install with: pip install discord.py")
        return self._client

    async def _get_http(self):
        """Get HTTP client for API calls without full bot."""
        if self._http is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession()
                self._http = True
            except ImportError:
                raise ImportError("aiohttp required for Discord HTTP API")
        return self._session

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
    ) -> Dict:
        """Make a Discord API request."""
        session = await self._get_http()
        url = f"https://discord.com/api/v10{endpoint}"
        headers = {
            "Authorization": f"Bot {self.config.bot_token}",
            "Content-Type": "application/json",
        }

        async with session.request(method, url, headers=headers, json=json) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Discord API error: {resp.status} - {text}")
            if resp.status == 204:
                return {}
            return await resp.json()

    async def send_message(
        self,
        channel_id: str,
        content: str,
        embeds: Optional[List[DiscordEmbed]] = None,
        reply_to: Optional[str] = None,
        tts: bool = False,
    ) -> DiscordMessage:
        """
        Send a message to a channel.

        Args:
            channel_id: Channel ID
            content: Message content
            embeds: List of embeds
            reply_to: Message ID to reply to
            tts: Text-to-speech

        Returns:
            Sent DiscordMessage
        """
        payload = {
            "content": content,
            "tts": tts,
        }

        if embeds:
            payload["embeds"] = [e.to_dict() for e in embeds]

        if reply_to:
            payload["message_reference"] = {"message_id": reply_to}

        data = await self._api_request(
            "POST",
            f"/channels/{channel_id}/messages",
            json=payload,
        )

        return DiscordMessage(
            content=content,
            channel_id=channel_id,
            id=data.get("id"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                if data.get("timestamp")
                else None
            ),
        )

    async def send_embed(
        self,
        channel_id: str,
        embed: DiscordEmbed,
        content: str = "",
    ) -> DiscordMessage:
        """
        Send an embed to a channel.

        Args:
            channel_id: Channel ID
            embed: Embed to send
            content: Optional text content

        Returns:
            Sent DiscordMessage
        """
        return await self.send_message(
            channel_id=channel_id,
            content=content,
            embeds=[embed],
        )

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None,
    ) -> DiscordMessage:
        """
        Edit an existing message.

        Args:
            channel_id: Channel ID
            message_id: Message ID to edit
            content: New content
            embeds: New embeds

        Returns:
            Edited DiscordMessage
        """
        payload = {}
        if content is not None:
            payload["content"] = content
        if embeds is not None:
            payload["embeds"] = [e.to_dict() for e in embeds]

        data = await self._api_request(
            "PATCH",
            f"/channels/{channel_id}/messages/{message_id}",
            json=payload,
        )

        return DiscordMessage(
            content=data.get("content", ""),
            channel_id=channel_id,
            id=message_id,
        )

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """Delete a message."""
        await self._api_request(
            "DELETE",
            f"/channels/{channel_id}/messages/{message_id}",
        )
        return True

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """
        Add a reaction to a message.

        Args:
            channel_id: Channel ID
            message_id: Message ID
            emoji: Emoji (unicode or custom format)

        Returns:
            True if successful
        """
        import urllib.parse

        emoji_encoded = urllib.parse.quote(emoji)

        await self._api_request(
            "PUT",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji_encoded}/@me",
        )
        return True

    async def get_channel_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[DiscordMessage]:
        """
        Get messages from a channel.

        Args:
            channel_id: Channel ID
            limit: Maximum messages (1-100)
            before: Get messages before this ID
            after: Get messages after this ID

        Returns:
            List of DiscordMessages
        """
        params = f"?limit={min(limit, 100)}"
        if before:
            params += f"&before={before}"
        if after:
            params += f"&after={after}"

        data = await self._api_request(
            "GET",
            f"/channels/{channel_id}/messages{params}",
        )

        messages = []
        for msg in data:
            author = (
                DiscordUser(
                    id=msg["author"]["id"],
                    name=msg["author"]["username"],
                    discriminator=msg["author"].get("discriminator", ""),
                    is_bot=msg["author"].get("bot", False),
                )
                if msg.get("author")
                else None
            )

            messages.append(
                DiscordMessage(
                    content=msg.get("content", ""),
                    channel_id=channel_id,
                    author=author,
                    id=msg.get("id"),
                    timestamp=(
                        datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
                        if msg.get("timestamp")
                        else None
                    ),
                    embeds=msg.get("embeds", []),
                    attachments=msg.get("attachments", []),
                )
            )

        return messages

    async def get_guild_channels(
        self,
        guild_id: str,
    ) -> List[DiscordChannel]:
        """
        Get channels in a guild.

        Args:
            guild_id: Guild ID

        Returns:
            List of DiscordChannels
        """
        data = await self._api_request(
            "GET",
            f"/guilds/{guild_id}/channels",
        )

        channels = []
        for ch in data:
            channel_types = {
                0: "text",
                2: "voice",
                4: "category",
                5: "news",
                13: "stage",
                15: "forum",
            }

            channels.append(
                DiscordChannel(
                    id=ch["id"],
                    name=ch.get("name", ""),
                    guild_id=guild_id,
                    type=channel_types.get(ch.get("type", 0), "unknown"),
                    topic=ch.get("topic", "") or "",
                    position=ch.get("position", 0),
                )
            )

        return channels

    async def get_guild_members(
        self,
        guild_id: str,
        limit: int = 100,
    ) -> List[DiscordUser]:
        """
        Get members of a guild.

        Args:
            guild_id: Guild ID
            limit: Maximum members to retrieve

        Returns:
            List of DiscordUsers
        """
        data = await self._api_request(
            "GET",
            f"/guilds/{guild_id}/members?limit={limit}",
        )

        members = []
        for member in data:
            user = member.get("user", {})
            members.append(
                DiscordUser(
                    id=user.get("id", ""),
                    name=user.get("username", ""),
                    discriminator=user.get("discriminator", ""),
                    avatar_url=(
                        f"https://cdn.discordapp.com/avatars/{user.get('id')}/{user.get('avatar')}.png"
                        if user.get("avatar")
                        else ""
                    ),
                    is_bot=user.get("bot", False),
                )
            )

        return members

    async def create_channel(
        self,
        guild_id: str,
        name: str,
        channel_type: str = "text",
        topic: str = "",
        parent_id: Optional[str] = None,
    ) -> DiscordChannel:
        """
        Create a new channel.

        Args:
            guild_id: Guild ID
            name: Channel name
            channel_type: Channel type (text, voice, category)
            topic: Channel topic
            parent_id: Parent category ID

        Returns:
            Created DiscordChannel
        """
        type_map = {
            "text": 0,
            "voice": 2,
            "category": 4,
            "news": 5,
        }

        payload = {
            "name": name,
            "type": type_map.get(channel_type, 0),
        }

        if topic:
            payload["topic"] = topic
        if parent_id:
            payload["parent_id"] = parent_id

        data = await self._api_request(
            "POST",
            f"/guilds/{guild_id}/channels",
            json=payload,
        )

        return DiscordChannel(
            id=data["id"],
            name=data["name"],
            guild_id=guild_id,
            type=channel_type,
            topic=topic,
        )

    async def create_thread(
        self,
        channel_id: str,
        name: str,
        message_id: Optional[str] = None,
        auto_archive_duration: int = 1440,
    ) -> DiscordChannel:
        """
        Create a thread.

        Args:
            channel_id: Parent channel ID
            name: Thread name
            message_id: Message to create thread from
            auto_archive_duration: Minutes until auto-archive

        Returns:
            Created thread as DiscordChannel
        """
        if message_id:
            endpoint = f"/channels/{channel_id}/messages/{message_id}/threads"
        else:
            endpoint = f"/channels/{channel_id}/threads"

        payload = {
            "name": name,
            "auto_archive_duration": auto_archive_duration,
        }

        if not message_id:
            payload["type"] = 11  # Public thread

        data = await self._api_request("POST", endpoint, json=payload)

        return DiscordChannel(
            id=data["id"],
            name=data["name"],
            guild_id=data.get("guild_id", ""),
            type="thread",
        )

    async def send_dm(
        self,
        user_id: str,
        content: str,
        embeds: Optional[List[DiscordEmbed]] = None,
    ) -> DiscordMessage:
        """
        Send a direct message to a user.

        Args:
            user_id: User ID
            content: Message content
            embeds: Optional embeds

        Returns:
            Sent DiscordMessage
        """
        # Create DM channel
        data = await self._api_request(
            "POST",
            "/users/@me/channels",
            json={"recipient_id": user_id},
        )

        channel_id = data["id"]
        return await self.send_message(channel_id, content, embeds=embeds)

    def create_embed(
        self,
        title: str = "",
        description: str = "",
        color: int = 0x5865F2,
    ) -> DiscordEmbed:
        """Create a new embed builder."""
        return DiscordEmbed(
            title=title,
            description=description,
            color=color,
        )

    async def close(self):
        """Close the integration and cleanup."""
        if hasattr(self, "_session") and self._session:
            await self._session.close()
