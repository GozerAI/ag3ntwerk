"""
ag3ntwerk Integrations - Cross-agent integration modules.

This package contains integration layers that connect agents
together for seamless data flow and coordinated decision-making.

Integration Modules:
- feedback_pipeline: Beacon -> Blueprint customer feedback to product insights
- security_gate: Citadel <-> Foundry deployment security gates
- nexus_bridge: Nexus <-> Nexus Priority Engine and Learning System
- ecommerce_bridge: Axiom/Echo <-> Shopify Manager and Medusa
- content_orchestrator: Echo/Beacon/Blueprint <-> AI Platform content generation
- research_platform: Axiom <-> AI Platform research and expert systems
- trend_intelligence: Blueprint/Axiom/Echo <-> Trend Analyzer market intelligence
- expert_panel: CEO/Nexus <-> AI Platform expert consensus systems

External Service Integrations:
- vector: Vector database integrations (pgvector, Milvus, Qdrant)
- workflow: Workflow automation (Flowise, n8n)
- browser: Browser automation (Playwright MCP)
"""

from ag3ntwerk.integrations.feedback_pipeline import (
    CustomerFeedbackPipeline,
    FeedbackItem,
    FeedbackCategory,
    ProductInsight,
)
from ag3ntwerk.integrations.security_gate import (
    SecurityGatedDeployment,
    SecurityGateStatus,
    SecurityCheckType,
    SecurityCheck,
    DeploymentSecurityGate,
    DeploymentRisk,
)
from ag3ntwerk.integrations.nexus_bridge import (
    NexusBridge,
    TaskOutcome,
    PrioritizedTask,
)
from ag3ntwerk.integrations.ecommerce_bridge import (
    ECommerceBridge,
    ProductInfo,
    PricingRecommendation,
    StorefrontAnalytics,
    StorefrontPlatform,
    PricingStrategy,
    InventoryStatus,
)
from ag3ntwerk.integrations.content_orchestrator import (
    ContentOrchestratorBridge,
    ContentRequest,
    ContentPiece,
    ContentType,
    ContentStatus,
    ContentWorkflow,
    WorkflowStatus,
    BlueprintSpec,
)
from ag3ntwerk.integrations.research_platform import (
    ResearchPlatformBridge,
    ResearchProject,
    ResearchFinding,
    ResearchType,
    ResearchStatus,
    ConfidenceLevel,
    EvidenceStrength,
    ConsensusResult as ResearchConsensusResult,
)
from ag3ntwerk.integrations.trend_intelligence import (
    TrendIntelligenceBridge,
    MarketTrend,
    MarketNiche,
    MarketOpportunity,
    CompetitiveSignal,
    TrendCategory,
    TrendDirection,
    OpportunityType,
)
from ag3ntwerk.integrations.expert_panel import (
    ExpertPanelBridge,
    ExpertProfile,
    ExpertOpinion,
    ConsensusResult,
    ConsensusStrategy,
    DecisionRequest,
    DecisionStatus,
    DecisionUrgency,
    ExpertType,
)

__all__ = [
    # Feedback pipeline (Beacon -> Blueprint)
    "CustomerFeedbackPipeline",
    "FeedbackItem",
    "FeedbackCategory",
    "ProductInsight",
    # Security gate (Citadel <-> Foundry)
    "SecurityGatedDeployment",
    "SecurityGateStatus",
    "SecurityCheckType",
    "SecurityCheck",
    "DeploymentSecurityGate",
    "DeploymentRisk",
    # Nexus bridge (Nexus <-> Nexus Priority/Learning)
    "NexusBridge",
    "TaskOutcome",
    "PrioritizedTask",
    # E-Commerce bridge (Axiom/Echo <-> Shopify/Medusa)
    "ECommerceBridge",
    "ProductInfo",
    "PricingRecommendation",
    "StorefrontAnalytics",
    "StorefrontPlatform",
    "PricingStrategy",
    "InventoryStatus",
    # Content orchestrator (Echo/Beacon/Blueprint <-> AI Platform)
    "ContentOrchestratorBridge",
    "ContentRequest",
    "ContentPiece",
    "ContentType",
    "ContentStatus",
    "ContentWorkflow",
    "WorkflowStatus",
    "BlueprintSpec",
    # Research platform (Axiom <-> AI Platform)
    "ResearchPlatformBridge",
    "ResearchProject",
    "ResearchFinding",
    "ResearchType",
    "ResearchStatus",
    "ConfidenceLevel",
    "EvidenceStrength",
    "ResearchConsensusResult",
    # Trend intelligence (Blueprint/Axiom/Echo <-> Trend Analyzer)
    "TrendIntelligenceBridge",
    "MarketTrend",
    "MarketNiche",
    "MarketOpportunity",
    "CompetitiveSignal",
    "TrendCategory",
    "TrendDirection",
    "OpportunityType",
    # Expert panel (CEO/Nexus <-> AI Platform experts)
    "ExpertPanelBridge",
    "ExpertProfile",
    "ExpertOpinion",
    "ConsensusResult",
    "ConsensusStrategy",
    "DecisionRequest",
    "DecisionStatus",
    "DecisionUrgency",
    "ExpertType",
    # External service integrations
    "vector",
    "workflow",
    "browser",
]

# Import subpackages for external service integrations
from ag3ntwerk.integrations import vector
from ag3ntwerk.integrations import workflow
from ag3ntwerk.integrations import browser
