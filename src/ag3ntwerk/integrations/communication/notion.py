"""
Notion Integration for ag3ntwerk.

Provides knowledge base and documentation management via Notion API.

Requirements:
    - pip install notion-client

Notion is ideal for:
    - Agent knowledge bases
    - Team documentation
    - Project wikis
    - Meeting notes
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class BlockType(str, Enum):
    """Notion block types."""

    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST = "bulleted_list_item"
    NUMBERED_LIST = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CODE = "code"
    QUOTE = "quote"
    CALLOUT = "callout"
    DIVIDER = "divider"
    TABLE = "table"
    IMAGE = "image"
    BOOKMARK = "bookmark"


class PropertyType(str, Enum):
    """Notion property types."""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone_number"
    RELATION = "relation"
    PEOPLE = "people"
    FILES = "files"
    STATUS = "status"


@dataclass
class NotionConfig:
    """Configuration for Notion integration."""

    api_key: str = ""
    default_workspace: str = ""


@dataclass
class RichText:
    """Represents rich text content."""

    content: str
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: str = "default"
    link: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        annotations = {
            "bold": self.bold,
            "italic": self.italic,
            "strikethrough": self.strikethrough,
            "underline": self.underline,
            "code": self.code,
            "color": self.color,
        }

        text_obj = {
            "type": "text",
            "text": {"content": self.content},
            "annotations": annotations,
        }

        if self.link:
            text_obj["text"]["link"] = {"url": self.link}

        return text_obj


@dataclass
class NotionBlock:
    """Represents a Notion block."""

    type: BlockType
    content: Union[str, List[RichText], Dict[str, Any]] = ""
    children: List["NotionBlock"] = field(default_factory=list)
    block_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        block = {"type": self.type.value}

        if self.type == BlockType.DIVIDER:
            block[self.type.value] = {}
        elif self.type == BlockType.CODE:
            if isinstance(self.content, dict):
                block[self.type.value] = self.content
            else:
                block[self.type.value] = {
                    "rich_text": [{"type": "text", "text": {"content": str(self.content)}}],
                    "language": "plain text",
                }
        elif self.type == BlockType.TO_DO:
            if isinstance(self.content, dict):
                block[self.type.value] = self.content
            else:
                block[self.type.value] = {
                    "rich_text": [{"type": "text", "text": {"content": str(self.content)}}],
                    "checked": False,
                }
        else:
            if isinstance(self.content, list):
                rich_text = [
                    rt.to_dict() if isinstance(rt, RichText) else rt for rt in self.content
                ]
            elif isinstance(self.content, str):
                rich_text = [{"type": "text", "text": {"content": self.content}}]
            else:
                rich_text = [{"type": "text", "text": {"content": str(self.content)}}]

            block[self.type.value] = {"rich_text": rich_text}

        if self.children:
            block[self.type.value]["children"] = [c.to_dict() for c in self.children]

        return block


@dataclass
class NotionPage:
    """Represents a Notion page."""

    title: str
    page_id: Optional[str] = None
    parent_id: Optional[str] = None
    parent_type: str = "page_id"  # page_id, database_id, workspace
    properties: Dict[str, Any] = field(default_factory=dict)
    blocks: List[NotionBlock] = field(default_factory=list)
    icon: Optional[str] = None  # Emoji or URL
    cover: Optional[str] = None  # URL
    url: str = ""
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None


@dataclass
class NotionDatabase:
    """Represents a Notion database."""

    title: str
    database_id: Optional[str] = None
    parent_id: Optional[str] = None
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    url: str = ""


@dataclass
class DatabaseQuery:
    """Query parameters for database queries."""

    filter: Optional[Dict[str, Any]] = None
    sorts: List[Dict[str, Any]] = field(default_factory=list)
    start_cursor: Optional[str] = None
    page_size: int = 100


class NotionIntegration:
    """
    Integration with Notion for knowledge management.

    Provides page creation, database management, and content operations.

    Example:
        integration = NotionIntegration(NotionConfig(
            api_key="secret_...",
        ))

        # Create a page
        page = await integration.create_page(NotionPage(
            title="Meeting Notes",
            parent_id="...",
            blocks=[
                NotionBlock(BlockType.HEADING_1, "Agenda"),
                NotionBlock(BlockType.BULLETED_LIST, "Item 1"),
                NotionBlock(BlockType.BULLETED_LIST, "Item 2"),
            ],
        ))

        # Query a database
        results = await integration.query_database(
            database_id="...",
            query=DatabaseQuery(
                filter={"property": "Status", "select": {"equals": "Done"}},
            ),
        )
    """

    def __init__(self, config: NotionConfig):
        """Initialize Notion integration."""
        self.config = config
        self._client = None

    def _get_client(self):
        """Get Notion client."""
        if self._client is None:
            try:
                from notion_client import Client

                self._client = Client(auth=self.config.api_key)
            except ImportError:
                raise ImportError(
                    "notion-client not installed. Install with: pip install notion-client"
                )
        return self._client

    async def _get_async_client(self):
        """Get async Notion client."""
        try:
            from notion_client import AsyncClient

            return AsyncClient(auth=self.config.api_key)
        except ImportError:
            raise ImportError(
                "notion-client not installed. Install with: pip install notion-client"
            )

    async def create_page(
        self,
        page: NotionPage,
    ) -> NotionPage:
        """
        Create a new Notion page.

        Args:
            page: NotionPage to create

        Returns:
            Created NotionPage with ID
        """
        client = await self._get_async_client()

        # Build parent
        if page.parent_type == "database_id":
            parent = {"database_id": page.parent_id}
        elif page.parent_type == "page_id":
            parent = {"page_id": page.parent_id}
        else:
            parent = {"workspace": True}

        # Build properties
        properties = {"title": {"title": [{"text": {"content": page.title}}]}}
        properties.update(page.properties)

        # Build request
        body = {
            "parent": parent,
            "properties": properties,
        }

        if page.icon:
            if page.icon.startswith("http"):
                body["icon"] = {"type": "external", "external": {"url": page.icon}}
            else:
                body["icon"] = {"type": "emoji", "emoji": page.icon}

        if page.cover:
            body["cover"] = {"type": "external", "external": {"url": page.cover}}

        if page.blocks:
            body["children"] = [b.to_dict() for b in page.blocks]

        result = await client.pages.create(**body)

        page.page_id = result["id"]
        page.url = result.get("url", "")
        page.created_time = datetime.fromisoformat(result["created_time"].replace("Z", "+00:00"))

        await client.aclose()
        return page

    async def get_page(self, page_id: str) -> NotionPage:
        """
        Get a Notion page.

        Args:
            page_id: Page ID

        Returns:
            NotionPage
        """
        client = await self._get_async_client()

        result = await client.pages.retrieve(page_id=page_id)

        # Extract title
        title = ""
        title_prop = result.get("properties", {}).get("title", {})
        if title_prop.get("title"):
            title = "".join(t.get("plain_text", "") for t in title_prop["title"])

        page = NotionPage(
            title=title,
            page_id=result["id"],
            properties=result.get("properties", {}),
            url=result.get("url", ""),
            created_time=datetime.fromisoformat(result["created_time"].replace("Z", "+00:00")),
            last_edited_time=datetime.fromisoformat(
                result["last_edited_time"].replace("Z", "+00:00")
            ),
        )

        # Get icon
        if result.get("icon"):
            if result["icon"]["type"] == "emoji":
                page.icon = result["icon"]["emoji"]
            elif result["icon"]["type"] == "external":
                page.icon = result["icon"]["external"]["url"]

        await client.aclose()
        return page

    async def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None,
        cover: Optional[str] = None,
        archived: Optional[bool] = None,
    ) -> NotionPage:
        """
        Update a Notion page.

        Args:
            page_id: Page ID
            properties: Properties to update
            icon: New icon
            cover: New cover
            archived: Archive status

        Returns:
            Updated NotionPage
        """
        client = await self._get_async_client()

        body = {}

        if properties:
            body["properties"] = properties

        if icon is not None:
            if icon.startswith("http"):
                body["icon"] = {"type": "external", "external": {"url": icon}}
            else:
                body["icon"] = {"type": "emoji", "emoji": icon}

        if cover is not None:
            body["cover"] = {"type": "external", "external": {"url": cover}}

        if archived is not None:
            body["archived"] = archived

        result = await client.pages.update(page_id=page_id, **body)

        await client.aclose()
        return await self.get_page(page_id)

    async def delete_page(self, page_id: str) -> bool:
        """Delete (archive) a page."""
        await self.update_page(page_id, archived=True)
        return True

    async def get_blocks(
        self,
        block_id: str,
        page_size: int = 100,
    ) -> List[NotionBlock]:
        """
        Get child blocks of a block/page.

        Args:
            block_id: Block or page ID
            page_size: Number of blocks per request

        Returns:
            List of NotionBlocks
        """
        client = await self._get_async_client()

        blocks = []
        start_cursor = None

        while True:
            kwargs = {"block_id": block_id, "page_size": page_size}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            result = await client.blocks.children.list(**kwargs)

            for block in result.get("results", []):
                block_type = block.get("type")
                try:
                    bt = BlockType(block_type)
                except ValueError:
                    bt = BlockType.PARAGRAPH

                content = ""
                block_content = block.get(block_type, {})
                if "rich_text" in block_content:
                    content = "".join(rt.get("plain_text", "") for rt in block_content["rich_text"])

                blocks.append(
                    NotionBlock(
                        type=bt,
                        content=content,
                        block_id=block["id"],
                    )
                )

            if not result.get("has_more"):
                break

            start_cursor = result.get("next_cursor")

        await client.aclose()
        return blocks

    async def append_blocks(
        self,
        block_id: str,
        blocks: List[NotionBlock],
    ) -> List[NotionBlock]:
        """
        Append blocks to a page/block.

        Args:
            block_id: Parent block/page ID
            blocks: Blocks to append

        Returns:
            Created blocks with IDs
        """
        client = await self._get_async_client()

        children = [b.to_dict() for b in blocks]

        result = await client.blocks.children.append(
            block_id=block_id,
            children=children,
        )

        # Update block IDs
        for i, block_data in enumerate(result.get("results", [])):
            if i < len(blocks):
                blocks[i].block_id = block_data["id"]

        await client.aclose()
        return blocks

    async def delete_block(self, block_id: str) -> bool:
        """Delete a block."""
        client = await self._get_async_client()
        await client.blocks.delete(block_id=block_id)
        await client.aclose()
        return True

    async def create_database(
        self,
        database: NotionDatabase,
    ) -> NotionDatabase:
        """
        Create a new database.

        Args:
            database: NotionDatabase to create

        Returns:
            Created NotionDatabase with ID
        """
        client = await self._get_async_client()

        body = {
            "parent": {"page_id": database.parent_id},
            "title": [{"type": "text", "text": {"content": database.title}}],
            "properties": database.properties
            or {
                "Name": {"title": {}},
            },
        }

        result = await client.databases.create(**body)

        database.database_id = result["id"]
        database.url = result.get("url", "")

        await client.aclose()
        return database

    async def get_database(self, database_id: str) -> NotionDatabase:
        """Get a database."""
        client = await self._get_async_client()

        result = await client.databases.retrieve(database_id=database_id)

        title = ""
        if result.get("title"):
            title = "".join(t.get("plain_text", "") for t in result["title"])

        database = NotionDatabase(
            title=title,
            database_id=result["id"],
            properties=result.get("properties", {}),
            url=result.get("url", ""),
        )

        await client.aclose()
        return database

    async def query_database(
        self,
        database_id: str,
        query: Optional[DatabaseQuery] = None,
    ) -> List[NotionPage]:
        """
        Query a database.

        Args:
            database_id: Database ID
            query: Query parameters

        Returns:
            List of pages matching query
        """
        client = await self._get_async_client()
        query = query or DatabaseQuery()

        kwargs = {"database_id": database_id, "page_size": query.page_size}

        if query.filter:
            kwargs["filter"] = query.filter

        if query.sorts:
            kwargs["sorts"] = query.sorts

        if query.start_cursor:
            kwargs["start_cursor"] = query.start_cursor

        result = await client.databases.query(**kwargs)

        pages = []
        for page_data in result.get("results", []):
            # Extract title from properties
            title = ""
            for prop_name, prop_value in page_data.get("properties", {}).items():
                if prop_value.get("type") == "title":
                    title_arr = prop_value.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_arr)
                    break

            pages.append(
                NotionPage(
                    title=title,
                    page_id=page_data["id"],
                    properties=page_data.get("properties", {}),
                    url=page_data.get("url", ""),
                    created_time=datetime.fromisoformat(
                        page_data["created_time"].replace("Z", "+00:00")
                    ),
                )
            )

        await client.aclose()
        return pages

    async def add_database_item(
        self,
        database_id: str,
        properties: Dict[str, Any],
    ) -> NotionPage:
        """
        Add an item to a database.

        Args:
            database_id: Database ID
            properties: Item properties

        Returns:
            Created page
        """
        page = NotionPage(
            title="",  # Title is in properties
            parent_id=database_id,
            parent_type="database_id",
            properties=properties,
        )
        return await self.create_page(page)

    async def search(
        self,
        query: str,
        filter_type: Optional[str] = None,  # "page" or "database"
        page_size: int = 100,
    ) -> List[Union[NotionPage, NotionDatabase]]:
        """
        Search Notion workspace.

        Args:
            query: Search query
            filter_type: Filter to pages or databases
            page_size: Results per page

        Returns:
            List of matching pages/databases
        """
        client = await self._get_async_client()

        kwargs = {"query": query, "page_size": page_size}

        if filter_type:
            kwargs["filter"] = {"property": "object", "value": filter_type}

        result = await client.search(**kwargs)

        results = []
        for item in result.get("results", []):
            if item["object"] == "page":
                title = ""
                for prop_name, prop_value in item.get("properties", {}).items():
                    if prop_value.get("type") == "title":
                        title_arr = prop_value.get("title", [])
                        title = "".join(t.get("plain_text", "") for t in title_arr)
                        break

                results.append(
                    NotionPage(
                        title=title,
                        page_id=item["id"],
                        url=item.get("url", ""),
                    )
                )
            elif item["object"] == "database":
                title = ""
                if item.get("title"):
                    title = "".join(t.get("plain_text", "") for t in item["title"])

                results.append(
                    NotionDatabase(
                        title=title,
                        database_id=item["id"],
                        url=item.get("url", ""),
                    )
                )

        await client.aclose()
        return results

    def build_filter(self) -> "FilterBuilder":
        """Get a filter builder for database queries."""
        return FilterBuilder()


class FilterBuilder:
    """Helper for building Notion database filters."""

    def __init__(self):
        self._filter = None

    def equals(self, property: str, prop_type: str, value: Any) -> "FilterBuilder":
        """Add equals condition."""
        self._filter = {
            "property": property,
            prop_type: {"equals": value},
        }
        return self

    def contains(self, property: str, value: str) -> "FilterBuilder":
        """Add contains condition for rich_text."""
        self._filter = {
            "property": property,
            "rich_text": {"contains": value},
        }
        return self

    def checkbox(self, property: str, checked: bool) -> "FilterBuilder":
        """Add checkbox condition."""
        self._filter = {
            "property": property,
            "checkbox": {"equals": checked},
        }
        return self

    def date_after(self, property: str, date: datetime) -> "FilterBuilder":
        """Add date after condition."""
        self._filter = {
            "property": property,
            "date": {"after": date.isoformat()},
        }
        return self

    def date_before(self, property: str, date: datetime) -> "FilterBuilder":
        """Add date before condition."""
        self._filter = {
            "property": property,
            "date": {"before": date.isoformat()},
        }
        return self

    def and_(self, *filters: "FilterBuilder") -> "FilterBuilder":
        """Combine filters with AND."""
        self._filter = {
            "and": [f.build() for f in filters],
        }
        return self

    def or_(self, *filters: "FilterBuilder") -> "FilterBuilder":
        """Combine filters with OR."""
        self._filter = {
            "or": [f.build() for f in filters],
        }
        return self

    def build(self) -> Dict[str, Any]:
        """Build the filter."""
        return self._filter
