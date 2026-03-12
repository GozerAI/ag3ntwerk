"""
Nexus Bridge - Integration between ag3ntwerk Nexus and Nexus systems.

This module provides a bridge connecting ag3ntwerk's Nexus (Nexus) to the
Nexus platform's intelligent systems:
- Priority Engine for intelligent task prioritization
- Learning System for historical outcome-based optimization
- Content Library for cross-agent content management

Features:
- Priority-based task ordering for Nexus delegation
- Learning from task outcomes to improve routing
- Executor performance tracking and optimization
- Context-aware prioritization
- Content management across agents (Echo, Forge, Blueprint, etc.)
- Agent-specific content domains
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Content Domain for Agents
# =============================================================================


class ExecutiveContentDomain(Enum):
    """Content domains owned by different agents."""

    Echo = "marketing"  # Marketing, brand, campaigns
    Forge = "technical"  # Technical docs, architecture, code
    Keystone = "financial"  # Financial reports, budgets
    Blueprint = "product"  # Product specs, features, roadmaps
    Nexus = "operational"  # Processes, workflows, SOPs
    Axiom = "revenue"  # Sales, revenue, pricing
    Compass = "security"  # Security policies, compliance
    Index = "data"  # Data governance, analytics
    GENERAL = "general"  # Cross-functional content


@dataclass
class ExecutiveContent:
    """Content item with agent context."""

    content_id: str
    title: str
    domain: ExecutiveContentDomain
    owner_executive: str
    content_type: str
    topics: List[str] = field(default_factory=list)
    quality_score: float = 0.8
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentRequest:
    """Request for content from an agent."""

    request_id: str
    requester: str  # Agent code requesting
    domain: ExecutiveContentDomain
    content_type: str
    topic: str
    difficulty: str = "intermediate"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskOutcome:
    """Outcome of a task execution for learning."""

    task_id: str
    task_type: str
    executor: str
    success: bool
    duration_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PrioritizedTask:
    """A task with priority information from Nexus."""

    task_id: str
    task_type: str
    priority_score: float
    urgency_score: float = 0.0
    value_score: float = 0.0
    learning_score: float = 0.0
    recommended_executor: Optional[str] = None
    reasoning: str = ""


class NexusBridge:
    """
    Bridge between ag3ntwerk Nexus and Nexus intelligent systems.

    This bridge enables Nexus to leverage:
    1. Priority Engine - For intelligent task ordering
    2. Learning System - For outcome-based optimization
    3. Content Library - For cross-agent content management

    Usage:
        bridge = NexusBridge()
        bridge.connect_nexus(priority_engine, learning_system)
        bridge.connect_content_library(content_library)

        # Prioritize tasks
        ordered = await bridge.prioritize_tasks(pending_tasks)

        # Record outcome for learning
        bridge.record_outcome(task_id, "Forge", success=True, duration_ms=1500)

        # Get executor recommendations
        best_exec = bridge.get_best_executor("code_review")

        # Content operations
        content = await bridge.create_executive_content(
            agent="Echo",
            content_type="concept",
            topic="Brand Guidelines"
        )
        related = bridge.get_content_for_executive("Forge", topic="API")
    """

    def __init__(
        self,
        coo: Optional[Any] = None,
        priority_engine: Optional[Any] = None,
        learning_system: Optional[Any] = None,
        content_library: Optional[Any] = None,
    ):
        """
        Initialize the Nexus bridge.

        Args:
            coo: Optional ag3ntwerk Nexus instance
            priority_engine: Optional Nexus PriorityEngine
            learning_system: Optional PersistentLearning system
            content_library: Optional Nexus ContentLibrary
        """
        self._coo = coo
        self._priority_engine = priority_engine
        self._learning_system = learning_system
        self._content_library = content_library

        # Outcome tracking
        self._outcomes: List[TaskOutcome] = []
        self._max_outcomes = 10000

        # Executor performance cache
        self._executor_stats: Dict[str, Dict[str, Any]] = {}

        # Task type to executor success mapping
        self._task_executor_success: Dict[str, Dict[str, float]] = {}

        # Agent to content domain mapping
        self._executive_domains: Dict[str, ExecutiveContentDomain] = {
            "Echo": ExecutiveContentDomain.Echo,
            "Forge": ExecutiveContentDomain.Forge,
            "Keystone": ExecutiveContentDomain.Keystone,
            "Blueprint": ExecutiveContentDomain.Blueprint,
            "Nexus": ExecutiveContentDomain.Nexus,
            "Axiom": ExecutiveContentDomain.Axiom,
            "Compass": ExecutiveContentDomain.Compass,
            "Index": ExecutiveContentDomain.Index,
        }

        # Content request tracking
        self._content_requests: List[ContentRequest] = []

        logger.info("NexusBridge initialized")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Nexus systems."""
        return (
            self._priority_engine is not None
            or self._learning_system is not None
            or self._content_library is not None
        )

    @property
    def has_content_library(self) -> bool:
        """Check if Content Library is connected."""
        return self._content_library is not None

    @property
    def content_library(self) -> Optional[Any]:
        """Get the connected Content Library."""
        return self._content_library

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        content_stats = {}
        if self._content_library:
            try:
                content_stats = self._content_library.get_library_statistics()
            except Exception as e:
                logger.debug("Failed to get content library stats: %s", e)
                content_stats = {"error": "Failed to get content stats"}

        return {
            "priority_engine_connected": self._priority_engine is not None,
            "learning_system_connected": self._learning_system is not None,
            "content_library_connected": self._content_library is not None,
            "coo_connected": self._coo is not None,
            "total_outcomes_recorded": len(self._outcomes),
            "executors_tracked": len(self._executor_stats),
            "task_types_tracked": len(self._task_executor_success),
            "content_requests_tracked": len(self._content_requests),
            "content_library_stats": content_stats,
        }

    def connect_nexus(
        self,
        priority_engine: Optional[Any] = None,
        learning_system: Optional[Any] = None,
        content_library: Optional[Any] = None,
    ) -> None:
        """Connect Nexus systems."""
        if priority_engine:
            self._priority_engine = priority_engine
            logger.info("Connected Priority Engine to bridge")
        if learning_system:
            self._learning_system = learning_system
            # Also wire learning to priority engine if both present
            if self._priority_engine:
                self._priority_engine.set_learning_system(learning_system)
            logger.info("Connected Learning System to bridge")
        if content_library:
            self._content_library = content_library
            logger.info("Connected Content Library to bridge")

    def connect_content_library(self, content_library: Any) -> None:
        """
        Connect Content Library to the bridge.

        Args:
            content_library: Nexus ContentLibrary instance
        """
        self._content_library = content_library
        logger.info("Connected Content Library to bridge")

    def connect_coo(self, coo: Any) -> None:
        """Connect ag3ntwerk Nexus."""
        self._coo = coo
        logger.info("Connected ag3ntwerk Nexus to bridge")

    async def prioritize_tasks(
        self,
        tasks: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PrioritizedTask]:
        """
        Prioritize tasks using Nexus Priority Engine.

        Args:
            tasks: List of tasks to prioritize
            context: Optional context for prioritization

        Returns:
            List of PrioritizedTask sorted by priority (highest first)
        """
        if not tasks:
            return []

        prioritized = []

        # Use Priority Engine if available
        if self._priority_engine:
            try:
                pe_context = {
                    "tasks": tasks,
                    **(context or {}),
                }
                pe_results = await self._priority_engine.prioritize(pe_context)

                for result in pe_results:
                    prioritized.append(
                        PrioritizedTask(
                            task_id=result.id,
                            task_type=getattr(result.item, "task_type", "unknown"),
                            priority_score=result.score.total_score,
                            urgency_score=result.score.factors.get("urgency", 0.0),
                            value_score=result.score.factors.get("value", 0.0),
                            learning_score=result.score.factors.get("learning", 0.0),
                            recommended_executor=result.executor_suggestion,
                            reasoning=result.score.reasoning,
                        )
                    )
            except Exception as e:
                logger.error(f"Priority Engine error: {e}")
                # Fall back to local prioritization
                prioritized = self._local_prioritize(tasks)
        else:
            # Local prioritization without Priority Engine
            prioritized = self._local_prioritize(tasks)

        # Sort by priority score (highest first)
        prioritized.sort(key=lambda p: p.priority_score, reverse=True)
        return prioritized

    def _local_prioritize(self, tasks: List[Any]) -> List[PrioritizedTask]:
        """Local prioritization when Priority Engine unavailable."""
        prioritized = []

        for task in tasks:
            task_id = getattr(task, "id", str(id(task)))
            task_type = getattr(task, "task_type", "unknown")
            priority = getattr(task, "priority", "medium")

            # Calculate scores based on local data
            priority_map = {
                "critical": 1.0,
                "high": 0.8,
                "medium": 0.5,
                "low": 0.3,
            }
            base_score = priority_map.get(str(priority).lower(), 0.5)

            # Add learning score from local cache
            learning_score = self._get_local_learning_score(task_type)

            # Get recommended executor
            recommended = self.get_best_executor(task_type)

            prioritized.append(
                PrioritizedTask(
                    task_id=task_id,
                    task_type=task_type,
                    priority_score=base_score * 0.8 + learning_score * 0.2,
                    urgency_score=base_score,
                    value_score=base_score,
                    learning_score=learning_score,
                    recommended_executor=recommended[0] if recommended else None,
                    reasoning=f"Priority: {priority}, Learning: {learning_score:.2f}",
                )
            )

        return prioritized

    def _get_local_learning_score(self, task_type: str) -> float:
        """Get learning score from local outcome history."""
        if task_type not in self._task_executor_success:
            return 0.5  # Default neutral score

        executor_scores = self._task_executor_success[task_type]
        if not executor_scores:
            return 0.5

        # Return best executor's success rate
        return max(executor_scores.values())

    def record_outcome(
        self,
        task_id: str,
        task_type: str,
        executor: str,
        success: bool,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record task outcome for learning.

        Args:
            task_id: Task identifier
            task_type: Type of task
            executor: Executor that handled the task
            success: Whether task succeeded
            duration_ms: Execution duration in milliseconds
            error: Error message if failed
            metadata: Additional metadata
        """
        outcome = TaskOutcome(
            task_id=task_id,
            task_type=task_type,
            executor=executor,
            success=success,
            duration_ms=duration_ms,
            error=error,
            metadata=metadata or {},
        )

        # Store outcome
        self._outcomes.append(outcome)
        if len(self._outcomes) > self._max_outcomes:
            self._outcomes = self._outcomes[-self._max_outcomes :]

        # Update executor stats
        self._update_executor_stats(executor, success, duration_ms)

        # Update task type -> executor success mapping
        self._update_task_executor_mapping(task_type, executor, success)

        # Send to Learning System if available
        if self._learning_system:
            try:
                self._learning_system.record_outcome(
                    task_id=task_id,
                    success=success,
                    executor=executor,
                    task_type=task_type,
                    duration_ms=duration_ms,
                    error=error,
                    metadata=metadata,
                )
            except Exception as e:
                logger.error(f"Failed to record outcome to Learning System: {e}")

        logger.debug(
            f"Recorded outcome: {task_type} by {executor} "
            f"({'success' if success else 'failed'})"
        )

    def _update_executor_stats(
        self,
        executor: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Update executor performance statistics."""
        if executor not in self._executor_stats:
            self._executor_stats[executor] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
            }

        stats = self._executor_stats[executor]
        stats["total_tasks"] += 1
        if success:
            stats["successful_tasks"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_tasks"]

    def _update_task_executor_mapping(
        self,
        task_type: str,
        executor: str,
        success: bool,
    ) -> None:
        """Update task type to executor success mapping."""
        if task_type not in self._task_executor_success:
            self._task_executor_success[task_type] = {}

        if executor not in self._task_executor_success[task_type]:
            self._task_executor_success[task_type][executor] = 0.5

        # Exponential moving average of success rate
        current = self._task_executor_success[task_type][executor]
        new_val = 1.0 if success else 0.0
        self._task_executor_success[task_type][executor] = 0.9 * current + 0.1 * new_val

    def get_best_executor(
        self,
        task_type: str,
        exclude: Optional[List[str]] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        Get the best executor for a task type based on historical performance.

        Args:
            task_type: Type of task
            exclude: Executors to exclude

        Returns:
            Tuple of (executor, success_rate) or None
        """
        exclude_set = set(exclude or [])

        # Try Learning System first
        if self._learning_system:
            try:
                result = self._learning_system.get_best_executor_for_task_type(task_type)
                if result:
                    exec_code, score = result
                    if exec_code not in exclude_set:
                        return (exec_code, score)
            except Exception as e:
                logger.debug(f"Learning System lookup failed: {e}")

        # Fall back to local data
        if task_type not in self._task_executor_success:
            return None

        executors = self._task_executor_success[task_type]
        best = None
        best_score = -1.0

        for executor, score in executors.items():
            if executor in exclude_set:
                continue
            if score > best_score:
                best = executor
                best_score = score

        return (best, best_score) if best else None

    def get_executor_stats(self, executor: str) -> Dict[str, Any]:
        """Get performance statistics for an executor."""
        if executor not in self._executor_stats:
            return {
                "executor": executor,
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
            }

        stats = self._executor_stats[executor]
        return {
            "executor": executor,
            "total_tasks": stats["total_tasks"],
            "success_rate": (
                stats["successful_tasks"] / stats["total_tasks"]
                if stats["total_tasks"] > 0
                else 0.0
            ),
            "avg_duration_ms": stats["avg_duration_ms"],
        }

    def get_all_executor_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all executors."""
        return {executor: self.get_executor_stats(executor) for executor in self._executor_stats}

    def get_task_type_performance(
        self,
        task_type: str,
    ) -> Dict[str, Any]:
        """Get performance data for a task type."""
        if task_type not in self._task_executor_success:
            return {
                "task_type": task_type,
                "executors": [],
                "best_executor": None,
            }

        executors = [
            {"executor": exe, "success_rate": rate}
            for exe, rate in self._task_executor_success[task_type].items()
        ]
        executors.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "task_type": task_type,
            "executors": executors,
            "best_executor": executors[0]["executor"] if executors else None,
        }

    async def get_learning_insights(
        self,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get learning insights from Nexus systems.

        Args:
            task_type: Optional task type filter

        Returns:
            Learning insights and recommendations
        """
        insights = {
            "available": self._learning_system is not None,
            "task_type": task_type,
            "local_data": True,
        }

        # Local insights
        if task_type:
            performance = self.get_task_type_performance(task_type)
            insights["performance"] = performance
        else:
            insights["executor_stats"] = self.get_all_executor_stats()
            insights["task_types"] = list(self._task_executor_success.keys())

        # Nexus Learning System insights
        if self._learning_system and task_type:
            try:
                similar = await self._learning_system.get_similar_outcomes(
                    task_type=task_type,
                    limit=10,
                )
                insights["similar_outcomes"] = len(similar)
                insights["success_count"] = sum(1 for o in similar if o.get("success", False))
            except Exception as e:
                logger.debug(f"Learning System insights error: {e}")

        return insights

    def clear_learning_cache(self) -> None:
        """Clear learning caches."""
        self._task_executor_success.clear()
        if self._priority_engine:
            self._priority_engine.clear_learning_cache()
        logger.info("Cleared learning caches")

    def reset_stats(self, executor: Optional[str] = None) -> None:
        """Reset performance statistics."""
        if executor:
            self._executor_stats.pop(executor, None)
        else:
            self._executor_stats.clear()
        logger.info(f"Reset stats for {'all executors' if not executor else executor}")

    # =========================================================================
    # Content Library Integration
    # =========================================================================

    def _get_content_enums(self) -> Tuple[Any, Any]:
        """
        Get ContentType and DifficultyLevel enums.

        Tries multiple import paths for flexibility.

        Returns:
            Tuple of (ContentType, DifficultyLevel) enums
        """
        # Try standard import paths
        try:
            from nexus.rag.content_library import ContentType, DifficultyLevel

            return ContentType, DifficultyLevel
        except ImportError:
            pass

        try:
            from nexus.rag.content_library.models import ContentType, DifficultyLevel

            return ContentType, DifficultyLevel
        except ImportError:
            pass

        # Fallback: access from library's storage module if available
        if self._content_library:
            try:
                # Get from the models module
                import importlib

                models = importlib.import_module(
                    self._content_library.__class__.__module__.rsplit(".", 1)[0] + ".models"
                )
                return models.ContentType, models.DifficultyLevel
            except (ImportError, AttributeError):
                pass

        # Last resort: create minimal enum-like classes
        from enum import Enum

        class ContentType(Enum):
            CONCEPT = "concept"
            PROCEDURE = "procedure"
            FACT = "fact"
            EXERCISE = "exercise"
            ASSESSMENT = "assessment"

        class DifficultyLevel(Enum):
            NOVICE = "novice"
            BEGINNER = "beginner"
            INTERMEDIATE = "intermediate"
            ADVANCED = "advanced"
            EXPERT = "expert"

        return ContentType, DifficultyLevel

    def _get_content_builder(self) -> Any:
        """Get ContentBuilder class."""
        try:
            from nexus.rag.content_library import ContentBuilder

            return ContentBuilder
        except ImportError:
            pass

        try:
            from nexus.rag.content_library.templates import ContentBuilder

            return ContentBuilder
        except ImportError:
            pass

        if self._content_library:
            try:
                import importlib

                templates = importlib.import_module(
                    self._content_library.__class__.__module__.rsplit(".", 1)[0] + ".templates"
                )
                return templates.ContentBuilder
            except (ImportError, AttributeError):
                pass

        return None

    def _get_interaction_type(self) -> Any:
        """Get InteractionType enum."""
        try:
            from nexus.rag.content_library import InteractionType

            return InteractionType
        except ImportError:
            pass

        try:
            from nexus.rag.content_library.models import InteractionType

            return InteractionType
        except ImportError:
            pass

        if self._content_library:
            try:
                import importlib

                models = importlib.import_module(
                    self._content_library.__class__.__module__.rsplit(".", 1)[0] + ".models"
                )
                return models.InteractionType
            except (ImportError, AttributeError):
                pass

        # Fallback
        from enum import Enum

        class InteractionType(Enum):
            VIEW = "view"
            COMPLETE = "complete"
            SKIP = "skip"
            BOOKMARK = "bookmark"
            RATE = "rate"
            FEEDBACK = "feedback"

        return InteractionType

    def _get_content_filters(self) -> Any:
        """Get ContentFilters class."""
        try:
            from nexus.rag.content_library import ContentFilters

            return ContentFilters
        except ImportError:
            pass

        try:
            from nexus.rag.content_library.models import ContentFilters

            return ContentFilters
        except ImportError:
            pass

        if self._content_library:
            try:
                import importlib

                models = importlib.import_module(
                    self._content_library.__class__.__module__.rsplit(".", 1)[0] + ".models"
                )
                return models.ContentFilters
            except (ImportError, AttributeError):
                pass

        return None

    def get_agent_domain(self, agent: str) -> ExecutiveContentDomain:
        """
        Get the content domain for an agent.

        Args:
            agent: Agent code (e.g., "Echo", "Forge")

        Returns:
            ExecutiveContentDomain for the agent
        """
        # Case-insensitive lookup: try exact match first, then title-case
        result = self._executive_domains.get(agent)
        if result is None:
            result = self._executive_domains.get(agent.strip().title())
        return result if result is not None else ExecutiveContentDomain.GENERAL

    async def create_executive_content(
        self,
        agent: str,
        content_type: str,
        topic: str,
        difficulty: str = "intermediate",
        auto_save: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExecutiveContent]:
        """
        Create content for an agent using the Content Library.

        Args:
            agent: Agent code (e.g., "Echo", "Forge")
            content_type: Type of content (concept, procedure, exercise, etc.)
            topic: Topic for the content
            difficulty: Difficulty level
            auto_save: Whether to save to Content Library
            metadata: Additional metadata

        Returns:
            ExecutiveContent or None if Content Library not connected
        """
        if not self._content_library:
            logger.warning("Content Library not connected")
            return None

        domain = self.get_agent_domain(agent)

        # Track the request
        request = ContentRequest(
            request_id=str(UUID(int=0)),  # Will be replaced
            requester=agent,
            domain=domain,
            content_type=content_type,
            topic=topic,
            difficulty=difficulty,
            metadata=metadata or {},
        )
        self._content_requests.append(request)

        try:
            # Get enums from the library's module
            ContentType, DifficultyLevel = self._get_content_enums()

            # Map content type string to enum
            content_type_map = {
                "concept": ContentType.CONCEPT,
                "procedure": ContentType.PROCEDURE,
                "exercise": ContentType.EXERCISE,
                "assessment": ContentType.ASSESSMENT,
                "fact": ContentType.FACT,
            }
            ct_enum = content_type_map.get(content_type.lower(), ContentType.CONCEPT)

            difficulty_map = {
                "novice": DifficultyLevel.NOVICE,
                "beginner": DifficultyLevel.BEGINNER,
                "intermediate": DifficultyLevel.INTERMEDIATE,
                "advanced": DifficultyLevel.ADVANCED,
                "expert": DifficultyLevel.EXPERT,
            }
            diff_enum = difficulty_map.get(difficulty.lower(), DifficultyLevel.INTERMEDIATE)

            # Generate content
            result = await self._content_library.generate_content(
                content_type=ct_enum,
                topic=topic,
                difficulty=diff_enum,
                auto_save=auto_save,
            )

            if result.success and result.content:
                # Add agent metadata
                result.content.metadata["agent"] = agent
                result.content.metadata["domain"] = domain.value
                result.content.tags.append(f"agent:{agent.lower()}")
                result.content.tags.append(f"domain:{domain.value}")

                # Update in library
                if auto_save:
                    self._content_library.update_content(
                        result.content.content_id,
                        {"metadata": result.content.metadata, "tags": result.content.tags},
                    )

                return ExecutiveContent(
                    content_id=result.content.content_id,
                    title=result.content.title,
                    domain=domain,
                    owner_executive=agent,
                    content_type=content_type,
                    topics=result.content.topics,
                    quality_score=result.content.quality_metrics.quality_score,
                    metadata=result.content.metadata,
                )

            logger.warning(f"Content generation failed: {result.error}")
            return None

        except Exception as e:
            logger.error(f"Error creating agent content: {e}")
            return None

    def store_executive_content(
        self,
        agent: str,
        title: str,
        body: str,
        content_type: str = "concept",
        topics: Optional[List[str]] = None,
        difficulty: str = "intermediate",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store manually created content for an agent.

        Args:
            agent: Agent code
            title: Content title
            body: Content body
            content_type: Type of content
            topics: List of topics
            difficulty: Difficulty level
            metadata: Additional metadata

        Returns:
            Content ID or None if failed
        """
        if not self._content_library:
            logger.warning("Content Library not connected")
            return None

        domain = self.get_agent_domain(agent)

        try:
            ContentBuilder = self._get_content_builder()
            if not ContentBuilder:
                logger.error("ContentBuilder not available")
                return None

            _, DifficultyLevel = self._get_content_enums()

            difficulty_map = {
                "novice": DifficultyLevel.NOVICE,
                "beginner": DifficultyLevel.BEGINNER,
                "intermediate": DifficultyLevel.INTERMEDIATE,
                "advanced": DifficultyLevel.ADVANCED,
                "expert": DifficultyLevel.EXPERT,
            }
            diff_enum = difficulty_map.get(difficulty.lower(), DifficultyLevel.INTERMEDIATE)

            # Build content
            builder = ContentBuilder()
            content = (
                builder.with_title(title)
                .with_body(body)
                .with_topics(topics or [])
                .with_difficulty(diff_enum)
                .with_tags(
                    [
                        f"agent:{agent.lower()}",
                        f"domain:{domain.value}",
                        content_type.lower(),
                    ]
                )
                .build()
            )

            # Add agent metadata
            content.metadata = {
                **(metadata or {}),
                "agent": agent,
                "domain": domain.value,
            }

            # Store in library
            created = self._content_library.create_content(content)
            logger.info(f"Stored content for {agent}: {created.content_id}")
            return created.content_id

        except Exception as e:
            logger.error(f"Error storing agent content: {e}")
            return None

    def get_content_for_executive(
        self,
        agent: str,
        topic: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[ExecutiveContent]:
        """
        Get content relevant to an agent.

        Args:
            agent: Agent code
            topic: Optional topic filter
            content_type: Optional content type filter
            limit: Maximum results

        Returns:
            List of ExecutiveContent
        """
        if not self._content_library:
            return []

        domain = self.get_agent_domain(agent)

        try:
            ContentFilters = self._get_content_filters()

            # Build filters
            tags = [f"domain:{domain.value}"]
            if content_type:
                tags.append(content_type.lower())

            filters = None
            if ContentFilters:
                filters = ContentFilters(
                    tags=tags,
                    topics=[topic] if topic else None,
                    limit=limit,
                )

            # Search content
            if topic:
                results = self._content_library.search_content(topic, filters)
            else:
                results = self._content_library.list_content(filters, limit=limit)

            # Convert to ExecutiveContent
            executive_content = []
            for content in results:
                exec_content = ExecutiveContent(
                    content_id=content.content_id,
                    title=content.title,
                    domain=domain,
                    owner_executive=content.metadata.get("agent", agent),
                    content_type=content.content_type.value,
                    topics=content.topics,
                    quality_score=content.quality_metrics.quality_score,
                    created_at=content.created_at,
                    metadata=content.metadata,
                )
                executive_content.append(exec_content)

            return executive_content

        except Exception as e:
            logger.error(f"Error getting agent content: {e}")
            return []

    def get_cross_executive_content(
        self,
        topics: List[str],
        agents: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, List[ExecutiveContent]]:
        """
        Get content across multiple agents for given topics.

        Args:
            topics: Topics to search
            agents: Optional list of agents to include
            limit: Maximum results per agent

        Returns:
            Dict mapping agent to their relevant content
        """
        if not self._content_library:
            return {}

        agents = agents or list(self._executive_domains.keys())
        result: Dict[str, List[ExecutiveContent]] = {}

        for agent in agents:
            exec_content = []
            for topic in topics:
                content = self.get_content_for_executive(
                    agent,
                    topic=topic,
                    limit=limit // len(topics) if topics else limit,
                )
                exec_content.extend(content)

            # Deduplicate by content_id
            seen_ids: Set[str] = set()
            unique_content = []
            for c in exec_content:
                if c.content_id not in seen_ids:
                    seen_ids.add(c.content_id)
                    unique_content.append(c)

            if unique_content:
                result[agent] = unique_content[:limit]

        return result

    def get_content_by_id(self, content_id: str) -> Optional[Any]:
        """
        Get content by ID from the Content Library.

        Args:
            content_id: Content identifier

        Returns:
            ContentItem or None
        """
        if not self._content_library:
            return None
        return self._content_library.get_content(content_id)

    def update_content(
        self,
        content_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update content in the library.

        Args:
            content_id: Content identifier
            updates: Fields to update

        Returns:
            True if successful
        """
        if not self._content_library:
            return False

        try:
            result = self._content_library.update_content(content_id, updates)
            return result is not None
        except Exception as e:
            logger.error(f"Error updating content: {e}")
            return False

    def record_content_interaction(
        self,
        content_id: str,
        agent: str,
        interaction_type: str,
        duration_seconds: int = 0,
        performance_score: Optional[float] = None,
        feedback: Optional[str] = None,
    ) -> bool:
        """
        Record an agent's interaction with content.

        Args:
            content_id: Content identifier
            agent: Agent code
            interaction_type: Type of interaction (view, complete, rate, etc.)
            duration_seconds: Duration of interaction
            performance_score: Optional performance score
            feedback: Optional feedback text

        Returns:
            True if recorded successfully
        """
        if not self._content_library:
            return False

        try:
            InteractionType = self._get_interaction_type()

            interaction_map = {
                "view": InteractionType.VIEW,
                "complete": InteractionType.COMPLETE,
                "skip": InteractionType.SKIP,
                "bookmark": InteractionType.BOOKMARK,
                "rate": InteractionType.RATE,
                "feedback": InteractionType.FEEDBACK,
            }
            it_enum = interaction_map.get(interaction_type.lower(), InteractionType.VIEW)

            return self._content_library.record_content_interaction(
                content_id=content_id,
                user_id=f"agent:{agent}",
                interaction_type=it_enum,
                duration_seconds=duration_seconds,
                performance_score=performance_score,
                feedback=feedback,
            )
        except Exception as e:
            logger.error(f"Error recording content interaction: {e}")
            return False

    def get_content_analytics(
        self,
        agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get content analytics, optionally filtered by agent.

        Args:
            agent: Optional agent filter

        Returns:
            Analytics data
        """
        if not self._content_library:
            return {"error": "Content Library not connected"}

        try:
            stats = self._content_library.get_library_statistics()

            if agent:
                # Filter to agent's content
                content = self.get_content_for_executive(agent, limit=100)
                stats["agent"] = agent
                stats["executive_content_count"] = len(content)
                stats["executive_avg_quality"] = (
                    sum(c.quality_score for c in content) / len(content) if content else 0.0
                )

            return stats
        except Exception as e:
            logger.error(f"Error getting content analytics: {e}")
            return {"error": str(e)}

    def get_learning_path_for_executive(
        self,
        agent: str,
        target_topic: str,
    ) -> List[str]:
        """
        Get a learning path for an agent on a topic.

        Args:
            agent: Agent code
            target_topic: Target topic to learn

        Returns:
            Ordered list of content IDs forming the learning path
        """
        if not self._content_library:
            return []

        try:
            # Find content on the topic
            content = self.get_content_for_executive(
                agent,
                topic=target_topic,
                limit=50,
            )

            if not content:
                return []

            # Get the most relevant content as target
            target_id = content[0].content_id

            # Get learning path from graph
            path = self._content_library.get_learning_path(target_id)

            if hasattr(path, "content_ids"):
                return path.content_ids
            elif isinstance(path, list):
                return path

            return [target_id]

        except Exception as e:
            logger.error(f"Error getting learning path: {e}")
            return []

    def get_content_requests_summary(self) -> Dict[str, Any]:
        """Get summary of content requests by agents."""
        by_executive: Dict[str, int] = {}
        by_domain: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for request in self._content_requests:
            by_executive[request.requester] = by_executive.get(request.requester, 0) + 1
            by_domain[request.domain.value] = by_domain.get(request.domain.value, 0) + 1
            by_type[request.content_type] = by_type.get(request.content_type, 0) + 1

        return {
            "total_requests": len(self._content_requests),
            "by_executive": by_executive,
            "by_domain": by_domain,
            "by_content_type": by_type,
        }

    # =========================================================================
    # Nexus Content Orchestration
    # =========================================================================

    def orchestrate_content_workflow(
        self,
        workflow_type: str,
        topic: str,
        agents: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrate a content workflow across multiple agents.

        Nexus coordinates content creation/review across agents.

        Args:
            workflow_type: Type of workflow (create, review, update, distribute)
            topic: Topic for the workflow
            agents: List of agents involved
            metadata: Additional workflow metadata

        Returns:
            Workflow status and assignments
        """
        # Use uuid4 for reliable unique IDs (hash can be negative which UUID rejects)
        from uuid import uuid4

        workflow_id = str(uuid4())

        # Determine responsibilities based on workflow type
        assignments: Dict[str, List[str]] = {}

        if workflow_type == "create":
            # Assign creation to domain experts
            for exec_code in agents:
                domain = self.get_agent_domain(exec_code)
                assignments[exec_code] = [
                    f"Create {domain.value} content for: {topic}",
                    f"Review related {domain.value} materials",
                ]

        elif workflow_type == "review":
            # Cross-agent review assignments
            for i, exec_code in enumerate(agents):
                reviewer = agents[(i + 1) % len(agents)]
                assignments[exec_code] = [
                    f"Review content from {reviewer}",
                    f"Provide feedback on {topic}",
                ]

        elif workflow_type == "update":
            # Update existing content
            for exec_code in agents:
                content = self.get_content_for_executive(exec_code, topic=topic, limit=5)
                if content:
                    assignments[exec_code] = [
                        f"Update {len(content)} content items for: {topic}",
                    ]

        elif workflow_type == "distribute":
            # Content distribution workflow
            source_exec = agents[0] if agents else "Nexus"
            for exec_code in agents[1:]:
                assignments[exec_code] = [
                    f"Review and adapt content from {source_exec}",
                    f"Localize for {self.get_agent_domain(exec_code).value} domain",
                ]

        return {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "topic": topic,
            "status": "initiated",
            "assignments": assignments,
            "executives_involved": agents,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

    def assign_content_to_executive(
        self,
        content_id: str,
        target_agent: str,
        assignment_type: str = "review",
        notes: Optional[str] = None,
    ) -> bool:
        """
        Assign content to an agent for action.

        Nexus can assign content from one domain to another agent.

        Args:
            content_id: Content to assign
            target_agent: Agent to assign to
            assignment_type: Type of assignment (review, update, adapt, approve)
            notes: Optional notes for the assignee

        Returns:
            True if assignment successful
        """
        if not self._content_library:
            return False

        content = self.get_content_by_id(content_id)
        if not content:
            logger.warning(f"Content not found: {content_id}")
            return False

        try:
            # Add assignment metadata
            assignments = content.metadata.get("assignments", [])
            assignments.append(
                {
                    "assigned_to": target_agent,
                    "assignment_type": assignment_type,
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                    "assigned_by": "Nexus",
                    "notes": notes,
                    "status": "pending",
                }
            )

            # Update content
            return self.update_content(
                content_id,
                {
                    "metadata": {
                        **content.metadata,
                        "assignments": assignments,
                        "last_assigned_to": target_agent,
                    }
                },
            )
        except Exception as e:
            logger.error(f"Error assigning content: {e}")
            return False

    def share_content_between_executives(
        self,
        content_id: str,
        source_executive: str,
        target_agents: List[str],
        share_type: str = "reference",
    ) -> Dict[str, bool]:
        """
        Share content from one agent to others.

        Args:
            content_id: Content to share
            source_executive: Agent sharing the content
            target_agents: Agents to share with
            share_type: Type of share (reference, copy, adapt)

        Returns:
            Dict mapping agent to share success
        """
        if not self._content_library:
            return {exec_code: False for exec_code in target_agents}

        content = self.get_content_by_id(content_id)
        if not content:
            return {exec_code: False for exec_code in target_agents}

        results: Dict[str, bool] = {}

        for target_exec in target_agents:
            try:
                if share_type == "reference":
                    # Just add reference tag
                    tags = list(content.tags)
                    tags.append(f"shared-with:{target_exec.lower()}")
                    self.update_content(content_id, {"tags": tags})
                    results[target_exec] = True

                elif share_type == "copy":
                    # Create a copy for the target agent
                    new_id = self.store_executive_content(
                        agent=target_exec,
                        title=f"{content.title} (from {source_executive})",
                        body=content.content_body,
                        content_type=content.content_type.value,
                        topics=content.topics,
                        metadata={
                            "copied_from": content_id,
                            "source_executive": source_executive,
                        },
                    )
                    results[target_exec] = new_id is not None

                elif share_type == "adapt":
                    # Create adapted version placeholder
                    new_id = self.store_executive_content(
                        agent=target_exec,
                        title=f"{content.title} (adapted for {target_exec})",
                        body=f"[Adapt from: {content_id}]\n\n{content.content_body}",
                        content_type=content.content_type.value,
                        topics=content.topics,
                        metadata={
                            "adapted_from": content_id,
                            "source_executive": source_executive,
                            "needs_adaptation": True,
                        },
                    )
                    results[target_exec] = new_id is not None

                else:
                    results[target_exec] = False

            except Exception as e:
                logger.error(f"Error sharing to {target_exec}: {e}")
                results[target_exec] = False

        return results

    def get_agent_content_dashboard(
        self,
        agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a content dashboard for Nexus oversight.

        Provides overview of content across all agents.

        Args:
            agent: Optional specific agent to focus on

        Returns:
            Dashboard data with content metrics per agent
        """
        dashboard: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agents": {},
            "summary": {
                "total_content": 0,
                "total_views": 0,
                "avg_quality": 0.0,
                "content_by_domain": {},
            },
        }

        executives_to_check = [agent] if agent else list(self._executive_domains.keys())

        quality_scores = []

        for exec_code in executives_to_check:
            content = self.get_content_for_executive(exec_code, limit=100)
            domain = self.get_agent_domain(exec_code)

            exec_data = {
                "domain": domain.value,
                "content_count": len(content),
                "avg_quality": (
                    sum(c.quality_score for c in content) / len(content) if content else 0.0
                ),
                "topics": list(set(topic for c in content for topic in c.topics))[:10],
                "recent_content": [
                    {"id": c.content_id, "title": c.title, "quality": c.quality_score}
                    for c in sorted(content, key=lambda x: x.created_at, reverse=True)[:5]
                ],
            }

            dashboard["agents"][exec_code] = exec_data
            dashboard["summary"]["total_content"] += len(content)

            if content:
                quality_scores.extend([c.quality_score for c in content])

            # Track by domain
            domain_key = domain.value
            dashboard["summary"]["content_by_domain"][domain_key] = dashboard["summary"][
                "content_by_domain"
            ].get(domain_key, 0) + len(content)

        if quality_scores:
            dashboard["summary"]["avg_quality"] = sum(quality_scores) / len(quality_scores)

        return dashboard

    def identify_content_gaps(
        self,
        topics: List[str],
    ) -> Dict[str, Any]:
        """
        Identify content gaps across agents for given topics.

        Nexus can use this to see where content is missing.

        Args:
            topics: Topics to check for gaps

        Returns:
            Gap analysis with recommendations
        """
        gaps: Dict[str, Any] = {
            "topics_analyzed": topics,
            "gaps_by_executive": {},
            "recommendations": [],
        }

        for exec_code in self._executive_domains.keys():
            exec_gaps = []
            for topic in topics:
                content = self.get_content_for_executive(exec_code, topic=topic, limit=10)
                if not content:
                    exec_gaps.append(topic)

            if exec_gaps:
                gaps["gaps_by_executive"][exec_code] = exec_gaps
                domain = self.get_agent_domain(exec_code)
                gaps["recommendations"].append(
                    {
                        "agent": exec_code,
                        "domain": domain.value,
                        "missing_topics": exec_gaps,
                        "action": f"Create {domain.value} content for: {', '.join(exec_gaps)}",
                    }
                )

        return gaps

    def get_content_quality_report(self) -> Dict[str, Any]:
        """
        Get a quality report for all agent content.

        Nexus oversight report for content quality.

        Returns:
            Quality report with issues and recommendations
        """
        report: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "by_executive": {},
            "low_quality_content": [],
            "high_quality_content": [],
            "recommendations": [],
        }

        LOW_QUALITY_THRESHOLD = 0.5
        HIGH_QUALITY_THRESHOLD = 0.85

        for exec_code in self._executive_domains.keys():
            content = self.get_content_for_executive(exec_code, limit=100)

            low_quality = [c for c in content if c.quality_score < LOW_QUALITY_THRESHOLD]
            high_quality = [c for c in content if c.quality_score >= HIGH_QUALITY_THRESHOLD]

            report["by_executive"][exec_code] = {
                "total": len(content),
                "low_quality_count": len(low_quality),
                "high_quality_count": len(high_quality),
                "avg_quality": (
                    sum(c.quality_score for c in content) / len(content) if content else 0.0
                ),
            }

            # Add to overall lists
            for c in low_quality:
                report["low_quality_content"].append(
                    {
                        "content_id": c.content_id,
                        "title": c.title,
                        "agent": exec_code,
                        "quality_score": c.quality_score,
                    }
                )

            for c in high_quality[:3]:  # Top 3 per agent
                report["high_quality_content"].append(
                    {
                        "content_id": c.content_id,
                        "title": c.title,
                        "agent": exec_code,
                        "quality_score": c.quality_score,
                    }
                )

            # Recommendations
            if len(low_quality) > len(content) * 0.3:
                report["recommendations"].append(
                    {
                        "agent": exec_code,
                        "issue": "High proportion of low-quality content",
                        "action": f"Review and improve {len(low_quality)} content items",
                    }
                )

        # Sort lists
        report["low_quality_content"].sort(key=lambda x: x["quality_score"])
        report["high_quality_content"].sort(key=lambda x: x["quality_score"], reverse=True)

        return report

    def delegate_content_creation(
        self,
        topic: str,
        target_agents: Optional[List[str]] = None,
        content_types: Optional[List[str]] = None,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """
        Nexus delegates content creation to appropriate agents.

        Automatically determines best agents for the topic.

        Args:
            topic: Topic for content creation
            target_agents: Specific agents (auto-select if None)
            content_types: Types of content to create
            priority: Task priority

        Returns:
            Delegation assignments
        """
        content_types = content_types or ["concept", "procedure"]

        # Auto-select agents based on topic if not specified
        if not target_agents:
            target_agents = self._select_executives_for_topic(topic)

        delegations = []

        for exec_code in target_agents:
            domain = self.get_agent_domain(exec_code)

            for content_type in content_types:
                delegation = {
                    "agent": exec_code,
                    "domain": domain.value,
                    "topic": topic,
                    "content_type": content_type,
                    "priority": priority,
                    "status": "assigned",
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                }
                delegations.append(delegation)

                # Track the request
                from uuid import uuid4

                self._content_requests.append(
                    ContentRequest(
                        request_id=str(uuid4()),
                        requester="Nexus",
                        domain=domain,
                        content_type=content_type,
                        topic=topic,
                        difficulty="intermediate",
                        metadata={"delegated_to": exec_code, "priority": priority},
                    )
                )

        return {
            "topic": topic,
            "priority": priority,
            "delegations": delegations,
            "total_assignments": len(delegations),
        }

    def _select_executives_for_topic(self, topic: str) -> List[str]:
        """
        Select appropriate agents for a topic based on keywords.

        Args:
            topic: Topic to analyze

        Returns:
            List of agent codes
        """
        topic_lower = topic.lower()

        # Keyword mapping to agents
        keyword_map = {
            "Echo": ["marketing", "brand", "campaign", "social", "content", "seo", "ads"],
            "Forge": ["api", "code", "architecture", "technical", "system", "software", "dev"],
            "Keystone": ["budget", "financial", "cost", "revenue", "profit", "accounting"],
            "Blueprint": ["product", "feature", "roadmap", "user", "ux", "requirements"],
            "Axiom": ["sales", "pricing", "deal", "customer", "conversion"],
            "Compass": ["security", "compliance", "risk", "audit", "policy"],
            "Index": ["data", "analytics", "metrics", "reporting", "dashboard"],
        }

        selected = []
        for exec_code, keywords in keyword_map.items():
            if any(kw in topic_lower for kw in keywords):
                selected.append(exec_code)

        # Default to Nexus domain if no match
        return selected if selected else ["Nexus"]

    def sync_content_across_domains(
        self,
        source_domain: str,
        target_domains: List[str],
        topics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Sync content knowledge across agent domains.

        Nexus ensures content consistency and sharing.

        Args:
            source_domain: Source domain to sync from
            target_domains: Target domains to sync to
            topics: Optional topic filter

        Returns:
            Sync results
        """
        # Find source agent
        source_exec = None
        for exec_code, domain in self._executive_domains.items():
            if domain.value == source_domain:
                source_exec = exec_code
                break

        if not source_exec:
            return {"error": f"Source domain not found: {source_domain}"}

        # Get source content
        source_content = self.get_content_for_executive(source_exec, limit=50)

        if topics:
            source_content = [
                c
                for c in source_content
                if any(t.lower() in [topic.lower() for topic in c.topics] for t in topics)
            ]

        sync_results = {
            "source_domain": source_domain,
            "source_executive": source_exec,
            "content_synced": len(source_content),
            "target_results": {},
        }

        # Find target agents
        for target_domain in target_domains:
            target_exec = None
            for exec_code, domain in self._executive_domains.items():
                if domain.value == target_domain:
                    target_exec = exec_code
                    break

            if not target_exec:
                sync_results["target_results"][target_domain] = {"error": "Domain not found"}
                continue

            # Share content
            shared_count = 0
            for content in source_content:
                result = self.share_content_between_executives(
                    content.content_id, source_exec, [target_exec], share_type="reference"
                )
                if result.get(target_exec, False):
                    shared_count += 1

            sync_results["target_results"][target_domain] = {
                "agent": target_exec,
                "content_shared": shared_count,
            }

        return sync_results
