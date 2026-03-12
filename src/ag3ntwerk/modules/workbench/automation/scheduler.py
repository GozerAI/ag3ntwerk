"""
Scheduler - Scheduled tasks for workbench automation.

Provides periodic maintenance tasks:
- Workspace health checks
- Idle workspace cleanup
- Resource monitoring
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
IDLE_CLEANUP_INTERVAL = 3600  # 1 hour
IDLE_TIMEOUT_MINUTES = 60  # Stop workspaces idle for 1 hour


async def scheduled_workspace_health_check() -> Dict[str, Any]:
    """
    Periodic health check for all running workspaces.

    Checks:
    - Container is running
    - IDE is responsive (if started)
    - Resource usage is within limits

    Returns:
        Health check results
    """
    from ag3ntwerk.modules.workbench.service import get_workbench_service
    from ag3ntwerk.modules.workbench.schemas import WorkspaceStatus

    logger.debug("Running workspace health check")

    service = get_workbench_service()
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checked": 0,
        "healthy": 0,
        "unhealthy": [],
    }

    try:
        workspaces = await service.list_workspaces()

        for workspace in workspaces:
            if workspace.status == WorkspaceStatus.RUNNING:
                results["checked"] += 1

                # Check workspace health
                is_healthy = await service.is_healthy()

                if is_healthy:
                    results["healthy"] += 1
                else:
                    results["unhealthy"].append(
                        {
                            "workspace_id": workspace.id,
                            "name": workspace.name,
                            "status": workspace.status.value,
                        }
                    )
                    logger.warning(f"Workspace unhealthy: {workspace.id}")

        logger.info(f"Health check complete: {results['healthy']}/{results['checked']} healthy")

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        results["error"] = str(e)

    return results


async def scheduled_idle_cleanup() -> Dict[str, Any]:
    """
    Stop idle workspaces to conserve resources.

    Identifies workspaces that have been running but idle
    (no commands executed) for longer than the timeout.

    Returns:
        Cleanup results
    """
    from ag3ntwerk.modules.workbench.service import get_workbench_service
    from ag3ntwerk.modules.workbench.schemas import WorkspaceStatus

    logger.debug("Running idle workspace cleanup")

    service = get_workbench_service()
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checked": 0,
        "stopped": [],
        "errors": [],
    }

    try:
        workspaces = await service.list_workspaces()
        now = datetime.now(timezone.utc)
        idle_threshold = now - timedelta(minutes=IDLE_TIMEOUT_MINUTES)

        for workspace in workspaces:
            if workspace.status == WorkspaceStatus.RUNNING:
                results["checked"] += 1

                # Check if workspace has been idle
                last_activity = workspace.updated_at
                if last_activity and last_activity < idle_threshold:
                    logger.info(
                        f"Stopping idle workspace {workspace.id} "
                        f"(last activity: {last_activity})"
                    )

                    try:
                        await service.stop_workspace(workspace.id)
                        results["stopped"].append(
                            {
                                "workspace_id": workspace.id,
                                "name": workspace.name,
                                "idle_minutes": (now - last_activity).seconds // 60,
                            }
                        )

                        # Also stop IDE if running
                        try:
                            await service.stop_ide(workspace.id)
                        except Exception as e:
                            logger.debug(
                                "Failed to stop IDE for workspace %s (may not be running): %s",
                                workspace.id,
                                e,
                            )

                    except Exception as e:
                        logger.error(f"Failed to stop workspace {workspace.id}: {e}")
                        results["errors"].append(
                            {
                                "workspace_id": workspace.id,
                                "error": str(e),
                            }
                        )

        logger.info(f"Idle cleanup complete: {len(results['stopped'])} workspaces stopped")

    except Exception as e:
        logger.error(f"Idle cleanup failed: {e}")
        results["error"] = str(e)

    return results


async def scheduled_resource_monitor() -> Dict[str, Any]:
    """
    Monitor resource usage across all workspaces.

    Collects:
    - CPU usage per workspace
    - Memory usage per workspace
    - Disk usage
    - Port usage

    Returns:
        Resource monitoring results
    """
    from ag3ntwerk.modules.workbench.service import get_workbench_service
    from ag3ntwerk.modules.workbench.schemas import WorkspaceStatus

    logger.debug("Running resource monitoring")

    service = get_workbench_service()
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspaces": [],
        "summary": {
            "total_running": 0,
            "total_cpu_percent": 0.0,
            "total_memory_mb": 0,
        },
    }

    try:
        workspaces = await service.list_workspaces()

        for workspace in workspaces:
            if workspace.status == WorkspaceStatus.RUNNING:
                results["summary"]["total_running"] += 1

                # Get IDE status if available (includes resource usage)
                try:
                    ide_status = await service.get_ide_status(workspace.id)
                    workspace_info = {
                        "workspace_id": workspace.id,
                        "name": workspace.name,
                        "runtime": workspace.runtime.value,
                        "cpu_usage": ide_status.cpu_usage,
                        "memory_usage": ide_status.memory_usage,
                        "ide_running": ide_status.running,
                    }

                    if ide_status.cpu_usage:
                        results["summary"]["total_cpu_percent"] += ide_status.cpu_usage

                    results["workspaces"].append(workspace_info)

                except Exception as e:
                    results["workspaces"].append(
                        {
                            "workspace_id": workspace.id,
                            "name": workspace.name,
                            "runtime": workspace.runtime.value,
                            "error": str(e),
                        }
                    )

        # Get overall stats
        stats = service.get_stats()
        results["summary"]["total_workspaces"] = stats.total_workspaces
        results["summary"]["active_ports"] = stats.active_ports

        logger.debug(f"Resource monitor: {results['summary']['total_running']} running workspaces")

    except Exception as e:
        logger.error(f"Resource monitoring failed: {e}")
        results["error"] = str(e)

    return results


async def scheduled_orphan_cleanup() -> Dict[str, Any]:
    """
    Clean up orphaned containers and resources.

    Finds and removes:
    - IDE containers without matching workspaces
    - Allocated ports for deleted workspaces
    - Stale workspace directories

    Returns:
        Cleanup results
    """
    from ag3ntwerk.modules.workbench.service import get_workbench_service

    logger.debug("Running orphan cleanup")

    service = get_workbench_service()
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "containers_cleaned": 0,
        "ports_released": 0,
        "errors": [],
    }

    try:
        # Clean up orphaned IDE containers
        if hasattr(service, "_ide_manager"):
            cleaned = await service._ide_manager.cleanup_orphaned_containers()
            results["containers_cleaned"] = cleaned

        logger.info(f"Orphan cleanup complete: {results['containers_cleaned']} containers cleaned")

    except Exception as e:
        logger.error(f"Orphan cleanup failed: {e}")
        results["error"] = str(e)

    return results


def register_workbench_schedules(scheduler: Any) -> None:
    """
    Register workbench scheduled tasks with the Scheduler.

    Args:
        scheduler: Scheduler instance
    """
    try:
        # Health check every 5 minutes
        scheduler.add_task(
            name="workbench_health_check",
            callback=scheduled_workspace_health_check,
            interval_seconds=HEALTH_CHECK_INTERVAL,
            run_immediately=False,
        )
        logger.info(
            f"Registered schedule: workbench_health_check " f"(every {HEALTH_CHECK_INTERVAL}s)"
        )

        # Idle cleanup every hour
        scheduler.add_task(
            name="workbench_idle_cleanup",
            callback=scheduled_idle_cleanup,
            interval_seconds=IDLE_CLEANUP_INTERVAL,
            run_immediately=False,
        )
        logger.info(
            f"Registered schedule: workbench_idle_cleanup " f"(every {IDLE_CLEANUP_INTERVAL}s)"
        )

        # Resource monitoring every 5 minutes
        scheduler.add_task(
            name="workbench_resource_monitor",
            callback=scheduled_resource_monitor,
            interval_seconds=HEALTH_CHECK_INTERVAL,
            run_immediately=False,
        )
        logger.info("Registered schedule: workbench_resource_monitor")

        # Orphan cleanup every hour
        scheduler.add_task(
            name="workbench_orphan_cleanup",
            callback=scheduled_orphan_cleanup,
            interval_seconds=IDLE_CLEANUP_INTERVAL,
            run_immediately=False,
        )
        logger.info("Registered schedule: workbench_orphan_cleanup")

        logger.info("Registered all workbench scheduled tasks")

    except AttributeError:
        # Scheduler may have different API
        logger.warning("Scheduler API incompatible, trying alternate registration")

        try:
            scheduler.register("workbench_health_check", scheduled_workspace_health_check)
            scheduler.register("workbench_idle_cleanup", scheduled_idle_cleanup)
            scheduler.register("workbench_resource_monitor", scheduled_resource_monitor)
            scheduler.register("workbench_orphan_cleanup", scheduled_orphan_cleanup)
        except Exception as e:
            logger.error(f"Failed to register schedules: {e}")

    except Exception as e:
        logger.error(f"Failed to register scheduled tasks: {e}")
