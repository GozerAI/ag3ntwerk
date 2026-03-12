"""
Escalation Facade - Escalation rules, monitoring, and deadline management.

This facade manages:
- Escalation rule registration
- Automatic escalation monitoring
- Deadline-based priority bumping
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ag3ntwerk.core.decisions.models import (
    Decision,
    DecisionState,
    Escalation,
    EscalationRule,
    AuditAction,
)
from ag3ntwerk.core.decisions._utils import generate_id, utc_now

logger = logging.getLogger(__name__)


class EscalationFacade:
    """
    Facade for escalation-related operations.

    Manages escalation rules, monitoring task, and automatic escalation.
    """

    def __init__(self):
        """Initialize the escalation facade."""
        self._escalation_rules: Dict[str, EscalationRule] = {}
        self._escalation_task: Optional[asyncio.Task] = None

        # Callbacks for cross-facade communication (set by DecisionManager)
        self._audit_callback: Optional[Callable[..., Any]] = None
        self._notification_callback: Optional[Callable[..., Awaitable[None]]] = None
        self._get_decisions: Optional[Callable[[], Dict[str, Decision]]] = None

    def set_callbacks(
        self,
        audit_callback: Callable[..., Any],
        notification_callback: Callable[..., Awaitable[None]],
        get_decisions: Callable[[], Dict[str, Decision]],
    ) -> None:
        """
        Set callbacks for cross-facade communication.

        Args:
            audit_callback: Function to add audit entries
            notification_callback: Function to send notifications
            get_decisions: Function to get all decisions
        """
        self._audit_callback = audit_callback
        self._notification_callback = notification_callback
        self._get_decisions = get_decisions

    # --- Rule Management ---

    def add_escalation_rule(self, rule: EscalationRule) -> None:
        """
        Add an escalation rule.

        Args:
            rule: The escalation rule to add
        """
        self._escalation_rules[rule.name] = rule
        logger.info(f"Added escalation rule: {rule.name}")

    def remove_escalation_rule(self, name: str) -> bool:
        """
        Remove an escalation rule.

        Args:
            name: Name of the rule to remove

        Returns:
            True if removed, False if not found
        """
        if name in self._escalation_rules:
            del self._escalation_rules[name]
            return True
        return False

    def get_escalation_rules(self) -> List[EscalationRule]:
        """Get all escalation rules."""
        return list(self._escalation_rules.values())

    # --- Monitoring ---

    async def start_escalation_monitor(self) -> None:
        """Start the escalation monitor task."""
        if self._escalation_task:
            return

        self._escalation_task = asyncio.create_task(self._escalation_loop())
        logger.info("Started escalation monitor")

    async def stop_escalation_monitor(self) -> None:
        """Stop the escalation monitor."""
        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass
            self._escalation_task = None
            logger.info("Stopped escalation monitor")

    async def _escalation_loop(self) -> None:
        """Monitor for escalation triggers."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._check_escalations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")

    async def _check_escalations(self) -> None:
        """Check for decisions needing escalation."""
        if not self._get_decisions:
            return

        decisions = self._get_decisions()
        now = datetime.now(timezone.utc)

        for decision in decisions.values():
            if decision.state != DecisionState.OPEN:
                continue

            # Check each escalation rule
            for rule in self._escalation_rules.values():
                if decision.escalation_level >= rule.max_escalations:
                    continue

                # Check if escalation is needed
                hours_open = (
                    now - (decision.opened_at or decision.created_at)
                ).total_seconds() / 3600

                if hours_open >= rule.trigger_hours:
                    # Check pending voters
                    pending = decision.required_voters - set(decision.votes.keys())
                    if pending:
                        await self._escalate_decision(decision, rule, list(pending))

    async def _escalate_decision(
        self,
        decision: Decision,
        rule: EscalationRule,
        from_voters: List[str],
    ) -> None:
        """
        Escalate a decision.

        Args:
            decision: The decision to escalate
            rule: The escalation rule that triggered
            from_voters: Voters who haven't responded
        """
        escalation = Escalation(
            id=generate_id(),
            decision_id=decision.id,
            from_voters=from_voters,
            to_voters=rule.escalate_to,
            reason=f"No response after {rule.trigger_hours} hours",
            escalated_at=utc_now(),
            escalation_level=decision.escalation_level + 1,
        )

        decision.escalations.append(escalation)
        decision.escalation_level += 1

        # Add escalation targets to required voters
        for voter in rule.escalate_to:
            decision.required_voters.add(voter)

        # Bump priority if configured
        if rule.priority_bump:
            decision.bump_priority()

        # Audit log
        if self._audit_callback:
            self._audit_callback(
                decision_id=decision.id,
                action=AuditAction.ESCALATED,
                actor="system",
                details={
                    "from_voters": from_voters,
                    "to_voters": rule.escalate_to,
                    "escalation_level": decision.escalation_level,
                },
            )

        # Notify escalation targets
        if self._notification_callback:
            await self._notification_callback(decision, "escalated")

        logger.warning(f"Decision {decision.id} escalated to level {decision.escalation_level}")

    # --- Stats ---

    def get_stats(self) -> Dict[str, Any]:
        """Get escalation facade statistics."""
        return {
            "escalation_rules_count": len(self._escalation_rules),
            "escalation_monitor_running": self._escalation_task is not None,
        }
