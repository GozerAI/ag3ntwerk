"""
Decision Manager - Central coordinator for the Decision Support system.

Delegates to domain-focused facades for actual implementation.
Maintains backward compatibility with existing API.
"""

import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.decisions.models import (
    AuditAction,
    AuditEntry,
    Decision,
    DecisionOutcome,
    DecisionPriority,
    DecisionState,
    DecisionTemplate,
    EscalationRule,
    Notification,
)
from ag3ntwerk.core.decisions.facades import (
    AuditFacade,
    EscalationFacade,
    NotificationFacade,
    VotingFacade,
)

logger = logging.getLogger(__name__)


class DecisionManager:
    """
    Central manager for collaborative decisions.

    Delegates to domain facades:
    - VotingFacade: Decision creation, voting, resolution
    - EscalationFacade: Escalation rules and monitoring
    - NotificationFacade: Notification system
    - AuditFacade: Audit trail

    All existing methods are maintained for backward compatibility.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the decision manager.

        Args:
            max_history: Maximum decisions to keep in history
        """
        # Initialize facades
        self._voting = VotingFacade(max_history)
        self._escalation = EscalationFacade()
        self._notification = NotificationFacade()
        self._audit = AuditFacade()

        # Set up cross-facade callbacks
        self._escalation.set_callbacks(
            audit_callback=self._audit.add_audit_entry,
            notification_callback=self._notification.send_notifications,
            get_decisions=self._voting.get_all_decisions,
        )

    # ==========================================================================
    # Decision Lifecycle (delegates to VotingFacade)
    # ==========================================================================

    async def create_decision(
        self,
        title: str,
        description: str,
        options: List[str],
        proposer: Optional[str] = None,
        required_voters: Optional[List[str]] = None,
        optional_voters: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        deadline_hours: Optional[float] = None,
        require_rationale: bool = False,
        require_unanimous: bool = False,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: DecisionPriority = DecisionPriority.NORMAL,
        category: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Decision:
        """
        Create a new decision.

        Args:
            title: Decision title
            description: Full description
            options: Available choices
            proposer: Who proposed the decision
            required_voters: Voters who must participate
            optional_voters: Optional participants
            deadline: Voting deadline
            deadline_hours: Hours until deadline (alternative)
            require_rationale: Require vote rationale
            require_unanimous: Require unanimous vote
            tags: Categorization tags
            context: Additional context
            priority: Decision priority
            category: Decision category
            template_id: Template used to create this decision

        Returns:
            Created Decision
        """
        decision = await self._voting.create_decision(
            title=title,
            description=description,
            options=options,
            proposer=proposer,
            required_voters=required_voters,
            optional_voters=optional_voters,
            deadline=deadline,
            deadline_hours=deadline_hours,
            require_rationale=require_rationale,
            require_unanimous=require_unanimous,
            tags=tags,
            context=context,
            priority=priority,
            category=category,
            template_id=template_id,
        )

        # Audit log
        self._audit.add_audit_entry(
            decision_id=decision.id,
            action=AuditAction.CREATED,
            actor=proposer or "system",
            details={"title": title, "options": options, "priority": priority.value},
        )

        # Send notifications to required voters
        await self._notification.send_notifications(decision, "created")

        return decision

    async def create_from_template(
        self,
        template_id: str,
        title: str,
        description: str,
        proposer: Optional[str] = None,
        additional_voters: Optional[List[str]] = None,
        override_deadline_hours: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Decision]:
        """Create a decision from a template."""
        decision = await self._voting.create_from_template(
            template_id=template_id,
            title=title,
            description=description,
            proposer=proposer,
            additional_voters=additional_voters,
            override_deadline_hours=override_deadline_hours,
            context=context,
        )

        if decision:
            self._audit.add_audit_entry(
                decision_id=decision.id,
                action=AuditAction.CREATED,
                actor=proposer or "system",
                details={"title": title, "template_id": template_id},
            )
            await self._notification.send_notifications(decision, "created")

        return decision

    async def open_voting(
        self,
        decision_id: str,
        deadline: Optional[datetime] = None,
    ) -> bool:
        """Open a decision for voting."""
        success = await self._voting.open_voting(decision_id, deadline)
        if success:
            self._audit.add_audit_entry(
                decision_id=decision_id,
                action=AuditAction.OPENED,
                actor="system",
            )
        return success

    async def cast_vote(
        self,
        decision_id: str,
        voter: str,
        choice: str,
        rationale: Optional[str] = None,
        confidence: float = 1.0,
    ) -> bool:
        """Cast a vote on a decision."""
        success = await self._voting.cast_vote(
            decision_id=decision_id,
            voter=voter,
            choice=choice,
            rationale=rationale,
            confidence=confidence,
        )
        if success:
            self._audit.add_audit_entry(
                decision_id=decision_id,
                action=AuditAction.VOTE_CAST,
                actor=voter,
                details={"choice": choice, "confidence": confidence},
            )
        return success

    async def resolve_decision(self, decision_id: str) -> Optional[DecisionOutcome]:
        """Resolve a decision."""
        outcome = await self._voting.resolve_decision(decision_id)
        if outcome:
            self._audit.add_audit_entry(
                decision_id=decision_id,
                action=AuditAction.RESOLVED,
                actor="system",
                details={"outcome": outcome.winning_choice, "consensus": outcome.consensus_level},
            )
            decision = self._voting.get_decision(decision_id)
            if decision:
                await self._notification.send_notifications(decision, "resolved")
        return outcome

    async def cancel_decision(
        self,
        decision_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Cancel a decision."""
        success = await self._voting.cancel_decision(decision_id, reason)
        if success:
            self._audit.add_audit_entry(
                decision_id=decision_id,
                action=AuditAction.CANCELLED,
                actor="system",
                details={"reason": reason} if reason else {},
            )
            decision = self._voting.get_decision(decision_id)
            if decision:
                await self._notification.send_notifications(decision, "cancelled")
        return success

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self._voting.get_decision(decision_id)

    def list_decisions(
        self,
        state: Optional[DecisionState] = None,
        voter: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Decision]:
        """List decisions with optional filtering."""
        return self._voting.list_decisions(
            state=state,
            voter=voter,
            tags=tags,
            limit=limit,
        )

    def get_pending_for_voter(self, voter: str) -> List[Decision]:
        """Get decisions awaiting a voter's input."""
        return self._voting.get_pending_for_voter(voter)

    def add_listener(
        self,
        callback: Callable[[Decision, str], Awaitable[None]],
    ) -> None:
        """Add a listener for decision events."""
        self._voting.add_listener(callback)

    def set_role_weight(self, role: str, weight: float) -> None:
        """Set the voting weight for a role."""
        self._voting.set_role_weight(role, weight)

    # ==========================================================================
    # Template Management (delegates to VotingFacade)
    # ==========================================================================

    def add_template(self, template: DecisionTemplate) -> None:
        """Add a decision template."""
        self._voting.add_template(template)

    def remove_template(self, template_id: str) -> bool:
        """Remove a decision template."""
        return self._voting.remove_template(template_id)

    def get_template(self, template_id: str) -> Optional[DecisionTemplate]:
        """Get a template by ID."""
        return self._voting.get_template(template_id)

    def list_templates(self) -> List[DecisionTemplate]:
        """List all templates."""
        return self._voting.list_templates()

    # ==========================================================================
    # Escalation (delegates to EscalationFacade)
    # ==========================================================================

    def add_escalation_rule(self, rule: EscalationRule) -> None:
        """Add an escalation rule."""
        self._escalation.add_escalation_rule(rule)

    def remove_escalation_rule(self, name: str) -> bool:
        """Remove an escalation rule."""
        return self._escalation.remove_escalation_rule(name)

    async def start_escalation_monitor(self) -> None:
        """Start the escalation monitor task."""
        await self._escalation.start_escalation_monitor()

    async def stop_escalation_monitor(self) -> None:
        """Stop the escalation monitor."""
        await self._escalation.stop_escalation_monitor()

    # ==========================================================================
    # Notifications (delegates to NotificationFacade)
    # ==========================================================================

    def add_notification_handler(
        self,
        handler: Callable[[Notification], Awaitable[None]],
    ) -> None:
        """Add a notification handler."""
        self._notification.add_notification_handler(handler)

    def get_notifications(
        self,
        recipient: Optional[str] = None,
        decision_id: Optional[str] = None,
        sent: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Notification]:
        """Get notifications."""
        return self._notification.get_notifications(
            recipient=recipient,
            decision_id=decision_id,
            sent=sent,
            limit=limit,
        )

    # ==========================================================================
    # Audit (delegates to AuditFacade)
    # ==========================================================================

    def get_audit_log(
        self,
        decision_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get audit log entries."""
        return self._audit.get_audit_log(
            decision_id=decision_id,
            action=action,
            actor=actor,
            limit=limit,
        )

    def export_audit_log(self, decision_id: Optional[str] = None) -> str:
        """Export audit log as JSON."""
        return self._audit.export_audit_log(decision_id)

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get decision system statistics."""
        return {
            **self._voting.get_stats(),
            **self._escalation.get_stats(),
            **self._notification.get_stats(),
            **self._audit.get_stats(),
        }

    # ==========================================================================
    # Direct Facade Access
    # ==========================================================================

    @property
    def voting(self) -> VotingFacade:
        """Get the voting facade."""
        return self._voting

    @property
    def escalation(self) -> EscalationFacade:
        """Get the escalation facade."""
        return self._escalation

    @property
    def notification(self) -> NotificationFacade:
        """Get the notification facade."""
        return self._notification

    @property
    def audit(self) -> AuditFacade:
        """Get the audit facade."""
        return self._audit
