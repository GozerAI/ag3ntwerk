"""
Service Adapter - Enables services to adapt based on learned patterns.

Allows services to:
- Query patterns relevant to their configuration
- Get recommended configuration adjustments
- Track configuration changes and their outcomes
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.learning.models import (
    PatternType,
    ScopeLevel,
    LearnedPattern,
)

if TYPE_CHECKING:
    from ag3ntwerk.learning.pattern_store import PatternStore
    from ag3ntwerk.learning.outcome_tracker import OutcomeTracker

logger = logging.getLogger(__name__)


class ConfigChangeType(Enum):
    """Types of configuration changes."""

    PARAMETER_UPDATE = "parameter_update"
    FEATURE_TOGGLE = "feature_toggle"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    RESOURCE_SCALING = "resource_scaling"
    BEHAVIOR_MODIFICATION = "behavior_modification"


class AdaptationStrategy(Enum):
    """Strategies for applying adaptations."""

    IMMEDIATE = "immediate"  # Apply immediately
    GRADUAL = "gradual"  # Roll out gradually
    EXPERIMENT = "experiment"  # Run as A/B experiment
    MANUAL = "manual"  # Require manual approval


@dataclass
class ConfigRecommendation:
    """
    A recommended configuration change based on learned patterns.
    """

    service_id: str
    parameter: str
    current_value: Any
    recommended_value: Any
    change_type: ConfigChangeType
    confidence: float
    reasoning: str
    expected_improvement: float
    patterns_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "parameter": self.parameter,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "change_type": self.change_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "expected_improvement": self.expected_improvement,
            "patterns_used": self.patterns_used,
        }


@dataclass
class ServiceConfig:
    """
    Configuration state for a service.
    """

    service_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active_recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "parameters": self.parameters,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
            "active_recommendations": self.active_recommendations,
        }


@dataclass
class ConfigChange:
    """
    Record of a configuration change.
    """

    id: str
    service_id: str
    parameter: str
    old_value: Any
    new_value: Any
    change_type: ConfigChangeType
    reason: str
    applied_at: datetime
    recommendation_id: Optional[str] = None
    success: Optional[bool] = None
    outcome_measured_at: Optional[datetime] = None
    outcome_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "parameter": self.parameter,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type.value,
            "reason": self.reason,
            "applied_at": self.applied_at.isoformat(),
            "recommendation_id": self.recommendation_id,
            "success": self.success,
            "outcome_measured_at": (
                self.outcome_measured_at.isoformat() if self.outcome_measured_at else None
            ),
            "outcome_metrics": self.outcome_metrics,
        }


class ServiceAdapter:
    """
    Adapter that enables services to adapt based on learned patterns.

    Provides:
    - Pattern-based configuration recommendations
    - Configuration change tracking
    - Outcome measurement for changes
    """

    # Virtual pattern type for configuration patterns
    CONFIG_PATTERN_TYPE = PatternType.CAPABILITY  # Reuse CAPABILITY for now

    def __init__(
        self,
        db: Any,
        pattern_store: "PatternStore",
        outcome_tracker: Optional["OutcomeTracker"] = None,
    ):
        """
        Initialize the service adapter.

        Args:
            db: Database connection
            pattern_store: PatternStore for querying patterns
            outcome_tracker: Optional OutcomeTracker for outcome recording
        """
        self._db = db
        self._pattern_store = pattern_store
        self._outcome_tracker = outcome_tracker

        # In-memory service configs
        self._service_configs: Dict[str, ServiceConfig] = {}

        # Configuration change history (in-memory, also persisted)
        self._change_history: List[ConfigChange] = []
        self._max_history_size = 1000

        # Pending recommendations
        self._pending_recommendations: Dict[str, ConfigRecommendation] = {}

    async def register_service(
        self,
        service_id: str,
        initial_config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServiceConfig:
        """
        Register a service for adaptation tracking.

        Args:
            service_id: Unique service identifier
            initial_config: Current service configuration
            metadata: Optional service metadata

        Returns:
            ServiceConfig for the service
        """
        config = ServiceConfig(
            service_id=service_id,
            parameters=initial_config,
            version=1,
            last_updated=datetime.now(timezone.utc),
        )
        self._service_configs[service_id] = config

        logger.info(f"Registered service for adaptation: {service_id}")
        return config

    async def get_service_config(self, service_id: str) -> Optional[ServiceConfig]:
        """Get the current configuration for a service."""
        return self._service_configs.get(service_id)

    async def update_service_config(
        self,
        service_id: str,
        updates: Dict[str, Any],
    ) -> ServiceConfig:
        """
        Update service configuration.

        Args:
            service_id: Service to update
            updates: Parameter updates

        Returns:
            Updated ServiceConfig
        """
        config = self._service_configs.get(service_id)
        if not config:
            # Auto-register if not registered
            config = await self.register_service(service_id, updates)
        else:
            config.parameters.update(updates)
            config.version += 1
            config.last_updated = datetime.now(timezone.utc)

        return config

    async def get_config_recommendations(
        self,
        service_id: str,
        min_confidence: float = 0.6,
    ) -> List[ConfigRecommendation]:
        """
        Get configuration recommendations for a service based on learned patterns.

        Args:
            service_id: Service to get recommendations for
            min_confidence: Minimum confidence threshold

        Returns:
            List of ConfigRecommendation
        """
        recommendations = []

        # Get current config
        config = self._service_configs.get(service_id)
        if not config:
            return recommendations

        # Get patterns for this service
        patterns = await self._pattern_store.get_patterns(
            scope_code=service_id,
            is_active=True,
        )

        # Also get patterns from similar services
        similar_patterns = await self._get_similar_service_patterns(service_id)
        patterns.extend(similar_patterns)

        # Analyze patterns for recommendations
        for pattern in patterns:
            if pattern.confidence < min_confidence:
                continue

            rec = self._analyze_pattern_for_recommendation(pattern, config)
            if rec:
                recommendations.append(rec)
                self._pending_recommendations[rec.parameter] = rec

        # Sort by confidence and expected improvement
        recommendations.sort(
            key=lambda r: (r.confidence, r.expected_improvement),
            reverse=True,
        )

        return recommendations

    async def apply_recommendation(
        self,
        service_id: str,
        recommendation: ConfigRecommendation,
        strategy: AdaptationStrategy = AdaptationStrategy.IMMEDIATE,
    ) -> ConfigChange:
        """
        Apply a configuration recommendation.

        Args:
            service_id: Service to update
            recommendation: Recommendation to apply
            strategy: How to apply the change

        Returns:
            ConfigChange record
        """
        import uuid

        config = self._service_configs.get(service_id)
        if not config:
            raise ValueError(f"Service {service_id} not registered")

        # Create change record
        change = ConfigChange(
            id=str(uuid.uuid4()),
            service_id=service_id,
            parameter=recommendation.parameter,
            old_value=config.parameters.get(recommendation.parameter),
            new_value=recommendation.recommended_value,
            change_type=recommendation.change_type,
            reason=recommendation.reasoning,
            applied_at=datetime.now(timezone.utc),
            recommendation_id=recommendation.parameter,  # Use parameter as ID
        )

        # Apply based on strategy
        if strategy == AdaptationStrategy.IMMEDIATE:
            config.parameters[recommendation.parameter] = recommendation.recommended_value
            config.version += 1
            config.last_updated = datetime.now(timezone.utc)
            logger.info(
                f"Applied config change for {service_id}: "
                f"{recommendation.parameter} = {recommendation.recommended_value}"
            )
        elif strategy == AdaptationStrategy.GRADUAL:
            # Would implement gradual rollout here
            logger.info(f"Scheduled gradual rollout for {service_id}: {recommendation.parameter}")
        elif strategy == AdaptationStrategy.EXPERIMENT:
            # Would set up A/B experiment here
            logger.info(f"Created experiment for {service_id}: {recommendation.parameter}")
        else:
            logger.info(f"Queued for manual approval: {service_id}: {recommendation.parameter}")

        # Record change
        self._change_history.append(change)
        if len(self._change_history) > self._max_history_size:
            self._change_history = self._change_history[-self._max_history_size :]

        # Persist change
        await self._persist_change(change)

        return change

    async def record_change_outcome(
        self,
        change_id: str,
        success: bool,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record the outcome of a configuration change.

        Args:
            change_id: ID of the change
            success: Whether the change was successful
            metrics: Optional outcome metrics
        """
        # Find change in history
        for change in self._change_history:
            if change.id == change_id:
                change.success = success
                change.outcome_measured_at = datetime.now(timezone.utc)
                change.outcome_metrics = metrics or {}

                # Update persisted record
                await self._update_change_outcome(change)

                # If successful, this could influence pattern confidence
                if success:
                    logger.info(f"Config change {change_id} succeeded with metrics: {metrics}")
                else:
                    logger.warning(f"Config change {change_id} failed: {metrics}")
                break

    async def get_change_history(
        self,
        service_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ConfigChange]:
        """
        Get configuration change history.

        Args:
            service_id: Optional filter by service
            limit: Max changes to return

        Returns:
            List of ConfigChange records
        """
        changes = self._change_history

        if service_id:
            changes = [c for c in changes if c.service_id == service_id]

        # Sort by most recent first
        changes = sorted(changes, key=lambda c: c.applied_at, reverse=True)

        return changes[:limit]

    async def get_adaptation_stats(
        self,
        service_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about adaptations.

        Args:
            service_id: Optional filter by service

        Returns:
            Statistics dictionary
        """
        changes = await self.get_change_history(service_id, limit=1000)

        if not changes:
            return {
                "total_changes": 0,
                "successful_changes": 0,
                "failed_changes": 0,
                "pending_changes": 0,
                "success_rate": 0.0,
            }

        total = len(changes)
        successful = sum(1 for c in changes if c.success is True)
        failed = sum(1 for c in changes if c.success is False)
        pending = sum(1 for c in changes if c.success is None)

        # Group by change type
        by_type: Dict[str, int] = {}
        for c in changes:
            type_name = c.change_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Group by service
        by_service: Dict[str, int] = {}
        for c in changes:
            by_service[c.service_id] = by_service.get(c.service_id, 0) + 1

        return {
            "total_changes": total,
            "successful_changes": successful,
            "failed_changes": failed,
            "pending_changes": pending,
            "success_rate": (
                successful / (successful + failed) if (successful + failed) > 0 else 0.0
            ),
            "by_type": by_type,
            "by_service": by_service,
        }

    async def rollback_change(
        self,
        change_id: str,
        reason: str = "Manual rollback",
    ) -> Optional[ConfigChange]:
        """
        Rollback a configuration change.

        Args:
            change_id: ID of the change to rollback
            reason: Reason for rollback

        Returns:
            New ConfigChange for the rollback, or None if not found
        """
        import uuid

        # Find original change
        original = None
        for change in self._change_history:
            if change.id == change_id:
                original = change
                break

        if not original:
            return None

        config = self._service_configs.get(original.service_id)
        if not config:
            return None

        # Create rollback change
        rollback = ConfigChange(
            id=str(uuid.uuid4()),
            service_id=original.service_id,
            parameter=original.parameter,
            old_value=original.new_value,
            new_value=original.old_value,
            change_type=original.change_type,
            reason=f"Rollback of {change_id}: {reason}",
            applied_at=datetime.now(timezone.utc),
        )

        # Apply rollback
        config.parameters[original.parameter] = original.old_value
        config.version += 1
        config.last_updated = datetime.now(timezone.utc)

        # Record
        self._change_history.append(rollback)
        await self._persist_change(rollback)

        logger.info(f"Rolled back change {change_id} for {original.service_id}")

        return rollback

    # Private methods

    async def _get_similar_service_patterns(
        self,
        service_id: str,
    ) -> List[LearnedPattern]:
        """Get patterns from similar services."""
        # This could be enhanced with actual service similarity analysis
        # For now, return empty list
        return []

    def _analyze_pattern_for_recommendation(
        self,
        pattern: LearnedPattern,
        config: ServiceConfig,
    ) -> Optional[ConfigRecommendation]:
        """
        Analyze a pattern to see if it suggests a configuration change.

        Args:
            pattern: Pattern to analyze
            config: Current service config

        Returns:
            ConfigRecommendation if applicable, None otherwise
        """
        # Parse pattern condition
        try:
            condition = json.loads(pattern.condition_json)
        except (json.JSONDecodeError, TypeError):
            return None

        # Look for parameter recommendations in pattern
        recommended_params = condition.get("recommended_params", {})
        if not recommended_params:
            return None

        # Check each recommended parameter
        for param, recommended_value in recommended_params.items():
            current_value = config.parameters.get(param)

            # Skip if already at recommended value
            if current_value == recommended_value:
                continue

            # Determine change type
            change_type = ConfigChangeType.PARAMETER_UPDATE
            if isinstance(recommended_value, bool):
                change_type = ConfigChangeType.FEATURE_TOGGLE
            elif param.endswith("_threshold") or param.endswith("_limit"):
                change_type = ConfigChangeType.THRESHOLD_ADJUSTMENT

            return ConfigRecommendation(
                service_id=config.service_id,
                parameter=param,
                current_value=current_value,
                recommended_value=recommended_value,
                change_type=change_type,
                confidence=pattern.confidence,
                reasoning=pattern.recommendation,
                expected_improvement=pattern.success_rate or 0.0,
                patterns_used=[pattern.id],
            )

        return None

    async def _persist_change(self, change: ConfigChange) -> None:
        """Persist a change to the database."""
        try:
            await self._db.execute(
                """
                INSERT INTO service_config_changes (
                    id, service_id, parameter, old_value, new_value,
                    change_type, reason, applied_at, recommendation_id,
                    success, outcome_measured_at, outcome_metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change.id,
                    change.service_id,
                    change.parameter,
                    json.dumps(change.old_value),
                    json.dumps(change.new_value),
                    change.change_type.value,
                    change.reason,
                    change.applied_at.isoformat(),
                    change.recommendation_id,
                    1 if change.success else 0 if change.success is False else None,
                    change.outcome_measured_at.isoformat() if change.outcome_measured_at else None,
                    json.dumps(change.outcome_metrics) if change.outcome_metrics else None,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to persist config change: {e}")

    async def _update_change_outcome(self, change: ConfigChange) -> None:
        """Update the outcome of a persisted change."""
        try:
            await self._db.execute(
                """
                UPDATE service_config_changes
                SET success = ?, outcome_measured_at = ?, outcome_metrics = ?
                WHERE id = ?
                """,
                (
                    1 if change.success else 0,
                    change.outcome_measured_at.isoformat() if change.outcome_measured_at else None,
                    json.dumps(change.outcome_metrics) if change.outcome_metrics else None,
                    change.id,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to update config change outcome: {e}")
