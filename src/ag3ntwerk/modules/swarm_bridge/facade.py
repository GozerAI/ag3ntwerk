"""
Swarm Facade.

Learning facade for the Swarm Bridge that provides a high-level
interface for ag3ntwerk agents to delegate tasks to the Swarm.
"""

import logging
from typing import Any, Dict, List, Optional

from .service import SwarmBridgeService

logger = logging.getLogger(__name__)

# Map ag3ntwerk agent capabilities to Swarm task tags
_AGENT_TASK_MAP = {
    # Technical cluster
    "Forge": ["code_review", "architecture", "security_audit", "refactoring", "debugging"],
    "Foundry": ["code_review", "debugging", "testing", "refactoring", "architecture"],
    "Sentinel": ["security_audit", "architecture", "data_governance"],
    "Citadel": ["security_audit", "code_review", "compliance"],
    # Business cluster
    "Keystone": ["cost_analysis", "revenue_analysis", "strategic_planning"],
    "Vector": ["revenue_analysis", "cost_analysis", "product_planning"],
    "Compass": ["strategic_planning", "revenue_analysis", "research"],
    "Blueprint": ["product_planning", "code_review", "testing"],
    # Operations cluster
    "Overwatch": ["task_routing", "architecture", "operational_planning"],
    "Nexus": ["operational_planning", "task_routing", "documentation"],
    "Index": ["data_governance", "documentation", "research"],
    "Axiom": ["research", "data_governance", "strategic_planning"],
    # Governance cluster
    "Accord": ["compliance", "risk_assessment", "documentation"],
    "Aegis": ["risk_assessment", "compliance", "strategic_planning"],
    "Beacon": ["customer_success", "documentation", "product_planning"],
    "Echo": ["marketing", "customer_success", "strategic_planning"],
}

# Map agent code to preferred domain model (fine-tuned LoRA)
_AGENT_DOMAIN_MODEL = {
    # Technical cluster -> ag3ntwerk-technical
    "Forge": "ag3ntwerk-technical",
    "Foundry": "ag3ntwerk-technical",
    "Sentinel": "ag3ntwerk-technical",
    "Citadel": "ag3ntwerk-technical",
    # Business cluster -> ag3ntwerk-business
    "Keystone": "ag3ntwerk-business",
    "Vector": "ag3ntwerk-business",
    "Compass": "ag3ntwerk-business",
    "Blueprint": "ag3ntwerk-business",
    # Operations cluster -> ag3ntwerk-operations
    "Overwatch": "ag3ntwerk-operations",
    "Nexus": "ag3ntwerk-operations",
    "Index": "ag3ntwerk-operations",
    "Axiom": "ag3ntwerk-operations",
    # Governance cluster -> ag3ntwerk-governance
    "Accord": "ag3ntwerk-governance",
    "Aegis": "ag3ntwerk-governance",
    "Beacon": "ag3ntwerk-governance",
    "Echo": "ag3ntwerk-governance",
}

# Map personality traits to routing preferences
_TRAIT_ROUTING = {
    "analytical": {"prefer_speed": False},
    "decisive": {"prefer_speed": True},
    "cautious": {"prefer_speed": False},
    "innovative": {"prefer_speed": False},
}


class SwarmFacade:
    """
    Facade for delegating tasks to the Claude Swarm.

    Provides methods for ag3ntwerk agents to submit tasks with
    context-aware routing and metacognition integration.
    """

    def __init__(self, service: SwarmBridgeService):
        self._service = service

    async def delegate_to_swarm(
        self,
        task: str,
        agent_code: str = "",
        agent_context: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        wait: bool = True,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """
        Delegate a task to the Swarm with ag3ntwerk context.

        Args:
            task: Task description / prompt.
            agent_code: ag3ntwerk agent code (e.g., "Forge", "Foundry").
            agent_context: Agent personality traits and context.
            priority: Task priority.
            wait: If True, wait for completion and return result.
            timeout: Max wait time in seconds.

        Returns:
            Task result dict (if wait=True) or {"task_id": ...}.
        """
        agent_context = agent_context or {}

        # Map agent to default task tags and preferred domain model
        task_tags = _AGENT_TASK_MAP.get(agent_code, [])
        preferred_model = _AGENT_DOMAIN_MODEL.get(agent_code, "ag3ntwerk-model")

        # Build metadata with ag3ntwerk context
        metadata = {
            "csuite_agent": agent_code,
            "task_tags": task_tags,
            "preferred_model": preferred_model,
            "agent_traits": agent_context.get("traits", {}),
        }

        # Determine priority boost and speed preference from agent traits
        traits = agent_context.get("traits", {})
        if traits.get("urgency", 0) > 0.7:
            priority = "high"

        # Apply trait-based routing preferences
        dominant_trait = traits.get("dominant_trait", "")
        trait_prefs = _TRAIT_ROUTING.get(dominant_trait, {})
        if trait_prefs.get("prefer_speed"):
            metadata["prefer_speed"] = True

        task_id = await self._service.submit_task(
            prompt=task,
            agent_code=agent_code,
            priority=priority,
            timeout=int(timeout),
            metadata=metadata,
        )

        if not wait:
            return {"task_id": task_id, "status": "submitted"}

        result = await self._service.wait_for_task(task_id, timeout=timeout)
        return result

    async def get_swarm_status(self) -> Dict[str, Any]:
        """Get current Swarm status."""
        available = await self._service.is_swarm_available()
        if not available:
            return {"available": False, "status": "unreachable"}

        status = await self._service.get_swarm_status()
        status["available"] = True
        return status

    async def get_routing_insights(self) -> Dict[str, Any]:
        """
        Get routing performance insights.

        Returns which models perform best at which task types,
        useful for metacognition and team optimization.
        """
        return await self._service.get_routing_insights()

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available Swarm models and their capabilities."""
        return await self._service.get_available_models()

    async def batch_delegate(
        self,
        tasks: List[Dict[str, Any]],
        agent_code: str = "",
    ) -> List[str]:
        """
        Submit multiple tasks to the Swarm.

        Args:
            tasks: List of {"prompt": ..., "priority": ...} dicts.
            agent_code: ag3ntwerk agent code.

        Returns:
            List of task IDs.
        """
        task_ids = []
        for task_def in tasks:
            task_id = await self._service.submit_task(
                prompt=task_def["prompt"],
                agent_code=agent_code,
                priority=task_def.get("priority", "normal"),
            )
            task_ids.append(task_id)
        return task_ids
