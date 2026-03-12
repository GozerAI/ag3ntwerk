"""
ag3ntwerk Orchestration Module.

Provides workflow orchestration for cross-functional agent coordination.
Enables complex multi-agent workflows like product launches, incident
response, and budget approvals.

Key Components:
- Orchestrator: Base class for workflow coordination
- AgentRegistry: Central registry for all agents
- Workflow: Base class for multi-step workflows
- WorkflowStep: Individual step in a workflow
- WorkflowFactory: Factory for creating workflows from definitions

Example (legacy class-based):
    ```python
    from ag3ntwerk.orchestration import (
        AgentRegistry,
        ProductLaunchWorkflow,
    )

    registry = AgentRegistry(llm_provider=provider)
    workflow = ProductLaunchWorkflow(registry)

    result = await workflow.execute(
        product_name="GozerAI Pro",
        features=["AI chat", "Code generation"],
    )
    ```

Example (new factory-based):
    ```python
    from ag3ntwerk.orchestration import AgentRegistry
    from ag3ntwerk.orchestration.factory import create_workflow

    registry = AgentRegistry(llm_provider=provider)
    workflow = create_workflow("product_launch", registry)

    result = await workflow.execute(
        product_name="GozerAI Pro",
        features=["AI chat", "Code generation"],
    )
    ```
"""

from ag3ntwerk.orchestration.base import (
    # Enums
    WorkflowStatus,
    StepStatus,
    # Models
    WorkflowStep,
    WorkflowContext,
    WorkflowResult,
    # Base classes
    Workflow,
    Orchestrator,
)
from ag3ntwerk.orchestration.registry import AgentRegistry
from ag3ntwerk.orchestration.workflows import (
    # Original workflows
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
    # Cross-functional workflows
    StrategicPlanningWorkflow,
    SecurityAuditWorkflow,
    CustomerOnboardingWorkflow,
    DataQualityWorkflow,
    RevenueGrowthWorkflow,
    ComplianceAuditWorkflow,
    ResearchInitiativeWorkflow,
    RiskAssessmentWorkflow,
    MarketingCampaignWorkflow,
    SprintPlanningWorkflow,
    TechnologyMigrationWorkflow,
    KnowledgeTransferWorkflow,
    CustomerChurnAnalysisWorkflow,
    # Single-agent internal workflows
    OperationsReviewWorkflow,
    TechDebtReviewWorkflow,
    FinancialCloseWorkflow,
    CodeQualityWorkflow,
    FeaturePrioritizationWorkflow,
    ThreatMonitoringWorkflow,
    DataPipelineMonitoringWorkflow,
    ExperimentCycleWorkflow,
    CustomerHealthReviewWorkflow,
    RevenueAnalysisWorkflow,
    RiskMonitoringWorkflow,
    ComplianceMonitoringWorkflow,
    BrandHealthWorkflow,
    InfrastructureHealthWorkflow,
    KnowledgeMaintenanceWorkflow,
    StrategicReviewWorkflow,
    # Workbench Pipeline Workflows
    CodeEvaluationDeploymentWorkflow,
    DatabaseProvisioningWorkflow,
    SecretsManagementWorkflow,
    # Content Distribution Pipeline
    ContentDistributionPipelineWorkflow,
)
from ag3ntwerk.orchestration.specialist_workflows import (
    # Keystone Specialist Workflows
    FinancialModelingWorkflow,
    CostAllocationWorkflow,
    InvestmentAnalysisWorkflow,
    # Forge Specialist Workflows
    CodeReviewWorkflow,
    BugFixWorkflow,
    TestGenerationWorkflow,
    DeploymentPlanningWorkflow,
    # Echo Specialist Workflows
    ContentCreationWorkflow,
    SEOAnalysisWorkflow,
    LeadGenerationWorkflow,
    # Blueprint Specialist Workflows
    UserStoryCreationWorkflow,
    FeatureScoringWorkflow,
    BacklogRefinementWorkflow,
    # Beacon Specialist Workflows
    FeedbackAnalysisWorkflow,
    ChurnPredictionWorkflow,
    NPSAnalysisWorkflow,
    TicketTriageWorkflow,
    # Index Specialist Workflows
    DataQualityCheckWorkflow,
    SchemaValidationWorkflow,
    # Vector Specialist Workflows
    RevenueTrackingWorkflow,
    ChurnAnalysisWorkflow,
    CohortAnalysisWorkflow,
    GrowthExperimentWorkflow,
    # Sentinel Specialist Workflows
    DataGovernanceWorkflow,
    SecurityAssessmentWorkflow,
    KnowledgeExtractionWorkflow,
    SystemsAnalysisWorkflow,
    # Axiom Specialist Workflows
    DeepResearchWorkflow,
    LiteratureReviewWorkflow,
    ExperimentDesignWorkflow,
    FeasibilityStudyWorkflow,
    # Compass Specialist Workflows
    MarketAnalysisWorkflow,
    CompetitiveAnalysisWorkflow,
    StrategicPlanningWorkflow as CSOStrategicPlanningWorkflow,
    GoToMarketWorkflow,
    # Nexus Specialist Workflows
    WorkflowDesignWorkflow,
    TaskAnalysisWorkflow,
    PerformanceReportWorkflow,
    ProcessOptimizationWorkflow,
    # Accord Specialist Workflows
    ComplianceAssessmentWorkflow,
    PolicyReviewWorkflow,
    AuditPreparationWorkflow,
    EthicsReviewWorkflow,
    # Aegis Specialist Workflows
    RiskAssessmentWorkflow as CRiORiskAssessmentWorkflow,
    ThreatModelingWorkflow,
    BCPPlanningWorkflow,
    IncidentAnalysisWorkflow,
    # Citadel Specialist Workflows
    SecurityScanWorkflow,
    ThreatHuntingWorkflow,
    IncidentResponseWorkflow as CSecOIncidentResponseWorkflow,
    SecurityComplianceWorkflow,
    # Foundry Specialist Workflows
    SprintPlanningWorkflow as CEngOSprintPlanningWorkflow,
    ReleaseManagementWorkflow,
    QualityAssuranceWorkflow,
    DevOpsPipelineWorkflow,
)
from ag3ntwerk.orchestration.aggregation_workflows import (
    # Keystone Aggregation Workflows
    ComprehensiveCostReviewWorkflow,
    BudgetPlanningCycleWorkflow,
    # Forge Aggregation Workflows
    TechnicalAssessmentWorkflow,
    FullDevOpsCycleWorkflow,
    # Echo Aggregation Workflows
    FullCampaignWorkflow,
    BrandHealthCheckWorkflow,
    # Blueprint Aggregation Workflows
    FeatureDeliveryWorkflow,
    SprintReadinessWorkflow,
    # Beacon Aggregation Workflows
    CustomerHealthReviewWorkflow as CCOCustomerHealthReviewWorkflow,
    VoiceOfCustomerWorkflow,
    # Vector Aggregation Workflows
    RevenueHealthCheckWorkflow,
    GrowthAnalysisWorkflow,
    # Sentinel Aggregation Workflows
    ITGovernanceReviewWorkflow,
    KnowledgeManagementWorkflow,
    # Axiom Aggregation Workflows
    ComprehensiveResearchWorkflow,
    FeasibilityAssessmentWorkflow,
    # Compass Aggregation Workflows
    StrategicAnalysisWorkflow,
    GTMPlanningWorkflow,
    # Nexus Aggregation Workflows
    OperationsReviewWorkflow as COOOperationsReviewWorkflow,
    CrossFunctionalCoordinationWorkflow,
    # Accord Aggregation Workflows
    ComplianceProgramReviewWorkflow,
    AuditReadinessWorkflow,
    # Aegis Aggregation Workflows
    EnterpriseRiskAssessmentWorkflow,
    BCPDRPlanningWorkflow,
    # Citadel Aggregation Workflows
    SecurityPostureAssessmentWorkflow,
    SecurityIncidentWorkflow,
    # Foundry Aggregation Workflows
    ReleaseCycleWorkflow,
    EngineeringMetricsWorkflow,
)

