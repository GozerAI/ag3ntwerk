"""
Learning System - Closed learning loops for the ag3ntwerk agent hierarchy.

This module provides the learning infrastructure that enables agents to
learn from task outcomes and automatically improve their behavior.

Main Components:
- LearningOrchestrator: Central coordinator for all learning
- OutcomeTracker: Records task outcomes across the hierarchy
- PatternStore: Stores and retrieves learned patterns
- IssueManager: Detects issues and creates fix tasks

Learning Loops:
- ExecutiveLearningLoop: Agent-level pattern analysis
- ManagerLearningLoop: Manager-level routing optimization
- SpecialistLearningLoop: Specialist-level skill refinement

Phase 2 - Predictive Capabilities:
- FailurePredictor: Predicts task failure risk
- LoadBalancer: Load-aware task assignment
- TaskModifier: Proactive task modification

Phase 3 - Self-Improvement:
- PatternExperimenter: A/B testing for patterns
- MetaLearner: Self-tuning parameters
- HandlerGenerator: Auto-generate handlers from patterns

Phase 4 - Proactive Behavior:
- OpportunityDetector: Detects improvement opportunities
- ProactiveTaskGenerator: Auto-generates maintenance tasks

Phase 5 - Full Autonomy:
- AutonomyController: Manages decision autonomy levels
- ContinuousLearningPipeline: Never-ending learning cycle

Phase 7 - Cross-Component Integration:
- WorkbenchBridge: Connects learning to Workbench UI
- PluginTelemetryAdapter: Plugin outcome tracking
- ServiceAdapter: Service configuration adaptation

Phase 8 - Advanced Feedback Loops:
- CapabilityEvolver: Agents develop new capabilities from demand
- PatternPropagator: Patterns spread to similar agents
- FailureInvestigator: Root cause analysis for failures

Phase 9 - Predictive Intelligence:
- DemandForecaster: Predicts task volume and type distribution
- CascadePredictor: Predicts downstream effects of decisions
- ContextOptimizer: Optimizes decisions based on rich context

Phase 10 - True Autonomy:
- SelfArchitect: System modifies its own architecture
- GoalAligner: Ensures autonomous decisions align with goals
- HandoffOptimizer: Minimizes human intervention while maximizing trust

Usage:
    ```python
    from ag3ntwerk.learning import (
        LearningOrchestrator,
        initialize_learning_orchestrator,
        get_learning_orchestrator,
    )
    from ag3ntwerk.learning.models import HierarchyPath

    # Initialize the learning system
    orchestrator = await initialize_learning_orchestrator(db, task_queue)

    # Connect to Nexus
    await coo.connect_learning_system(orchestrator)

    # Record outcomes (happens automatically through Nexus)
    # Get learning stats
    stats = await orchestrator.get_stats()
    ```
"""

from ag3ntwerk.learning.models import (
    # Enums
    OutcomeType,
    ErrorCategory,
    PatternType,
    ScopeLevel,
    IssueSeverity,
    IssueType,
    IssueStatus,
    PerformanceTrend,
    # Data classes
    HierarchyPath,
    TaskOutcomeRecord,
    LearnedPattern,
    LearningIssue,
    LearningAdjustment,
    AgentPerformance,
)
from ag3ntwerk.learning.orchestrator import (
    LearningOrchestrator,
    get_learning_orchestrator,
    initialize_learning_orchestrator,
    reset_learning_orchestrator,
)

