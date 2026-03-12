"""
n8n Integration for ag3ntwerk.

Provides integration with n8n workflow automation platform.
Allows ag3ntwerk agents to trigger external workflows and receive webhooks.

Requirements:
    - n8n server running
    - pip install aiohttp

Setup:
    docker run -d --name n8n -p 5678:5678 n8nio/n8n
"""

import asyncio
import hashlib
import hmac
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from uuid import uuid4

import aiohttp

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """n8n workflow status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    """n8n execution status."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WAITING = "waiting"
    CANCELED = "canceled"


@dataclass
class N8nWorkflow:
    """Represents an n8n workflow."""

    id: str
    name: str
    active: bool = False
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    connections: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class N8nExecution:
    """Represents an n8n workflow execution."""

    id: str
    workflow_id: str
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    mode: str = "manual"
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class N8nWebhook:
    """Represents an n8n webhook configuration."""

    id: str
    path: str
    method: str = "POST"
    workflow_id: str = ""
    node_name: str = ""
    is_production: bool = True
    url: str = ""


class N8nClient:
    """
    Client for interacting with n8n automation platform.

    n8n is a workflow automation tool that connects various services.
    This client allows ag3ntwerk to trigger workflows and receive results.

    Features:
    - List and manage workflows
    - Trigger workflow executions
    - Monitor execution status
    - Send webhook payloads
    - Manage credentials

    Example:
        client = N8nClient("http://localhost:5678", api_key="your-api-key")
        await client.initialize()

        # List workflows
        workflows = await client.list_workflows()

        # Trigger a workflow
        execution = await client.execute_workflow(
            workflow_id="123",
            data={"input": "value"},
        )

        # Wait for completion
        result = await client.wait_for_execution(execution.id)
        print(result.data)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5678",
        api_key: Optional[str] = None,
        timeout: int = 300,
    ):
        """
        Initialize n8n client.

        Args:
            base_url: n8n server URL
            api_key: API key for authentication
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
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    async def initialize(self) -> None:
        """Initialize the HTTP session and verify connection."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

        # Verify connection by getting health
        try:
            async with self._session.get(
                f"{self.base_url}/healthz",
            ) as response:
                if response.status == 200:
                    self._connected = True
                    logger.info(f"Connected to n8n at {self.base_url}")
                else:
                    logger.warning(f"n8n health check returned status {response.status}")
        except aiohttp.ClientError as e:
            logger.warning(f"Could not connect to n8n: {e}")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            self._connected = False

    async def list_workflows(
        self,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
    ) -> List[N8nWorkflow]:
        """
        List all workflows.

        Args:
            active_only: Only return active workflows
            tags: Filter by tags

        Returns:
            List of N8nWorkflow objects
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        params = {}
        if active_only:
            params["active"] = "true"
        if tags:
            params["tags"] = ",".join(tags)

        async with self._session.get(
            f"{self.base_url}/api/v1/workflows",
            headers=self._get_headers(),
            params=params,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Failed to list workflows: {error_text}")

            data = await response.json()
            workflows = []

            for item in data.get("data", []):
                workflows.append(
                    N8nWorkflow(
                        id=str(item.get("id", "")),
                        name=item.get("name", ""),
                        active=item.get("active", False),
                        nodes=item.get("nodes", []),
                        connections=item.get("connections", {}),
                        tags=[t.get("name", "") for t in item.get("tags", [])],
                        metadata=item,
                    )
                )

            return workflows

    async def get_workflow(self, workflow_id: str) -> Optional[N8nWorkflow]:
        """
        Get a specific workflow by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            N8nWorkflow or None if not found
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.get(
            f"{self.base_url}/api/v1/workflows/{workflow_id}",
            headers=self._get_headers(),
        ) as response:
            if response.status == 404:
                return None
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Failed to get workflow: {error_text}")

            item = await response.json()
            return N8nWorkflow(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                active=item.get("active", False),
                nodes=item.get("nodes", []),
                connections=item.get("connections", {}),
                tags=[t.get("name", "") for t in item.get("tags", [])],
                metadata=item,
            )

    async def activate_workflow(self, workflow_id: str) -> bool:
        """
        Activate a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if activated successfully
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/activate",
            headers=self._get_headers(),
        ) as response:
            return response.status == 200

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        Deactivate a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deactivated successfully
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/deactivate",
            headers=self._get_headers(),
        ) as response:
            return response.status == 200

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = False,
    ) -> N8nExecution:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow ID
            data: Input data for the workflow
            wait_for_completion: Whether to wait for execution to complete

        Returns:
            N8nExecution with execution details
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        payload = {}
        if data:
            payload["data"] = data

        async with self._session.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            if response.status not in (200, 201):
                error_text = await response.text()
                raise RuntimeError(f"Failed to execute workflow: {error_text}")

            result = await response.json()
            execution = N8nExecution(
                id=str(result.get("executionId", result.get("id", ""))),
                workflow_id=workflow_id,
                status=ExecutionStatus.RUNNING,
                mode="api",
                data=result.get("data", {}),
            )

            if wait_for_completion:
                return await self.wait_for_execution(execution.id)

            return execution

    async def get_execution(self, execution_id: str) -> Optional[N8nExecution]:
        """
        Get execution details.

        Args:
            execution_id: Execution ID

        Returns:
            N8nExecution or None if not found
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.get(
            f"{self.base_url}/api/v1/executions/{execution_id}",
            headers=self._get_headers(),
        ) as response:
            if response.status == 404:
                return None
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Failed to get execution: {error_text}")

            item = await response.json()

            # Parse status
            finished = item.get("finished", False)
            has_error = bool(item.get("error"))

            if has_error:
                status = ExecutionStatus.ERROR
            elif finished:
                status = ExecutionStatus.SUCCESS
            else:
                status = ExecutionStatus.RUNNING

            return N8nExecution(
                id=str(item.get("id", "")),
                workflow_id=str(item.get("workflowId", "")),
                status=status,
                mode=item.get("mode", ""),
                data=item.get("data", {}),
                error=item.get("error", {}).get("message") if item.get("error") else None,
            )

    async def wait_for_execution(
        self,
        execution_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> N8nExecution:
        """
        Wait for an execution to complete.

        Args:
            execution_id: Execution ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds

        Returns:
            Completed N8nExecution

        Raises:
            TimeoutError: If execution doesn't complete in time
        """
        start_time = asyncio.get_running_loop().time()

        while True:
            execution = await self.get_execution(execution_id)

            if execution is None:
                raise RuntimeError(f"Execution not found: {execution_id}")

            if execution.status in (
                ExecutionStatus.SUCCESS,
                ExecutionStatus.ERROR,
                ExecutionStatus.CANCELED,
            ):
                return execution

            elapsed = asyncio.get_running_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Execution {execution_id} timed out after {timeout}s")

            await asyncio.sleep(poll_interval)

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 20,
    ) -> List[N8nExecution]:
        """
        List workflow executions.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status
            limit: Maximum results

        Returns:
            List of N8nExecution objects
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        params = {"limit": str(limit)}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status.value

        async with self._session.get(
            f"{self.base_url}/api/v1/executions",
            headers=self._get_headers(),
            params=params,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Failed to list executions: {error_text}")

            data = await response.json()
            executions = []

            for item in data.get("data", []):
                finished = item.get("finished", False)
                has_error = bool(item.get("error"))

                if has_error:
                    exec_status = ExecutionStatus.ERROR
                elif finished:
                    exec_status = ExecutionStatus.SUCCESS
                else:
                    exec_status = ExecutionStatus.RUNNING

                executions.append(
                    N8nExecution(
                        id=str(item.get("id", "")),
                        workflow_id=str(item.get("workflowId", "")),
                        status=exec_status,
                        mode=item.get("mode", ""),
                        data=item.get("data", {}),
                        error=item.get("error", {}).get("message") if item.get("error") else None,
                    )
                )

            return executions

    async def delete_execution(self, execution_id: str) -> bool:
        """
        Delete an execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if deleted successfully
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        async with self._session.delete(
            f"{self.base_url}/api/v1/executions/{execution_id}",
            headers=self._get_headers(),
        ) as response:
            return response.status == 200

    async def send_webhook(
        self,
        webhook_path: str,
        data: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send data to an n8n webhook.

        Args:
            webhook_path: Webhook path (after /webhook/)
            data: Data to send
            method: HTTP method (POST, GET, etc.)
            headers: Optional additional headers

        Returns:
            Response data from webhook
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        url = f"{self.base_url}/webhook/{webhook_path.lstrip('/')}"

        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        if method.upper() == "GET":
            async with self._session.get(url, headers=request_headers, params=data) as response:
                if response.content_type == "application/json":
                    return await response.json()
                return {"response": await response.text(), "status": response.status}
        else:
            async with self._session.post(url, headers=request_headers, json=data) as response:
                if response.content_type == "application/json":
                    return await response.json()
                return {"response": await response.text(), "status": response.status}

    async def send_webhook_test(
        self,
        webhook_path: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send data to an n8n test webhook.

        Test webhooks are used when testing workflows in the n8n editor.

        Args:
            webhook_path: Webhook path
            data: Data to send

        Returns:
            Response data from webhook
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        url = f"{self.base_url}/webhook-test/{webhook_path.lstrip('/')}"

        async with self._session.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data,
        ) as response:
            if response.content_type == "application/json":
                return await response.json()
            return {"response": await response.text(), "status": response.status}


class N8nWebhookHandler:
    """
    Handler for receiving webhooks from n8n.

    This allows ag3ntwerk to receive callbacks and events from n8n workflows.

    Example:
        handler = N8nWebhookHandler(secret="shared_secret")

        @handler.on("task_completed")
        async def handle_task_completed(data):
            print(f"Task completed: {data}")

        # In your FastAPI app:
        @app.post("/webhooks/n8n/{event_type}")
        async def n8n_webhook(event_type: str, request: Request):
            return await handler.handle(event_type, await request.json())
    """

    def __init__(
        self,
        secret: Optional[str] = None,
        verify_signature: bool = True,
    ):
        """
        Initialize webhook handler.

        Args:
            secret: Shared secret for signature verification
            verify_signature: Whether to verify webhook signatures
        """
        self.secret = secret
        self.verify_signature = verify_signature and secret is not None
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event_type: str):
        """
        Decorator to register a webhook handler.

        Args:
            event_type: Event type to handle

        Returns:
            Decorator function
        """

        def decorator(func: Callable):
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(func)
            return func

        return decorator

    def register_handler(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """
        Register a webhook handler.

        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw request body
            signature: Signature from X-N8N-Signature header

        Returns:
            True if signature is valid
        """
        if not self.secret:
            return True

        expected = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle(
        self,
        event_type: str,
        data: Dict[str, Any],
        signature: Optional[str] = None,
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Handle an incoming webhook.

        Args:
            event_type: Type of event
            data: Webhook payload
            signature: Optional signature for verification
            raw_body: Raw request body for signature verification

        Returns:
            Response data
        """
        # Verify signature if enabled
        if self.verify_signature and raw_body and signature:
            if not self.verify_webhook_signature(raw_body, signature):
                return {"error": "Invalid signature", "status": 401}

        # Get handlers for this event type
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            # Check for wildcard handler
            handlers = self._handlers.get("*", [])

        if not handlers:
            logger.warning(f"No handler for webhook event: {event_type}")
            return {"status": "no_handler", "event_type": event_type}

        # Execute all handlers
        results = []
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Webhook handler error: {e}")
                results.append({"error": str(e)})

        return {
            "status": "processed",
            "event_type": event_type,
            "handler_count": len(handlers),
            "results": results,
        }


class N8nExecutive:
    """
    Wrapper to use n8n workflows as ag3ntwerk agents.

    This allows an n8n workflow to be treated as an agent
    that can be called by the Nexus orchestrator.

    Example:
        # Create agent from n8n workflow
        data_exec = N8nExecutive(
            client=n8n_client,
            workflow_id="data_processing_123",
            name="Data Processor",
            domain="data",
        )

        # Execute task through the workflow
        result = await data_exec.execute(task)
    """

    def __init__(
        self,
        client: N8nClient,
        workflow_id: str,
        name: str = "n8n Agent",
        domain: str = "general",
        codename: str = "Workflow",
        wait_for_completion: bool = True,
    ):
        """
        Initialize n8n agent.

        Args:
            client: N8nClient instance
            workflow_id: ID of the n8n workflow to use
            name: Display name for the agent
            domain: Domain of expertise
            codename: Codename for the agent
            wait_for_completion: Wait for workflow to complete
        """
        self.client = client
        self.workflow_id = workflow_id
        self.name = name
        self.domain = domain
        self.codename = codename
        self.wait_for_completion = wait_for_completion

    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task through the n8n workflow.

        Args:
            task_description: Description of the task
            context: Optional context for the task

        Returns:
            Result dictionary with output and metadata
        """
        # Build workflow input
        workflow_data = {
            "task": task_description,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }

        execution = await self.client.execute_workflow(
            workflow_id=self.workflow_id,
            data=workflow_data,
            wait_for_completion=self.wait_for_completion,
        )

        if execution.status == ExecutionStatus.ERROR:
            return {
                "success": False,
                "error": execution.error,
                "execution_id": execution.id,
            }

        return {
            "success": True,
            "output": execution.data,
            "execution_id": execution.id,
            "status": execution.status.value,
        }
