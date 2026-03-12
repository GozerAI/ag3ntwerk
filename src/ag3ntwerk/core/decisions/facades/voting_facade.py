"""
Voting Facade - Decision creation, voting, and resolution.

This facade manages:
- Decision creation (from scratch and templates)
- Voting lifecycle (open, cast, retract, resolve)
- Decision queries (list, get, pending)
- Template management
"""

import asyncio
import inspect
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from ag3ntwerk.core.decisions.models import (
    Decision,
    DecisionOutcome,
    DecisionPriority,
    DecisionState,
    DecisionTemplate,
)
from ag3ntwerk.core.decisions._utils import generate_id, utc_now

logger = logging.getLogger(__name__)


class VotingFacade:
    """
    Facade for voting-related operations.

    Manages decision creation, voting, and resolution.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the voting facade.

        Args:
            max_history: Maximum decisions to keep in history
        """
        self._decisions: Dict[str, Decision] = {}
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[Decision, str], Awaitable[None]]] = []

        # Role-based weights
        self._role_weights: Dict[str, float] = {
            "CEO": 2.0,
            "Forge": 2.0,
            "Keystone": 2.0,
            "Nexus": 2.0,
            "VP": 1.5,
            "Director": 1.25,
            "Manager": 1.0,
            "Lead": 1.0,
        }

        # Templates
        self._templates: Dict[str, DecisionTemplate] = {}
        self._init_default_templates()

    def _init_default_templates(self) -> None:
        """Initialize default decision templates."""
        templates = [
            DecisionTemplate(
                id="architecture-change",
                name="Architecture Change",
                description="Proposal for architectural changes to the system",
                options=["Approve", "Reject", "Defer", "Request More Info"],
                default_required_voters=["Forge", "Lead Architect"],
                require_rationale=True,
                priority=DecisionPriority.HIGH,
                tags=["architecture", "technical"],
            ),
            DecisionTemplate(
                id="budget-approval",
                name="Budget Approval",
                description="Approval for budget allocation or expenditure",
                options=["Approve", "Approve with Conditions", "Reject"],
                default_required_voters=["Keystone", "CEO"],
                require_rationale=True,
                priority=DecisionPriority.HIGH,
                tags=["budget", "financial"],
            ),
            DecisionTemplate(
                id="hiring-decision",
                name="Hiring Decision",
                description="Decision to hire a candidate",
                options=["Strong Hire", "Hire", "No Hire", "More Interviews"],
                default_required_voters=["Hiring Manager", "HR"],
                require_rationale=True,
                tags=["hiring", "hr"],
            ),
            DecisionTemplate(
                id="risk-assessment",
                name="Risk Assessment",
                description="Assessment and decision on identified risks",
                options=["Accept Risk", "Mitigate", "Avoid", "Transfer"],
                default_required_voters=["Risk Owner", "Forge"],
                require_rationale=True,
                priority=DecisionPriority.HIGH,
                tags=["risk", "security"],
            ),
            DecisionTemplate(
                id="policy-change",
                name="Policy Change",
                description="Proposal to change company policy",
                options=["Approve", "Approve with Modifications", "Reject"],
                default_required_voters=["CEO", "Legal"],
                require_unanimous=True,
                priority=DecisionPriority.URGENT,
                tags=["policy", "compliance"],
            ),
        ]

        for template in templates:
            self._templates[template.id] = template

    # --- Decision Creation ---

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
        decision_id = generate_id()

        if deadline_hours and not deadline:
            deadline = datetime.now(timezone.utc) + timedelta(hours=deadline_hours)

        # Set weights for voters
        voter_weights = {}
        all_voters = set(required_voters or []) | set(optional_voters or [])
        for voter in all_voters:
            # Try to determine weight from role
            for role, weight in self._role_weights.items():
                if role.upper() in voter.upper():
                    voter_weights[voter] = weight
                    break
            if voter not in voter_weights:
                voter_weights[voter] = 1.0

        decision = Decision(
            id=decision_id,
            title=title,
            description=description,
            options=options,
            proposer=proposer,
            required_voters=set(required_voters or []),
            optional_voters=set(optional_voters or []),
            voter_weights=voter_weights,
            deadline=deadline,
            require_rationale=require_rationale,
            require_unanimous=require_unanimous,
            tags=tags or [],
            context=context or {},
            priority=priority,
            category=category,
            template_id=template_id,
        )

        async with self._lock:
            self._decisions[decision_id] = decision
            self._cleanup_old_decisions()

        logger.info(f"Created decision: {decision_id} - {title}")
        await self._notify_listeners(decision, "created")

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
        """
        Create a decision from a template.

        Args:
            template_id: Template ID
            title: Decision title
            description: Full description
            proposer: Who proposed
            additional_voters: Additional required voters
            override_deadline_hours: Override template deadline
            context: Additional context

        Returns:
            Created Decision or None if template not found
        """
        template = self._templates.get(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            return None

        required_voters = list(template.default_required_voters)
        if additional_voters:
            required_voters.extend(additional_voters)

        deadline_hours = override_deadline_hours or template.default_deadline_hours

        return await self.create_decision(
            title=title,
            description=description,
            options=template.options,
            proposer=proposer,
            required_voters=required_voters,
            optional_voters=template.default_optional_voters,
            deadline_hours=deadline_hours,
            require_rationale=template.require_rationale,
            require_unanimous=template.require_unanimous,
            tags=template.tags,
            context=context,
            priority=template.priority,
            template_id=template_id,
        )

    # --- Voting Lifecycle ---

    async def open_voting(
        self,
        decision_id: str,
        deadline: Optional[datetime] = None,
    ) -> bool:
        """
        Open a decision for voting.

        Args:
            decision_id: Decision ID
            deadline: Optional deadline

        Returns:
            True if opened
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            return False

        try:
            decision.open_voting(deadline)
            await self._notify_listeners(decision, "opened")
            return True
        except ValueError:
            return False

    async def cast_vote(
        self,
        decision_id: str,
        voter: str,
        choice: str,
        rationale: Optional[str] = None,
        confidence: float = 1.0,
    ) -> bool:
        """
        Cast a vote on a decision.

        Args:
            decision_id: Decision ID
            voter: Who is voting
            choice: The choice
            rationale: Reason for vote
            confidence: Confidence (0-1)

        Returns:
            True if vote was accepted
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            return False

        success = decision.cast_vote(voter, choice, rationale, confidence)
        if success:
            await self._notify_listeners(decision, "vote_cast")

            # Check if all required votes are in
            summary = decision.get_vote_summary()
            if not summary["pending_required_voters"]:
                # Auto-resolve if all required votes received
                await self.resolve_decision(decision_id)

        return success

    async def resolve_decision(self, decision_id: str) -> Optional[DecisionOutcome]:
        """
        Resolve a decision.

        Args:
            decision_id: Decision ID

        Returns:
            Outcome or None
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            return None

        outcome = decision.resolve()
        if outcome:
            await self._notify_listeners(decision, "resolved")

        return outcome

    async def cancel_decision(
        self,
        decision_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Cancel a decision.

        Args:
            decision_id: Decision ID
            reason: Cancellation reason

        Returns:
            True if cancelled
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            return False

        decision.cancel(reason)
        await self._notify_listeners(decision, "cancelled")
        return True

    # --- Queries ---

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self._decisions.get(decision_id)

    def get_all_decisions(self) -> Dict[str, Decision]:
        """Get all decisions (for escalation facade)."""
        return self._decisions

    def list_decisions(
        self,
        state: Optional[DecisionState] = None,
        voter: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Decision]:
        """
        List decisions with optional filtering.

        Args:
            state: Filter by state
            voter: Filter by required voter
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of decisions
        """
        decisions = list(self._decisions.values())

        if state:
            decisions = [d for d in decisions if d.state == state]

        if voter:
            decisions = [
                d for d in decisions if voter in d.required_voters or voter in d.optional_voters
            ]

        if tags:
            tag_set = set(tags)
            decisions = [d for d in decisions if tag_set & set(d.tags)]

        # Sort by created_at descending
        decisions.sort(key=lambda d: d.created_at, reverse=True)

        return decisions[:limit]

    def get_pending_for_voter(self, voter: str) -> List[Decision]:
        """Get decisions awaiting a voter's input."""
        return [
            d
            for d in self._decisions.values()
            if d.state == DecisionState.OPEN and voter in d.required_voters and voter not in d.votes
        ]

    # --- Template Management ---

    def add_template(self, template: DecisionTemplate) -> None:
        """Add a decision template."""
        self._templates[template.id] = template
        logger.info(f"Added decision template: {template.id}")

    def remove_template(self, template_id: str) -> bool:
        """Remove a decision template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def get_template(self, template_id: str) -> Optional[DecisionTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[DecisionTemplate]:
        """List all templates."""
        return list(self._templates.values())

    # --- Listeners ---

    def add_listener(
        self,
        callback: Callable[[Decision, str], Awaitable[None]],
    ) -> None:
        """
        Add a listener for decision events.

        Args:
            callback: Function called with (decision, event_type)
        """
        self._listeners.append(callback)

    async def _notify_listeners(
        self,
        decision: Decision,
        event_type: str,
    ) -> None:
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                if inspect.iscoroutinefunction(listener):
                    await listener(decision, event_type)
                else:
                    listener(decision, event_type)
            except Exception as e:
                logger.exception(f"Error in decision listener: {e}")

    # --- Internal ---

    def _cleanup_old_decisions(self) -> None:
        """Remove old resolved/cancelled decisions."""
        if len(self._decisions) <= self._max_history:
            return

        # Sort by resolved/cancelled time, keep newest
        removable = [
            (d.id, d.resolved_at or d.created_at)
            for d in self._decisions.values()
            if d.state in (DecisionState.RESOLVED, DecisionState.CANCELLED)
        ]

        removable.sort(key=lambda x: x[1])
        to_remove = len(self._decisions) - self._max_history

        for decision_id, _ in removable[:to_remove]:
            del self._decisions[decision_id]

    def set_role_weight(self, role: str, weight: float) -> None:
        """Set the voting weight for a role."""
        self._role_weights[role] = weight

    # --- Stats ---

    def get_stats(self) -> Dict[str, Any]:
        """Get voting facade statistics."""
        decisions = list(self._decisions.values())

        by_state = defaultdict(int)
        for d in decisions:
            by_state[d.state.value] += 1

        by_priority = defaultdict(int)
        for d in decisions:
            by_priority[d.priority.value] += 1

        resolved = [d for d in decisions if d.outcome]
        avg_consensus = 0.0
        if resolved:
            avg_consensus = sum(d.outcome.consensus_level for d in resolved) / len(resolved)

        return {
            "total_decisions": len(decisions),
            "by_state": dict(by_state),
            "by_priority": dict(by_priority),
            "average_consensus": avg_consensus,
            "total_votes_cast": sum(len(d.votes) for d in decisions),
            "total_escalations": sum(d.escalation_level for d in decisions),
            "total_templates": len(self._templates),
        }