# Facades (for direct access to domain-specific functionality)
from ag3ntwerk.learning.facades import (
    CoreLearningFacade,
    RoutingFacade,
    PredictionFacade,
    ExperimentationFacade,
    ProactiveFacade,
    AutonomyFacade,
    IntegrationFacade,
    EvolutionFacade,
    IntelligenceFacade,
    AdvancedAutonomyFacade,
    MetacognitionFacade,
)
from ag3ntwerk.learning.outcome_tracker import OutcomeTracker
from ag3ntwerk.learning.pattern_store import PatternStore
from ag3ntwerk.learning.issue_manager import IssueManager
from ag3ntwerk.learning.dynamic_router import DynamicRouter, RoutingDecision, RoutingScore
from ag3ntwerk.learning.pattern_tracker import PatternTracker, PatternApplication, PatternEffectiveness
from ag3ntwerk.learning.confidence_calibrator import ConfidenceCalibrator, CalibrationCurve
from ag3ntwerk.learning.failure_predictor import (
    FailurePredictor,
    FailureRisk,
    RiskLevel,
    Mitigation,
    MitigationType,
    ErrorPatternStats,
)
from ag3ntwerk.learning.load_balancer import (
    LoadBalancer,
    LoadBalanceDecision,
    AgentLoad,
)
from ag3ntwerk.learning.task_modifier import (
    TaskModifier,
    ModifiedTask,
    TaskModification,
    create_task_modifier,
)
from ag3ntwerk.learning.pattern_experiment import (
    PatternExperimenter,
    PatternExperiment,
    ExperimentResult,
    ExperimentStatus,
    ExperimentConclusion,
    ExperimentGroup,
)
from ag3ntwerk.learning.meta_learner import (
    MetaLearner,
    TunableParameter,
    EffectivenessMetrics,
    TuningResult,
    ParameterCategory,
)
from ag3ntwerk.learning.handler_generator import (
    HandlerGenerator,
    GeneratedHandler,
    HandlerCandidate,
    HandlerStatus,
)
from ag3ntwerk.learning.opportunity_detector import (
    OpportunityDetector,
    Opportunity,
    OpportunityType,
    OpportunityPriority,
    CapabilityGap,
    WorkflowAnalysis,
)
from ag3ntwerk.learning.proactive_generator import (
    ProactiveTaskGenerator,
    ProactiveTask,
    ProactiveTaskType,
    TaskPriority,
)
from ag3ntwerk.learning.autonomy_controller import (
    AutonomyController,
    AutonomyLevel,
    ActionCategory,
    AutonomyDecision,
    PendingApproval,
    ActionLog,
)
from ag3ntwerk.learning.continuous_pipeline import (
    ContinuousLearningPipeline,
    PipelineState,
    PipelineConfig,
    CycleResult,
    CyclePhase,
)
from ag3ntwerk.learning.workbench_bridge import (
    WorkbenchBridge,
    LearningDashboard,
    AgentInsight,
    ApprovalAction,
)
from ag3ntwerk.learning.plugin_telemetry import (
    PluginTelemetryAdapter,
    PluginOperation,
    PluginStats,
    OperationContext,
)
from ag3ntwerk.learning.service_adapter import (
    ServiceAdapter,
    ConfigChangeType,
    AdaptationStrategy,
    ConfigRecommendation,
    ServiceConfig,
    ConfigChange,
)
from ag3ntwerk.learning.capability_evolver import (
    CapabilityEvolver,
    CapabilityType,
    EvolutionStatus,
    DemandGap,
    NewCapability,
    EvolutionResult,
)
from ag3ntwerk.learning.pattern_propagator import (
    PatternPropagator,
    PropagationStatus,
    SimilarityMetric,
    AgentSimilarity,
    PropagationRecord,
    PropagationResult,
)
from ag3ntwerk.learning.failure_investigator import (
    FailureInvestigator,
    RootCauseType,
    CorrelationType,
    InvestigationStatus,
    RootCause,
    Correlation,
    RecommendedFix,
    Investigation,
)
from ag3ntwerk.learning.demand_forecaster import (
    DemandForecaster,
    SeasonalityType,
    TrendDirection,
    ScalingAction,
    TimeSeriesPoint,
    SeasonalPattern,
    TrendInfo,
    TaskTypeDistribution,
    ConfidenceInterval,
    ScalingRecommendation,
    DemandForecast,
)
from ag3ntwerk.learning.cascade_predictor import (
    CascadePredictor,
    RiskLevel as CascadeRiskLevel,
    ImpactType,
    AgentLoad as CascadeAgentLoad,
    DownstreamAgent,
    CascadeRisk,
    RoutingDecision as CascadeRoutingDecision,
    CascadeEffect,
    CascadeHistoryEntry,
)
from ag3ntwerk.learning.context_optimizer import (
    ContextOptimizer,
    OptimizationType,
    TimeOfDay,
    LoadLevel,
    ExecutionContext,
    Task as OptTask,
    TimePattern,
    LoadPattern,
    OptimizationAction,
    AgentRecommendation,
    OptimizedTask,
)
from ag3ntwerk.learning.self_architect import (
    SelfArchitect,
    ProposalType,
    ProposalStatus,
    BottleneckType,
    AgentMetrics,
    Bottleneck,
    UnderutilizedAgent,
    CapabilityGapInfo as ArchCapabilityGap,
    AgentProposal,
    MergeProposal,
    SplitProposal,
    ArchitectureProposal,
)
from ag3ntwerk.learning.goal_aligner import (
    GoalAligner,
    GoalType,
    GoalPriority,
    AlignmentLevel,
    ActionRecommendation,
    Goal,
    GoalConflict,
    AlignmentScore,
    AutonomousDecision,
)
from ag3ntwerk.learning.handoff_optimizer import (
    HandoffOptimizer,
    TrustLevel,
    HandoffReason,
    PromotionStatus,
    ApprovalHistory,
    ActionTrust,
    PromotableAction,
    DemotableAction,
    HandoffStrategy,
)

