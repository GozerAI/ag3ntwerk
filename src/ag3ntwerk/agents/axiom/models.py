"""
Axiom (Axiom) Research Domain Models.

Data models for research, experimentation, analysis, and scientific investigation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ResearchStatus(Enum):
    """Research project status."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    DATA_COLLECTION = "data_collection"
    ANALYSIS = "analysis"
    REVIEW = "review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class ResearchType(Enum):
    """Types of research."""

    EXPLORATORY = "exploratory"
    DESCRIPTIVE = "descriptive"
    EXPLANATORY = "explanatory"
    EXPERIMENTAL = "experimental"
    CORRELATIONAL = "correlational"
    META_ANALYSIS = "meta_analysis"
    CASE_STUDY = "case_study"
    LITERATURE_REVIEW = "literature_review"


class HypothesisStatus(Enum):
    """Hypothesis testing status."""

    PROPOSED = "proposed"
    UNDER_TEST = "under_test"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    REVISED = "revised"


class EvidenceStrength(Enum):
    """Strength of evidence."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"
    CONTRADICTORY = "contradictory"


class DataQuality(Enum):
    """Data quality levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Statistical confidence levels."""

    VERY_HIGH = "very_high"  # 99%
    HIGH = "high"  # 95%
    MODERATE = "moderate"  # 90%
    LOW = "low"  # 80%
    VERY_LOW = "very_low"  # <80%


class AnalysisMethod(Enum):
    """Types of analysis methods."""

    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    STATISTICAL = "statistical"
    THEMATIC = "thematic"
    COMPARATIVE = "comparative"


class PublicationStatus(Enum):
    """Research publication status."""

    DRAFT = "draft"
    INTERNAL = "internal"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    PUBLISHED = "published"
    REJECTED = "rejected"


@dataclass
class ResearchProject:
    """Represents a research project."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    research_type: ResearchType = ResearchType.EXPLORATORY
    status: ResearchStatus = ResearchStatus.PROPOSED
    principal_investigator: str = ""
    team_members: List[str] = field(default_factory=list)
    research_questions: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    methodology: str = ""
    scope: str = ""
    constraints: List[str] = field(default_factory=list)
    budget: float = 0.0
    start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    deliverables: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypothesis:
    """Represents a research hypothesis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    statement: str = ""
    null_hypothesis: str = ""
    alternative_hypothesis: str = ""
    project_id: Optional[str] = None
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    evidence_strength: EvidenceStrength = EvidenceStrength.INSUFFICIENT
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    tests_performed: List[str] = field(default_factory=list)
    confidence_level: Optional[ConfidenceLevel] = None
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    conclusion: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    tested_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    """Represents an experiment design."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    project_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    objective: str = ""
    independent_variables: List[Dict[str, Any]] = field(default_factory=list)
    dependent_variables: List[Dict[str, Any]] = field(default_factory=list)
    controlled_variables: List[Dict[str, Any]] = field(default_factory=list)
    methodology: str = ""
    sample_size: int = 0
    sampling_method: str = ""
    control_group: bool = True
    randomization: bool = True
    blinding: str = "none"  # none, single, double
    duration_days: int = 0
    data_collection_methods: List[str] = field(default_factory=list)
    analysis_plan: str = ""
    expected_outcomes: List[str] = field(default_factory=list)
    risks_and_mitigations: List[Dict[str, str]] = field(default_factory=list)
    status: ResearchStatus = ResearchStatus.PROPOSED
    created_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSet:
    """Represents a research data set."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    project_id: Optional[str] = None
    source: str = ""
    collection_method: str = ""
    sample_size: int = 0
    variables: List[Dict[str, Any]] = field(default_factory=list)  # {name, type, description}
    quality: DataQuality = DataQuality.UNKNOWN
    quality_issues: List[str] = field(default_factory=list)
    missing_data_percent: float = 0.0
    format: str = ""  # csv, json, parquet, etc.
    size_bytes: int = 0
    collected_at: Optional[datetime] = None
    validated: bool = False
    validated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LiteratureReview:
    """Represents a literature review."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    research_question: str = ""
    scope: str = ""
    methodology: str = ""
    search_strategy: str = ""
    databases_searched: List[str] = field(default_factory=list)
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    sources_found: int = 0
    sources_included: int = 0
    key_themes: List[str] = field(default_factory=list)
    findings_synthesis: str = ""
    gaps_identified: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataAnalysis:
    """Represents a data analysis task."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    dataset_id: Optional[str] = None
    analysis_type: AnalysisMethod = AnalysisMethod.QUANTITATIVE
    research_questions: List[str] = field(default_factory=list)
    methods_used: List[str] = field(default_factory=list)
    statistical_tests: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    visualizations: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_level: Optional[ConfidenceLevel] = None
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchFinding:
    """Represents a research finding."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    summary: str = ""
    detailed_finding: str = ""
    project_id: Optional[str] = None
    analysis_id: Optional[str] = None
    finding_type: str = ""  # insight, pattern, correlation, causation, anomaly
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    supporting_data: List[Dict[str, Any]] = field(default_factory=list)
    implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    validated: bool = False
    validated_by: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCauseAnalysis:
    """Represents a root cause analysis."""

    id: str = field(default_factory=lambda: str(uuid4()))
    problem_statement: str = ""
    symptoms: List[str] = field(default_factory=list)
    scope: str = ""
    timeline: str = ""
    data_collected: List[Dict[str, Any]] = field(default_factory=list)
    analysis_methods: List[str] = field(default_factory=list)  # fishbone, 5whys, fault_tree
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    root_causes: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    corrective_actions: List[Dict[str, Any]] = field(default_factory=list)
    preventive_measures: List[str] = field(default_factory=list)
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    analyst: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeasibilityStudy:
    """Represents a feasibility study."""

    id: str = field(default_factory=lambda: str(uuid4()))
    proposal: str = ""
    description: str = ""
    technical_feasibility: Dict[str, Any] = field(default_factory=dict)
    economic_feasibility: Dict[str, Any] = field(default_factory=dict)
    operational_feasibility: Dict[str, Any] = field(default_factory=dict)
    schedule_feasibility: Dict[str, Any] = field(default_factory=dict)
    legal_feasibility: Dict[str, Any] = field(default_factory=dict)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    overall_assessment: str = ""  # feasible, conditionally_feasible, not_feasible
    recommendations: List[str] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Benchmark:
    """Represents a benchmarking study."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    benchmark_type: str = ""  # competitive, industry, internal, best_practice
    subject: str = ""
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    comparisons: List[Dict[str, Any]] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    gaps_identified: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    status: ResearchStatus = ResearchStatus.IN_PROGRESS
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPublication:
    """Represents a research publication."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    project_id: Optional[str] = None
    publication_type: str = ""  # paper, report, whitepaper, patent
    status: PublicationStatus = PublicationStatus.DRAFT
    venue: str = ""  # journal, conference, internal
    keywords: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    url: Optional[str] = None
    citations: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    submitted_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchMetrics:
    """Research department metrics."""

    timestamp: datetime = field(default_factory=_utcnow)

    # Project metrics
    total_projects: int = 0
    active_projects: int = 0
    completed_projects: int = 0
    on_hold_projects: int = 0

    # Output metrics
    total_findings: int = 0
    validated_findings: int = 0
    total_publications: int = 0
    publications_this_year: int = 0

    # Hypothesis metrics
    hypotheses_tested: int = 0
    hypotheses_supported: int = 0
    hypotheses_refuted: int = 0

    # Quality metrics
    average_confidence_level: float = 0.0
    data_quality_score: float = 0.0
    replication_rate: float = 0.0

    # Efficiency metrics
    avg_project_duration_days: float = 0.0
    findings_per_project: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


# Research capabilities
RESEARCH_DOMAIN_CAPABILITIES = [
    # Core research
    "deep_research",
    "literature_review",
    "experiment_design",
    "hypothesis_testing",
    "meta_analysis",
    # Analysis
    "data_analysis",
    "statistical_analysis",
    "qualitative_analysis",
    "trend_research",
    "root_cause_analysis",
    # Assessment
    "feasibility_study",
    "technology_assessment",
    "impact_analysis",
    "benchmarking",
    # Publication
    "research_writing",
    "patent_analysis",
    "peer_review",
]
