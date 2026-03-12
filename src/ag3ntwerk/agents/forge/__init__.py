"""Forge (Forge) - Forge Development Module."""

from ag3ntwerk.agents.forge.agent import Forge

# Codename alias for product narrative
Forge = Forge

# Managers
from ag3ntwerk.agents.forge.managers import (
    ArchitectureManager,
    CodeQualityManager,
    TestingManager,
    DevOpsManager,
)

# Specialists
from ag3ntwerk.agents.forge.specialists import (
    SeniorDeveloper,
    CodeReviewer,
    SystemArchitect,
    QAEngineer,
    DevOpsEngineer,
    TechnicalWriter,
)

# Models
from ag3ntwerk.agents.forge.models import (
    # Enums
    ProjectStatus,
    TaskPriority,
    CodeQuality,
    ReviewStatus,
    TestStatus,
    DeploymentStatus,
    ArchitecturePattern,
    TechStackLayer,
    BugSeverity,
    BugStatus,
    # Dataclasses
    Project,
    CodeReview,
    CodeGeneration,
    Bug,
    TestSuite,
    Refactoring,
    ArchitectureDesign,
    Deployment,
    TechStack,
    CodingStandard,
    DebugSession,
    PerformanceOptimization,
    APIDesign,
    DatabaseDesign,
    DevelopmentMetrics,
    # Capabilities
    DEVELOPMENT_CAPABILITIES,
)

__all__ = [
    # Main agent
    "Forge",
    "Forge",
    # Managers
    "ArchitectureManager",
    "CodeQualityManager",
    "TestingManager",
    "DevOpsManager",
    # Specialists
    "SeniorDeveloper",
    "CodeReviewer",
    "SystemArchitect",
    "QAEngineer",
    "DevOpsEngineer",
    "TechnicalWriter",
    # Enums
    "ProjectStatus",
    "TaskPriority",
    "CodeQuality",
    "ReviewStatus",
    "TestStatus",
    "DeploymentStatus",
    "ArchitecturePattern",
    "TechStackLayer",
    "BugSeverity",
    "BugStatus",
    # Dataclasses
    "Project",
    "CodeReview",
    "CodeGeneration",
    "Bug",
    "TestSuite",
    "Refactoring",
    "ArchitectureDesign",
    "Deployment",
    "TechStack",
    "CodingStandard",
    "DebugSession",
    "PerformanceOptimization",
    "APIDesign",
    "DatabaseDesign",
    "DevelopmentMetrics",
    # Capabilities
    "DEVELOPMENT_CAPABILITIES",
]
