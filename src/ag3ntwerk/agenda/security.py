"""
Security module for the Autonomous Agenda Engine.

This module provides:
1. Risk Assessment - Evaluate risk level and categories for agenda items
2. Human-in-the-Loop Checkpoints - Configurable approval workflow
3. Audit Logging - Track all security-relevant actions

The security system ensures that high-risk actions require human approval
while allowing low-risk, routine tasks to proceed automatically.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    AgendaItem,
    AuditEntry,
    Checkpoint,
    CheckpointType,
    HITLConfig,
    Obstacle,
    RiskAssessment,
    RiskCategory,
    RiskLevel,
    Strategy,
    StrategyType,
)

logger = get_logger(__name__)


# =============================================================================
# Risk Indicators
# =============================================================================

# Keywords that indicate specific risk categories
RISK_INDICATORS: Dict[RiskCategory, List[str]] = {
    RiskCategory.FINANCIAL: [
        "payment",
        "budget",
        "cost",
        "invoice",
        "subscription",
        "billing",
        "price",
        "fee",
        "charge",
        "refund",
        "credit",
        "debit",
        "transaction",
        "purchase",
        "expense",
        "revenue",
        "money",
        "fund",
        "financial",
    ],
    RiskCategory.DATA: [
        "delete",
        "remove",
        "modify",
        "update",
        "migrate",
        "export",
        "import",
        "transform",
        "clean",
        "purge",
        "archive",
        "backup",
        "restore",
        "database",
        "table",
        "record",
        "data",
        "pii",
        "personal",
    ],
    RiskCategory.SECURITY: [
        "credential",
        "password",
        "secret",
        "key",
        "token",
        "auth",
        "permission",
        "access",
        "role",
        "privilege",
        "encrypt",
        "decrypt",
        "certificate",
        "ssl",
        "tls",
        "firewall",
        "security",
        "vulnerability",
    ],
    RiskCategory.INFRASTRUCTURE: [
        "deploy",
        "release",
        "rollback",
        "provision",
        "scale",
        "restart",
        "shutdown",
        "terminate",
        "server",
        "instance",
        "container",
        "cluster",
        "infrastructure",
        "production",
        "staging",
        "environment",
    ],
    RiskCategory.EXTERNAL: [
        "api",
        "webhook",
        "integration",
        "third-party",
        "external",
        "partner",
        "vendor",
        "service",
        "endpoint",
        "request",
        "response",
        "callback",
    ],
    RiskCategory.REPUTATION: [
        "publish",
        "announce",
        "social",
        "marketing",
        "public",
        "press",
        "media",
        "customer",
        "user",
        "communication",
        "message",
        "email",
        "notification",
        "broadcast",
        "tweet",
        "post",
    ],
    RiskCategory.LEGAL: [
        "contract",
        "compliance",
        "gdpr",
        "ccpa",
        "terms",
        "policy",
        "agreement",
        "legal",
        "regulation",
        "audit",
        "privacy",
        "consent",
        "copyright",
        "license",
        "trademark",
    ],
}

# Risk level scores for categories
CATEGORY_RISK_SCORES: Dict[RiskCategory, float] = {
    RiskCategory.FINANCIAL: 0.8,
    RiskCategory.SECURITY: 0.9,
    RiskCategory.LEGAL: 0.8,
    RiskCategory.DATA: 0.6,
    RiskCategory.INFRASTRUCTURE: 0.7,
    RiskCategory.EXTERNAL: 0.5,
    RiskCategory.REPUTATION: 0.6,
}

# Task types with inherent risk levels
HIGH_RISK_TASK_TYPES = {
    "deployment": RiskLevel.HIGH,
    "data_migration": RiskLevel.HIGH,
    "credential_rotation": RiskLevel.CRITICAL,
    "payment_processing": RiskLevel.CRITICAL,
    "security_scan": RiskLevel.HIGH,
    "production_release": RiskLevel.CRITICAL,
    "access_control": RiskLevel.HIGH,
    "incident_response": RiskLevel.HIGH,
    "compliance_check": RiskLevel.MEDIUM,
    "audit": RiskLevel.MEDIUM,
}


# =============================================================================
# Risk Assessor
# =============================================================================


class RiskAssessor:
    """
    Assess risk of agenda items and strategies.

    The assessor evaluates:
    - Risk level (MINIMAL, LOW, MEDIUM, HIGH, CRITICAL)
    - Risk categories (FINANCIAL, DATA, SECURITY, etc.)
    - Specific risks and mitigations
    - Approval requirements

    Example:
        assessor = RiskAssessor()
        assessment = assessor.assess_agenda_item(item)
        if assessment.requires_approval:
            # Create checkpoint for human review
    """

    def __init__(self, config: Optional[HITLConfig] = None):
        """
        Initialize the risk assessor.

        Args:
            config: HITL configuration for approval thresholds
        """
        self.config = config or HITLConfig()

    def assess_agenda_item(self, item: AgendaItem) -> RiskAssessment:
        """
        Assess risk for an agenda item.

        Args:
            item: The agenda item to assess

        Returns:
            RiskAssessment with risk level, categories, and approval requirements
        """
        # Combine text for analysis
        text = f"{item.title} {item.description} {item.task_type}".lower()

        # Detect risk categories
        categories = self._detect_categories(text)

        # Check task type for inherent risk
        task_type_risk = HIGH_RISK_TASK_TYPES.get(item.task_type)

        # Calculate risk score
        risk_score = self._calculate_risk_score(categories, item)

        # Determine risk level
        risk_level = self._score_to_level(risk_score, task_type_risk)

        # Identify specific risks
        risks = self._identify_risks(item, categories)

        # Suggest mitigations
        mitigations = self._suggest_mitigations(risks, categories)

        # Determine if approval required
        requires_approval, approval_reason = self._check_approval_required(
            item, risk_level, categories
        )

        return RiskAssessment(
            item_id=item.id,
            item_type="agenda_item",
            risk_level=risk_level,
            risk_categories=categories,
            risk_score=risk_score,
            risks=risks,
            mitigations=mitigations,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            approver_role="user" if risk_level.value in ("high", "critical") else None,
        )

    def assess_strategy(self, strategy: Strategy) -> RiskAssessment:
        """
        Assess risk for a strategy.

        Args:
            strategy: The strategy to assess

        Returns:
            RiskAssessment for the strategy
        """
        text = f"{strategy.title} {strategy.description}".lower()

        categories = self._detect_categories(text)

        # Strategy type affects risk
        strategy_type_multiplier = {
            StrategyType.INTERNAL_CHANGE: 0.5,
            StrategyType.TASK_GENERATION: 0.6,
            StrategyType.TOOL_INGESTION: 0.8,
            StrategyType.GOAL_MODIFICATION: 0.7,
        }

        base_score = self._calculate_base_score(categories)
        risk_score = base_score * strategy_type_multiplier.get(strategy.strategy_type, 1.0)

        # Tool ingestion always has some infrastructure risk
        if strategy.strategy_type == StrategyType.TOOL_INGESTION:
            if RiskCategory.INFRASTRUCTURE not in categories:
                categories.append(RiskCategory.INFRASTRUCTURE)

        risk_level = self._score_to_level(risk_score)

        risks = [
            f"Strategy type: {strategy.strategy_type.value}",
            f"Estimated cost: ${strategy.estimated_cost_usd:.2f}",
            f"Confidence: {strategy.confidence:.0%}",
        ]

        # Check if this strategy type always requires approval
        requires_approval = False
        approval_reason = None
        if strategy.strategy_type in self.config.always_approve_strategy_types:
            requires_approval = True
            approval_reason = f"Strategy type {strategy.strategy_type.value} requires approval"
        elif risk_level.value in ("high", "critical"):
            requires_approval = True
            approval_reason = f"High risk level: {risk_level.value}"

        return RiskAssessment(
            item_id=strategy.id,
            item_type="strategy",
            risk_level=risk_level,
            risk_categories=categories,
            risk_score=risk_score,
            risks=risks,
            mitigations=["Review strategy details before approval"],
            requires_approval=requires_approval,
            approval_reason=approval_reason,
        )

    def assess_obstacle_resolution(
        self,
        obstacle: Obstacle,
        strategy: Strategy,
    ) -> RiskAssessment:
        """
        Assess risk of resolving an obstacle with a strategy.

        Args:
            obstacle: The obstacle being resolved
            strategy: The strategy being used

        Returns:
            Combined risk assessment
        """
        # Get strategy assessment as base
        strategy_assessment = self.assess_strategy(strategy)

        # Combine obstacle context
        text = f"{obstacle.title} {obstacle.description}".lower()
        obstacle_categories = self._detect_categories(text)

        # Merge categories
        all_categories = list(set(strategy_assessment.risk_categories + obstacle_categories))

        # Recalculate risk with combined context
        combined_score = (
            strategy_assessment.risk_score + self._calculate_base_score(obstacle_categories)
        ) / 2

        risk_level = self._score_to_level(combined_score)

        return RiskAssessment(
            item_id=f"{obstacle.id}:{strategy.id}",
            item_type="obstacle_resolution",
            risk_level=risk_level,
            risk_categories=all_categories,
            risk_score=combined_score,
            risks=strategy_assessment.risks + [f"Resolving obstacle: {obstacle.title}"],
            mitigations=strategy_assessment.mitigations,
            requires_approval=strategy_assessment.requires_approval,
            approval_reason=strategy_assessment.approval_reason,
        )

    def _detect_categories(self, text: str) -> List[RiskCategory]:
        """Detect risk categories from text."""
        categories = []
        for category, keywords in RISK_INDICATORS.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
        return categories

    def _calculate_base_score(self, categories: List[RiskCategory]) -> float:
        """Calculate base risk score from categories."""
        if not categories:
            return 0.1

        scores = [CATEGORY_RISK_SCORES.get(c, 0.5) for c in categories]
        return max(scores)  # Use highest category score

    def _calculate_risk_score(
        self,
        categories: List[RiskCategory],
        item: AgendaItem,
    ) -> float:
        """Calculate comprehensive risk score."""
        base_score = self._calculate_base_score(categories)

        # Adjust based on item properties
        adjustments = 0.0

        # Higher estimated cost = higher risk
        if item.estimated_cost_usd > 50:
            adjustments += 0.1
        elif item.estimated_cost_usd > 100:
            adjustments += 0.2

        # Lower confidence = higher risk
        if item.confidence_score < 0.5:
            adjustments += 0.15
        elif item.confidence_score < 0.3:
            adjustments += 0.25

        # Obstacle resolution has some inherent risk
        if item.is_obstacle_resolution:
            adjustments += 0.1

        return min(base_score + adjustments, 1.0)

    def _score_to_level(
        self,
        score: float,
        override: Optional[RiskLevel] = None,
    ) -> RiskLevel:
        """Convert risk score to risk level."""
        if override:
            return override

        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    def _identify_risks(
        self,
        item: AgendaItem,
        categories: List[RiskCategory],
    ) -> List[str]:
        """Identify specific risks for the item."""
        risks = []

        for category in categories:
            if category == RiskCategory.FINANCIAL:
                risks.append("May incur costs or affect budgets")
            elif category == RiskCategory.DATA:
                risks.append("May modify or delete data")
            elif category == RiskCategory.SECURITY:
                risks.append("May affect system security")
            elif category == RiskCategory.INFRASTRUCTURE:
                risks.append("May affect system infrastructure")
            elif category == RiskCategory.EXTERNAL:
                risks.append("Involves external service calls")
            elif category == RiskCategory.REPUTATION:
                risks.append("May affect public perception")
            elif category == RiskCategory.LEGAL:
                risks.append("May have legal implications")

        if item.task_type in HIGH_RISK_TASK_TYPES:
            risks.append(f"High-risk task type: {item.task_type}")

        return risks

    def _suggest_mitigations(
        self,
        risks: List[str],
        categories: List[RiskCategory],
    ) -> List[str]:
        """Suggest mitigations for identified risks."""
        mitigations = ["Review task details before execution"]

        for category in categories:
            if category == RiskCategory.FINANCIAL:
                mitigations.append("Verify budget availability")
            elif category == RiskCategory.DATA:
                mitigations.append("Ensure backup exists")
            elif category == RiskCategory.SECURITY:
                mitigations.append("Validate with security review")
            elif category == RiskCategory.INFRASTRUCTURE:
                mitigations.append("Test in staging first")

        return mitigations

    def _check_approval_required(
        self,
        item: AgendaItem,
        risk_level: RiskLevel,
        categories: List[RiskCategory],
    ) -> Tuple[bool, Optional[str]]:
        """Check if approval is required based on config."""
        if not self.config.enabled:
            return False, None

        # Check risk level threshold
        risk_levels_ordered = [
            RiskLevel.MINIMAL,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        threshold_idx = risk_levels_ordered.index(self.config.approval_threshold_risk_level)
        current_idx = risk_levels_ordered.index(risk_level)

        if current_idx >= threshold_idx:
            return True, f"Risk level {risk_level.value} exceeds threshold"

        # Check category overrides
        for category in categories:
            if category in self.config.always_approve_categories:
                return True, f"Category {category.value} requires approval"

        # Check task type overrides
        if item.task_type in self.config.always_approve_task_types:
            return True, f"Task type {item.task_type} requires approval"

        # Check cost threshold
        if item.estimated_cost_usd > self.config.auto_execute_max_cost_usd:
            return True, f"Cost ${item.estimated_cost_usd:.2f} exceeds auto-execute limit"

        return False, None


# =============================================================================
# Checkpoint Manager
# =============================================================================


class CheckpointManager:
    """
    Manage human-in-the-loop checkpoints.

    The checkpoint manager:
    - Determines when checkpoints are needed
    - Creates and tracks checkpoints
    - Handles approval/rejection workflow
    - Manages escalation for timeouts

    Example:
        manager = CheckpointManager(config, risk_assessor)
        if manager.should_checkpoint(item)[0]:
            checkpoint = manager.create_checkpoint(item, CheckpointType.APPROVAL, "reason")
            # Wait for approval
            approved = await manager.wait_for_approval(checkpoint)
    """

    def __init__(
        self,
        config: HITLConfig,
        risk_assessor: RiskAssessor,
    ):
        """
        Initialize the checkpoint manager.

        Args:
            config: HITL configuration
            risk_assessor: Risk assessor instance
        """
        self.config = config
        self.risk_assessor = risk_assessor
        self._pending_checkpoints: Dict[str, Checkpoint] = {}
        self._resolved_checkpoints: Dict[str, Checkpoint] = {}

    def should_checkpoint(
        self,
        item: AgendaItem,
    ) -> Tuple[bool, CheckpointType, str]:
        """
        Determine if item needs human checkpoint and why.

        Args:
            item: The agenda item to check

        Returns:
            Tuple of (needs_checkpoint, checkpoint_type, reason)
        """
        if not self.config.enabled:
            return False, CheckpointType.NOTIFICATION, "HITL disabled"

        # Use risk assessment
        assessment = item.risk_assessment
        if not assessment:
            assessment = self.risk_assessor.assess_agenda_item(item)

        if assessment.requires_approval:
            return True, CheckpointType.APPROVAL, assessment.approval_reason or "Risk assessment"

        # Check for review-level items
        if assessment.risk_level == RiskLevel.MEDIUM:
            return True, CheckpointType.REVIEW, "Medium risk item"

        # Notification for any item with identified risks
        if assessment.risks and assessment.risk_level != RiskLevel.MINIMAL:
            return True, CheckpointType.NOTIFICATION, "Risk identified"

        return False, CheckpointType.NOTIFICATION, "No checkpoint needed"

    def create_checkpoint(
        self,
        item: AgendaItem,
        checkpoint_type: CheckpointType,
        reason: str,
    ) -> Checkpoint:
        """
        Create a checkpoint for an agenda item.

        Args:
            item: The agenda item
            checkpoint_type: Type of checkpoint
            reason: Why the checkpoint was created

        Returns:
            Created Checkpoint
        """
        # Get or create risk assessment
        risk_assessment = item.risk_assessment
        if not risk_assessment:
            risk_assessment = self.risk_assessor.assess_agenda_item(item)

        # Set expiration
        expires_at = datetime.now() + timedelta(hours=self.config.approval_timeout_hours)

        # Determine options based on checkpoint type
        if checkpoint_type == CheckpointType.APPROVAL:
            options = ["Approve", "Reject", "Modify", "Defer"]
        elif checkpoint_type == CheckpointType.REVIEW:
            options = ["Acknowledge", "Flag for Review", "Approve Anyway"]
        elif checkpoint_type == CheckpointType.CONFIRMATION:
            options = ["Confirm", "Cancel"]
        else:  # NOTIFICATION
            options = ["Acknowledge"]

        checkpoint = Checkpoint(
            checkpoint_type=checkpoint_type,
            trigger_reason=reason,
            risk_assessment=risk_assessment,
            item_id=item.id,
            title=f"Review: {item.title}",
            description=(
                f"Task: {item.title}\n\n"
                f"Type: {item.task_type}\n"
                f"Agent: {item.recommended_agent}\n"
                f"Risk Level: {risk_assessment.risk_level.value}\n"
                f"Reason: {reason}"
            ),
            context={
                "item": item.to_dict(),
                "risk_assessment": risk_assessment.to_dict(),
            },
            options=options,
            default_option=options[0] if checkpoint_type != CheckpointType.APPROVAL else None,
            expires_at=expires_at,
        )

        self._pending_checkpoints[checkpoint.id] = checkpoint

        logger.info(f"Created {checkpoint_type.value} checkpoint for item '{item.title}'")

        return checkpoint

    def create_strategy_checkpoint(
        self,
        strategy: Strategy,
        obstacle: Obstacle,
    ) -> Checkpoint:
        """
        Create a checkpoint for strategy approval.

        Args:
            strategy: The strategy to approve
            obstacle: The obstacle being addressed

        Returns:
            Created Checkpoint
        """
        risk_assessment = self.risk_assessor.assess_strategy(strategy)

        expires_at = datetime.now() + timedelta(hours=self.config.approval_timeout_hours)

        checkpoint = Checkpoint(
            checkpoint_type=CheckpointType.APPROVAL,
            trigger_reason=f"Strategy approval for: {obstacle.title}",
            risk_assessment=risk_assessment,
            strategy_id=strategy.id,
            title=f"Approve Strategy: {strategy.title}",
            description=(
                f"Strategy: {strategy.title}\n\n"
                f"Type: {strategy.strategy_type.value}\n"
                f"Obstacle: {obstacle.title}\n"
                f"Estimated Effort: {strategy.estimated_effort_hours} hours\n"
                f"Estimated Cost: ${strategy.estimated_cost_usd:.2f}\n"
                f"Confidence: {strategy.confidence:.0%}"
            ),
            context={
                "strategy": strategy.to_dict(),
                "obstacle": obstacle.to_dict(),
                "risk_assessment": risk_assessment.to_dict(),
            },
            options=["Approve", "Reject", "Modify", "Request Alternative"],
            expires_at=expires_at,
        )

        self._pending_checkpoints[checkpoint.id] = checkpoint

        return checkpoint

    async def wait_for_approval(
        self,
        checkpoint: Checkpoint,
        timeout_hours: Optional[int] = None,
    ) -> bool:
        """
        Wait for checkpoint approval (async, for integration).

        In a real implementation, this would integrate with a notification
        system and wait for user response.

        Args:
            checkpoint: The checkpoint to wait for
            timeout_hours: Override timeout

        Returns:
            True if approved, False otherwise
        """
        # In actual implementation, this would poll or await user action
        # For now, return based on checkpoint status
        return checkpoint.status == "approved"

    def approve(
        self,
        checkpoint_id: str,
        approver: str,
        notes: str = "",
    ) -> bool:
        """
        Approve a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint
            approver: Who approved it
            notes: Optional notes

        Returns:
            True if successfully approved
        """
        checkpoint = self._pending_checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False

        checkpoint.status = "approved"
        checkpoint.resolved_by = approver
        checkpoint.resolved_at = datetime.now()
        checkpoint.resolution_notes = notes
        checkpoint.selected_option = "Approve"

        # Move to resolved
        self._resolved_checkpoints[checkpoint_id] = checkpoint
        del self._pending_checkpoints[checkpoint_id]

        logger.info(f"Checkpoint {checkpoint_id} approved by {approver}")

        return True

    def reject(
        self,
        checkpoint_id: str,
        approver: str,
        reason: str,
    ) -> bool:
        """
        Reject a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint
            approver: Who rejected it
            reason: Why it was rejected

        Returns:
            True if successfully rejected
        """
        checkpoint = self._pending_checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False

        checkpoint.status = "rejected"
        checkpoint.resolved_by = approver
        checkpoint.resolved_at = datetime.now()
        checkpoint.resolution_notes = reason
        checkpoint.selected_option = "Reject"

        self._resolved_checkpoints[checkpoint_id] = checkpoint
        del self._pending_checkpoints[checkpoint_id]

        logger.info(f"Checkpoint {checkpoint_id} rejected by {approver}: {reason}")

        return True

    def modify(
        self,
        checkpoint_id: str,
        approver: str,
        modifications: Dict[str, Any],
    ) -> bool:
        """
        Approve with modifications.

        Args:
            checkpoint_id: ID of the checkpoint
            approver: Who modified it
            modifications: Changes to apply

        Returns:
            True if successfully modified
        """
        checkpoint = self._pending_checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False

        checkpoint.status = "modified"
        checkpoint.resolved_by = approver
        checkpoint.resolved_at = datetime.now()
        checkpoint.resolution_notes = f"Modified: {modifications}"
        checkpoint.selected_option = "Modify"
        checkpoint.context["modifications"] = modifications

        self._resolved_checkpoints[checkpoint_id] = checkpoint
        del self._pending_checkpoints[checkpoint_id]

        return True

    def get_pending_checkpoints(self) -> List[Checkpoint]:
        """Get all pending checkpoints."""
        return list(self._pending_checkpoints.values())

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        return self._pending_checkpoints.get(checkpoint_id) or self._resolved_checkpoints.get(
            checkpoint_id
        )

    def batch_approve(
        self,
        checkpoint_ids: List[str],
        approver: str,
    ) -> int:
        """
        Batch approve multiple checkpoints.

        Args:
            checkpoint_ids: IDs to approve
            approver: Who approved them

        Returns:
            Number of checkpoints approved
        """
        if not self.config.allow_batch_approval:
            return 0

        # Limit batch size
        ids_to_process = checkpoint_ids[: self.config.max_batch_size]

        count = 0
        for cid in ids_to_process:
            if self.approve(cid, approver, "Batch approved"):
                count += 1

        return count

    async def check_for_escalation(self) -> List[Checkpoint]:
        """Check for checkpoints needing escalation."""
        to_escalate = []
        now = datetime.now()
        escalation_threshold = timedelta(hours=self.config.escalation_after_hours)

        for checkpoint in self._pending_checkpoints.values():
            age = now - checkpoint.created_at
            if age >= escalation_threshold and not checkpoint.escalated_at:
                to_escalate.append(checkpoint)

        return to_escalate

    async def escalate(self, checkpoint: Checkpoint) -> None:
        """Escalate a checkpoint."""
        checkpoint.escalated_at = datetime.now()
        checkpoint.escalated_to = "admin"  # Could be configurable

        logger.warning(
            f"Checkpoint {checkpoint.id} escalated after "
            f"{self.config.escalation_after_hours} hours without resolution"
        )


# =============================================================================
# Audit Logger
# =============================================================================


class AuditLogger:
    """
    Log all security-relevant actions.

    Maintains a complete audit trail of:
    - Checkpoint creation
    - Approvals and rejections
    - Auto-execution decisions
    - Escalations

    Example:
        audit = AuditLogger()
        entry = audit.log_approval(checkpoint, "user@example.com")
        trail = audit.get_audit_trail(start_time=yesterday)
    """

    def __init__(self, max_entries: int = 10000):
        """
        Initialize the audit logger.

        Args:
            max_entries: Maximum entries to keep in memory
        """
        self.max_entries = max_entries
        self._entries: List[AuditEntry] = []

    def _add_entry(self, entry: AuditEntry) -> str:
        """Add an entry to the log."""
        self._entries.append(entry)

        # Trim if needed
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]

        return entry.id

    def log_checkpoint_created(self, checkpoint: Checkpoint) -> str:
        """Log checkpoint creation."""
        entry = AuditEntry(
            action_type="checkpoint_created",
            checkpoint_id=checkpoint.id,
            item_id=checkpoint.item_id,
            strategy_id=checkpoint.strategy_id,
            actor="system",
            risk_level=(
                checkpoint.risk_assessment.risk_level if checkpoint.risk_assessment else None
            ),
            risk_score=(
                checkpoint.risk_assessment.risk_score if checkpoint.risk_assessment else None
            ),
            decision=checkpoint.checkpoint_type.value,
            reason=checkpoint.trigger_reason,
            context={
                "title": checkpoint.title,
                "options": checkpoint.options,
            },
        )
        return self._add_entry(entry)

    def log_approval(self, checkpoint: Checkpoint, approver: str) -> str:
        """Log approval action."""
        entry = AuditEntry(
            action_type="approval",
            checkpoint_id=checkpoint.id,
            item_id=checkpoint.item_id,
            strategy_id=checkpoint.strategy_id,
            actor=f"user:{approver}",
            actor_role="approver",
            risk_level=(
                checkpoint.risk_assessment.risk_level if checkpoint.risk_assessment else None
            ),
            decision="approved",
            reason=checkpoint.resolution_notes,
            context={
                "title": checkpoint.title,
                "selected_option": checkpoint.selected_option,
            },
        )
        return self._add_entry(entry)

    def log_rejection(
        self,
        checkpoint: Checkpoint,
        approver: str,
        reason: str,
    ) -> str:
        """Log rejection action."""
        entry = AuditEntry(
            action_type="rejection",
            checkpoint_id=checkpoint.id,
            item_id=checkpoint.item_id,
            strategy_id=checkpoint.strategy_id,
            actor=f"user:{approver}",
            actor_role="approver",
            risk_level=(
                checkpoint.risk_assessment.risk_level if checkpoint.risk_assessment else None
            ),
            decision="rejected",
            reason=reason,
            context={
                "title": checkpoint.title,
            },
        )
        return self._add_entry(entry)

    def log_auto_execution(self, item: AgendaItem, reason: str) -> str:
        """Log automatic execution (no approval needed)."""
        entry = AuditEntry(
            action_type="auto_execution",
            item_id=item.id,
            actor="auto",
            risk_level=item.risk_assessment.risk_level if item.risk_assessment else RiskLevel.LOW,
            risk_score=item.risk_assessment.risk_score if item.risk_assessment else 0.0,
            decision="auto_approved",
            reason=reason,
            context={
                "title": item.title,
                "task_type": item.task_type,
                "agent": item.recommended_agent,
            },
        )
        return self._add_entry(entry)

    def log_escalation(self, checkpoint: Checkpoint) -> str:
        """Log escalation action."""
        entry = AuditEntry(
            action_type="escalation",
            checkpoint_id=checkpoint.id,
            item_id=checkpoint.item_id,
            strategy_id=checkpoint.strategy_id,
            actor="system",
            risk_level=(
                checkpoint.risk_assessment.risk_level if checkpoint.risk_assessment else None
            ),
            decision="escalated",
            reason=f"No response after escalation threshold",
            context={
                "title": checkpoint.title,
                "escalated_to": checkpoint.escalated_to,
                "hours_pending": (datetime.now() - checkpoint.created_at).total_seconds() / 3600,
            },
        )
        return self._add_entry(entry)

    def get_audit_trail(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        action_types: Optional[List[str]] = None,
        item_id: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> List[AuditEntry]:
        """
        Query the audit trail.

        Args:
            start_time: Filter by start time
            end_time: Filter by end time
            action_types: Filter by action types
            item_id: Filter by item ID
            actor: Filter by actor

        Returns:
            Filtered list of audit entries
        """
        entries = self._entries

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        if action_types:
            entries = [e for e in entries if e.action_type in action_types]

        if item_id:
            entries = [e for e in entries if e.item_id == item_id]

        if actor:
            entries = [e for e in entries if actor in e.actor]

        return entries

    def get_summary(
        self,
        start_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get summary statistics of audit trail."""
        entries = self._entries
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if not entries:
            return {"total": 0}

        by_action = {}
        by_risk_level = {}

        for entry in entries:
            by_action[entry.action_type] = by_action.get(entry.action_type, 0) + 1
            if entry.risk_level:
                level = entry.risk_level.value
                by_risk_level[level] = by_risk_level.get(level, 0) + 1

        approvals = len([e for e in entries if e.action_type == "approval"])
        rejections = len([e for e in entries if e.action_type == "rejection"])

        return {
            "total": len(entries),
            "by_action": by_action,
            "by_risk_level": by_risk_level,
            "approval_rate": (
                approvals / (approvals + rejections) if (approvals + rejections) > 0 else 0
            ),
            "escalations": by_action.get("escalation", 0),
            "auto_executions": by_action.get("auto_execution", 0),
        }
