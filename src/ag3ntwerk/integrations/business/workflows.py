"""
Workflow Automation Integration for ag3ntwerk.

Provides integration with Zapier and n8n.

Requirements:
    - Zapier: Uses webhooks (no special library)
    - n8n: pip install aiohttp

Workflows is ideal for:
    - Process automation
    - Cross-system integrations
    - Trigger-based actions
    - Data synchronization
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowProvider(str, Enum):
    """Workflow automation providers."""

    ZAPIER = "zapier"
    N8N = "n8n"


@dataclass
class Workflow:
    """Represents a workflow."""

    id: str
    name: str
    active: bool = True
    trigger: str = ""
    actions: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    run_count: int = 0
    last_run: Optional[datetime] = None


@dataclass
class WorkflowRun:
    """Represents a workflow execution."""

    id: str
    workflow_id: str
    status: str = ""  # success, error, running
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


class WorkflowIntegration:
    """
    Integration with workflow automation platforms.

    Supports Zapier webhooks and n8n API.

    Example:
        # Zapier webhook
        workflows = WorkflowIntegration(
            provider=WorkflowProvider.ZAPIER,
        )

        # Trigger a Zap
        await workflows.trigger_webhook(
            webhook_url="https://hooks.zapier.com/...",
            data={"event": "new_lead", "name": "John"},
        )

        # n8n
        workflows = WorkflowIntegration(
            provider=WorkflowProvider.N8N,
            n8n_url="http://localhost:5678",
            n8n_api_key="...",
        )

        # List workflows
        wfs = await workflows.list_workflows()
    """

    def __init__(
        self,
        provider: WorkflowProvider,
        n8n_url: str = "http://localhost:5678",
        n8n_api_key: str = "",
    ):
        """Initialize workflow integration."""
        self.provider = provider
        self.n8n_url = n8n_url.rstrip("/")
        self.n8n_api_key = n8n_api_key
        self._session = None

    async def _get_session(self):
        """Get aiohttp session."""
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession()
            except ImportError:
                raise ImportError("aiohttp not installed. Install with: pip install aiohttp")
        return self._session

    async def trigger_webhook(
        self,
        webhook_url: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Trigger a webhook (works with Zapier, n8n, and others).

        Args:
            webhook_url: Webhook URL
            data: Data to send

        Returns:
            Response data
        """
        session = await self._get_session()

        async with session.post(
            webhook_url,
            json=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status >= 400:
                text = await response.text()
                raise Exception(f"Webhook failed: {response.status} - {text}")

            try:
                return await response.json()
            except (ValueError, TypeError):
                return {"status": "ok", "status_code": response.status}

    async def list_workflows(self) -> List[Workflow]:
        """
        List workflows (n8n only).

        Returns:
            List of Workflows
        """
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("List workflows only supported for n8n")

        session = await self._get_session()

        async with session.get(
            f"{self.n8n_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": self.n8n_api_key},
        ) as response:
            data = await response.json()

        return [
            Workflow(
                id=wf["id"],
                name=wf.get("name", ""),
                active=wf.get("active", False),
                created_at=(
                    datetime.fromisoformat(wf["createdAt"].replace("Z", "+00:00"))
                    if wf.get("createdAt")
                    else None
                ),
                updated_at=(
                    datetime.fromisoformat(wf["updatedAt"].replace("Z", "+00:00"))
                    if wf.get("updatedAt")
                    else None
                ),
            )
            for wf in data.get("data", [])
        ]

    async def get_workflow(self, workflow_id: str) -> Workflow:
        """
        Get a specific workflow (n8n only).

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow
        """
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("Get workflow only supported for n8n")

        session = await self._get_session()

        async with session.get(
            f"{self.n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": self.n8n_api_key},
        ) as response:
            wf = await response.json()

        nodes = wf.get("nodes", [])
        trigger = ""
        actions = []

        for node in nodes:
            if node.get("type", "").endswith("Trigger"):
                trigger = node.get("type", "")
            else:
                actions.append(node.get("type", ""))

        return Workflow(
            id=wf["id"],
            name=wf.get("name", ""),
            active=wf.get("active", False),
            trigger=trigger,
            actions=actions,
            created_at=(
                datetime.fromisoformat(wf["createdAt"].replace("Z", "+00:00"))
                if wf.get("createdAt")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(wf["updatedAt"].replace("Z", "+00:00"))
                if wf.get("updatedAt")
                else None
            ),
        )

    async def create_workflow(
        self,
        name: str,
        nodes: list,
        connections: dict,
        settings: Optional[Dict[str, Any]] = None,
        active: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new workflow in n8n.

        Args:
            name: Workflow name
            nodes: List of node definitions
            connections: Connection mappings between nodes
            settings: Optional workflow settings
            active: Whether to activate the workflow immediately

        Returns:
            Created workflow data including 'id'
        """
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("Create workflow only supported for n8n")

        session = await self._get_session()

        payload = {
            "name": name,
            "nodes": nodes,
            "connections": connections,
            "active": active,
        }
        if settings:
            payload["settings"] = settings

        async with session.post(
            f"{self.n8n_url}/api/v1/workflows",
            json=payload,
            headers={
                "X-N8N-API-KEY": self.n8n_api_key,
                "Content-Type": "application/json",
            },
        ) as response:
            if response.status >= 400:
                text = await response.text()
                raise Exception(f"Create workflow failed: {response.status} - {text}")
            return await response.json()

    async def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow (n8n only)."""
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("Activate workflow only supported for n8n")

        session = await self._get_session()

        async with session.patch(
            f"{self.n8n_url}/api/v1/workflows/{workflow_id}/activate",
            headers={"X-N8N-API-KEY": self.n8n_api_key},
        ) as response:
            return response.status == 200

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """Deactivate a workflow (n8n only)."""
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("Deactivate workflow only supported for n8n")

        session = await self._get_session()

        async with session.patch(
            f"{self.n8n_url}/api/v1/workflows/{workflow_id}/deactivate",
            headers={"X-N8N-API-KEY": self.n8n_api_key},
        ) as response:
            return response.status == 200

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        """
        Execute a workflow (n8n only).

        Args:
            workflow_id: Workflow ID
            data: Input data

        Returns:
            WorkflowRun with execution results
        """
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("Execute workflow only supported for n8n")

        session = await self._get_session()

        async with session.post(
            f"{self.n8n_url}/api/v1/workflows/{workflow_id}/run",
            json={"data": data or {}},
            headers={
                "X-N8N-API-KEY": self.n8n_api_key,
                "Content-Type": "application/json",
            },
        ) as response:
            result = await response.json()

        return WorkflowRun(
            id=result.get("executionId", ""),
            workflow_id=workflow_id,
            status="success" if result.get("success") else "error",
            data=result.get("data", {}),
        )

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[WorkflowRun]:
        """
        List workflow executions (n8n only).

        Args:
            workflow_id: Filter by workflow
            status: Filter by status
            limit: Maximum results

        Returns:
            List of WorkflowRuns
        """
        if self.provider != WorkflowProvider.N8N:
            raise NotImplementedError("List executions only supported for n8n")

        session = await self._get_session()

        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status

        async with session.get(
            f"{self.n8n_url}/api/v1/executions",
            params=params,
            headers={"X-N8N-API-KEY": self.n8n_api_key},
        ) as response:
            data = await response.json()

        return [
            WorkflowRun(
                id=ex.get("id", ""),
                workflow_id=ex.get("workflowId", ""),
                status=ex.get("status", ""),
                started_at=(
                    datetime.fromisoformat(ex["startedAt"].replace("Z", "+00:00"))
                    if ex.get("startedAt")
                    else None
                ),
                finished_at=(
                    datetime.fromisoformat(ex["finishedAt"].replace("Z", "+00:00"))
                    if ex.get("finishedAt")
                    else None
                ),
            )
            for ex in data.get("data", [])
        ]

    async def close(self):
        """Close session."""
        if self._session:
            await self._session.close()
            self._session = None
