"""
Task Handlers - TaskQueue integration for workbench pipelines.

Enables scheduled and triggered pipeline executions via the TaskQueue.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def handle_pipeline_task(task: Any) -> Dict[str, Any]:
    """
    Handle pipeline execution task from queue.

    Task payload:
    {
        "workspace_id": "ws-123",
        "pipeline_type": "full" | "evaluate" | "oneclick",
        "options": {...},
    }

    Args:
        task: QueuedTask instance

    Returns:
        Result dictionary
    """
    from ag3ntwerk.modules.workbench.pipeline import get_workbench_pipeline
    from ag3ntwerk.modules.workbench.pipeline_schemas import (
        EvaluationOptions,
        PipelineOptions,
    )
    from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer
    from ag3ntwerk.modules.workbench.service import get_workbench_service

    workspace_id = task.payload.get("workspace_id")
    pipeline_type = task.payload.get("pipeline_type", "full")
    options_data = task.payload.get("options", {})

    if not workspace_id:
        raise ValueError("workspace_id is required in task payload")

    logger.info(f"Processing pipeline task: {task.id} ({pipeline_type}) for {workspace_id}")

    pipeline = get_workbench_pipeline()

    if pipeline_type == "evaluate":
        options = EvaluationOptions(**options_data)
        result = await pipeline.run_evaluation(workspace_id, options)
        return result.to_dict()

    elif pipeline_type == "full":
        options = PipelineOptions(**options_data)
        result = await pipeline.run_full_pipeline(workspace_id, options)
        return result.to_dict()

    elif pipeline_type == "oneclick":
        service = get_workbench_service()
        deployer = OneClickDeployer(service)
        result = await deployer.deploy(
            workspace_id=workspace_id,
            target=options_data.get("target", "auto"),
            generate_configs=options_data.get("generate_configs", True),
            environment=options_data.get("environment"),
        )
        return result.to_dict()

    elif pipeline_type == "with_database":
        options = PipelineOptions(**options_data)
        result = await pipeline.run_with_database(workspace_id, options)
        return result.to_dict()

    elif pipeline_type == "with_secrets":
        options = PipelineOptions(**options_data)
        result = await pipeline.run_with_secrets(workspace_id, options)
        return result.to_dict()

    elif pipeline_type == "complete":
        options = PipelineOptions(**options_data)
        result = await pipeline.run_complete(workspace_id, options)
        return result.to_dict()

    else:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")


async def handle_deploy_task(task: Any) -> Dict[str, Any]:
    """
    Handle deployment task from queue.

    Task payload:
    {
        "workspace_id": "ws-123",
        "target": "vercel" | "docker_registry" | "local" | "auto",
        "environment": {...},
        "generate_configs": true,
    }

    Args:
        task: QueuedTask instance

    Returns:
        Result dictionary
    """
    from ag3ntwerk.modules.workbench.deployers.oneclick import OneClickDeployer
    from ag3ntwerk.modules.workbench.service import get_workbench_service

    workspace_id = task.payload.get("workspace_id")
    target = task.payload.get("target", "auto")
    environment = task.payload.get("environment", {})
    generate_configs = task.payload.get("generate_configs", True)

    if not workspace_id:
        raise ValueError("workspace_id is required in task payload")

    logger.info(f"Processing deploy task: {task.id} to {target}")

    service = get_workbench_service()
    deployer = OneClickDeployer(service)

    result = await deployer.deploy(
        workspace_id=workspace_id,
        target=target,
        generate_configs=generate_configs,
        environment=environment,
    )

    return result.to_dict()


async def handle_ide_task(task: Any) -> Dict[str, Any]:
    """
    Handle IDE management task from queue.

    Task payload:
    {
        "workspace_id": "ws-123",
        "action": "start" | "stop" | "status",
        "password": "optional-password",
    }

    Args:
        task: QueuedTask instance

    Returns:
        Result dictionary
    """
    from ag3ntwerk.modules.workbench.service import get_workbench_service

    workspace_id = task.payload.get("workspace_id")
    action = task.payload.get("action", "start")
    password = task.payload.get("password")

    if not workspace_id:
        raise ValueError("workspace_id is required in task payload")

    logger.info(f"Processing IDE task: {task.id} ({action}) for {workspace_id}")

    service = get_workbench_service()

    if action == "start":
        result = await service.start_ide(workspace_id, password)
        return result.to_dict()

    elif action == "stop":
        success = await service.stop_ide(workspace_id)
        return {"success": success, "workspace_id": workspace_id}

    elif action == "status":
        status = await service.get_ide_status(workspace_id)
        return status.to_dict()

    else:
        raise ValueError(f"Unknown IDE action: {action}")


def register_workbench_handlers(queue: Any) -> None:
    """
    Register workbench task handlers with the TaskQueue.

    Args:
        queue: TaskQueue instance
    """
    # Register pipeline handler
    queue.register_handler("workbench.pipeline", handle_pipeline_task)
    logger.info("Registered handler: workbench.pipeline")

    # Register deploy handler
    queue.register_handler("workbench.deploy", handle_deploy_task)
    logger.info("Registered handler: workbench.deploy")

    # Register IDE handler
    queue.register_handler("workbench.ide", handle_ide_task)
    logger.info("Registered handler: workbench.ide")

    logger.info("Registered all workbench task handlers")