__all__ = [
    # Enums
    "WorkflowStatus",
    "StepStatus",
    # Models
    "WorkflowStep",
    "WorkflowContext",
    "WorkflowResult",
    # Base classes
    "Workflow",
    "Orchestrator",
    # Registry
    "AgentRegistry",
    # Original Workflows
    "ProductLaunchWorkflow",
    "IncidentResponseWorkflow",
    "BudgetApprovalWorkflow",
    "FeatureReleaseWorkflow",
    # Cross-functional Workflows
    "StrategicPlanningWorkflow",
    "SecurityAuditWorkflow",
    "CustomerOnboardingWorkflow",
    "DataQualityWorkflow",
    "RevenueGrowthWorkflow",
    "ComplianceAuditWorkflow",
    "ResearchInitiativeWorkflow",
    "RiskAssessmentWorkflow",
    "MarketingCampaignWorkflow",
    "SprintPlanningWorkflow",
    "TechnologyMigrationWorkflow",
    "KnowledgeTransferWorkflow",
    "CustomerChurnAnalysisWorkflow",
    # Single-Agent Internal Workflows
    "OperationsReviewWorkflow",
    "TechDebtReviewWorkflow",
    "FinancialCloseWorkflow",
    "CodeQualityWorkflow",
    "FeaturePrioritizationWorkflow",
    "ThreatMonitoringWorkflow",
    "DataPipelineMonitoringWorkflow",
    "ExperimentCycleWorkflow",
    "CustomerHealthReviewWorkflow",
    "RevenueAnalysisWorkflow",
    "RiskMonitoringWorkflow",
    "ComplianceMonitoringWorkflow",
    "BrandHealthWorkflow",
    "InfrastructureHealthWorkflow",
    "KnowledgeMaintenanceWorkflow",
    "StrategicReviewWorkflow",
    # Workbench Pipeline Workflows
    "CodeEvaluationDeploymentWorkflow",
    "DatabaseProvisioningWorkflow",
    "SecretsManagementWorkflow",
    # Content Distribution Pipeline
    "ContentDistributionPipelineWorkflow",
    # Specialist Workflows
    "FinancialModelingWorkflow",
    "CostAllocationWorkflow",
    "InvestmentAnalysisWorkflow",
    "CodeReviewWorkflow",
    "BugFixWorkflow",
    "TestGenerationWorkflow",
    "DeploymentPlanningWorkflow",
    "ContentCreationWorkflow",
    "SEOAnalysisWorkflow",
    "LeadGenerationWorkflow",
    "UserStoryCreationWorkflow",
    "FeatureScoringWorkflow",
    "BacklogRefinementWorkflow",
    "FeedbackAnalysisWorkflow",
    "ChurnPredictionWorkflow",
    "NPSAnalysisWorkflow",
    "TicketTriageWorkflow",
    "DataQualityCheckWorkflow",
    "SchemaValidationWorkflow",
    # Vector Specialist Workflows
    "RevenueTrackingWorkflow",
    "ChurnAnalysisWorkflow",
    "CohortAnalysisWorkflow",
    "GrowthExperimentWorkflow",
    # Sentinel Specialist Workflows
    "DataGovernanceWorkflow",
    "SecurityAssessmentWorkflow",
    "KnowledgeExtractionWorkflow",
    "SystemsAnalysisWorkflow",
    # Axiom Specialist Workflows
    "DeepResearchWorkflow",
    "LiteratureReviewWorkflow",
    "ExperimentDesignWorkflow",
    "FeasibilityStudyWorkflow",
    # Compass Specialist Workflows
    "MarketAnalysisWorkflow",
    "CompetitiveAnalysisWorkflow",
    "CSOStrategicPlanningWorkflow",
    "GoToMarketWorkflow",
    # Nexus Specialist Workflows
    "WorkflowDesignWorkflow",
    "TaskAnalysisWorkflow",
    "PerformanceReportWorkflow",
    "ProcessOptimizationWorkflow",
    # Accord Specialist Workflows
    "ComplianceAssessmentWorkflow",
    "PolicyReviewWorkflow",
    "AuditPreparationWorkflow",
    "EthicsReviewWorkflow",
    # Aegis Specialist Workflows
    "CRiORiskAssessmentWorkflow",
    "ThreatModelingWorkflow",
    "BCPPlanningWorkflow",
    "IncidentAnalysisWorkflow",
    # Citadel Specialist Workflows
    "SecurityScanWorkflow",
    "ThreatHuntingWorkflow",
    "CSecOIncidentResponseWorkflow",
    "SecurityComplianceWorkflow",
    # Foundry Specialist Workflows
    "CEngOSprintPlanningWorkflow",
    "ReleaseManagementWorkflow",
    "QualityAssuranceWorkflow",
    "DevOpsPipelineWorkflow",
    # Manager Aggregation Workflows
    "ComprehensiveCostReviewWorkflow",
    "BudgetPlanningCycleWorkflow",
    "TechnicalAssessmentWorkflow",
    "FullDevOpsCycleWorkflow",
    "FullCampaignWorkflow",
    "BrandHealthCheckWorkflow",
    "FeatureDeliveryWorkflow",
    "SprintReadinessWorkflow",
    "CCOCustomerHealthReviewWorkflow",
    "VoiceOfCustomerWorkflow",
    # Vector Aggregation Workflows
    "RevenueHealthCheckWorkflow",
    "GrowthAnalysisWorkflow",
    # Sentinel Aggregation Workflows
    "ITGovernanceReviewWorkflow",
    "KnowledgeManagementWorkflow",
    # Axiom Aggregation Workflows
    "ComprehensiveResearchWorkflow",
    "FeasibilityAssessmentWorkflow",
    # Compass Aggregation Workflows
    "StrategicAnalysisWorkflow",
    "GTMPlanningWorkflow",
    # Nexus Aggregation Workflows
    "COOOperationsReviewWorkflow",
    "CrossFunctionalCoordinationWorkflow",
    # Accord Aggregation Workflows
    "ComplianceProgramReviewWorkflow",
    "AuditReadinessWorkflow",
    # Aegis Aggregation Workflows
    "EnterpriseRiskAssessmentWorkflow",
    "BCPDRPlanningWorkflow",
    # Citadel Aggregation Workflows
    "SecurityPostureAssessmentWorkflow",
    "SecurityIncidentWorkflow",
    # Foundry Aggregation Workflows
    "ReleaseCycleWorkflow",
    "EngineeringMetricsWorkflow",
]