# Nexus Sync (Phase 11 - Integration with Nexus)
from ag3ntwerk.learning.nexus_sync import (
    NexusSyncBridge,
    SyncConfig,
    OutcomeSummary,
    PatternSyncRecord,
    create_nexus_sync_bridge,
)

__all__ = [
    # Main orchestrator
    "LearningOrchestrator",
    "get_learning_orchestrator",
    "initialize_learning_orchestrator",
    "reset_learning_orchestrator",
    # Facades
    "CoreLearningFacade",
    "RoutingFacade",
    "PredictionFacade",
    "ExperimentationFacade",
    "ProactiveFacade",
    "AutonomyFacade",
    "IntegrationFacade",
    "EvolutionFacade",
    "IntelligenceFacade",
    "AdvancedAutonomyFacade",
    "MetacognitionFacade",
    # Components
    "OutcomeTracker",
    "PatternStore",
    "IssueManager",
    # Enums
    "OutcomeType",
    "ErrorCategory",
    "PatternType",
    "ScopeLevel",
    "IssueSeverity",
    "IssueType",
    "IssueStatus",
    "PerformanceTrend",
    # Data models
    "HierarchyPath",
    "TaskOutcomeRecord",
    "LearnedPattern",
    "LearningIssue",
    "LearningAdjustment",
    "AgentPerformance",
    # Dynamic router
    "DynamicRouter",
    "RoutingDecision",
    "RoutingScore",
    # Pattern tracker
    "PatternTracker",
    "PatternApplication",
    "PatternEffectiveness",
    # Confidence calibrator
    "ConfidenceCalibrator",
    "CalibrationCurve",
    # Failure predictor (Phase 2)
    "FailurePredictor",
    "FailureRisk",
    "RiskLevel",
    "Mitigation",
    "MitigationType",
    "ErrorPatternStats",
    # Load balancer (Phase 2)
    "LoadBalancer",
    "LoadBalanceDecision",
    "AgentLoad",
    # Task modifier (Phase 2)
    "TaskModifier",
    "ModifiedTask",
    "TaskModification",
    "create_task_modifier",
    # Pattern experimenter (Phase 3)
    "PatternExperimenter",
    "PatternExperiment",
    "ExperimentResult",
    "ExperimentStatus",
    "ExperimentConclusion",
    "ExperimentGroup",
    # Meta-learner (Phase 3)
    "MetaLearner",
    "TunableParameter",
    "EffectivenessMetrics",
    "TuningResult",
    "ParameterCategory",
    # Handler generator (Phase 3)
    "HandlerGenerator",
    "GeneratedHandler",
    "HandlerCandidate",
    "HandlerStatus",
    # Opportunity detector (Phase 4)
    "OpportunityDetector",
    "Opportunity",
    "OpportunityType",
    "OpportunityPriority",
    "CapabilityGap",
    "WorkflowAnalysis",
    # Proactive task generator (Phase 4)
    "ProactiveTaskGenerator",
    "ProactiveTask",
    "ProactiveTaskType",
    "TaskPriority",
    # Autonomy controller (Phase 5)
    "AutonomyController",
    "AutonomyLevel",
    "ActionCategory",
    "AutonomyDecision",
    "PendingApproval",
    "ActionLog",
    # Continuous pipeline (Phase 5)
    "ContinuousLearningPipeline",
    "PipelineState",
    "PipelineConfig",
    "CycleResult",
    "CyclePhase",
    # Workbench bridge (Phase 7)
    "WorkbenchBridge",
    "LearningDashboard",
    "AgentInsight",
    "ApprovalAction",
    # Plugin telemetry (Phase 7)
    "PluginTelemetryAdapter",
    "PluginOperation",
    "PluginStats",
    "OperationContext",
    # Service adapter (Phase 7)
    "ServiceAdapter",
    "ConfigChangeType",
    "AdaptationStrategy",
    "ConfigRecommendation",
    "ServiceConfig",
    "ConfigChange",
    # Capability evolver (Phase 8)
    "CapabilityEvolver",
    "CapabilityType",
    "EvolutionStatus",
    "DemandGap",
    "NewCapability",
    "EvolutionResult",
    # Pattern propagator (Phase 8)
    "PatternPropagator",
    "PropagationStatus",
    "SimilarityMetric",
    "AgentSimilarity",
    "PropagationRecord",
    "PropagationResult",
    # Failure investigator (Phase 8)
    "FailureInvestigator",
    "RootCauseType",
    "CorrelationType",
    "InvestigationStatus",
    "RootCause",
    "Correlation",
    "RecommendedFix",
    "Investigation",
    # Demand forecaster (Phase 9)
    "DemandForecaster",
    "SeasonalityType",
    "TrendDirection",
    "ScalingAction",
    "TimeSeriesPoint",
    "SeasonalPattern",
    "TrendInfo",
    "TaskTypeDistribution",
    "ConfidenceInterval",
    "ScalingRecommendation",
    "DemandForecast",
    # Cascade predictor (Phase 9)
    "CascadePredictor",
    "CascadeRiskLevel",
    "ImpactType",
    "CascadeAgentLoad",
    "DownstreamAgent",
    "CascadeRisk",
    "CascadeRoutingDecision",
    "CascadeEffect",
    "CascadeHistoryEntry",
    # Context optimizer (Phase 9)
    "ContextOptimizer",
    "OptimizationType",
    "TimeOfDay",
    "LoadLevel",
    "ExecutionContext",
    "OptTask",
    "TimePattern",
    "LoadPattern",
    "OptimizationAction",
    "AgentRecommendation",
    "OptimizedTask",
    # Self-architect (Phase 10)
    "SelfArchitect",
    "ProposalType",
    "ProposalStatus",
    "BottleneckType",
    "AgentMetrics",
    "Bottleneck",
    "UnderutilizedAgent",
    "ArchCapabilityGap",
    "AgentProposal",
    "MergeProposal",
    "SplitProposal",
    "ArchitectureProposal",
    # Goal aligner (Phase 10)
    "GoalAligner",
    "GoalType",
    "GoalPriority",
    "AlignmentLevel",
    "ActionRecommendation",
    "Goal",
    "GoalConflict",
    "AlignmentScore",
    "AutonomousDecision",
    # Handoff optimizer (Phase 10)
    "HandoffOptimizer",
    "TrustLevel",
    "HandoffReason",
    "PromotionStatus",
    "ApprovalHistory",
    "ActionTrust",
    "PromotableAction",
    "DemotableAction",
    "HandoffStrategy",
    # Nexus sync (Phase 11)
    "NexusSyncBridge",
    "SyncConfig",
    "OutcomeSummary",
    "PatternSyncRecord",
    "create_nexus_sync_bridge",
]
