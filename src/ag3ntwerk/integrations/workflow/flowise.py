"""
Flowise Integration for ag3ntwerk.

Provides integration with Flowise visual LLM workflow builder.
Allows ag3ntwerk agents to leverage pre-built Flowise chatflows and agentflows.

Requirements:
    - Flowise server running
    - pip install aiohttp

Setup:
    docker run -d --name flowise -p 3000:3000 flowiseai/flowise
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class FlowType(str, Enum):
    """Type of Flowise flow."""

    CHATFLOW = "chatflow"
    AGENTFLOW = "agentflow"


@dataclass
class FlowiseMessage:
    """A message in a Flowise conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowiseWorkflow:
    """Represents a Flowise workflow (chatflow or agentflow)."""

    id: str
    name: str
    flow_type: FlowType = FlowType.CHATFLOW
    description: str = ""
    deployed: bool = False
    api_endpoint: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowiseResponse:
    """Response from a Flowise prediction."""

    text: str
    source_documents: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    flow_id: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)


class FlowiseClient:
    """
    Client for interacting with Flowise server.

    Flowise provides a visual interface for building LLM chains and agents.
    This client allows ag3ntwerk to trigger and interact with Flowise flows.

    Features:
    - Execute chatflows and agentflows
    - Manage conversation sessions
    - Stream responses
    - File uploads for RAG

    Example:
        client = FlowiseClient("http://localhost:3000")
        await client.initialize()

        # List available flows
        flows = await client.list_flows()

        # Execute a chatflow
        response = await client.predict(
            flow_id="abc123",
            question="What is the capital of France?",
            session_id="user_session_1",
        )
        print(response.text)

        # Stream response
        async for chunk in client.predict_stream(
            flow_id="abc123",
            question="Tell me a story",
        ):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Initialize Flowise client.

        Args:
            base_url: Flowise server URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def initialize(self) -> None:
        """Initialize the HTTP session and verify connection."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

        # Verify connection
        try:
            async with self._session.get(
                f"{self.base_url}/api/v1/ping",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    self._connected = True
                    logger.info(f"Connected to Flowise at {self.base_url}")
                else:
                    logger.warning(f"Flowise ping returned status {response.status}")
        except aiohttp.ClientError as e:
            logger.warning(f"Could not connect to Flowise: {e}")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            self._connected = False

    async def list_flows(
        self,
        flow_type: Optional[FlowType] = None,
    ) -> List[FlowiseWorkflow]:
        """
        List available Flowise flows.

        Args:
            flow_type: Filter by flow type (chatflow or agentflow)

        Returns:
            List of FlowiseWorkflow objects
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        flows = []

        # Get chatflows
        if flow_type is None or flow_type == FlowType.CHATFLOW:
            async with self._session.get(
                f"{self.base_url}/api/v1/chatflows",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        flows.append(
                            FlowiseWorkflow(
                                id=item.get("id", ""),
                                name=item.get("name", ""),
                                flow_type=FlowType.CHATFLOW,
                                description=item.get("description", ""),
                                deployed=item.get("deployed", False),
                                api_endpoint=f"{self.base_url}/api/v1/prediction/{item.get('id', '')}",
                                category=item.get("category"),
                                metadata=item,
                            )
                        )

        # Get agentflows
        if flow_type is None or flow_type == FlowType.AGENTFLOW:
            async with self._session.get(
                f"{self.base_url}/api/v1/agentflows",
                headers=self._get_headers(),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        flows.append(
                            FlowiseWorkflow(
                                id=item.get("id", ""),
                                name=item.get("name", ""),
                                flow_type=FlowType.AGENTFLOW,
                                description=item.get("description", ""),
                                deployed=item.get("deployed", False),
                                api_endpoint=f"{self.base_url}/api/v1/prediction/{item.get('id', '')}",
                                category=item.get("category"),
                                metadata=item,
                            )
                        )

        return flows

    async def get_flow(self, flow_id: str) -> Optional[FlowiseWorkflow]:
        """
        Get a specific flow by ID.

        Args:
            flow_id: Flow ID

        Returns:
            FlowiseWorkflow or None if not found
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        # Try chatflow first
        async with self._session.get(
            f"{self.base_url}/api/v1/chatflows/{flow_id}",
            headers=self._get_headers(),
        ) as response:
            if response.status == 200:
                item = await response.json()
                return FlowiseWorkflow(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    flow_type=FlowType.CHATFLOW,
                    description=item.get("description", ""),
                    deployed=item.get("deployed", False),
                    api_endpoint=f"{self.base_url}/api/v1/prediction/{flow_id}",
                    category=item.get("category"),
                    metadata=item,
                )

        # Try agentflow
        async with self._session.get(
            f"{self.base_url}/api/v1/agentflows/{flow_id}",
            headers=self._get_headers(),
        ) as response:
            if response.status == 200:
                item = await response.json()
                return FlowiseWorkflow(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    flow_type=FlowType.AGENTFLOW,
                    description=item.get("description", ""),
                    deployed=item.get("deployed", False),
                    api_endpoint=f"{self.base_url}/api/v1/prediction/{flow_id}",
                    category=item.get("category"),
                    metadata=item,
                )

        return None

    async def predict(
        self,
        flow_id: str,
        question: str,
        session_id: Optional[str] = None,
        history: Optional[List[FlowiseMessage]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        uploads: Optional[List[Dict[str, Any]]] = None,
    ) -> FlowiseResponse:
        """
        Execute a prediction on a Flowise flow.

        Args:
            flow_id: ID of the chatflow or agentflow
            question: The user's question/input
            session_id: Session ID for conversation continuity
            history: Optional conversation history
            overrides: Optional configuration overrides
            uploads: Optional file uploads for RAG

        Returns:
            FlowiseResponse with the prediction result
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        payload = {
            "question": question,
        }

        if session_id:
            payload["sessionId"] = session_id

        if history:
            payload["history"] = [{"role": msg.role, "content": msg.content} for msg in history]

        if overrides:
            payload["overrideConfig"] = overrides

        if uploads:
            payload["uploads"] = uploads

        async with self._session.post(
            f"{self.base_url}/api/v1/prediction/{flow_id}",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Flowise prediction failed: {error_text}")

            data = await response.json()

            return FlowiseResponse(
                text=data.get("text", data.get("response", "")),
                source_documents=data.get("sourceDocuments", []),
                usage=data.get("usage", {}),
                session_id=data.get("sessionId") or session_id,
                flow_id=flow_id,
                raw_response=data,
            )

    async def predict_stream(
        self,
        flow_id: str,
        question: str,
        session_id: Optional[str] = None,
        history: Optional[List[FlowiseMessage]] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ):
        """
        Stream a prediction response from a Flowise flow.

        Args:
            flow_id: ID of the chatflow or agentflow
            question: The user's question/input
            session_id: Session ID for conversation continuity
            history: Optional conversation history
            overrides: Optional configuration overrides

        Yields:
            Text chunks as they arrive
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        payload = {
            "question": question,
            "streaming": True,
        }

        if session_id:
            payload["sessionId"] = session_id

        if history:
            payload["history"] = [{"role": msg.role, "content": msg.content} for msg in history]

        if overrides:
            payload["overrideConfig"] = overrides

        async with self._session.post(
            f"{self.base_url}/api/v1/prediction/{flow_id}",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Flowise stream failed: {error_text}")

            async for line in response.content:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: "):
                    chunk = decoded[6:]
                    if chunk and chunk != "[DONE]":
                        yield chunk

    async def upsert_vector(
        self,
        flow_id: str,
        document: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upsert a document into a flow's vector store.

        Args:
            flow_id: ID of the chatflow with vector store
            document: Document text to embed and store
            metadata: Optional metadata

        Returns:
            Upsert result from Flowise
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        payload = {
            "document": document,
        }

        if metadata:
            payload["metadata"] = metadata

        async with self._session.post(
            f"{self.base_url}/api/v1/vector/upsert/{flow_id}",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Flowise vector upsert failed: {error_text}")

            return await response.json()

    async def get_chat_history(
        self,
        flow_id: str,
        session_id: str,
        sort_order: str = "DESC",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[FlowiseMessage]:
        """
        Get chat history for a session.

        Args:
            flow_id: Flow ID
            session_id: Session ID
            sort_order: "ASC" or "DESC"
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)

        Returns:
            List of messages in the conversation
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        params = {
            "order": sort_order,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        async with self._session.get(
            f"{self.base_url}/api/v1/chatmessage/{flow_id}/{session_id}",
            headers=self._get_headers(),
            params=params,
        ) as response:
            if response.status != 200:
                return []

            data = await response.json()
            messages = []
            for item in data:
                messages.append(
                    FlowiseMessage(
                        role=item.get("role", ""),
                        content=item.get("content", ""),
                        metadata=item,
                    )
                )
            return messages

    async def delete_chat_history(
        self,
        flow_id: str,
        session_id: str,
    ) -> bool:
        """
        Delete chat history for a session.

        Args:
            flow_id: Flow ID
            session_id: Session ID

        Returns:
            True if deleted successfully
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.delete(
            f"{self.base_url}/api/v1/chatmessage/{flow_id}/{session_id}",
            headers=self._get_headers(),
        ) as response:
            return response.status == 200

    async def upload_file(
        self,
        flow_id: str,
        file_path: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to be used in a flow.

        Args:
            flow_id: Flow ID
            file_path: Path to the file
            file_name: Optional display name for the file

        Returns:
            Upload result including file ID
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        import os

        if file_name is None:
            file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field(
                "files",
                f,
                filename=file_name,
            )

            # Remove Content-Type for multipart
            headers = self._get_headers()
            headers.pop("Content-Type", None)

            async with self._session.post(
                f"{self.base_url}/api/v1/attachments/{flow_id}",
                headers=headers,
                data=data,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Flowise file upload failed: {error_text}")

                return await response.json()


class FlowiseExecutive:
    """
    Wrapper to use Flowise flows as ag3ntwerk agents.

    This allows a Flowise chatflow/agentflow to be treated as
    an agent that can be called by the Nexus orchestrator.

    Example:
        # Create agent from Flowise flow
        research_exec = FlowiseExecutive(
            client=flowise_client,
            flow_id="research_flow_123",
            name="Research Assistant",
            domain="research",
        )

        # Execute task through the flow
        result = await research_exec.execute(task)
    """

    def __init__(
        self,
        client: FlowiseClient,
        flow_id: str,
        name: str = "Flowise Agent",
        domain: str = "general",
        codename: str = "Flow",
    ):
        """
        Initialize Flowise agent.

        Args:
            client: FlowiseClient instance
            flow_id: ID of the Flowise flow to use
            name: Display name for the agent
            domain: Domain of expertise
            codename: Codename for the agent
        """
        self.client = client
        self.flow_id = flow_id
        self.name = name
        self.domain = domain
        self.codename = codename
        self._session_id: Optional[str] = None

    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task through the Flowise flow.

        Args:
            task_description: Description of the task
            context: Optional context for the task

        Returns:
            Result dictionary with output and metadata
        """
        # Build question with context
        question = task_description
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            question = f"{task_description}\n\nContext:\n{context_str}"

        response = await self.client.predict(
            flow_id=self.flow_id,
            question=question,
            session_id=self._session_id,
        )

        # Store session for continuity
        self._session_id = response.session_id

        return {
            "success": True,
            "output": response.text,
            "source_documents": response.source_documents,
            "usage": response.usage,
            "session_id": response.session_id,
        }

    def reset_session(self) -> None:
        """Reset the conversation session."""
        self._session_id = None
