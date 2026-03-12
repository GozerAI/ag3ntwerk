"""
Workbench Automation Package.

Provides automation hooks for:
- TaskQueue integration (scheduled/triggered pipeline execution)
- Event triggers (file changes, webhooks)
- Scheduled tasks (health checks, cleanup)
"""

from ag3ntwerk.modules.workbench.automation.task_handlers import (
    handle_pipeline_task,
    handle_deploy_task,
    register_workbench_handlers,
)
from ag3ntwerk.modules.workbench.automation.triggers import (
    on_file_changed,
    on_webhook_deploy,
    register_workbench_triggers,
)
from ag3ntwerk.modules.workbench.automation.scheduler import (
    scheduled_workspace_health_check,
    scheduled_idle_cleanup,
    register_workbench_schedules,
)

__all__ = [
    # Task handlers
    "handle_pipeline_task",
    "handle_deploy_task",
    "register_workbench_handlers",
    # Triggers
    "on_file_changed",
    "on_webhook_deploy",
    "register_workbench_triggers",
    # Scheduler
    "scheduled_workspace_health_check",
    "scheduled_idle_cleanup",
    "register_workbench_schedules",
    # Bootstrap
    "bootstrap_workbench_automation",
]


async def bootstrap_workbench_automation() -> None:
    """
    Bootstrap all workbench automation.

    Call this during application startup to wire up:
    - Task handlers (for queued pipeline execution)
    - Event triggers (for reactive automation)
    - Scheduled tasks (for periodic maintenance)

    Example:
        ```python
        from ag3ntwerk.modules.workbench.automation import bootstrap_workbench_automation

        # During app startup
        await bootstrap_workbench_automation()
        ```
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Import queue and register handlers
        try:
            from ag3ntwerk.core.queue import get_task_queue

            queue = get_task_queue()
            register_workbench_handlers(queue)
            logger.info("Registered workbench task handlers with TaskQueue")
        except ImportError:
            logger.warning("TaskQueue not available, skipping handler registration")
        except Exception as e:
            logger.error(f"Failed to register task handlers: {e}")

        # Import trigger manager and register triggers
        try:
            # Note: TriggerManager may be in nexus package
            from nexus.automations.triggers import TriggerManager

            trigger_manager = TriggerManager()
            register_workbench_triggers(trigger_manager)
            trigger_manager.start()
            logger.info("Registered workbench triggers with TriggerManager")
        except ImportError:
            logger.warning("TriggerManager not available, skipping trigger registration")
        except Exception as e:
            logger.error(f"Failed to register triggers: {e}")

        # Import scheduler and register scheduled tasks
        try:
            # Note: Scheduler may be in sentinel package
            from sentinel.core.scheduler import Scheduler

            scheduler = Scheduler()
            register_workbench_schedules(scheduler)
            await scheduler.start()
            logger.info("Registered workbench scheduled tasks with Scheduler")
        except ImportError:
            logger.warning("Scheduler not available, skipping schedule registration")
        except Exception as e:
            logger.error(f"Failed to register scheduled tasks: {e}")

        logger.info("Workbench automation bootstrap complete")

    except Exception as e:
        logger.error(f"Workbench automation bootstrap failed: {e}")
        raise
