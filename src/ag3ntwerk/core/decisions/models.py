"""
Decision Models - Enums and Dataclasses for the Decision Support system.

Contains all data structures used by the decision facades and manager.
"""

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class DecisionState(str, Enum):
    """State of a decision."""

    DRAFT = "draft"
    OPEN = "open"  # Accepting votes
    CLOSED = "closed"  # Voting ended
    RESOLVED = "resolved"  # Outcome determined
    CANCELLED = "cancelled"


class VoteWeight(Enum):
    """Voting weights for different roles."""

    STANDARD = 1.0
    SENIOR = 1.5
    AGENT = 2.0
    VETO = float("inf")  # Can block decision


class DecisionPriority(str, Enum):
    """Priority level for decisions."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """Types of audit actions."""

    CREATED = "created"
    OPENED = "opened"
    VOTE_CAST = "vote_cast"
    VOTE_RETRACTED = "vote_retracted"
    DELEGATED = "delegated"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    DEADLINE_EXTENDED = "deadline_extended"
    COMMENT_ADDED = "comment_added"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class AuditEntry:
    """Entry in the decision audit trail."""

    id: str
    decision_id: str
    action: AuditAction
    actor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "action": self.action.value,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


@dataclass
class EscalationRule:
    """Rule for automatic escalation."""

    name: str
    trigger_hours: float  # Hours without response
    escalate_to: List[str]  # Who to escalate to
    priority_bump: bool = True  # Increase priority
    notification_template: Optional[str] = None
    max_escalations: int = 3  # Maximum escalation attempts


@dataclass
class Escalation:
    """Record of an escalation."""

    id: str
    decision_id: str
    from_voters: List[str]
    to_voters: List[str]
    reason: str
    escalated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    escalation_level: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "from_voters": self.from_voters,
            "to_voters": self.to_voters,
            "reason": self.reason,
            "escalated_at": self.escalated_at.isoformat(),
            "escalation_level": self.escalation_level,
        }


@dataclass
class DecisionTemplate:
    """Template for common decision types."""

    id: str
    name: str
    description: str
    options: List[str]
    default_required_voters: List[str] = field(default_factory=list)
    default_optional_voters: List[str] = field(default_factory=list)
    default_deadline_hours: Optional[float] = None
    require_rationale: bool = False
    require_unanimous: bool = False
    min_participation: float = 0.5
    priority: DecisionPriority = DecisionPriority.NORMAL
    tags: List[str] = field(default_factory=list)
    impact_template: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "options": self.options,
            "default_required_voters": self.default_required_voters,
            "default_optional_voters": self.default_optional_voters,
            "default_deadline_hours": self.default_deadline_hours,
            "require_rationale": self.require_rationale,
            "require_unanimous": self.require_unanimous,
            "min_participation": self.min_participation,
            "priority": self.priority.value,
            "tags": self.tags,
        }


@dataclass
class Notification:
    """Notification about a decision event."""

    id: str
    decision_id: str
    recipient: str
    event_type: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent: bool = False
    sent_at: Optional[datetime] = None
    channel: str = "internal"  # internal, email, slack, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "recipient": self.recipient,
            "event_type": self.event_type,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "sent": self.sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "channel": self.channel,
        }


@dataclass
class Delegation:
    """Delegation of voting authority."""

    id: str
    decision_id: str
    from_voter: str
    to_voter: str
    reason: Optional[str] = None
    delegated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "from_voter": self.from_voter,
            "to_voter": self.to_voter,
            "reason": self.reason,
            "delegated_at": self.delegated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Comment:
    """Comment on a decision."""

    id: str
    decision_id: str
    author: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_id: Optional[str] = None  # For threaded comments

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "parent_id": self.parent_id,
        }


@dataclass
class Vote:
    """A vote on a decision."""

    voter: str
    choice: str
    weight: float = 1.0
    rationale: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0  # 0-1 confidence in vote

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter": self.voter,
            "choice": self.choice,
            "weight": self.weight,
            "rationale": self.rationale,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
        }


@dataclass
class ImpactAssessment:
    """Assessment of decision impact."""

    area: str  # e.g., "technical", "financial", "operational"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_systems: List[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None
    risks: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "severity": self.severity,
            "description": self.description,
            "affected_systems": self.affected_systems,
            "estimated_effort": self.estimated_effort,
            "risks": self.risks,
            "benefits": self.benefits,
        }


@dataclass
class DecisionOutcome:
    """Outcome of a decision."""

    winning_choice: Optional[str]
    vote_counts: Dict[str, float]  # choice -> weighted vote count
    consensus_level: float  # 0-1, how strong the consensus is
    participating_voters: int
    total_eligible_voters: int
    resolved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolution_method: str = "majority"  # majority, unanimous, weighted
    vetoed: bool = False
    veto_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "winning_choice": self.winning_choice,
            "vote_counts": self.vote_counts,
            "consensus_level": self.consensus_level,
            "participating_voters": self.participating_voters,
            "total_eligible_voters": self.total_eligible_voters,
            "resolved_at": self.resolved_at.isoformat(),
            "resolution_method": self.resolution_method,
            "vetoed": self.vetoed,
            "veto_by": self.veto_by,
        }


@dataclass
class Decision:
    """A decision requiring collaborative input."""

    id: str
    title: str
    description: str
    options: List[str]
    state: DecisionState = DecisionState.DRAFT

    # Participants
    proposer: Optional[str] = None
    required_voters: Set[str] = field(default_factory=set)
    optional_voters: Set[str] = field(default_factory=set)

    # Voting
    votes: Dict[str, Vote] = field(default_factory=dict)
    voter_weights: Dict[str, float] = field(default_factory=dict)

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    opened_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    impact_assessments: List[ImpactAssessment] = field(default_factory=list)
    related_decisions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Outcome
    outcome: Optional[DecisionOutcome] = None

    # Settings
    require_rationale: bool = False
    require_unanimous: bool = False
    min_participation: float = 0.5  # Minimum % of required voters

    # Priority and category
    priority: DecisionPriority = DecisionPriority.NORMAL
    category: Optional[str] = None
    template_id: Optional[str] = None

    # Delegations and escalations
    delegations: Dict[str, Delegation] = field(default_factory=dict)
    escalations: List[Escalation] = field(default_factory=list)
    escalation_level: int = 0

    # Comments
    comments: List[Comment] = field(default_factory=list)

    def cast_vote(
        self,
        voter: str,
        choice: str,
        rationale: Optional[str] = None,
        confidence: float = 1.0,
    ) -> bool:
        """
        Cast a vote on this decision.

        Args:
            voter: Who is voting
            choice: The choice being voted for
            rationale: Reason for the vote
            confidence: Confidence level (0-1)

        Returns:
            True if vote was accepted
        """
        if self.state != DecisionState.OPEN:
            logger.warning(f"Cannot vote on decision {self.id}: state is {self.state}")
            return False

        if choice not in self.options:
            logger.warning(f"Invalid choice '{choice}' for decision {self.id}")
            return False

        if self.require_rationale and not rationale:
            logger.warning(f"Rationale required for decision {self.id}")
            return False

        if self.deadline and datetime.now(timezone.utc) > self.deadline:
            logger.warning(f"Voting deadline passed for decision {self.id}")
            return False

        weight = self.voter_weights.get(voter, 1.0)

        self.votes[voter] = Vote(
            voter=voter,
            choice=choice,
            weight=weight,
            rationale=rationale,
            confidence=confidence,
        )

        logger.info(f"Vote cast: {voter} -> {choice} on decision {self.id}")
        return True

    def retract_vote(self, voter: str) -> bool:
        """Retract a previously cast vote."""
        if self.state != DecisionState.OPEN:
            return False

        if voter in self.votes:
            del self.votes[voter]
            return True
        return False

    def add_impact_assessment(self, assessment: ImpactAssessment) -> None:
        """Add an impact assessment."""
        self.impact_assessments.append(assessment)

    def open_voting(self, deadline: Optional[datetime] = None) -> None:
        """Open the decision for voting."""
        if self.state != DecisionState.DRAFT:
            raise ValueError(f"Cannot open decision in state {self.state}")

        self.state = DecisionState.OPEN
        self.opened_at = datetime.now(timezone.utc)
        self.deadline = deadline

    def close_voting(self) -> None:
        """Close voting without resolving."""
        if self.state == DecisionState.OPEN:
            self.state = DecisionState.CLOSED

    def resolve(self) -> Optional[DecisionOutcome]:
        """
        Resolve the decision based on votes.

        Returns:
            DecisionOutcome or None if cannot resolve
        """
        if self.state not in (DecisionState.OPEN, DecisionState.CLOSED):
            return None

        # Check minimum participation
        required_votes = len(self.required_voters)
        actual_required_votes = sum(1 for v in self.required_voters if v in self.votes)

        if required_votes > 0:
            participation = actual_required_votes / required_votes
            if participation < self.min_participation:
                logger.warning(
                    f"Insufficient participation ({participation:.0%}) for decision {self.id}"
                )
                return None

        # Calculate weighted vote counts
        vote_counts: Dict[str, float] = defaultdict(float)
        for vote in self.votes.values():
            weighted_vote = vote.weight * vote.confidence
            vote_counts[vote.choice] += weighted_vote

        # Check for veto
        vetoed = False
        veto_by = None
        for vote in self.votes.values():
            if vote.weight == float("inf"):
                # Veto power used
                vetoed = True
                veto_by = vote.voter
                break

        # Determine winner
        winning_choice = None
        if not vetoed and vote_counts:
            if self.require_unanimous:
                # Check if all votes are the same
                choices = set(vote_counts.keys())
                if len(choices) == 1:
                    winning_choice = list(choices)[0]
            else:
                # Simple weighted majority
                winning_choice = max(vote_counts.items(), key=lambda x: x[1])[0]

        # Calculate consensus level
        total_votes = sum(vote_counts.values())
        consensus_level = 0.0
        if winning_choice and total_votes > 0:
            consensus_level = vote_counts[winning_choice] / total_votes

        self.outcome = DecisionOutcome(
            winning_choice=winning_choice if not vetoed else None,
            vote_counts=dict(vote_counts),
            consensus_level=consensus_level,
            participating_voters=len(self.votes),
            total_eligible_voters=len(self.required_voters) + len(self.optional_voters),
            resolution_method="unanimous" if self.require_unanimous else "weighted_majority",
            vetoed=vetoed,
            veto_by=veto_by,
        )

        self.state = DecisionState.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)

        logger.info(
            f"Decision {self.id} resolved: {winning_choice} " f"(consensus: {consensus_level:.0%})"
        )

        return self.outcome

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the decision."""
        self.state = DecisionState.CANCELLED
        if reason:
            self.context["cancellation_reason"] = reason

    def get_vote_summary(self) -> Dict[str, Any]:
        """Get a summary of current votes."""
        vote_counts: Dict[str, int] = defaultdict(int)
        weighted_counts: Dict[str, float] = defaultdict(float)

        for vote in self.votes.values():
            vote_counts[vote.choice] += 1
            weighted_counts[vote.choice] += vote.weight * vote.confidence

        pending_required = self.required_voters - set(self.votes.keys())

        return {
            "total_votes": len(self.votes),
            "vote_counts": dict(vote_counts),
            "weighted_counts": dict(weighted_counts),
            "pending_required_voters": list(pending_required),
            "participation_rate": (
                len(set(self.votes.keys()) & self.required_voters) / len(self.required_voters)
                if self.required_voters
                else 1.0
            ),
        }

    def delegate_vote(
        self,
        from_voter: str,
        to_voter: str,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Delegation:
        """
        Delegate voting authority to another voter.

        Args:
            from_voter: Original voter
            to_voter: Delegate
            reason: Reason for delegation
            expires_at: When delegation expires

        Returns:
            Delegation record
        """
        delegation = Delegation(
            id=str(uuid.uuid4()),
            decision_id=self.id,
            from_voter=from_voter,
            to_voter=to_voter,
            reason=reason,
            expires_at=expires_at,
        )

        self.delegations[from_voter] = delegation

        # Transfer weight if set
        if from_voter in self.voter_weights:
            self.voter_weights[to_voter] = (
                self.voter_weights.get(to_voter, 1.0) + self.voter_weights[from_voter]
            )

        logger.info(f"Vote delegated: {from_voter} -> {to_voter} on decision {self.id}")
        return delegation

    def revoke_delegation(self, from_voter: str) -> bool:
        """Revoke a delegation."""
        if from_voter in self.delegations:
            del self.delegations[from_voter]
            return True
        return False

    def get_effective_voter(self, voter: str) -> str:
        """Get the effective voter (following delegation chain)."""
        visited = set()
        current = voter

        while current in self.delegations:
            if current in visited:
                # Circular delegation - break
                return voter
            visited.add(current)

            delegation = self.delegations[current]
            if delegation.is_valid():
                current = delegation.to_voter
            else:
                break

        return current

    def add_comment(
        self,
        author: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Comment:
        """
        Add a comment to the decision.

        Args:
            author: Comment author
            content: Comment content
            parent_id: Parent comment ID for threading

        Returns:
            Created comment
        """
        comment = Comment(
            id=str(uuid.uuid4()),
            decision_id=self.id,
            author=author,
            content=content,
            parent_id=parent_id,
        )

        self.comments.append(comment)
        logger.debug(f"Comment added to decision {self.id} by {author}")
        return comment

    def get_comments(self, threaded: bool = False) -> List[Dict[str, Any]]:
        """
        Get comments, optionally in threaded format.

        Args:
            threaded: Return as threaded structure

        Returns:
            List of comments
        """
        if not threaded:
            return [c.to_dict() for c in self.comments]

        # Build threaded structure
        by_parent: Dict[Optional[str], List[Comment]] = defaultdict(list)
        for comment in self.comments:
            by_parent[comment.parent_id].append(comment)

        def build_thread(parent_id: Optional[str]) -> List[Dict[str, Any]]:
            result = []
            for comment in by_parent[parent_id]:
                item = comment.to_dict()
                item["replies"] = build_thread(comment.id)
                result.append(item)
            return result

        return build_thread(None)

    def extend_deadline(self, new_deadline: datetime) -> None:
        """Extend the voting deadline."""
        if self.deadline and new_deadline <= self.deadline:
            raise ValueError("New deadline must be after current deadline")
        self.deadline = new_deadline
        logger.info(f"Deadline extended for decision {self.id} to {new_deadline}")

    def bump_priority(self) -> None:
        """Increase the priority of this decision."""
        priority_order = [
            DecisionPriority.LOW,
            DecisionPriority.NORMAL,
            DecisionPriority.HIGH,
            DecisionPriority.URGENT,
            DecisionPriority.CRITICAL,
        ]
        current_idx = priority_order.index(self.priority)
        if current_idx < len(priority_order) - 1:
            self.priority = priority_order[current_idx + 1]
            logger.info(f"Priority bumped for decision {self.id} to {self.priority.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "options": self.options,
            "state": self.state.value,
            "proposer": self.proposer,
            "required_voters": list(self.required_voters),
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "votes": {k: v.to_dict() for k, v in self.votes.items()},
            "vote_summary": self.get_vote_summary(),
            "impact_assessments": [a.to_dict() for a in self.impact_assessments],
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "tags": self.tags,
            "priority": self.priority.value,
            "category": self.category,
            "template_id": self.template_id,
            "delegations": {k: v.to_dict() for k, v in self.delegations.items()},
            "escalations": [e.to_dict() for e in self.escalations],
            "escalation_level": self.escalation_level,
            "comments": [c.to_dict() for c in self.comments],
        }
