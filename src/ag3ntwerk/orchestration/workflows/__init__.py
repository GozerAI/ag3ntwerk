"""
Pre-built Workflows.

Standard cross-functional workflows for common business scenarios.

This module re-exports all workflow classes for backward compatibility.
Workflows are organized into domain-specific modules:

- business.py: Product launches, budget approval, strategic planning, etc.
- engineering.py: Feature releases, sprint planning, tech migration, etc.
- security.py: Security audits, compliance, risk assessment, etc.
- customer.py: Customer onboarding, churn analysis, revenue growth, etc.
- data.py: Data quality, pipeline monitoring, experiments, etc.
- research.py: Research initiatives, knowledge maintenance
- incident.py: Incident response
- infrastructure.py: Database provisioning, secrets management, etc.
"""

# Business Operations Workflows
from ag3ntwerk.orchestration.workflows.business import (
    ProductLaunchWorkflow,
    BudgetApprovalWorkflow,
    StrategicPlanningWorkflow,
    OperationsReviewWorkflow,
    FinancialCloseWorkflow,
    StrategicReviewWorkflow,
    KnowledgeTransferWorkflow,
)

# Engineering & DevOps Workflows
from ag3ntwerk.orchestration.workflows.engineering import (
    FeatureReleaseWorkflow,
    SprintPlanningWorkflow,
    TechnologyMigrationWorkflow,
    TechDebtReviewWorkflow,
    CodeQualityWorkflow,
    InfrastructureHealthWorkflow,
    CodeEvaluationDeploymentWorkflow,
)

# Security & Compliance Workflows
from ag3ntwerk.orchestration.workflows.security import (
    SecurityAuditWorkflow,
    ComplianceAuditWorkflow,
    RiskAssessmentWorkflow,
    ThreatMonitoringWorkflow,
    RiskMonitoringWorkflow,
    ComplianceMonitoringWorkflow,
)

# Customer & Revenue Workflows
from ag3ntwerk.orchestration.workflows.customer import (
    CustomerOnboardingWorkflow,
    CustomerChurnAnalysisWorkflow,
    CustomerHealthReviewWorkflow,
    RevenueGrowthWorkflow,
    RevenueAnalysisWorkflow,
    MarketingCampaignWorkflow,
)

# Data & Analytics Workflows
from ag3ntwerk.orchestration.workflows.data import (
    DataQualityWorkflow,
    DataPipelineMonitoringWorkflow,
    ExperimentCycleWorkflow,
    FeaturePrioritizationWorkflow,
    BrandHealthWorkflow,
)

# Research & Knowledge Workflows
from ag3ntwerk.orchestration.workflows.research import (
    ResearchInitiativeWorkflow,
    KnowledgeMaintenanceWorkflow,
)

# Incident Response Workflow
from ag3ntwerk.orchestration.workflows.incident import (
    IncidentResponseWorkflow,
)

# Infrastructure Workflows (Workbench)
from ag3ntwerk.orchestration.workflows.infrastructure import (
    DatabaseProvisioningWorkflow,
    SecretsManagementWorkflow,
    ContentDistributionPipelineWorkflow,
)

__all__ = [
    # Business Operations
    "ProductLaunchWorkflow",
    "BudgetApprovalWorkflow",
    "StrategicPlanningWorkflow",
    "OperationsReviewWorkflow",
    "FinancialCloseWorkflow",
    "StrategicReviewWorkflow",
    "KnowledgeTransferWorkflow",
    # Engineering & DevOps
    "FeatureReleaseWorkflow",
    "SprintPlanningWorkflow",
    "TechnologyMigrationWorkflow",
    "TechDebtReviewWorkflow",
    "CodeQualityWorkflow",
    "InfrastructureHealthWorkflow",
    "CodeEvaluationDeploymentWorkflow",
    # Security & Compliance
    "SecurityAuditWorkflow",
    "ComplianceAuditWorkflow",
    "RiskAssessmentWorkflow",
    "ThreatMonitoringWorkflow",
    "RiskMonitoringWorkflow",
    "ComplianceMonitoringWorkflow",
    # Customer & Revenue
    "CustomerOnboardingWorkflow",
    "CustomerChurnAnalysisWorkflow",
    "CustomerHealthReviewWorkflow",
    "RevenueGrowthWorkflow",
    "RevenueAnalysisWorkflow",
    "MarketingCampaignWorkflow",
    # Data & Analytics
    "DataQualityWorkflow",
    "DataPipelineMonitoringWorkflow",
    "ExperimentCycleWorkflow",
    "FeaturePrioritizationWorkflow",
    "BrandHealthWorkflow",
    # Research & Knowledge
    "ResearchInitiativeWorkflow",
    "KnowledgeMaintenanceWorkflow",
    # Incident Response
    "IncidentResponseWorkflow",
    # Infrastructure (Workbench)
    "DatabaseProvisioningWorkflow",
    "SecretsManagementWorkflow",
    "ContentDistributionPipelineWorkflow",
]
