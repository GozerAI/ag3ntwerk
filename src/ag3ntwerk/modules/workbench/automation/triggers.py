"""
Triggers - Event-driven automation for workbench.

Connects file events, webhooks, and other triggers to pipeline execution.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Source file extensions that should trigger rebuilds
SOURCE_EXTENSIONS = [
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".vue",
    ".svelte",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
]

# Config files that should trigger full rebuild
CONFIG_FILES = [
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "pyproject.toml",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "vercel.json",
    "netlify.toml",
    ".env.example",
]


async def on_file_changed(event: Any) -> None:
    """
    Handle file change events - trigger rebuild/redeploy.

    Event data:
    {
        "workspace_id": "ws-123",
        "file_path": "src/main.py",
        "change_type": "modified" | "created" | "deleted",
    }

    Args:
        event: TriggerEvent instance
    """
    workspace_id = event.data.get("workspace_id")
    file_path = event.data.get("file_path", "")
    change_type = event.data.get("change_type", "modified")

    if not workspace_id:
        logger.warning("File change event missing workspace_id")
        return

    # Determine if this file should trigger a rebuild
    should_rebuild = False
    is_config_change = False

    # Check if it's a source file
    for ext in SOURCE_EXTENSIONS:
        if file_path.endswith(ext):
            should_rebuild = True
            break

    # Check if it's a config file
    for config in CONFIG_FILES:
        if file_path.endswith(config):
            should_rebuild = True
            is_config_change = True
            break

    if not should_rebuild:
        logger.debug(f"Ignoring file change: {file_path}")
        return

    logger.info(f"File change detected: {file_path} ({change_type}) in {workspace_id}")

    try:
        # Try to enqueue via TaskQueue
        from ag3ntwerk.core.queue import enqueue_task

        if is_config_change:
            # Config changes → full pipeline with config regeneration
            await enqueue_task(
                task_type="workbench.pipeline",
                payload={
                    "workspace_id": workspace_id,
                    "pipeline_type": "oneclick",
                    "options": {
                        "target": "auto",
                        "generate_configs": True,
                    },
                },
                priority=5,  # Normal priority
            )
        else:
            # Source changes → just evaluation
            await enqueue_task(
                task_type="workbench.pipeline",
                payload={
                    "workspace_id": workspace_id,
                    "pipeline_type": "evaluate",
                    "options": {},
                },
                priority=5,
            )

        logger.info(f"Enqueued rebuild task for {workspace_id}")

    except ImportError:
        logger.warning("TaskQueue not available for file change handling")
    except Exception as e:
        logger.error(f"Failed to enqueue rebuild task: {e}")


async def on_webhook_deploy(event: Any) -> None:
    """
    Handle webhook-triggered deployments (e.g., GitHub push).

    Event data:
    {
        "workspace_id": "ws-123",
        "ref": "refs/heads/main",
        "target": "vercel" | "auto",
        "source": "github" | "gitlab" | "bitbucket",
        "commit_sha": "abc123",
    }

    Args:
        event: TriggerEvent instance
    """
    workspace_id = event.data.get("workspace_id")
    target = event.data.get("target", "auto")
    ref = event.data.get("ref", "")
    source = event.data.get("source", "unknown")
    commit_sha = event.data.get("commit_sha")

    if not workspace_id:
        logger.warning("Webhook deploy event missing workspace_id")
        return

    # Only deploy on main/master branch by default
    deploy_branches = ["main", "master", "production", "release"]
    should_deploy = not ref or any(branch in ref for branch in deploy_branches)

    if not should_deploy:
        logger.info(f"Skipping deploy for non-production branch: {ref}")
        return

    logger.info(
        f"Webhook deploy triggered for {workspace_id} from {source} "
        f"(ref: {ref}, commit: {commit_sha})"
    )

    try:
        from ag3ntwerk.core.queue import enqueue_task

        await enqueue_task(
            task_type="workbench.deploy",
            payload={
                "workspace_id": workspace_id,
                "target": target,
                "generate_configs": True,
                "environment": {
                    "GIT_COMMIT": commit_sha or "",
                    "GIT_REF": ref,
                    "DEPLOY_SOURCE": source,
                },
            },
            priority=3,  # Higher priority for webhook deploys
        )

        logger.info(f"Enqueued webhook deploy task for {workspace_id}")

    except ImportError:
        logger.warning("TaskQueue not available for webhook deploy")
    except Exception as e:
        logger.error(f"Failed to enqueue webhook deploy task: {e}")


async def on_schedule_deploy(event: Any) -> None:
    """
    Handle scheduled deployment events (e.g., nightly builds).

    Event data:
    {
        "workspace_id": "ws-123",
        "target": "vercel" | "auto",
        "schedule_name": "nightly-build",
    }

    Args:
        event: TriggerEvent instance
    """
    workspace_id = event.data.get("workspace_id")
    target = event.data.get("target", "auto")
    schedule_name = event.data.get("schedule_name", "scheduled")

    if not workspace_id:
        logger.warning("Scheduled deploy event missing workspace_id")
        return

    logger.info(f"Scheduled deploy for {workspace_id} ({schedule_name})")

    try:
        from ag3ntwerk.core.queue import enqueue_task

        await enqueue_task(
            task_type="workbench.deploy",
            payload={
                "workspace_id": workspace_id,
                "target": target,
                "generate_configs": True,
                "environment": {
                    "DEPLOY_TRIGGER": "scheduled",
                    "SCHEDULE_NAME": schedule_name,
                },
            },
            priority=7,  # Lower priority for scheduled deploys
        )

    except ImportError:
        logger.warning("TaskQueue not available for scheduled deploy")
    except Exception as e:
        logger.error(f"Failed to enqueue scheduled deploy task: {e}")


def register_workbench_triggers(manager: Any) -> None:
    """
    Register workbench triggers with the TriggerManager.

    Args:
        manager: TriggerManager instance
    """
    try:
        # Try to import trigger types
        from nexus.automations.triggers import Trigger, TriggerType

        # File change trigger
        manager.register_trigger(
            Trigger(
                name="workbench_file_change",
                trigger_type=TriggerType.FILE_MODIFIED,
                callback=on_file_changed,
                filters={
                    "workspace_id": lambda x: x is not None,
                },
            )
        )
        logger.info("Registered trigger: workbench_file_change")

        # File created trigger
        manager.register_trigger(
            Trigger(
                name="workbench_file_created",
                trigger_type=TriggerType.FILE_CREATED,
                callback=on_file_changed,
                filters={
                    "workspace_id": lambda x: x is not None,
                },
            )
        )
        logger.info("Registered trigger: workbench_file_created")

        # Webhook deploy trigger
        manager.register_trigger(
            Trigger(
                name="workbench_webhook_deploy",
                trigger_type=TriggerType.WEBHOOK,
                callback=on_webhook_deploy,
                filters={
                    "event_type": lambda x: x in ["push", "release"],
                },
            )
        )
        logger.info("Registered trigger: workbench_webhook_deploy")

        logger.info("Registered all workbench triggers")

    except ImportError:
        # Fall back to simple registration
        logger.warning("Trigger types not available, using simple registration")

        manager.register("workbench_file_change", on_file_changed)
        manager.register("workbench_webhook_deploy", on_webhook_deploy)
        manager.register("workbench_schedule_deploy", on_schedule_deploy)

    except Exception as e:
        logger.error(f"Failed to register triggers: {e}")
