"""
ag3ntwerk Initialization Factory.

Centralized initialization for the ag3ntwerk system. This module provides a single
source of truth for:
- Overwatch (Overwatch) creation and configuration as internal coordinator
- Agent wiring (all 14 active agents to Overwatch)
- Learning system initialization and connection
- Proper hierarchy establishment
- Service bridge initialization for external services (Nexus, Forge, Sentinel)

The Overwatch (Overwatch / Overwatch) is the internal coordination layer that:
- Routes tasks to appropriate agents
- Detects drift and escalates to external Nexus (Nexus) when needed
- Manages workflows and operational metrics

The learning system is wired into Overwatch for cross-agent synthesis, but can
also be accessed by individual agents for their domain-specific learning.

Usage:
    ```python
    from ag3ntwerk.initialization import (
        initialize_system,
        AgentSystem,
    )

    # Full initialization with learning system
    system = await initialize_system(
        llm_provider=provider,
        db=database,
        task_queue=queue,
        enable_learning=True,
    )

    # Access components
    cos = system.cos  # or system.coo for backward compatibility
    orchestrator = system.learning_orchestrator

    # Execute tasks through Overwatch (learning is automatic)
    result = await cos.execute(task)

    # Get cross-agent insights from Overwatch
    insights = await cos.get_learning_insights()
    ```
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from ag3ntwerk.core.logging import get_logger

if TYPE_CHECKING:
    from ag3ntwerk.agents.overwatch import Overwatch
    from ag3ntwerk.llm.base import BaseLLMProvider
    from ag3ntwerk.learning.orchestrator import LearningOrchestrator
    from ag3ntwerk.persistence.database import Database

logger = get_logger(__name__)

# Agents to skip during auto-wiring
# Nexus: Now external service (use Overwatch for internal coordination)
# Overwatch: Is the internal coordinator, not a subordinate
SKIP_AGENTS: Set[str] = {"Nexus", "Overwatch"}

# All active agent codes (14 total)
ACTIVE_AGENTS: Set[str] = {
    "Beacon",  # Beacon (Beacon)
    "Forge",  # Forge (Forge)
    "Keystone",  # Keystone (Keystone)
    "Sentinel",  # Sentinel (Sentinel)
    "Compass",  # Compass (Compass)
    "Index",  # Index (Index)
    "Blueprint",  # Blueprint (Blueprint)
    "Echo",  # Echo (Echo)
    "Citadel",  # Citadel (Citadel)
    "Accord",  # Accord (Accord)
    "Foundry",  # Foundry (Foundry)
    "Aegis",  # Aegis (Aegis)
    "Axiom",  # Axiom (Axiom)
    "Vector",  # Vector (Vector)
}


@dataclass
class AgentSystem:
    """
    Container for initialized ag3ntwerk system components.

    The Overwatch (Overwatch) is the internal coordination layer. All task execution,
    routing decisions, and cross-agent synthesis flows through Overwatch.

    When drift is detected, Overwatch can escalate to the external Nexus (Nexus) service
    via the NexusBridge for strategic guidance.

    The learning orchestrator provides learning capabilities that are:
    1. Connected to Overwatch for cross-agent pattern synthesis
    2. Available to individual agents for domain-specific learning

    Attributes:
        cos: The Overwatch (Overwatch) - internal coordination layer
        learning_orchestrator: Learning system coordinator (optional)
        registered_executives: List of agent codes registered to Overwatch
        learning_enabled: Whether learning system is active
    """

    cos: "Overwatch"
    learning_orchestrator: Optional["LearningOrchestrator"] = None
    registered_executives: List[str] = field(default_factory=list)
    learning_enabled: bool = False

    @property
    def coo(self) -> "Overwatch":
        """Backward compatibility alias for cos."""
        return self.cos

    @property
    def executive_count(self) -> int:
        """Number of agents registered to Overwatch."""
        return len(self.registered_executives)

    def get_status(self) -> Dict[str, Any]:
        """Get system status summary."""
        return {
            "cos_ready": self.cos is not None,
            "coo_ready": self.cos is not None,  # backward compat
            "executives_registered": self.executive_count,
            "agent_codes": self.registered_executives,
            "learning_enabled": self.learning_enabled,
            "learning_orchestrator_ready": self.learning_orchestrator is not None,
        }


async def initialize_system(
    llm_provider: "BaseLLMProvider",
    db: Optional["Database"] = None,
    task_queue: Optional[Any] = None,
    enable_learning: bool = True,
    config: Optional[Dict[str, Any]] = None,
) -> AgentSystem:
    """
    Initialize the complete ag3ntwerk system.

    This is the single entry point for initializing the ag3ntwerk hierarchy with
    proper wiring of all agents and the learning system.

    The Overwatch (Overwatch) is established as the internal coordination layer:
    - All 14 active agents are registered as Overwatch subordinates
    - Task routing flows through Overwatch
    - Learning system connects to Overwatch for cross-agent synthesis
    - Overwatch synthesizes information across all agents for human consumption
    - Drift detection triggers escalation to external Nexus (Nexus) via bridges

    Args:
        llm_provider: Connected LLM provider for AI capabilities
        db: Database connection for persistence (required if enable_learning=True)
        task_queue: Task queue for async operations (required if enable_learning=True)
        enable_learning: Whether to initialize and connect the learning system
        config: Optional configuration overrides
            - enabled_agents: Set of agent codes to enable (default: all)
            - skip_executives: Additional agents to skip
            - learning_config: Configuration for learning system

    Returns:
        AgentSystem containing initialized components

    Raises:
        ValueError: If learning is enabled but db/task_queue not provided

    Example:
        ```python
        # Basic initialization
        system = await initialize_system(llm_provider=provider)

        # With learning system
        system = await initialize_system(
            llm_provider=provider,
            db=database,
            task_queue=queue,
            enable_learning=True,
        )

        # With custom configuration
        system = await initialize_system(
            llm_provider=provider,
            config={
                "enabled_agents": {"Forge", "Keystone", "Sentinel"},
                "learning_config": {"analysis_interval_seconds": 300},
            },
        )
        ```
    """
    config = config or {}

    # Validate learning requirements
    if enable_learning and (db is None or task_queue is None):
        logger.warning("Learning system requires db and task_queue. Disabling learning.")
        enable_learning = False

    # Import components
    from ag3ntwerk.agents.overwatch import Overwatch
    from ag3ntwerk.orchestration.registry import AgentRegistry

    # Initialize Overwatch - the internal coordination layer
    cos = Overwatch(llm_provider=llm_provider)
    logger.info("Overwatch (Overwatch) initialized as coordination layer")

    # Initialize registry for loading agents
    registry = AgentRegistry(llm_provider)

    # Determine which agents to wire
    enabled_agents = config.get("enabled_agents", ACTIVE_AGENTS)
    extra_skip = config.get("skip_executives", set())
    skip_set = SKIP_AGENTS | extra_skip

    # Wire all enabled agents to Overwatch
    registered = []
    for code in registry.get_available_codes():
        if code in skip_set:
            continue
        if enabled_agents and code not in enabled_agents:
            continue

        try:
            agent = registry.get(code)
            cos.register_subordinate(agent)
            registered.append(code)
            logger.debug(f"Registered {code} to Overwatch")
        except Exception as e:
            logger.warning(f"Could not register {code} to Overwatch: {e}")

    logger.info(f"Wired {len(registered)} agents to Overwatch: {', '.join(sorted(registered))}")

    # Initialize learning system if enabled
    learning_orchestrator = None
    if enable_learning:
        learning_orchestrator = await _initialize_learning_system(
            cos=cos,
            db=db,
            task_queue=task_queue,
            config=config.get("learning_config", {}),
        )

    return AgentSystem(
        cos=cos,
        learning_orchestrator=learning_orchestrator,
        registered_executives=registered,
        learning_enabled=enable_learning and learning_orchestrator is not None,
    )


async def _initialize_learning_system(
    cos: "Overwatch",
    db: "Database",
    task_queue: Any,
    config: Dict[str, Any],
) -> Optional["LearningOrchestrator"]:
    """
    Initialize and connect the learning system.

    The learning system is connected to Overwatch for:
    1. Recording task outcomes across the entire hierarchy
    2. Cross-agent pattern synthesis
    3. Routing optimization based on learned patterns
    4. Generating insights for human consumption

    Args:
        cos: The initialized Overwatch (Overwatch)
        db: Database for persistence
        task_queue: Task queue for async operations
        config: Learning-specific configuration

    Returns:
        Initialized LearningOrchestrator or None if initialization fails
    """
    try:
        from ag3ntwerk.learning import (
            initialize_learning_orchestrator,
        )

        # Initialize the learning orchestrator
        orchestrator = await initialize_learning_orchestrator(db, task_queue)

        # Connect to Overwatch - this enables:
        # - Automatic outcome recording
        # - Learning-informed routing
        # - Cross-agent synthesis
        await cos.connect_learning_system(orchestrator)

        logger.info(
            "Learning system initialized and connected to Overwatch",
            extra={"stats": await orchestrator.get_stats()},
        )

        return orchestrator

    except ImportError as e:
        logger.warning(f"Learning system not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize learning system: {e}")
        return None


def create_overwatch_with_agents(
    llm_provider: "BaseLLMProvider",
    enabled_agents: Optional[Set[str]] = None,
) -> "Overwatch":
    """
    Synchronous helper to create Overwatch with agents wired.

    Use this when you don't need the learning system but want proper
    agent wiring. For full initialization with learning, use
    `initialize_system()` instead.

    Args:
        llm_provider: Connected LLM provider
        enabled_agents: Optional set of agents to enable (default: all)

    Returns:
        Overwatch with all enabled agents registered as subordinates

    Example:
        ```python
        cos = create_overwatch_with_agents(provider)
        result = await cos.execute(task)
        ```
    """
    from ag3ntwerk.agents.overwatch import Overwatch
    from ag3ntwerk.orchestration.registry import AgentRegistry

    cos = Overwatch(llm_provider=llm_provider)
    registry = AgentRegistry(llm_provider)

    enabled = enabled_agents or ACTIVE_AGENTS

    for code in registry.get_available_codes():
        if code in SKIP_AGENTS:
            continue
        if code not in enabled:
            continue

        try:
            agent = registry.get(code)
            cos.register_subordinate(agent)
        except Exception as e:
            logger.warning(f"Could not register {code}: {e}")

    return cos
