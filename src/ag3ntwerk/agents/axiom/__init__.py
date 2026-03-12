"""Axiom (Axiom) - Axiom Research Module."""

from ag3ntwerk.agents.axiom.agent import Axiom

# Codename alias for product narrative
Axiom = Axiom

# Managers
from ag3ntwerk.agents.axiom.managers import (
    ResearchProjectManager,
    ExperimentationManager,
    DataAnalysisManager,
    AssessmentManager,
)

# Specialists
from ag3ntwerk.agents.axiom.specialists import (
    ResearchScientist,
    DataScientist,
    ExperimentDesigner,
    AnalyticsSpecialist,
    FeasibilityAnalyst,
)

# Models
from ag3ntwerk.agents.axiom.models import (
    # Enums
    ResearchStatus,
    ResearchType,
    HypothesisStatus,
    EvidenceStrength,
    DataQuality,
    ConfidenceLevel,
    AnalysisMethod,
    PublicationStatus,
    # Dataclasses
    ResearchProject,
    Hypothesis,
    Experiment,
    DataSet,
    LiteratureReview,
    DataAnalysis,
    ResearchFinding,
    RootCauseAnalysis,
    FeasibilityStudy,
    Benchmark,
    ResearchPublication,
    ResearchMetrics,
    # Capabilities
    RESEARCH_DOMAIN_CAPABILITIES,
)

__all__ = [
    # Main agent
    "Axiom",
    "Axiom",
    # Managers
    "ResearchProjectManager",
    "ExperimentationManager",
    "DataAnalysisManager",
    "AssessmentManager",
    # Specialists
    "ResearchScientist",
    "DataScientist",
    "ExperimentDesigner",
    "AnalyticsSpecialist",
    "FeasibilityAnalyst",
    # Enums
    "ResearchStatus",
    "ResearchType",
    "HypothesisStatus",
    "EvidenceStrength",
    "DataQuality",
    "ConfidenceLevel",
    "AnalysisMethod",
    "PublicationStatus",
    # Dataclasses
    "ResearchProject",
    "Hypothesis",
    "Experiment",
    "DataSet",
    "LiteratureReview",
    "DataAnalysis",
    "ResearchFinding",
    "RootCauseAnalysis",
    "FeasibilityStudy",
    "Benchmark",
    "ResearchPublication",
    "ResearchMetrics",
    # Capabilities
    "RESEARCH_DOMAIN_CAPABILITIES",
]
