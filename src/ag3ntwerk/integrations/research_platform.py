"""
Research Platform Bridge - Integration between ag3ntwerk Axiom and AI Platform.

This module provides a bridge connecting the Axiom (Axiom)
to the ai-platform-unified research capabilities:
- Deep research execution
- Expert panel consultation
- Insight discovery
- Research synthesis

Primary user:
- Axiom (Axiom): Research coordination, methodology, insights

Features:
- Multi-source research aggregation
- Expert consensus integration
- Research project management
- Finding synthesis and validation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ResearchType(Enum):
    """Types of research that can be conducted."""

    DEEP_RESEARCH = "deep_research"
    LITERATURE_REVIEW = "literature_review"
    MARKET_RESEARCH = "market_research"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    TECHNOLOGY_SCAN = "technology_scan"
    TREND_ANALYSIS = "trend_analysis"
    FEASIBILITY_STUDY = "feasibility_study"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    META_ANALYSIS = "meta_analysis"


class ResearchStatus(Enum):
    """Status of a research project."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    NEEDS_MORE_DATA = "needs_more_data"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ConfidenceLevel(Enum):
    """Confidence level for research findings."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EvidenceStrength(Enum):
    """Strength of evidence for findings."""

    ANECDOTAL = "anecdotal"
    OBSERVATIONAL = "observational"
    CORRELATIONAL = "correlational"
    EXPERIMENTAL = "experimental"
    META_ANALYTIC = "meta_analytic"


@dataclass
class ResearchSource:
    """A source used in research."""

    id: str
    name: str
    source_type: str  # api, database, document, web, expert
    reliability_score: float = 0.8
    last_updated: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchFinding:
    """A finding from research."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    evidence: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_strength: EvidenceStrength = EvidenceStrength.OBSERVATIONAL
    sources: List[str] = field(default_factory=list)
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence.value,
            "evidence_strength": self.evidence_strength.value,
            "sources": self.sources,
            "implications": self.implications,
            "limitations": self.limitations,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExpertOpinion:
    """Opinion from an expert in the panel."""

    expert_id: str
    expert_type: str  # analyst, researcher, engineer, strategist
    opinion: str
    confidence: float = 0.8
    supporting_evidence: List[str] = field(default_factory=list)
    dissenting_points: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """Result of expert panel consensus."""

    topic: str
    consensus_reached: bool = False
    consensus_statement: str = ""
    confidence_score: float = 0.0
    agreement_level: float = 0.0
    opinions: List[ExpertOpinion] = field(default_factory=list)
    key_agreements: List[str] = field(default_factory=list)
    key_disagreements: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchProject:
    """A research project managed by the Axiom."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    research_type: ResearchType = ResearchType.DEEP_RESEARCH
    status: ResearchStatus = ResearchStatus.QUEUED
    objectives: List[str] = field(default_factory=list)
    methodology: Optional[str] = None
    sources_consulted: List[str] = field(default_factory=list)
    findings: List[ResearchFinding] = field(default_factory=list)
    consensus: Optional[ConsensusResult] = None
    requester: str = ""
    priority: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "research_type": self.research_type.value,
            "status": self.status.value,
            "objectives": self.objectives,
            "findings_count": len(self.findings),
            "has_consensus": self.consensus is not None,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ResearchPlatformBridge:
    """
    Bridge between Axiom (Axiom) and AI Platform research capabilities.

    This bridge enables:
    1. Deep research execution with multiple sources
    2. Expert panel consultation
    3. Insight discovery and synthesis
    4. Research project management

    Usage:
        bridge = ResearchPlatformBridge()
        bridge.connect_platform(ai_platform, expert_panel, insights_engine)

        # Create research project
        project = await bridge.create_research_project(
            title="AI in Healthcare Market Analysis",
            research_type=ResearchType.MARKET_RESEARCH,
            objectives=["Identify market size", "Map key players"],
        )

        # Execute research
        results = await bridge.execute_research(project.id)

        # Get expert consensus
        consensus = await bridge.get_expert_consensus(project.id)
    """

    # Confidence level scoring
    CONFIDENCE_SCORES = {
        ConfidenceLevel.VERY_LOW: 0.2,
        ConfidenceLevel.LOW: 0.4,
        ConfidenceLevel.MEDIUM: 0.6,
        ConfidenceLevel.HIGH: 0.8,
        ConfidenceLevel.VERY_HIGH: 0.95,
    }

    # Evidence strength multipliers
    EVIDENCE_MULTIPLIERS = {
        EvidenceStrength.ANECDOTAL: 0.5,
        EvidenceStrength.OBSERVATIONAL: 0.7,
        EvidenceStrength.CORRELATIONAL: 0.8,
        EvidenceStrength.EXPERIMENTAL: 0.9,
        EvidenceStrength.META_ANALYTIC: 1.0,
    }

    def __init__(
        self,
        cro: Optional[Any] = None,
    ):
        """
        Initialize the Research Platform bridge.

        Args:
            cro: Optional Axiom instance
        """
        self._cro = cro

        # AI Platform connections
        self._ai_platform: Optional[Any] = None
        self._expert_panel: Optional[Any] = None
        self._insights_engine: Optional[Any] = None
        self._consensus_engine: Optional[Any] = None

        # Research sources
        self._sources: Dict[str, ResearchSource] = {}

        # Projects and findings
        self._projects: Dict[UUID, ResearchProject] = {}
        self._findings_db: Dict[str, List[ResearchFinding]] = {}

        # Expert configuration
        self._expert_types = [
            "research_expert",
            "analyst_expert",
            "engineer_expert",
            "strategist_expert",
            "critic_expert",
        ]

        # Metrics
        self._metrics = {
            "projects_created": 0,
            "projects_completed": 0,
            "findings_generated": 0,
            "consensus_reached": 0,
            "avg_confidence_score": 0.0,
            "total_research_hours": 0.0,
        }

        logger.info("ResearchPlatformBridge initialized")

    def connect_platform(
        self,
        ai_platform: Any = None,
        expert_panel: Any = None,
        insights_engine: Any = None,
        consensus_engine: Any = None,
    ) -> None:
        """
        Connect to AI Platform research systems.

        Args:
            ai_platform: UnifiedAIPlatform instance
            expert_panel: Expert panel for opinions
            insights_engine: InsightsEngine for discovery
            consensus_engine: ConsensusEngine for expert agreement
        """
        if ai_platform:
            self._ai_platform = ai_platform
            logger.info("Connected UnifiedAIPlatform")
        if expert_panel:
            self._expert_panel = expert_panel
            logger.info("Connected Expert Panel")
        if insights_engine:
            self._insights_engine = insights_engine
            logger.info("Connected Insights Engine")
        if consensus_engine:
            self._consensus_engine = consensus_engine
            logger.info("Connected Consensus Engine")

    def connect_cro(self, cro: Any) -> None:
        """Connect Axiom (Axiom) to the bridge."""
        self._cro = cro
        logger.info("Connected Axiom (Axiom) to research platform")

    def register_source(self, source: ResearchSource) -> None:
        """Register a research source."""
        self._sources[source.id] = source
        logger.info(f"Registered research source: {source.name}")

    async def create_research_project(
        self,
        title: str,
        research_type: ResearchType = ResearchType.DEEP_RESEARCH,
        description: str = "",
        objectives: Optional[List[str]] = None,
        methodology: Optional[str] = None,
        requester: str = "",
        priority: int = 5,
    ) -> ResearchProject:
        """
        Create a new research project.

        Args:
            title: Project title
            research_type: Type of research
            description: Project description
            objectives: Research objectives
            methodology: Research methodology
            requester: Who requested the research
            priority: Priority level (1-10)

        Returns:
            Created ResearchProject
        """
        project = ResearchProject(
            title=title,
            description=description,
            research_type=research_type,
            objectives=objectives or [],
            methodology=methodology,
            requester=requester,
            priority=priority,
        )

        self._projects[project.id] = project
        self._metrics["projects_created"] += 1

        logger.info(f"Created research project: {title}")
        return project

    async def execute_research(
        self,
        project_id: UUID,
        use_experts: bool = True,
        depth: str = "comprehensive",
    ) -> ResearchProject:
        """
        Execute research for a project.

        Args:
            project_id: Project identifier
            use_experts: Whether to use expert panel
            depth: Research depth (quick, standard, comprehensive)

        Returns:
            Updated ResearchProject with findings
        """
        if project_id not in self._projects:
            raise ValueError(f"Unknown project: {project_id}")

        project = self._projects[project_id]
        project.status = ResearchStatus.IN_PROGRESS
        project.started_at = datetime.now(timezone.utc)

        findings = []

        # Use AI Platform for research
        if self._ai_platform:
            try:
                # Build research query
                query = self._build_research_query(project, depth)

                # Execute research
                result = await self._ai_platform.research(query)

                # Parse findings from result
                parsed_findings = self._parse_research_result(result, project)
                findings.extend(parsed_findings)

            except Exception as e:
                logger.error(f"AI Platform research failed: {e}")
                project.metadata["research_error"] = str(e)

        # Use insights engine for discovery
        if self._insights_engine:
            try:
                insights = await self._insights_engine.discover(
                    topic=project.title,
                    context=project.description,
                )
                insight_findings = self._convert_insights_to_findings(insights)
                findings.extend(insight_findings)

            except Exception as e:
                logger.error(f"Insights discovery failed: {e}")

        # Get expert opinions if requested
        if use_experts and (self._expert_panel or self._consensus_engine):
            try:
                consensus = await self._get_expert_consensus_internal(
                    project.title,
                    project.description,
                    findings,
                )
                project.consensus = consensus

                if consensus.consensus_reached:
                    self._metrics["consensus_reached"] += 1

            except Exception as e:
                logger.error(f"Expert consensus failed: {e}")

        # Update project
        project.findings = findings
        project.sources_consulted = list(self._sources.keys())
        project.status = (
            ResearchStatus.AWAITING_REVIEW if findings else ResearchStatus.NEEDS_MORE_DATA
        )
        project.completed_at = datetime.now(timezone.utc)

        # Store findings by topic
        topic_key = project.title.lower().replace(" ", "_")
        if topic_key not in self._findings_db:
            self._findings_db[topic_key] = []
        self._findings_db[topic_key].extend(findings)

        self._metrics["findings_generated"] += len(findings)

        if project.status == ResearchStatus.AWAITING_REVIEW:
            self._metrics["projects_completed"] += 1

        return project

    def _build_research_query(self, project: ResearchProject, depth: str) -> str:
        """Build research query for AI Platform."""
        depth_instructions = {
            "quick": "Provide a brief overview with key points only.",
            "standard": "Provide a comprehensive analysis with supporting evidence.",
            "comprehensive": "Provide an exhaustive analysis covering all aspects, with multiple perspectives and detailed evidence.",
        }

        query = f"""Research Topic: {project.title}

