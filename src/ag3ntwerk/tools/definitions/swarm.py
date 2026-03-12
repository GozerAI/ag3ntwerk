"""
Swarm Tool Definitions.

Tools for delegating tasks to the Claude Swarm from any ag3ntwerk agent.
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


class SwarmExecuteTool(BaseTool):
    """Execute a task on the Claude Swarm."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="execute_on_swarm",
            description="Delegate a coding task to the Claude Swarm for execution by local LLMs with tool calling",
            category=ToolCategory.AUTOMATION,
            tags=["swarm", "delegate", "code", "llm", "local", "tool_calling"],
            examples=[
                "Review the code quality of src/main.py",
                "Find security vulnerabilities in the auth module",
                "Generate unit tests for the payment service",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="prompt",
                description="Task prompt to send to the Swarm",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="task_type",
                description="Task type hint (code_review, debugging, testing, security_audit, documentation, architecture, general)",
                param_type=ParameterType.STRING,
                required=False,
                default="general",
            ),
            ToolParameter(
                name="priority",
                description="Task priority (low, normal, high, critical)",
                param_type=ParameterType.STRING,
                required=False,
                default="normal",
            ),
            ToolParameter(
                name="wait",
                description="Wait for task completion (default True)",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=True,
            ),
            ToolParameter(
                name="timeout",
                description="Timeout in seconds (default 300)",
                param_type=ParameterType.INTEGER,
                required=False,
                default=300,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        prompt = kwargs.get("prompt", "")
        task_type = kwargs.get("task_type", "general")
        priority = kwargs.get("priority", "normal")
        wait = kwargs.get("wait", True)
        timeout = kwargs.get("timeout", 300)

        try:
            from ag3ntwerk.modules.swarm_bridge.service import SwarmBridgeService

            service = SwarmBridgeService()

            # Check availability
            available = await service.is_swarm_available()
            if not available:
                return ToolResult(
                    success=False,
                    error="Swarm is not available. Ensure the Swarm API is running.",
                    error_type="ConnectionError",
                )

            # Get the calling agent's code from the execution context
            agent_code = kwargs.get("_agent_code", "")

            task_id = await service.submit_task(
                prompt=prompt,
                agent_code=agent_code,
                priority=priority,
                timeout=timeout,
                metadata={"task_type": task_type},
            )

            if not wait:
                return ToolResult(
                    success=True,
                    data={
                        "task_id": task_id,
                        "status": "submitted",
                        "message": f"Task submitted to Swarm: {task_id}",
                    },
                )

            # Wait for completion
            result = await service.wait_for_task(task_id, timeout=float(timeout))

            if result.get("status") == "completed":
                output = result.get("result", {}).get("output", "")
                model = result.get("result", {}).get("model", "unknown")
                tool_calls = result.get("result", {}).get("tool_calls", [])
                return ToolResult(
                    success=True,
                    data={
                        "task_id": task_id,
                        "output": output,
                        "model": model,
                        "tool_calls_count": len(tool_calls),
                        "duration_seconds": result.get("duration_seconds", 0),
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Task failed"),
                    error_type="SwarmTaskError",
                    data={"task_id": task_id},
                )

        except TimeoutError:
            return ToolResult(
                success=False,
                error=f"Task did not complete within {timeout}s",
                error_type="TimeoutError",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class SwarmStatusTool(BaseTool):
    """Check the status of the Claude Swarm."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="swarm_status",
            description="Check the status of the Claude Swarm (instances, models, tasks)",
            category=ToolCategory.AUTOMATION,
            tags=["swarm", "status", "health"],
            examples=["Check swarm status", "Is the swarm running?"],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    async def _execute(self, **kwargs) -> ToolResult:
        try:
            from ag3ntwerk.modules.swarm_bridge.service import SwarmBridgeService

            service = SwarmBridgeService()
            available = await service.is_swarm_available()

            if not available:
                return ToolResult(
                    success=True,
                    data={"available": False, "message": "Swarm is not reachable"},
                )

            status = await service.get_swarm_status()
            models = await service.get_available_models()

            return ToolResult(
                success=True,
                data={
                    "available": True,
                    "running": status.get("running", False),
                    "workers": status.get("workers", 0),
                    "instances": status.get("instances", {}),
                    "tasks": status.get("tasks", {}),
                    "models_count": len(models),
                    "tool_capable_models": [
                        m["name"] for m in models if m.get("supports_tool_calling")
                    ],
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
