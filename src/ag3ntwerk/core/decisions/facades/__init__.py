"""
Decision Facades - Domain-focused coordinators for the Decision Support system.

Each facade owns a coherent set of operations and provides a focused API
for its domain. The main DecisionManager delegates to these facades.
"""

from ag3ntwerk.core.decisions.facades.audit_facade import AuditFacade
from ag3ntwerk.core.decisions.facades.notification_facade import NotificationFacade
from ag3ntwerk.core.decisions.facades.escalation_facade import EscalationFacade
from ag3ntwerk.core.decisions.facades.voting_facade import VotingFacade

__all__ = [
    "AuditFacade",
    "NotificationFacade",
    "EscalationFacade",
    "VotingFacade",
]
