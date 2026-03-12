"""
Collaborative Decision Support for ag3ntwerk.

Enables structured decision-making with multiple agents:
- Decision proposals and voting
- Weighted consensus building
- Decision history and rationale
- Impact assessment
- Approval workflows
- Escalation with deadlines
- Decision templates
- Audit trail

Usage:
    from ag3ntwerk.core.decisions import (
        DecisionManager,
        Decision,
        Vote,
        get_decision_manager,
        propose_decision,
    )

    # Propose a decision
    decision = await propose_decision(
        title="Adopt new framework",
        description="Proposal to migrate to FastAPI",
        options=["Approve", "Reject", "Defer"],
        required_voters=["Forge", "CEO"],
    )

    # Cast votes
    await decision.cast_vote("Forge", "Approve", rationale="Performance benefits")
    await decision.cast_vote("CEO", "Approve", rationale="Cost effective")

    # Check outcome
    outcome = await decision.resolve()
"""

# Models (enums and dataclasses)
from ag3ntwerk.core.decisions.models import (
    # Enums
    DecisionState,
    VoteWeight,
    DecisionPriority,
    AuditAction,
    # Dataclasses
    AuditEntry,
    EscalationRule,
    Escalation,
    DecisionTemplate,
    Notification,
    Delegation,
    Comment,
    Vote,
    ImpactAssessment,
    DecisionOutcome,
    Decision,
)

# Manager
from ag3ntwerk.core.decisions.manager import DecisionManager

# Facades (for direct access)
from ag3ntwerk.core.decisions.facades import (
    VotingFacade,
    EscalationFacade,
    NotificationFacade,
    AuditFacade,
)

# Module-level utilities
from typing import List, Optional

_manager: Optional[DecisionManager] = None


def get_decision_manager() -> DecisionManager:
    """Get the global decision manager."""
    global _manager
    if _manager is None:
        _manager = DecisionManager()
    return _manager


async def propose_decision(
    title: str,
    description: str,
    options: List[str],
    **kwargs,
) -> Decision:
    """
    Propose a new decision.

    Args:
        title: Decision title
        description: Full description
        options: Available choices
        **kwargs: Additional decision options

    Returns:
        Created Decision
    """
    manager = get_decision_manager()
    decision = await manager.create_decision(title, description, options, **kwargs)
    await manager.open_voting(decision.id)
    return decision


__all__ = [
    # Enums
    "DecisionState",
    "VoteWeight",
    "DecisionPriority",
    "AuditAction",
    # Data classes
    "Vote",
    "ImpactAssessment",
    "DecisionOutcome",
    "Decision",
    "AuditEntry",
    "EscalationRule",
    "Escalation",
    "DecisionTemplate",
    "Notification",
    "Delegation",
    "Comment",
    # Manager
    "DecisionManager",
    "get_decision_manager",
    # Facades
    "VotingFacade",
    "EscalationFacade",
    "NotificationFacade",
    "AuditFacade",
    # Functions
    "propose_decision",
]
