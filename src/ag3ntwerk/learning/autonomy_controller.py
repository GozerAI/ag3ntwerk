"""
Autonomy Controller - Manages decision autonomy levels across the learning system.

Controls which actions the system can take autonomously vs. those requiring
human approval or supervision.

Autonomy Levels:
1. FULL - System acts autonomously, no logging required
2. SUPERVISED - System acts autonomously but logs all actions
3. ADVISORY - System recommends but waits for human confirmation
4. HUMAN_REQUIRED - Human must explicitly approve before action
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    """Levels of autonomy for different actions."""

    FULL = "full"  # Act without logging
    SUPERVISED = "supervised"  # Act with logging
    ADVISORY = "advisory"  # Recommend, wait for confirmation
    HUMAN_REQUIRED = "human_required"  # Must have explicit approval


class ActionCategory(Enum):
    """Categories of actions the system can take."""

    # Routing actions
    ROUTINE_ROUTING = "routine_routing"
    DYNAMIC_ROUTING = "dynamic_routing"
    FALLBACK_ROUTING = "fallback_routing"

    # Learning actions
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    PATTERN_CREATION = "pattern_creation"
    PATTERN_DEACTIVATION = "pattern_deactivation"
    PARAMETER_TUNING = "parameter_tuning"

    # Handler actions
    HANDLER_GENERATION = "handler_generation"
    HANDLER_ACTIVATION = "handler_activation"
    HANDLER_DEPRECATION = "handler_deprecation"

    # Task actions
    PROACTIVE_TASK_CREATION = "proactive_task_creation"
    TASK_PRIORITY_ADJUSTMENT = "task_priority_adjustment"
    TASK_CANCELLATION = "task_cancellation"

    # Experiment actions
    EXPERIMENT_START = "experiment_start"
    EXPERIMENT_CONCLUSION = "experiment_conclusion"

    # System actions
    WORKFLOW_MODIFICATION = "workflow_modification"
    AGENT_CAPABILITY_CHANGE = "agent_capability_change"
    SYSTEM_PARAMETER_CHANGE = "system_parameter_change"


@dataclass
class AutonomyDecision:
    """Result of an autonomy check."""

    action: str
    level: AutonomyLevel
    proceed: bool
    requires_approval: bool = False
    requires_logging: bool = False
    reason: str = ""
    approval_id: Optional[str] = None
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "level": self.level.value,
            "proceed": self.proceed,
            "requires_approval": self.requires_approval,
            "requires_logging": self.requires_logging,
            "reason": self.reason,
            "approval_id": self.approval_id,
            "decided_at": self.decided_at.isoformat(),
        }


@dataclass
class PendingApproval:
    """An action awaiting human approval."""

    id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    category: ActionCategory = ActionCategory.ROUTINE_ROUTING
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    impact_assessment: str = ""
    recommended_decision: bool = True

    # Status
    status: str = "pending"  # pending, approved, denied, expired
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "category": self.category.value,
            "description": self.description,
            "context": self.context,
            "impact_assessment": self.impact_assessment,
            "recommended_decision": self.recommended_decision,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by,
        }


@dataclass
class ActionLog:
    """Log entry for supervised actions."""

    id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    category: ActionCategory = ActionCategory.ROUTINE_ROUTING
    autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    success: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "category": self.category.value,
            "autonomy_level": self.autonomy_level.value,
            "description": self.description,
            "context": self.context,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
        }


class AutonomyController:
    """
    Manages decision autonomy levels for the learning system.

    Controls which actions the system can take autonomously and which
    require human approval or supervision.
    """

    # Default autonomy levels for each action category
    DEFAULT_AUTONOMY_LEVELS: Dict[ActionCategory, AutonomyLevel] = {
        # Fully autonomous - routine operations
        ActionCategory.ROUTINE_ROUTING: AutonomyLevel.FULL,
        ActionCategory.CONFIDENCE_CALIBRATION: AutonomyLevel.FULL,
        ActionCategory.PATTERN_CREATION: AutonomyLevel.FULL,
        ActionCategory.PARAMETER_TUNING: AutonomyLevel.FULL,
        ActionCategory.PROACTIVE_TASK_CREATION: AutonomyLevel.FULL,
        # Supervised - potentially impactful but reversible
        ActionCategory.DYNAMIC_ROUTING: AutonomyLevel.SUPERVISED,
        ActionCategory.FALLBACK_ROUTING: AutonomyLevel.SUPERVISED,
        ActionCategory.HANDLER_GENERATION: AutonomyLevel.SUPERVISED,
        ActionCategory.HANDLER_ACTIVATION: AutonomyLevel.SUPERVISED,
        ActionCategory.PATTERN_DEACTIVATION: AutonomyLevel.SUPERVISED,
        ActionCategory.TASK_PRIORITY_ADJUSTMENT: AutonomyLevel.SUPERVISED,
        ActionCategory.EXPERIMENT_START: AutonomyLevel.SUPERVISED,
        ActionCategory.EXPERIMENT_CONCLUSION: AutonomyLevel.SUPERVISED,
        # Advisory - significant impact, human should confirm
        ActionCategory.WORKFLOW_MODIFICATION: AutonomyLevel.ADVISORY,
        ActionCategory.HANDLER_DEPRECATION: AutonomyLevel.ADVISORY,
        ActionCategory.TASK_CANCELLATION: AutonomyLevel.ADVISORY,
        # Human required - irreversible or high-impact
        ActionCategory.AGENT_CAPABILITY_CHANGE: AutonomyLevel.HUMAN_REQUIRED,
        ActionCategory.SYSTEM_PARAMETER_CHANGE: AutonomyLevel.HUMAN_REQUIRED,
    }

    # Approval expiration time
    DEFAULT_APPROVAL_EXPIRY_HOURS = 24

    def __init__(
        self,
        db: Optional[Any] = None,
        custom_levels: Optional[Dict[ActionCategory, AutonomyLevel]] = None,
    ):
        """
        Initialize the autonomy controller.

        Args:
            db: Optional database connection for persistence
            custom_levels: Optional custom autonomy level overrides
        """
        self._db = db

        # Merge default levels with custom overrides
        self._autonomy_levels = dict(self.DEFAULT_AUTONOMY_LEVELS)
        if custom_levels:
            self._autonomy_levels.update(custom_levels)

        # Pending approvals
        self._pending_approvals: Dict[str, PendingApproval] = {}

        # Action log (in-memory, can be persisted)
        self._action_log: List[ActionLog] = []

        # Callbacks for approval requests
        self._approval_callbacks: List[Callable[[PendingApproval], None]] = []

        # Override rules (temporary overrides for specific contexts)
        self._overrides: Dict[str, AutonomyLevel] = {}

    def check_autonomy(
        self,
        action: str,
        category: Optional[ActionCategory] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomyDecision:
        """
        Check autonomy level for an action.

        Args:
            action: Specific action name
            category: Action category (will be inferred if not provided)
            context: Optional context for the decision

        Returns:
            AutonomyDecision with proceed/approval requirements
        """
        # Infer category from action name if not provided
        if category is None:
            category = self._infer_category(action)

        # Check for specific overrides
        if action in self._overrides:
            level = self._overrides[action]
        else:
            level = self._autonomy_levels.get(category, AutonomyLevel.HUMAN_REQUIRED)

        # Build decision based on level
        if level == AutonomyLevel.FULL:
            return AutonomyDecision(
                action=action,
                level=level,
                proceed=True,
                requires_approval=False,
                requires_logging=False,
                reason="Fully autonomous action",
            )

        elif level == AutonomyLevel.SUPERVISED:
            return AutonomyDecision(
                action=action,
                level=level,
                proceed=True,
                requires_approval=False,
                requires_logging=True,
                reason="Supervised action - will be logged",
            )

        elif level == AutonomyLevel.ADVISORY:
            # Check if we have pending approval
            approval = self._find_pending_approval(action, context)
            if approval and approval.status == "approved":
                return AutonomyDecision(
                    action=action,
                    level=level,
                    proceed=True,
                    requires_approval=False,
                    requires_logging=True,
                    reason="Previously approved advisory action",
                    approval_id=approval.id,
                )

            return AutonomyDecision(
                action=action,
                level=level,
                proceed=False,
                requires_approval=True,
                requires_logging=True,
                reason="Advisory action - requires human confirmation",
            )

        else:  # HUMAN_REQUIRED
            # Check if we have pending approval
            approval = self._find_pending_approval(action, context)
            if approval and approval.status == "approved":
                return AutonomyDecision(
                    action=action,
                    level=level,
                    proceed=True,
                    requires_approval=False,
                    requires_logging=True,
                    reason="Human-approved action",
                    approval_id=approval.id,
                )

            return AutonomyDecision(
                action=action,
                level=level,
                proceed=False,
                requires_approval=True,
                requires_logging=True,
                reason="Action requires explicit human approval",
            )

    async def request_approval(
        self,
        action: str,
        category: ActionCategory,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        impact_assessment: str = "",
        recommended_decision: bool = True,
        expiry_hours: Optional[int] = None,
    ) -> PendingApproval:
        """
        Request human approval for an action.

        Args:
            action: Action name
            category: Action category
            description: Human-readable description
            context: Context for the action
            impact_assessment: Assessment of potential impact
            recommended_decision: Whether system recommends approval
            expiry_hours: Hours until approval expires

        Returns:
            PendingApproval object
        """
        expiry = expiry_hours or self.DEFAULT_APPROVAL_EXPIRY_HOURS

        approval = PendingApproval(
            action=action,
            category=category,
            description=description,
            context=context or {},
            impact_assessment=impact_assessment,
            recommended_decision=recommended_decision,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry),
        )

        self._pending_approvals[approval.id] = approval

        # Notify callbacks
        for callback in self._approval_callbacks:
            try:
                callback(approval)
            except Exception as e:
                logger.warning(f"Approval callback failed: {e}")

        # Persist if db is available
        if self._db:
            await self._persist_approval(approval)

        logger.info(f"Approval requested for {action}: {approval.id}")

        return approval

    async def approve(
        self,
        approval_id: str,
        approver: str = "human",
    ) -> bool:
        """
        Approve a pending action.

        Args:
            approval_id: ID of the pending approval
            approver: Identifier of the approver

        Returns:
            True if approved successfully
        """
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False

        if approval.status != "pending":
            return False

        # Check expiration
        if approval.expires_at and datetime.now(timezone.utc) > approval.expires_at:
            approval.status = "expired"
            return False

        approval.status = "approved"
        approval.decided_at = datetime.now(timezone.utc)
        approval.decided_by = approver

        # Persist if db is available
        if self._db:
            await self._update_approval(approval)

        logger.info(f"Approval granted for {approval.action} by {approver}")

        return True

    async def deny(
        self,
        approval_id: str,
        denier: str = "human",
        reason: str = "",
    ) -> bool:
        """
        Deny a pending action.

        Args:
            approval_id: ID of the pending approval
            denier: Identifier of the person denying
            reason: Reason for denial

        Returns:
            True if denied successfully
        """
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False

        if approval.status != "pending":
            return False

        approval.status = "denied"
        approval.decided_at = datetime.now(timezone.utc)
        approval.decided_by = denier

        # Persist if db is available
        if self._db:
            await self._update_approval(approval)

        logger.info(f"Approval denied for {approval.action} by {denier}: {reason}")

        return True

    async def log_action(
        self,
        action: str,
        category: ActionCategory,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> ActionLog:
        """
        Log a supervised action.

        Args:
            action: Action name
            category: Action category
            description: Human-readable description
            context: Context for the action
            result: Result of the action
            success: Whether action succeeded

        Returns:
            ActionLog entry
        """
        log_entry = ActionLog(
            action=action,
            category=category,
            autonomy_level=self._autonomy_levels.get(category, AutonomyLevel.SUPERVISED),
            description=description,
            context=context or {},
            result=result,
            success=success,
        )

        self._action_log.append(log_entry)

        # Persist if db is available
        if self._db:
            await self._persist_log(log_entry)

        logger.debug(f"Action logged: {action} - {'success' if success else 'failure'}")

        return log_entry

    def set_autonomy_level(
        self,
        category: ActionCategory,
        level: AutonomyLevel,
    ) -> None:
        """
        Set the autonomy level for a category.

        Args:
            category: Action category
            level: New autonomy level
        """
        old_level = self._autonomy_levels.get(category)
        self._autonomy_levels[category] = level

        logger.info(f"Autonomy level changed for {category.value}: {old_level} -> {level}")

    def set_override(
        self,
        action: str,
        level: AutonomyLevel,
    ) -> None:
        """
        Set a temporary override for a specific action.

        Args:
            action: Specific action name
            level: Override autonomy level
        """
        self._overrides[action] = level
        logger.info(f"Override set for {action}: {level}")

    def clear_override(self, action: str) -> bool:
        """
        Clear an override for a specific action.

        Args:
            action: Action name

        Returns:
            True if override was cleared
        """
        if action in self._overrides:
            del self._overrides[action]
            return True
        return False

    def register_approval_callback(
        self,
        callback: Callable[[PendingApproval], None],
    ) -> None:
        """
        Register a callback for when approvals are requested.

        Args:
            callback: Function to call with PendingApproval
        """
        self._approval_callbacks.append(callback)

    def get_pending_approvals(self) -> List[PendingApproval]:
        """Get all pending approvals."""
        now = datetime.now(timezone.utc)
        pending = []

        for approval in self._pending_approvals.values():
            if approval.status == "pending":
                # Check expiration
                if approval.expires_at and now > approval.expires_at:
                    approval.status = "expired"
                else:
                    pending.append(approval)

        return pending

    def get_approval(self, approval_id: str) -> Optional[PendingApproval]:
        """Get a specific approval by ID."""
        return self._pending_approvals.get(approval_id)

    def get_action_log(
        self,
        limit: int = 100,
        category: Optional[ActionCategory] = None,
        since: Optional[datetime] = None,
    ) -> List[ActionLog]:
        """
        Get action log entries.

        Args:
            limit: Maximum entries to return
            category: Filter by category
            since: Filter by timestamp

        Returns:
            List of ActionLog entries
        """
        logs = self._action_log

        if category:
            logs = [l for l in logs if l.category == category]

        if since:
            logs = [l for l in logs if l.timestamp >= since]

        # Return most recent first
        return sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]

    def get_autonomy_levels(self) -> Dict[str, str]:
        """Get all current autonomy levels."""
        return {cat.value: level.value for cat, level in self._autonomy_levels.items()}

    async def get_stats(self) -> Dict[str, Any]:
        """Get autonomy controller statistics."""
        pending = self.get_pending_approvals()

        # Count by status
        status_counts = {"pending": 0, "approved": 0, "denied": 0, "expired": 0}
        for approval in self._pending_approvals.values():
            status_counts[approval.status] = status_counts.get(approval.status, 0) + 1

        # Count logged actions by category
        action_counts: Dict[str, int] = {}
        for log in self._action_log:
            cat = log.category.value
            action_counts[cat] = action_counts.get(cat, 0) + 1

        return {
            "pending_approvals": len(pending),
            "approval_status_counts": status_counts,
            "total_logged_actions": len(self._action_log),
            "actions_by_category": action_counts,
            "override_count": len(self._overrides),
            "autonomy_levels": self.get_autonomy_levels(),
        }

    def _infer_category(self, action: str) -> ActionCategory:
        """Infer action category from action name."""
        action_lower = action.lower()

        if "routing" in action_lower or "route" in action_lower:
            if "fallback" in action_lower:
                return ActionCategory.FALLBACK_ROUTING
            if "dynamic" in action_lower:
                return ActionCategory.DYNAMIC_ROUTING
            return ActionCategory.ROUTINE_ROUTING

        if "calibrat" in action_lower:
            return ActionCategory.CONFIDENCE_CALIBRATION

        if "pattern" in action_lower:
            if "deactivat" in action_lower or "disable" in action_lower:
                return ActionCategory.PATTERN_DEACTIVATION
            return ActionCategory.PATTERN_CREATION

        if "parameter" in action_lower or "param" in action_lower:
            if "system" in action_lower:
                return ActionCategory.SYSTEM_PARAMETER_CHANGE
            return ActionCategory.PARAMETER_TUNING

        if "handler" in action_lower:
            if "generat" in action_lower:
                return ActionCategory.HANDLER_GENERATION
            if "activat" in action_lower:
                return ActionCategory.HANDLER_ACTIVATION
            if "deprecat" in action_lower:
                return ActionCategory.HANDLER_DEPRECATION

        if "task" in action_lower:
            if "creat" in action_lower or "generat" in action_lower:
                return ActionCategory.PROACTIVE_TASK_CREATION
            if "cancel" in action_lower:
                return ActionCategory.TASK_CANCELLATION
            if "priority" in action_lower:
                return ActionCategory.TASK_PRIORITY_ADJUSTMENT

        if "experiment" in action_lower:
            if "start" in action_lower or "begin" in action_lower:
                return ActionCategory.EXPERIMENT_START
            return ActionCategory.EXPERIMENT_CONCLUSION

        if "workflow" in action_lower:
            return ActionCategory.WORKFLOW_MODIFICATION

        if "capabilit" in action_lower or "agent" in action_lower:
            return ActionCategory.AGENT_CAPABILITY_CHANGE

        # Default to requiring human approval for unknown actions
        return ActionCategory.SYSTEM_PARAMETER_CHANGE

    def _find_pending_approval(
        self,
        action: str,
        context: Optional[Dict[str, Any]],
    ) -> Optional[PendingApproval]:
        """Find a pending approval matching the action and context."""
        for approval in self._pending_approvals.values():
            if approval.action == action and approval.status in ("pending", "approved"):
                # Check expiration for pending
                if approval.status == "pending":
                    if approval.expires_at and datetime.now(timezone.utc) > approval.expires_at:
                        approval.status = "expired"
                        continue
                return approval
        return None

    async def _persist_approval(self, approval: PendingApproval) -> None:
        """Persist an approval to the database."""
        try:
            await self._db.execute(
                """
                INSERT INTO autonomy_approvals (
                    id, action, category, description, context_json,
                    impact_assessment, recommended_decision, status,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.id,
                    approval.action,
                    approval.category.value,
                    approval.description,
                    str(approval.context),
                    approval.impact_assessment,
                    approval.recommended_decision,
                    approval.status,
                    approval.created_at.isoformat(),
                    approval.expires_at.isoformat() if approval.expires_at else None,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist approval: {e}")

    async def _update_approval(self, approval: PendingApproval) -> None:
        """Update an approval in the database."""
        try:
            await self._db.execute(
                """
                UPDATE autonomy_approvals
                SET status = ?, decided_at = ?, decided_by = ?
                WHERE id = ?
                """,
                (
                    approval.status,
                    approval.decided_at.isoformat() if approval.decided_at else None,
                    approval.decided_by,
                    approval.id,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to update approval: {e}")

    async def _persist_log(self, log: ActionLog) -> None:
        """Persist an action log to the database."""
        try:
            await self._db.execute(
                """
                INSERT INTO autonomy_action_logs (
                    id, action, category, autonomy_level, description,
                    context_json, result_json, success, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.id,
                    log.action,
                    log.category.value,
                    log.autonomy_level.value,
                    log.description,
                    str(log.context),
                    str(log.result) if log.result else None,
                    log.success,
                    log.timestamp.isoformat(),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist action log: {e}")

    async def cleanup_expired_approvals(self) -> int:
        """
        Clean up expired approvals.

        Returns:
            Number of approvals cleaned up
        """
        now = datetime.now(timezone.utc)
        expired_count = 0

        for approval in self._pending_approvals.values():
            if approval.status == "pending":
                if approval.expires_at and now > approval.expires_at:
                    approval.status = "expired"
                    expired_count += 1

        return expired_count
