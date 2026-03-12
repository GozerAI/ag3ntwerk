"""
Agent Communication Layer.

This module provides the abstraction for agent-to-agent communication,
supporting both local (in-process) and distributed (network) deployments.

Architecture:
- LocalCommunicator: Direct method calls when agents run on same machine
- DistributedCommunicator: Message queue/RPC for distributed deployments
"""

import inspect

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4
import asyncio
import json

if TYPE_CHECKING:
    from ag3ntwerk.core.base import Agent, Task, TaskResult


@dataclass
class AgentMessage:
    """A message between agents."""

    id: str = field(default_factory=lambda: str(uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: str = "task"  # task, result, query, broadcast
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For request-response tracking

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=data.get("id", str(uuid4())),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            message_type=data.get("message_type", "task"),
            payload=data.get("payload", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            correlation_id=data.get("correlation_id"),
        )


class AgentCommunicator(ABC):
    """
    Abstract interface for agent-to-agent communication.

    This abstraction allows the same agent code to run either:
    - Locally: All agents in the same process, direct method calls
    - Distributed: Agents on different machines, communicating via message bus
    """

    @abstractmethod
    async def send_task(
        self,
        agent_code: str,
        task: "Task",
        timeout: float = 60.0,
    ) -> "TaskResult":
        """
        Send a task to another agent and wait for result.

        Args:
            agent_code: The target agent's code (e.g., "Sentinel", "Forge")
            task: The task to send
            timeout: Maximum wait time in seconds

        Returns:
            TaskResult from the target agent
        """
        pass

    @abstractmethod
    async def broadcast(
        self,
        message: AgentMessage,
        agent_codes: Optional[List[str]] = None,
    ) -> None:
        """
        Broadcast a message to multiple agents.

        Args:
            message: The message to broadcast
            agent_codes: Specific agents to target (or all if None)
        """
        pass

    @abstractmethod
    async def query_agent(
        self,
        agent_code: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a query to an agent and get a response.

        Args:
            agent_code: The target agent's code
            query: The query string
            context: Additional context for the query

        Returns:
            Response string from the agent
        """
        pass

    @abstractmethod
    def register_handler(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """
        Register a handler for a specific message type.

        Args:
            message_type: The type of message to handle
            handler: Callback function to process messages
        """
        pass

    @abstractmethod
    async def get_agent_status(self, agent_code: str) -> Dict[str, Any]:
        """
        Get the status of an agent.

        Args:
            agent_code: The agent's code

        Returns:
            Status dictionary with health, load, etc.
        """
        pass


class LocalCommunicator(AgentCommunicator):
    """
    Direct in-process communication for co-located agents.

    This is the simplest deployment model where all agents run
    in the same process and communicate via method calls.
    """

    def __init__(self):
        self._agents: Dict[str, "Agent"] = {}
        self._handlers: Dict[str, List[Callable]] = {}

    def register_agent(self, agent: "Agent") -> None:
        """Register an agent with the communicator."""
        self._agents[agent.code] = agent

    def unregister_agent(self, agent_code: str) -> None:
        """Unregister an agent."""
        self._agents.pop(agent_code, None)

    def get_agent(self, agent_code: str) -> Optional["Agent"]:
        """Get a registered agent by code."""
        return self._agents.get(agent_code)

    async def send_task(
        self,
        agent_code: str,
        task: "Task",
        timeout: float = 60.0,
    ) -> "TaskResult":
        """Send a task directly to a local agent."""
        from ag3ntwerk.core.base import TaskResult

        agent = self._agents.get(agent_code)
        if not agent:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Agent {agent_code} not found",
            )

        try:
            result = await asyncio.wait_for(
                agent.execute(task),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Task timed out after {timeout}s",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    async def broadcast(
        self,
        message: AgentMessage,
        agent_codes: Optional[List[str]] = None,
    ) -> None:
        """Broadcast a message to local agents."""
        targets = agent_codes or list(self._agents.keys())

        for code in targets:
            agent = self._agents.get(code)
            if agent and hasattr(agent, "receive_message"):
                await agent.receive_message(message)

        # Also call registered handlers
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                print(f"Handler error: {e}")

    async def query_agent(
        self,
        agent_code: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Query a local agent directly."""
        agent = self._agents.get(agent_code)
        if not agent:
            return f"Error: Agent {agent_code} not found"

        if hasattr(agent, "handle_query"):
            return await agent.handle_query(query, context)
        elif agent.llm_provider:
            return await agent.reason(query, context)
        else:
            return f"Agent {agent_code} cannot handle queries"

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """Register a message handler."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def get_agent_status(self, agent_code: str) -> Dict[str, Any]:
        """Get status of a local agent."""
        agent = self._agents.get(agent_code)
        if not agent:
            return {"error": f"Agent {agent_code} not found"}

        return {
            "code": agent.code,
            "name": agent.name,
            "domain": agent.domain,
            "active": agent.is_active,
            "has_llm": agent.llm_provider is not None,
            "task_history_count": len(agent.get_history()),
        }


class DistributedCommunicator(AgentCommunicator):
    """
    Network-based communication for distributed agents.

    Uses Redis pub/sub for message passing between agents
    running on different machines.

    Note: Requires redis-py async library.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        agent_code: str = "",
        channel_prefix: str = "ag3ntwerk",
    ):
        self.redis_url = redis_url
        self.agent_code = agent_code
        self.channel_prefix = channel_prefix
        self._redis = None
        self._pubsub = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.redis_url)
            self._pubsub = self._redis.pubsub()

            # Subscribe to our agent's channel
            if self.agent_code:
                await self._pubsub.subscribe(f"{self.channel_prefix}:{self.agent_code}")
                # Start listener task
                asyncio.create_task(self._listen())

            return True
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _listen(self) -> None:
        """Background task to listen for messages."""
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    agent_message = AgentMessage.from_dict(data)
                    await self._handle_message(agent_message)
                except Exception as e:
                    print(f"Error processing message: {e}")

    async def _handle_message(self, message: AgentMessage) -> None:
        """Process an incoming message."""
        # Check if this is a response to a pending request
        if message.correlation_id and message.correlation_id in self._pending_responses:
            future = self._pending_responses.pop(message.correlation_id)
            future.set_result(message)
            return

        # Call registered handlers
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                print(f"Handler error: {e}")

    async def send_task(
        self,
        agent_code: str,
        task: "Task",
        timeout: float = 60.0,
    ) -> "TaskResult":
        """Send a task via Redis to a remote agent."""
        from ag3ntwerk.core.base import TaskResult

        if not self._redis:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Not connected to Redis",
            )

        # Create request message
        message = AgentMessage(
            sender=self.agent_code,
            recipient=agent_code,
            message_type="task",
            payload=task.to_dict(),
        )

        # Set up response future
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[message.id] = future

        # Send message
        channel = f"{self.channel_prefix}:{agent_code}"
        await self._redis.publish(channel, message.to_json())

        try:
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            result_data = response.payload

            return TaskResult(
                task_id=result_data.get("task_id", task.id),
                success=result_data.get("success", False),
                output=result_data.get("output"),
                error=result_data.get("error"),
            )
        except asyncio.TimeoutError:
            self._pending_responses.pop(message.id, None)
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Task timed out after {timeout}s",
            )

    async def broadcast(
        self,
        message: AgentMessage,
        agent_codes: Optional[List[str]] = None,
    ) -> None:
        """Broadcast via Redis pub/sub."""
        if not self._redis:
            return

        if agent_codes:
            # Send to specific agents
            for code in agent_codes:
                channel = f"{self.channel_prefix}:{code}"
                await self._redis.publish(channel, message.to_json())
        else:
            # Broadcast to all via broadcast channel
            channel = f"{self.channel_prefix}:broadcast"
            await self._redis.publish(channel, message.to_json())

    async def query_agent(
        self,
        agent_code: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a query via Redis."""
        if not self._redis:
            return "Error: Not connected to Redis"

        message = AgentMessage(
            sender=self.agent_code,
            recipient=agent_code,
            message_type="query",
            payload={"query": query, "context": context or {}},
        )

        future: asyncio.Future = asyncio.Future()
        self._pending_responses[message.id] = future

        channel = f"{self.channel_prefix}:{agent_code}"
        await self._redis.publish(channel, message.to_json())

        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response.payload.get("response", "")
        except asyncio.TimeoutError:
            self._pending_responses.pop(message.id, None)
            return "Error: Query timed out"

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """Register a message handler."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def get_agent_status(self, agent_code: str) -> Dict[str, Any]:
        """Query agent status via Redis."""
        if not self._redis:
            return {"error": "Not connected to Redis"}

        message = AgentMessage(
            sender=self.agent_code,
            recipient=agent_code,
            message_type="status_query",
            payload={},
        )

        future: asyncio.Future = asyncio.Future()
        self._pending_responses[message.id] = future

        channel = f"{self.channel_prefix}:{agent_code}"
        await self._redis.publish(channel, message.to_json())

        try:
            response = await asyncio.wait_for(future, timeout=5.0)
            return response.payload
        except asyncio.TimeoutError:
            self._pending_responses.pop(message.id, None)
            return {"error": f"Agent {agent_code} not responding"}
