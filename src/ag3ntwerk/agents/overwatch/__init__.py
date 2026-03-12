"""Overwatch - Coordination and Execution Layer.

The Overwatch (Overwatch) is the executor/coordinator that manages workflows,
routing, and health tracking. It operates under strategic guidance from
the external Nexus (Nexus) and handles day-to-day task coordination.

Example:
    ```python
    from ag3ntwerk.agents.overwatch import Overwatch

    # Basic usage
    cos = Overwatch()

    # With Nexus connection
    cos = Overwatch()
    await cos.connect_to_nexus("redis://localhost:6379")
    ```
"""

from ag3ntwerk.agents.overwatch.agent import Overwatch

# Codename alias for product narrative
Overwatch = Overwatch

# Nexus Bridge (optional, for strategic Nexus communication)
try:
    from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig

    NEXUS_BRIDGE_AVAILABLE = True
except ImportError:
    NEXUS_BRIDGE_AVAILABLE = False
    NexusBridge = None
    NexusBridgeConfig = None

# Managers
from ag3ntwerk.agents.overwatch.managers import (
    WorkflowManager,
    TaskRoutingManager,
    ProcessManager,
    CoordinationManager,
)

# Specialists
from ag3ntwerk.agents.overwatch.specialists import (
    WorkflowDesigner,
    TaskAnalyst,
    MetricsAnalyst,
    ProcessEngineer,
    OKRCoordinator,
)

# Models
from ag3ntwerk.agents.overwatch.models import (
    # Enums
    WorkflowStatus,
    TaskRoutingStrategy,
    ExecutionMode,
    OperationalHealth,
    ProcessStatus,
    OKRStatus,
    EfficiencyLevel,
    DelegationResult,
    # Dataclasses
    WorkflowStep,
    Workflow,
    TaskDelegation,
    RoutingRule,
    OperationalMetrics,
    ExecutiveStatus,
    BusinessProcess,
    OKR,
    CrossFunctionalProject,
    OperatingCadence,
    VendorOperation,
    DeliveryReliability,
    SystemHealthCheck,
    # Drift Detection
    DriftType,
    DriftSignal,
    StrategicContext,
    # Capabilities
    ORCHESTRATION_CAPABILITIES,
)

__all__ = [
    # Main coordinator
    "Overwatch",
    "Overwatch",
    # Nexus Bridge (optional)
    "NexusBridge",
    "NexusBridgeConfig",
    "NEXUS_BRIDGE_AVAILABLE",
    # Managers
    "WorkflowManager",
    "TaskRoutingManager",
    "ProcessManager",
    "CoordinationManager",
    # Specialists
    "WorkflowDesigner",
    "TaskAnalyst",
    "MetricsAnalyst",
    "ProcessEngineer",
    "OKRCoordinator",
    # Enums
    "WorkflowStatus",
    "TaskRoutingStrategy",
    "ExecutionMode",
    "OperationalHealth",
    "ProcessStatus",
    "OKRStatus",
    "EfficiencyLevel",
    "DelegationResult",
    # Dataclasses
    "WorkflowStep",
    "Workflow",
    "TaskDelegation",
    "RoutingRule",
    "OperationalMetrics",
    "ExecutiveStatus",
    "BusinessProcess",
    "OKR",
    "CrossFunctionalProject",
    "OperatingCadence",
    "VendorOperation",
    "DeliveryReliability",
    "SystemHealthCheck",
    # Drift Detection
    "DriftType",
    "DriftSignal",
    "StrategicContext",
    # Capabilities
    "ORCHESTRATION_CAPABILITIES",
]
