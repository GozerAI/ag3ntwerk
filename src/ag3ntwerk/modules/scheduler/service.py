"""
Scheduler Service - High-level service interface for agents.

Provides a unified API for ag3ntwerk agents to interact with
task scheduling and workflow orchestration.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ag3ntwerk.modules.scheduler.core import (
    ScheduleConfig,
    ScheduleFrequency,
    ScheduledTask,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    TASK_TEMPLATES,
)
from ag3ntwerk.modules.scheduler.engine import SchedulerEngine
from ag3ntwerk.modules.scheduler.workflows import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutor,
    WorkflowStep,
    WorkflowStatus,
    create_daily_operations_workflow,
    create_pricing_optimization_workflow,
    create_brand_audit_workflow,
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    High-level scheduler service for ag3ntwerk agents.

    This service provides a unified interface for:
    - Nexus (Conductor): Full scheduler management, workflow orchestration
    - CEO (Apex): High-level status, strategic workflows
    - Keystone (Keystone): Financial task scheduling
    - Axiom (Axiom): Sales/commerce task scheduling

    Example:
        ```python
        service = SchedulerService()

        # Schedule a task
        task_id = service.schedule_task(
            name="Daily Trend Analysis",
            handler_name="trend_service.run_analysis",
            frequency="daily",
            priority="high",
        )

        # Start the scheduler
        await service.start()

        # Get agent report
        report = service.get_agent_report("Nexus")
        ```
    """

    def __init__(self):
        """Initialize the scheduler service."""
        self._engine = SchedulerEngine()
        self._workflow_executor = WorkflowExecutor()
        self._handlers: Dict[str, Callable] = {}
        self._initialized = False

        # Register pre-defined workflows
        self._register_default_workflows()

    def _register_default_workflows(self) -> None:
        """Register default workflow definitions."""
        workflows = [
            create_daily_operations_workflow(),
            create_pricing_optimization_workflow(),
            create_brand_audit_workflow(),
        ]

        for workflow in workflows:
            self._workflow_executor.register_workflow(workflow)
            logger.info(f"Registered workflow: {workflow.name}")

    def register_handler(
        self,
        name: str,
        handler: Callable,
    ) -> None:
        """
        Register a task handler.

        Args:
            name: Handler name (used in task definitions)
            handler: Callable to execute (sync or async)
        """
        self._handlers[name] = handler
        self._engine.register_handler(name, handler)
        self._workflow_executor.register_handler(name, handler)
        logger.info(f"Registered handler: {name}")

    def schedule_task(
        self,
        name: str,
        handler_name: str,
        description: str = "",
        frequency: str = "daily",
        priority: str = "normal",
        category: str = "operations",
        owner_executive: str = "Nexus",
        handler_params: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None,
        hour: int = 0,
        minute: int = 0,
        day_of_week: Optional[int] = None,
        enabled: bool = True,
    ) -> str:
        """
        Schedule a new task.

        Args:
            name: Task name
            handler_name: Name of registered handler
            description: Task description
            frequency: Frequency (hourly, daily, weekly, monthly)
            priority: Priority level
            category: Task category
            owner_executive: Agent code who owns this task
            handler_params: Parameters to pass to handler
            cron_expression: Optional cron expression
            hour: Hour to run (for daily/weekly/monthly)
            minute: Minute to run
            day_of_week: Day of week (0=Monday) for weekly tasks
            enabled: Whether task is enabled

        Returns:
            Task ID
        """
        frequency_map = {
            "hourly": ScheduleFrequency.HOURLY,
            "daily": ScheduleFrequency.DAILY,
            "weekly": ScheduleFrequency.WEEKLY,
            "monthly": ScheduleFrequency.MONTHLY,
            "on_demand": ScheduleFrequency.ON_DEMAND,
        }

        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        category_map = {
            "operations": TaskCategory.OPERATIONS,
            "analytics": TaskCategory.ANALYTICS,
            "maintenance": TaskCategory.MAINTENANCE,
            "reporting": TaskCategory.REPORTING,
            "integration": TaskCategory.INTEGRATION,
        }

        schedule = ScheduleConfig(
            frequency=frequency_map.get(frequency, ScheduleFrequency.DAILY),
            cron_expression=cron_expression,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
        )

        task = ScheduledTask(
            name=name,
            description=description,
            handler_name=handler_name,
            handler_params=handler_params or {},
            schedule=schedule,
            priority=priority_map.get(priority, TaskPriority.NORMAL),
            category=category_map.get(category, TaskCategory.OPERATIONS),
            owner_executive=owner_executive,
            enabled=enabled,
        )

        self._engine.schedule_task(task)
        self._initialized = True

        return task.id

    def schedule_from_template(
        self,
        template_name: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Schedule a task from a pre-defined template.

        Args:
            template_name: Name of template (from TASK_TEMPLATES)
            overrides: Optional parameter overrides

        Returns:
            Task ID
        """
        if template_name not in TASK_TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")

        template = TASK_TEMPLATES[template_name].copy()
        if overrides:
            template.update(overrides)

        return self.schedule_task(**template)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        task = self._engine.get_task(task_id)
        return task.to_dict() if task else None

    def list_tasks(
        self,
        owner_executive: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List scheduled tasks with optional filters.

        Args:
            owner_executive: Filter by owner
            category: Filter by category
            status: Filter by status

        Returns:
            List of task dictionaries
        """
        tasks = self._engine.list_tasks()

        if owner_executive:
            tasks = [t for t in tasks if t.owner_executive == owner_executive]

        if category:
            category_map = {
                "operations": TaskCategory.OPERATIONS,
                "analytics": TaskCategory.ANALYTICS,
                "maintenance": TaskCategory.MAINTENANCE,
                "reporting": TaskCategory.REPORTING,
            }
            cat = category_map.get(category)
            if cat:
                tasks = [t for t in tasks if t.category == cat]

        if status:
            status_map = {
                "active": TaskStatus.ACTIVE,
                "paused": TaskStatus.PAUSED,
                "completed": TaskStatus.COMPLETED,
            }
            st = status_map.get(status)
            if st:
                tasks = [t for t in tasks if t.status == st]

        return [t.to_dict() for t in tasks]

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        task = self._engine.get_task(task_id)
        if task:
            task.enabled = True
            task.status = TaskStatus.SCHEDULED
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        task = self._engine.get_task(task_id)
        if task:
            task.enabled = False
            task.status = TaskStatus.PAUSED
            return True
        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the schedule."""
        return self._engine.remove_task(task_id)

    async def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """
        Run a task immediately (on-demand).

        Args:
            task_id: ID of task to run

        Returns:
            Execution result
        """
        result = await self._engine.execute_task(task_id)
        return result.to_dict()

    # Workflow Management

    def create_workflow(
        self,
        name: str,
        description: str = "",
        owner_executive: str = "Nexus",
        parallel_execution: bool = False,
        stop_on_failure: bool = True,
    ) -> str:
        """
        Create a new workflow definition.

        Args:
            name: Workflow name
            description: Workflow description
            owner_executive: Agent who owns this workflow
            parallel_execution: Run independent steps in parallel
            stop_on_failure: Stop workflow on step failure

        Returns:
            Workflow ID
        """
        workflow = WorkflowDefinition(
            name=name,
            description=description,
            owner_executive=owner_executive,
            parallel_execution=parallel_execution,
            stop_on_failure=stop_on_failure,
        )

        self._workflow_executor.register_workflow(workflow)
        return workflow.id

    def add_workflow_step(
        self,
        workflow_id: str,
        name: str,
        handler_name: str,
        description: str = "",
        depends_on: Optional[List[str]] = None,
        handler_params: Optional[Dict[str, Any]] = None,
        continue_on_failure: bool = False,
        timeout_seconds: int = 300,
    ) -> Optional[str]:
        """
        Add a step to a workflow.

        Args:
            workflow_id: ID of workflow
            name: Step name
            handler_name: Handler to execute
            description: Step description
            depends_on: List of step IDs this depends on
            handler_params: Parameters for handler
            continue_on_failure: Continue workflow if step fails
            timeout_seconds: Step timeout

        Returns:
            Step ID or None if workflow not found
        """
        workflow = self._workflow_executor.get_workflow(workflow_id)
        if not workflow:
            return None

        step = WorkflowStep(
            name=name,
            description=description,
            handler_name=handler_name,
            handler_params=handler_params or {},
            depends_on=depends_on or [],
            continue_on_failure=continue_on_failure,
            timeout_seconds=timeout_seconds,
        )

        workflow.add_step(step)
        return step.id

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow by ID."""
        workflow = self._workflow_executor.get_workflow(workflow_id)
        return workflow.to_dict() if workflow else None

    def list_workflows(
        self,
        owner_executive: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all workflows."""
        workflows = self._workflow_executor.list_workflows()

        if owner_executive:
            workflows = [w for w in workflows if w.owner_executive == owner_executive]

        return [w.to_dict() for w in workflows]

    async def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of workflow to execute
            initial_context: Initial context data

        Returns:
            Workflow execution result
        """
        execution = await self._workflow_executor.execute_workflow(
            workflow_id,
            initial_context,
        )
        return execution.to_dict()

    def get_workflow_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get workflow execution history."""
        executions = self._workflow_executor.get_executions(workflow_id, limit)
        return [e.to_dict() for e in executions]

    # Scheduler Control

    async def start(self) -> None:
        """Start the scheduler engine."""
        await self._engine.start()

    async def stop(self) -> None:
        """Stop the scheduler engine."""
        await self._engine.stop()

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._engine._running

    # Agent Reports

    def get_agent_report(self, agent_code: str) -> Dict[str, Any]:
        """
        Generate a report tailored for a specific agent.

        Args:
            agent_code: The agent code (Nexus, CEO, Keystone, Axiom)

        Returns:
            Agent-specific scheduler report
        """
        base_info = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scheduler_running": self._engine._running,
        }

        engine_stats = self._engine.get_metrics()
        queue_stats = engine_stats.get("queue_stats", {})
        workflow_stats = self._workflow_executor.get_stats()

        if agent_code == "Nexus":
            # Operations focus: full visibility and control
            tasks = self.list_tasks()
            workflows = self.list_workflows()

            return {
                "agent": "Nexus",
                "focus": "Operations & Orchestration",
                **base_info,
                "scheduler_overview": {
                    "total_tasks": queue_stats.get("total_tasks", 0),
                    "running_tasks": queue_stats.get("running_tasks", 0),
                    "uptime_seconds": engine_stats.get("uptime_seconds"),
                },
                "tasks_by_category": queue_stats.get("by_category", {}),
                "tasks_by_priority": queue_stats.get("by_priority", {}),
                "tasks_by_status": queue_stats.get("by_status", {}),
                "workflows": {
                    "registered": workflow_stats.get("registered_workflows", 0),
                    "total_executions": workflow_stats.get("total_executions", 0),
                    "by_status": workflow_stats.get("by_status", {}),
                },
                "all_tasks": tasks,
                "all_workflows": workflows,
                "recommendations": self._generate_coo_recommendations(queue_stats),
            }

        elif agent_code == "CEO":
            # Strategic focus: high-level status, critical items
            return {
                "agent": "CEO",
                "focus": "Strategic Overview",
                **base_info,
                "operational_health": {
                    "scheduler_active": self._engine._running,
                    "total_automated_tasks": queue_stats.get("total_tasks", 0),
                    "automation_rate": self._calculate_automation_rate(),
                },
                "critical_workflows": [
                    w.to_dict()
                    for w in self._workflow_executor.list_workflows()
                    if w.owner_executive == "CEO"
                ],
                "executive_task_distribution": self._get_task_distribution_by_agent(),
                "key_metrics": {
                    "tasks_today": self._count_tasks_run_today(),
                    "success_rate": self._calculate_success_rate(queue_stats),
                    "active_workflows": workflow_stats.get("registered_workflows", 0),
                },
            }

        elif agent_code == "Keystone":
            # Financial focus: cost-related tasks, financial workflows
            financial_tasks = self.list_tasks(owner_executive="Keystone")
            financial_tasks.extend(self.list_tasks(category="analytics"))

            return {
                "agent": "Keystone",
                "focus": "Financial Operations",
                **base_info,
                "financial_tasks": {
                    "total": len(financial_tasks),
                    "active": len([t for t in financial_tasks if t.get("enabled", False)]),
                    "tasks": financial_tasks,
                },
                "scheduled_reports": [
                    t
                    for t in self.list_tasks(category="reporting")
                    if "financial" in t.get("name", "").lower()
                    or "cost" in t.get("name", "").lower()
                    or "pricing" in t.get("name", "").lower()
                ],
                "automation_cost_savings": {
                    "automated_tasks": queue_stats.get("total_tasks", 0),
                    "estimated_hours_saved_monthly": queue_stats.get("total_tasks", 0) * 2,
                },
            }

        elif agent_code == "Axiom":
            # Revenue focus: sales and commerce tasks
            revenue_tasks = self.list_tasks(owner_executive="Axiom")

            return {
                "agent": "Axiom",
                "focus": "Revenue Operations",
                **base_info,
                "revenue_tasks": {
                    "total": len(revenue_tasks),
                    "tasks": revenue_tasks,
                },
                "commerce_automation": {
                    "pricing_tasks": len(
                        [t for t in revenue_tasks if "pricing" in t.get("name", "").lower()]
                    ),
                    "inventory_tasks": len(
                        [t for t in revenue_tasks if "inventory" in t.get("name", "").lower()]
                    ),
                },
                "scheduled_sales_reports": [
                    t
                    for t in self.list_tasks(category="reporting")
                    if "sales" in t.get("name", "").lower()
                    or "revenue" in t.get("name", "").lower()
                ],
            }

        elif agent_code == "Echo":
            # Marketing focus: trend and campaign tasks
            marketing_tasks = self.list_tasks(owner_executive="Echo")

            return {
                "agent": "Echo",
                "focus": "Marketing Operations",
                **base_info,
                "marketing_tasks": {
                    "total": len(marketing_tasks),
                    "tasks": marketing_tasks,
                },
                "trend_monitoring": {
                    "trend_tasks": len(
                        [t for t in marketing_tasks if "trend" in t.get("name", "").lower()]
                    ),
                    "brand_tasks": len(
                        [t for t in marketing_tasks if "brand" in t.get("name", "").lower()]
                    ),
                },
            }

        else:
            # Default: basic overview
            return {
                "agent": agent_code,
                "focus": "General Overview",
                **base_info,
                "your_tasks": self.list_tasks(owner_executive=agent_code),
                "scheduler_stats": engine_stats,
            }

    def _generate_coo_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate operational recommendations for Nexus."""
        recommendations = []

        total_tasks = stats.get("total_tasks", 0)
        running_tasks = stats.get("running_tasks", 0)

        if total_tasks == 0:
            recommendations.append("No tasks scheduled - consider adding automated tasks")

        if running_tasks > total_tasks * 0.5:
            recommendations.append("Many tasks currently running - monitor for bottlenecks")

        if not recommendations:
            recommendations.append("Scheduler operating normally")

        return recommendations

    def _calculate_automation_rate(self) -> float:
        """Calculate automation coverage rate."""
        # Placeholder - would compare automated vs manual tasks
        metrics = self._engine.get_metrics()
        queue_stats = metrics.get("queue_stats", {})
        total = queue_stats.get("total_tasks", 0)
        return 100.0 if total > 0 else 0.0

    def _get_task_distribution_by_agent(self) -> Dict[str, int]:
        """Get task count by agent owner."""
        tasks = self._engine.list_tasks()
        distribution = {}
        for task in tasks:
            owner = task.owner_executive
            distribution[owner] = distribution.get(owner, 0) + 1
        return distribution

    def _count_tasks_run_today(self) -> int:
        """Count tasks that ran today."""
        today = datetime.now(timezone.utc).date()
        count = 0
        for task in self._engine.list_tasks():
            if task.last_run and task.last_run.date() == today:
                count += 1
        return count

    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate task success rate."""
        total = stats.get("total_executions", 0)
        if total == 0:
            return 100.0

        successful = sum(
            1 for exec_info in stats.get("recent_executions", []) if exec_info.get("success", False)
        )
        return (successful / min(total, len(stats.get("recent_executions", [])))) * 100

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "initialized": self._initialized,
            "scheduler_running": self._engine._running,
            "engine": self._engine.get_metrics(),
            "workflows": self._workflow_executor.get_stats(),
            "registered_handlers": len(self._handlers),
        }

    async def run_autonomous_cycle(self) -> Dict[str, Any]:
        """
        Run an autonomous operational cycle.

        Designed to be called by the Nexus for periodic
        self-management operations.
        """
        results = {
            "cycle_started_at": datetime.now(timezone.utc).isoformat(),
            "tasks_executed": [],
            "workflows_executed": [],
        }

        # Get all due tasks
        due_tasks = self._engine.get_due_tasks()

        # Execute due tasks
        for task in due_tasks[:5]:  # Limit to 5 per cycle
            try:
                result = await self._engine.execute_task(task.id)
                results["tasks_executed"].append(
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "success": result.success,
                    }
                )
            except Exception as e:
                results["tasks_executed"].append(
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "success": False,
                        "error": str(e),
                    }
                )

        results["cycle_completed_at"] = datetime.now(timezone.utc).isoformat()
        results["tasks_processed"] = len(results["tasks_executed"])

        return results