Description: {project.description}

Research Objectives:
{chr(10).join(f'- {obj}' for obj in project.objectives) if project.objectives else '- General exploration of the topic'}

Research Type: {project.research_type.value}

{depth_instructions.get(depth, depth_instructions['standard'])}

Provide structured findings including:
1. Key insights and discoveries
2. Supporting evidence
3. Confidence levels
4. Implications
5. Limitations and caveats
6. Recommendations for further research"""

        return query

    def _parse_research_result(
        self,
        result: Any,
        project: ResearchProject,
    ) -> List[ResearchFinding]:
        """Parse research result into findings."""
        findings = []

        # Handle string result
        if isinstance(result, str):
            # Create a main finding from the result
            finding = ResearchFinding(
                title=f"Research: {project.title}",
                description=result[:500] + "..." if len(result) > 500 else result,
                evidence=result,
                confidence=ConfidenceLevel.MEDIUM,
                evidence_strength=EvidenceStrength.OBSERVATIONAL,
                sources=["ai_platform"],
            )
            findings.append(finding)

        # Handle structured result
        elif isinstance(result, dict):
            if "findings" in result:
                for f in result["findings"]:
                    finding = ResearchFinding(
                        title=f.get("title", "Finding"),
                        description=f.get("description", ""),
                        evidence=f.get("evidence", ""),
                        confidence=ConfidenceLevel(f.get("confidence", "medium")),
                        sources=f.get("sources", []),
                    )
                    findings.append(finding)
            else:
                finding = ResearchFinding(
                    title=f"Research: {project.title}",
                    description=str(result),
                    confidence=ConfidenceLevel.MEDIUM,
                )
                findings.append(finding)

        return findings

    def _convert_insights_to_findings(
        self,
        insights: Any,
    ) -> List[ResearchFinding]:
        """Convert insights to research findings."""
        findings = []

        if isinstance(insights, list):
            for insight in insights:
                if isinstance(insight, dict):
                    finding = ResearchFinding(
                        title=insight.get("title", "Insight"),
                        description=insight.get("description", str(insight)),
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_strength=EvidenceStrength.OBSERVATIONAL,
                        sources=["insights_engine"],
                    )
                    findings.append(finding)

        return findings

    async def _get_expert_consensus_internal(
        self,
        topic: str,
        context: str,
        findings: List[ResearchFinding],
    ) -> ConsensusResult:
        """Get expert consensus on findings."""
        opinions = []

        # Use consensus engine if available
        if self._consensus_engine:
            try:
                result = await self._consensus_engine.consensus(
                    topic=topic,
                    context=context,
                    findings=[f.to_dict() for f in findings],
                )

                if isinstance(result, dict):
                    return ConsensusResult(
                        topic=topic,
                        consensus_reached=result.get("consensus_reached", False),
                        consensus_statement=result.get("statement", ""),
                        confidence_score=result.get("confidence", 0.0),
                        agreement_level=result.get("agreement", 0.0),
                        recommendations=result.get("recommendations", []),
                    )

            except Exception as e:
                logger.error(f"Consensus engine failed: {e}")

        # Use expert panel if available
        if self._expert_panel:
            try:
                for expert_type in self._expert_types:
                    opinion = await self._expert_panel.generate_opinion(
                        expert_type=expert_type,
                        topic=topic,
                        context=context,
                    )
                    if opinion:
                        opinions.append(
                            ExpertOpinion(
                                expert_id=expert_type,
                                expert_type=expert_type.split("_")[0],
                                opinion=opinion.get("opinion", ""),
                                confidence=opinion.get("confidence", 0.7),
                                recommendations=opinion.get("recommendations", []),
                            )
                        )

            except Exception as e:
                logger.error(f"Expert panel failed: {e}")

        # Synthesize consensus from opinions
        if opinions:
            avg_confidence = sum(o.confidence for o in opinions) / len(opinions)
            consensus_reached = avg_confidence >= 0.7

            return ConsensusResult(
                topic=topic,
                consensus_reached=consensus_reached,
                confidence_score=avg_confidence,
                agreement_level=avg_confidence,
                opinions=opinions,
                recommendations=[rec for o in opinions for rec in o.recommendations][:5],
            )

        # Fallback consensus
        return ConsensusResult(
            topic=topic,
            consensus_reached=False,
            consensus_statement="No expert consensus available",
        )

    async def get_expert_consensus(
        self,
        project_id: UUID,
    ) -> ConsensusResult:
        """
        Get or refresh expert consensus for a project.

        Args:
            project_id: Project identifier

        Returns:
            ConsensusResult with expert opinions
        """
        if project_id not in self._projects:
            raise ValueError(f"Unknown project: {project_id}")

        project = self._projects[project_id]

        consensus = await self._get_expert_consensus_internal(
            project.title,
            project.description,
            project.findings,
        )

        project.consensus = consensus
        return consensus

    def get_finding_confidence_score(self, finding: ResearchFinding) -> float:
        """Calculate overall confidence score for a finding."""
        base_score = self.CONFIDENCE_SCORES.get(finding.confidence, 0.6)
        multiplier = self.EVIDENCE_MULTIPLIERS.get(finding.evidence_strength, 0.7)

        # Adjust for number of sources
        source_bonus = min(0.1, len(finding.sources) * 0.02)

        return min(1.0, base_score * multiplier + source_bonus)

    async def synthesize_findings(
        self,
        topic: str,
        include_consensus: bool = True,
    ) -> Dict[str, Any]:
        """
        Synthesize all findings related to a topic.

        Args:
            topic: Topic to synthesize
            include_consensus: Whether to include consensus analysis

        Returns:
            Synthesized findings report
        """
        topic_key = topic.lower().replace(" ", "_")
        findings = self._findings_db.get(topic_key, [])

        # Find related projects
        related_projects = [
            p
            for p in self._projects.values()
            if topic.lower() in p.title.lower() or topic.lower() in p.description.lower()
        ]

        # Aggregate findings from projects
        for project in related_projects:
            findings.extend(project.findings)

        # Deduplicate
        seen_titles = set()
        unique_findings = []
        for f in findings:
            if f.title not in seen_titles:
                seen_titles.add(f.title)
                unique_findings.append(f)

        # Score and sort findings
        scored_findings = [(f, self.get_finding_confidence_score(f)) for f in unique_findings]
        scored_findings.sort(key=lambda x: x[1], reverse=True)

        # Build synthesis
        synthesis = {
            "topic": topic,
            "total_findings": len(unique_findings),
            "related_projects": len(related_projects),
            "top_findings": [{**f.to_dict(), "score": score} for f, score in scored_findings[:10]],
            "confidence_distribution": self._get_confidence_distribution(unique_findings),
            "evidence_distribution": self._get_evidence_distribution(unique_findings),
            "key_implications": self._extract_key_implications(unique_findings),
            "limitations": self._extract_limitations(unique_findings),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add consensus if available
        if include_consensus:
            consensus_results = [p.consensus for p in related_projects if p.consensus is not None]
            if consensus_results:
                synthesis["consensus_summary"] = {
                    "projects_with_consensus": len(consensus_results),
                    "avg_agreement": sum(c.agreement_level for c in consensus_results)
                    / len(consensus_results),
                    "overall_recommendations": list(
                        set(rec for c in consensus_results for rec in c.recommendations)
                    )[:10],
                }

        return synthesis

    def _get_confidence_distribution(
        self,
        findings: List[ResearchFinding],
    ) -> Dict[str, int]:
        """Get distribution of confidence levels."""
        dist = {level.value: 0 for level in ConfidenceLevel}
        for f in findings:
            dist[f.confidence.value] += 1
        return dist

    def _get_evidence_distribution(
        self,
        findings: List[ResearchFinding],
    ) -> Dict[str, int]:
        """Get distribution of evidence strengths."""
        dist = {strength.value: 0 for strength in EvidenceStrength}
        for f in findings:
            dist[f.evidence_strength.value] += 1
        return dist

    def _extract_key_implications(
        self,
        findings: List[ResearchFinding],
    ) -> List[str]:
        """Extract key implications from findings."""
        implications = []
        for f in findings:
            implications.extend(f.implications)
        return list(set(implications))[:10]

    def _extract_limitations(
        self,
        findings: List[ResearchFinding],
    ) -> List[str]:
        """Extract limitations from findings."""
        limitations = []
        for f in findings:
            limitations.extend(f.limitations)
        return list(set(limitations))[:10]

    def get_research_for_cro(self) -> Dict[str, Any]:
        """
        Get research data formatted for Axiom analysis.

        Returns:
            Data structured for Axiom consumption
        """
        status_counts = {}
        for p in self._projects.values():
            status = p.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        type_counts = {}
        for p in self._projects.values():
            rt = p.research_type.value
            type_counts[rt] = type_counts.get(rt, 0) + 1

        return {
            "summary": {
                "total_projects": len(self._projects),
                "active_projects": len(
                    [p for p in self._projects.values() if p.status == ResearchStatus.IN_PROGRESS]
                ),
                "total_findings": sum(len(p.findings) for p in self._projects.values()),
                "registered_sources": len(self._sources),
            },
            "by_status": status_counts,
            "by_type": type_counts,
            "recent_projects": [
                p.to_dict()
                for p in sorted(
                    self._projects.values(),
                    key=lambda x: x.created_at,
                    reverse=True,
                )[:10]
            ],
            "high_priority_projects": [
                p.to_dict()
                for p in sorted(
                    [p for p in self._projects.values() if p.priority >= 7],
                    key=lambda x: x.priority,
                    reverse=True,
                )[:5]
            ],
            "platform_status": {
                "ai_platform_connected": self._ai_platform is not None,
                "expert_panel_connected": self._expert_panel is not None,
                "insights_engine_connected": self._insights_engine is not None,
                "consensus_engine_connected": self._consensus_engine is not None,
            },
            "metrics": self._metrics,
        }

    def approve_project(self, project_id: UUID) -> bool:
        """Approve research project as complete."""
        if project_id not in self._projects:
            return False

        project = self._projects[project_id]
        project.status = ResearchStatus.COMPLETED
        return True

    def archive_project(self, project_id: UUID) -> bool:
        """Archive a research project."""
        if project_id not in self._projects:
            return False

        project = self._projects[project_id]
        project.status = ResearchStatus.ARCHIVED
        return True

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "cro_connected": self._cro is not None,
            "ai_platform_connected": self._ai_platform is not None,
            "expert_panel_connected": self._expert_panel is not None,
            "insights_engine_connected": self._insights_engine is not None,
            "consensus_engine_connected": self._consensus_engine is not None,
            "registered_sources": len(self._sources),
            "active_projects": len(
                [p for p in self._projects.values() if p.status == ResearchStatus.IN_PROGRESS]
            ),
            **self._metrics,
        }
