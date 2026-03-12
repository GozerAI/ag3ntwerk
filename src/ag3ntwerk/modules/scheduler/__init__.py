"""
Autonomous Scheduler Module.

Provides task scheduling, autonomous execution, and reporting automation
for ag3ntwerk agents. Enables scheduled trend scans, pricing updates,
and automated reporting.

Primary Owner: Nexus (Conductor)
Secondary Owner: CEO (Apex)

Integrates with:
- Trend Intelligence (daily scans)
- Commerce Operations (pricing updates, inventory alerts)
- Brand Suite (consistency audits)
"""

from ag3ntwerk.modules.scheduler.core import (
    ScheduleFrequency,
    TaskStatus,
    ScheduledTask,
    TaskExecution,
    ExecutionResult,
)
from ag3ntwerk.modules.scheduler.engine import (
    SchedulerEngine,
    TaskQueue,
)
from ag3ntwerk.modules.scheduler.workflows import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowExecutor,
)
from ag3ntwerk.modules.scheduler.service import SchedulerService
from ag3ntwerk.modules.scheduler.persistence import SchedulerPersistence

__all__ = [
    # Core
    "ScheduleFrequency",
    "TaskStatus",
    "ScheduledTask",
    "TaskExecution",
    "ExecutionResult",
    # Engine
    "SchedulerEngine",
    "TaskQueue",
    # Workflows
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowExecutor",
    # Service
    "SchedulerService",
    # Persistence
    "SchedulerPersistence",
]
