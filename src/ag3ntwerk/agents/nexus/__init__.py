"""
Nexus - Deprecated Compatibility Shim.

DEPRECATION NOTICE:
-------------------
This module is deprecated. The Nexus functionality has been fully consolidated
into the Overwatch (Overwatch) module at ``ag3ntwerk.agents.overwatch``.

The Nexus class is now a thin alias for Overwatch. Please update your imports:

    # Old (deprecated):
    from ag3ntwerk.agents.nexus import Nexus

    # New (recommended):
    from ag3ntwerk.agents.overwatch import Overwatch

The true Nexus (AutonomousCOO / Nexus) is implemented as an external
strategic service that provides guidance to Overwatch via the NexusBridge.
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "ag3ntwerk.agents.nexus is deprecated. Use ag3ntwerk.agents.overwatch instead. "
    "Nexus is now an alias for Overwatch (Overwatch).",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export Overwatch as Nexus for backward compatibility
from ag3ntwerk.agents.overwatch import Overwatch as Nexus

# Codename alias for product narrative
Nexus = Nexus

# Re-export all public API from cos for backward compatibility
from ag3ntwerk.agents.overwatch import (
    # Managers
    WorkflowManager,
    TaskRoutingManager,
    ProcessManager,
    CoordinationManager,
    # Specialists
    WorkflowDesigner,
    TaskAnalyst,
    MetricsAnalyst,
    ProcessEngineer,
    OKRCoordinator,
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
    # Main agent (deprecated, use Overwatch instead)
    "Nexus",
    "Nexus",
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
