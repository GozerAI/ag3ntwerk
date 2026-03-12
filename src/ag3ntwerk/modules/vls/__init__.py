"""
Vertical Launch System (VLS) Module.

Autonomous vertical discovery and monetization pipeline with
evidence-based gating and hard stage transitions.

## Overview

The VLS enables the ag3ntwerk system to autonomously:
1. Identify viable market niches (Market Intelligence)
2. Validate economic feasibility (Validation & Economics)
3. Define launch specifications (Blueprint Definition)
4. Build and deploy infrastructure (Build & Deployment)
5. Configure lead intake systems (Lead Intake)
6. Acquire lead buyers (Buyer Acquisition)
7. Set up routing and delivery (Routing & Delivery)
8. Configure billing and revenue (Billing & Revenue)
9. Implement monitoring and stop-loss (Monitoring & Stop-Loss)
10. Capture knowledge for future launches (Knowledge Capture)

## Key Features

- **Evidence-based gating**: Hard gates between stages require measurable evidence
- **Deterministic behavior**: Same inputs produce same outputs
- **Failure-safe defaults**: System pauses on ambiguous or negative signals
- **Modular architecture**: Each stage is independently testable and replaceable
- **Deep integration**: Leverages existing ag3ntwerk modules (trends, commerce, scheduler, workbench)

## Usage

```python
from ag3ntwerk.modules.vls import VLSService

# Initialize service
vls = VLSService()

# Launch a new vertical
launch_id = await vls.launch_vertical(
    vertical_name="Local Home Services - Plumbing",
    constraints={"max_budget": 50000, "target_metros": ["NYC", "LA"]},
)

# Check status
status = await vls.get_launch_status(launch_id)

# Pause if needed
await vls.pause_launch(launch_id)
```

## Agent Access

The VLS module is accessible to all agents with different capabilities:

- **CEO, Nexus**: Full pipeline orchestration and oversight
- **Echo**: Market intelligence and positioning
- **Keystone**: Economics validation and financial modeling
- **Blueprint**: Blueprint definition and product specification
- **Forge**: Infrastructure generation and deployment
- **Index**: Data systems, lead intake, knowledge capture
- **Vector**: Buyer acquisition, billing, and revenue
- **Foundry**: Routing and delivery orchestration
- **Aegis**: Monitoring and risk management
"""

# Core data models
from ag3ntwerk.modules.vls.core import (
    NicheCandidate,
    EconomicsModel,
    VerticalBlueprint,
    LeadRecord,
    BuyerProfile,
    LaunchStatus,
    StageStatus,
    GateStatus,
    VerticalStatus,
    stage_number_from_status,
    status_from_stage_number,
)

# State management
from ag3ntwerk.modules.vls.state import (
    LaunchState,
    VLSStateManager,
)

# Gate validation
from ag3ntwerk.modules.vls.gates import (
    VLSGate,
    GateEvidence,
    GateResult,
    MarketIntelligenceGate,
    ValidationEconomicsGate,
    BlueprintDefinitionGate,
    OperationalReadinessGate,
    MonitoringStopLossGate,
    GATE_REGISTRY,
    get_gate,
)

# Evidence collection
from ag3ntwerk.modules.vls.evidence import (
    EvidenceItem,
    EvidenceScore,
    EvidenceCollector,
    calculate_confidence_score,
    calculate_evidence_score,
    aggregate_evidence_by_type,
    filter_evidence_by_confidence,
    get_most_recent_evidence,
    generate_evidence_summary,
)

# Workflows
from ag3ntwerk.modules.vls.workflows import (
    VERTICAL_LAUNCH_PIPELINE,
    VLS_QUICK_VALIDATION,
    ALL_VLS_WORKFLOWS,
)

# Service interface (will be imported after creation)
try:
    from ag3ntwerk.modules.vls.service import VLSService
except ImportError:
    # Service not yet implemented
    VLSService = None  # type: ignore


__all__ = [
    # Core models
    "NicheCandidate",
    "EconomicsModel",
    "VerticalBlueprint",
    "LeadRecord",
    "BuyerProfile",
    "LaunchStatus",
    "StageStatus",
    "GateStatus",
    "VerticalStatus",
    "stage_number_from_status",
    "status_from_stage_number",
    # State
    "LaunchState",
    "VLSStateManager",
    # Gates
    "VLSGate",
    "GateEvidence",
    "GateResult",
    "MarketIntelligenceGate",
    "ValidationEconomicsGate",
    "BlueprintDefinitionGate",
    "OperationalReadinessGate",
    "MonitoringStopLossGate",
    "GATE_REGISTRY",
    "get_gate",
    # Evidence
    "EvidenceItem",
    "EvidenceScore",
    "EvidenceCollector",
    "calculate_confidence_score",
    "calculate_evidence_score",
    "aggregate_evidence_by_type",
    "filter_evidence_by_confidence",
    "get_most_recent_evidence",
    "generate_evidence_summary",
    # Workflows
    "VERTICAL_LAUNCH_PIPELINE",
    "VLS_QUICK_VALIDATION",
    "ALL_VLS_WORKFLOWS",
    # Service
    "VLSService",
]


# Module version
__version__ = "1.0.0"
