"""
Autonomous Research - Deep research workflows for the ag3ntwerk platform.

Extends the AutonomousWorkflow pattern to provide specialized research
processes including market intelligence scanning, technology radar,
trend deep research, and competitive intelligence gathering.

Each workflow produces structured output that can be aggregated by
the AutonomousResearchEngine coordinator.
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ag3ntwerk.modules.autonomous_workflows import (
    AutonomousWorkflow,
    AutonomousWorkflowResult,
    WorkflowStepResult,
)
from ag3ntwerk.modules.integration import ModuleIntegration, get_integration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Research-specific data structures
# ---------------------------------------------------------------------------


@dataclass
class ResearchRecord:
    """A timestamped record of a research execution."""

    research_type: str
    result: AutonomousWorkflowResult
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the record to a dictionary."""
        return {
            "research_type": self.research_type,
            "executed_at": self.executed_at.isoformat(),
            "success": self.result.success,
            "summary": self.result.summary,
            "workflow": self.result.to_dict(),
        }


@dataclass
class RecurringSchedule:
    """Configuration for a recurring research schedule."""

    research_type: str
    interval_hours: float
    last_run: Optional[datetime] = None
    enabled: bool = True

    @property
    def next_run(self) -> Optional[datetime]:
        """Calculate the next scheduled run time."""
        if self.last_run is None:
            return datetime.now(timezone.utc)
        from datetime import timedelta

        return self.last_run + timedelta(hours=self.interval_hours)

    @property
    def is_due(self) -> bool:
        """Return True when the schedule is due for execution."""
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        return datetime.now(timezone.utc) >= self.next_run


# ---------------------------------------------------------------------------
# Workflow helper mixin
# ---------------------------------------------------------------------------


class _ResearchStepMixin:
    """
    Shared step-execution logic for research workflows.

    Provides the ``_run_step`` helper that is consistent with the pattern
    used throughout ``autonomous_workflows.py``.
    """

    async def _run_step(
        self,
        step_name: str,
        module: str,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> WorkflowStepResult:
        """
        Execute a single workflow step with timing and error handling.

        Args:
            step_name: Human-readable name for this step.
            module: The module identifier associated with this step.
            func: The callable to execute (sync or async).
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            A ``WorkflowStepResult`` capturing success/failure and output.
        """
        step_result = WorkflowStepResult(
            step_name=step_name,
            module=module,
            success=False,
            started_at=datetime.now(timezone.utc),
        )

        try:
            if inspect.iscoroutinefunction(func):
                output = await func(*args, **kwargs)
            else:
                output = func(*args, **kwargs)

            step_result.success = True
            step_result.output = output

        except Exception as e:
            step_result.error = str(e)
            logger.error("Research step '%s' failed: %s", step_name, e)

        step_result.completed_at = datetime.now(timezone.utc)
        step_result.duration_seconds = (
            step_result.completed_at - step_result.started_at
        ).total_seconds()

        return step_result


# ---------------------------------------------------------------------------
# MarketIntelligenceWorkflow
# ---------------------------------------------------------------------------


class MarketIntelligenceWorkflow(_ResearchStepMixin, AutonomousWorkflow):
    """
    Market Intelligence Scan Workflow.

    Performs a comprehensive market intelligence scan through four stages:
    1. Gather market signals from available trend and commerce sources.
    2. Analyze the competitive landscape.
    3. Identify strategic opportunities and risk factors.
    4. Generate a consolidated insights report.

    Produces structured output containing:
        - market_signals
        - competitors
        - opportunities
        - risk_factors
    """

    name = "market_intelligence_scan"
    description = "Gather and analyze market intelligence signals"
    owner_executive = "Echo"

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the market intelligence scan workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1: Gather market signals -----------------------------------
        step1 = await self._run_step(
            "Gather Market Signals",
            "trends",
            self._gather_market_signals,
            ctx,
        )
        result.steps.append(step1)

        # Step 2: Analyze competitive landscape ---------------------------
        step2 = await self._run_step(
            "Analyze Competitive Landscape",
            "trends",
            self._analyze_competitive_landscape,
            step1.output if step1.success else {},
            ctx,
        )
        result.steps.append(step2)

        # Step 3: Identify opportunities ----------------------------------
        step3 = await self._run_step(
            "Identify Opportunities",
            "trends",
            self._identify_opportunities,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            ctx,
        )
        result.steps.append(step3)

        # Step 4: Generate insights report --------------------------------
        step4 = await self._run_step(
            "Generate Insights Report",
            "integration",
            self._generate_insights_report,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Compile summary -------------------------------------------------
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "market_signals": step1.output if step1.success else step1.error,
            "competitors": step2.output if step2.success else step2.error,
            "opportunities": step3.output if step3.success else step3.error,
            "risk_factors": (
                step3.output.get("risk_factors", [])
                if step3.success and isinstance(step3.output, dict)
                else []
            ),
            "insights_report": step4.output if step4.success else step4.error,
        }

        return result

    # -- internal helpers --------------------------------------------------

    async def _gather_market_signals(
        self,
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect market signals from trend and commerce data."""
        signals: Dict[str, Any] = {
            "trending_topics": [],
            "commerce_indicators": [],
            "source_count": 0,
        }

        try:
            sources = ctx.get("sources", ["google", "reddit", "hackernews"])
            trend_data = await self._integration.execute_module_task(
                "trends",
                "run_analysis",
                {"sources": sources},
            )
            signals["trending_topics"] = trend_data.get("trends", [])
            signals["source_count"] = len(sources)
        except Exception as e:
            logger.warning("Trend signal collection encountered an issue: %s", e)
            signals["trend_error"] = str(e)

        try:
            commerce_data = self._integration.commerce_service.get_margin_analysis()
            signals["commerce_indicators"] = commerce_data.get("products", [])
        except Exception as e:
            logger.warning("Commerce signal collection encountered an issue: %s", e)
            signals["commerce_error"] = str(e)

        return signals

    async def _analyze_competitive_landscape(
        self,
        market_signals: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze the competitive landscape from gathered signals."""
        competitors: List[Dict[str, Any]] = []
        trending = market_signals.get("trending_topics", [])

        for topic in trending[:10]:
            name = topic if isinstance(topic, str) else topic.get("name", "unknown")
            competitors.append(
                {
                    "topic": name,
                    "competitive_intensity": "moderate",
                    "market_saturation": "medium",
                }
            )

        return {
            "competitors": competitors,
            "landscape_assessment": (
                "high_competition" if len(competitors) > 5 else "moderate_competition"
            ),
            "analyzed_signals": len(trending),
        }

    async def _identify_opportunities(
        self,
        market_signals: Dict[str, Any],
        landscape: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Identify strategic opportunities and risk factors."""
        min_score = ctx.get("min_opportunity_score", 50)
        opportunities: List[Dict[str, Any]] = []
        risk_factors: List[Dict[str, Any]] = []

        try:
            niche_data = self._integration.trend_service.identify_niches(
                min_opportunity_score=min_score,
            )
            for niche in niche_data.get("niches", []):
                opportunities.append(
                    {
                        "name": niche.get("name", "unknown"),
                        "score": niche.get("opportunity_score", 0),
                        "category": niche.get("category", "general"),
                    }
                )
        except Exception as e:
            logger.warning("Niche identification encountered an issue: %s", e)

        intensity = landscape.get("landscape_assessment", "moderate_competition")
        if intensity == "high_competition":
            risk_factors.append(
                {
                    "type": "market_saturation",
                    "severity": "high",
                    "description": "Market shows high competitive intensity",
                }
            )

        if not opportunities:
            risk_factors.append(
                {
                    "type": "low_opportunity",
                    "severity": "medium",
                    "description": "No significant niche opportunities detected",
                }
            )

        return {
            "opportunities": opportunities,
            "risk_factors": risk_factors,
            "opportunity_count": len(opportunities),
            "risk_count": len(risk_factors),
        }

    def _generate_insights_report(
        self,
        signals: Dict[str, Any],
        landscape: Dict[str, Any],
        opportunities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compile all findings into a consolidated insights report."""
        return {
            "report_type": "market_intelligence_scan",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "signal_count": signals.get("source_count", 0),
            "competitor_count": len(landscape.get("competitors", [])),
            "opportunity_count": opportunities.get("opportunity_count", 0),
            "risk_count": opportunities.get("risk_count", 0),
            "top_opportunities": opportunities.get("opportunities", [])[:5],
            "top_risks": opportunities.get("risk_factors", [])[:5],
            "landscape_assessment": landscape.get("landscape_assessment", "unknown"),
        }


# ---------------------------------------------------------------------------
# TechnologyRadarWorkflow
# ---------------------------------------------------------------------------


class TechnologyRadarWorkflow(_ResearchStepMixin, AutonomousWorkflow):
    """
    Technology Radar Scan Workflow.

    Scans the technology landscape and evaluates emerging technologies
    for relevance and adoption risk through four stages:
    1. Scan the tech landscape for emerging technologies.
    2. Evaluate relevance to current business objectives.
    3. Assess adoption risks and readiness.
    4. Generate prioritized recommendations.

    Produces structured output containing:
        - emerging_technologies
        - relevance_scores
        - adoption_recommendations
    """

    name = "technology_radar_scan"
    description = "Scan and evaluate the emerging technology landscape"
    owner_executive = "Forge"

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the technology radar scan workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1: Scan tech landscape -------------------------------------
        step1 = await self._run_step(
            "Scan Tech Landscape",
            "trends",
            self._scan_tech_landscape,
            ctx,
        )
        result.steps.append(step1)

        # Step 2: Evaluate relevance --------------------------------------
        step2 = await self._run_step(
            "Evaluate Relevance",
            "trends",
            self._evaluate_relevance,
            step1.output if step1.success else {},
            ctx,
        )
        result.steps.append(step2)

        # Step 3: Assess adoption risk ------------------------------------
        step3 = await self._run_step(
            "Assess Adoption Risk",
            "trends",
            self._assess_adoption_risk,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
        )
        result.steps.append(step3)

        # Step 4: Generate recommendations --------------------------------
        step4 = await self._run_step(
            "Generate Recommendations",
            "integration",
            self._generate_recommendations,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Compile summary -------------------------------------------------
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "emerging_technologies": (
                step1.output.get("technologies", [])
                if step1.success and isinstance(step1.output, dict)
                else []
            ),
            "relevance_scores": (
                step2.output.get("scores", {})
                if step2.success and isinstance(step2.output, dict)
                else {}
            ),
            "adoption_recommendations": (
                step4.output.get("recommendations", [])
                if step4.success and isinstance(step4.output, dict)
                else []
            ),
        }

        return result

    # -- internal helpers --------------------------------------------------

    async def _scan_tech_landscape(
        self,
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Scan trending technology topics from available sources."""
        technologies: List[Dict[str, Any]] = []

        try:
            sources = ctx.get("tech_sources", ["hackernews", "producthunt"])
            trend_data = await self._integration.execute_module_task(
                "trends",
                "run_analysis",
                {"sources": sources},
            )
            for trend in trend_data.get("trends", []):
                name = trend if isinstance(trend, str) else trend.get("name", "unknown")
                technologies.append(
                    {
                        "name": name,
                        "source": "trend_scan",
                        "category": "emerging",
                        "first_seen": datetime.now(timezone.utc).isoformat(),
                    }
                )
        except Exception as e:
            logger.warning("Tech landscape scan encountered an issue: %s", e)

        return {
            "technologies": technologies,
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "technology_count": len(technologies),
        }

    def _evaluate_relevance(
        self,
        tech_data: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score each technology for business relevance."""
        scores: Dict[str, float] = {}
        business_focus = ctx.get("business_focus", [])

        for tech in tech_data.get("technologies", []):
            name = tech.get("name", "unknown")
            # Default relevance heuristic: higher if business focus keywords match
            base_score = 50.0
            if business_focus:
                for keyword in business_focus:
                    if keyword.lower() in name.lower():
                        base_score += 20.0
            scores[name] = min(base_score, 100.0)

        return {
            "scores": scores,
            "evaluated_count": len(scores),
            "high_relevance": [k for k, v in scores.items() if v >= 70.0],
        }

    def _assess_adoption_risk(
        self,
        tech_data: Dict[str, Any],
        relevance_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess adoption risk for each technology."""
        risk_assessments: List[Dict[str, Any]] = []
        scores = relevance_data.get("scores", {})

        for tech in tech_data.get("technologies", []):
            name = tech.get("name", "unknown")
            relevance = scores.get(name, 50.0)

            # Simple risk classification based on relevance
            if relevance >= 70.0:
                risk_level = "low"
                readiness = "adopt"
            elif relevance >= 50.0:
                risk_level = "medium"
                readiness = "trial"
            else:
                risk_level = "high"
                readiness = "assess"

            risk_assessments.append(
                {
                    "technology": name,
                    "risk_level": risk_level,
                    "readiness": readiness,
                    "relevance_score": relevance,
                }
            )

        return {
            "assessments": risk_assessments,
            "total_assessed": len(risk_assessments),
            "adopt_ready": len([a for a in risk_assessments if a["readiness"] == "adopt"]),
            "trial_ready": len([a for a in risk_assessments if a["readiness"] == "trial"]),
            "assess_only": len([a for a in risk_assessments if a["readiness"] == "assess"]),
        }

    def _generate_recommendations(
        self,
        tech_data: Dict[str, Any],
        relevance_data: Dict[str, Any],
        risk_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate prioritized adoption recommendations."""
        recommendations: List[Dict[str, Any]] = []

        for assessment in risk_data.get("assessments", []):
            tech_name = assessment.get("technology", "unknown")
            recommendations.append(
                {
                    "technology": tech_name,
                    "action": assessment.get("readiness", "assess"),
                    "risk_level": assessment.get("risk_level", "high"),
                    "relevance_score": assessment.get("relevance_score", 0.0),
                    "rationale": (
                        f"{tech_name} is recommended for "
                        f"{assessment.get('readiness', 'assessment')} "
                        f"with {assessment.get('risk_level', 'unknown')} adoption risk."
                    ),
                }
            )

        # Sort by relevance descending
        recommendations.sort(key=lambda r: r["relevance_score"], reverse=True)

        return {
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_recommendations": len(recommendations),
        }


# ---------------------------------------------------------------------------
# TrendResearchWorkflow
# ---------------------------------------------------------------------------


class TrendResearchWorkflow(_ResearchStepMixin, AutonomousWorkflow):
    """
    Trend Deep Research Workflow.

    Performs deep research into identified trends through four stages:
    1. Collect trend data from multiple sources.
    2. Cross-reference sources for validation.
    3. Validate emerging patterns statistically.
    4. Synthesize findings into actionable insights.

    Uses ``integration.trend_service`` when available for direct
    trend data access.

    Produces structured output containing:
        - trends
        - validation_scores
        - actionable_insights
    """

    name = "trend_deep_research"
    description = "Deep research and validation of identified trends"
    owner_executive = "Echo"

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the trend deep research workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1: Collect trend data --------------------------------------
        step1 = await self._run_step(
            "Collect Trend Data",
            "trends",
            self._collect_trend_data,
            ctx,
        )
        result.steps.append(step1)

        # Step 2: Cross-reference sources ---------------------------------
        step2 = await self._run_step(
            "Cross-Reference Sources",
            "trends",
            self._cross_reference_sources,
            step1.output if step1.success else {},
            ctx,
        )
        result.steps.append(step2)

        # Step 3: Validate patterns ---------------------------------------
        step3 = await self._run_step(
            "Validate Patterns",
            "trends",
            self._validate_patterns,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
        )
        result.steps.append(step3)

        # Step 4: Synthesize findings -------------------------------------
        step4 = await self._run_step(
            "Synthesize Findings",
            "integration",
            self._synthesize_findings,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Compile summary -------------------------------------------------
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "trends": (
                step1.output.get("trends", [])
                if step1.success and isinstance(step1.output, dict)
                else []
            ),
            "validation_scores": (
                step3.output.get("validation_scores", {})
                if step3.success and isinstance(step3.output, dict)
                else {}
            ),
            "actionable_insights": (
                step4.output.get("actionable_insights", [])
                if step4.success and isinstance(step4.output, dict)
                else []
            ),
        }

        return result

    # -- internal helpers --------------------------------------------------

    async def _collect_trend_data(
        self,
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect raw trend data using the trend service."""
        trends: List[Dict[str, Any]] = []
        sources_used: List[str] = []

        # Use integration.trend_service when available
        try:
            trend_service = self._integration.trend_service
            sources = ctx.get("sources", ["google", "reddit", "hackernews", "producthunt"])
            analysis = await trend_service.run_analysis_cycle(sources=sources)
            trends.extend(analysis.get("trends", []))
            sources_used.extend(sources)
        except Exception as e:
            logger.warning("Trend service data collection encountered an issue: %s", e)

        # Also pull from the trending endpoint
        try:
            trending = self._integration.trend_service.get_trending(
                category=ctx.get("category"),
                min_score=ctx.get("min_score", 0),
                limit=ctx.get("limit", 30),
            )
            for item in trending.get("trends", []):
                if item not in trends:
                    trends.append(item)
        except Exception as e:
            logger.warning("Trending data fetch encountered an issue: %s", e)

        return {
            "trends": trends,
            "sources_used": sources_used,
            "trend_count": len(trends),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _cross_reference_sources(
        self,
        trend_data: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Cross-reference trend data across multiple sources."""
        cross_references: List[Dict[str, Any]] = []

        try:
            correlations = self._integration.trend_service.get_correlations(
                trend_id=ctx.get("trend_id"),
            )
            cross_references.append(
                {
                    "type": "correlation_analysis",
                    "data": correlations,
                }
            )
        except Exception as e:
            logger.warning("Correlation analysis encountered an issue: %s", e)

        # Determine how many sources each trend appeared in
        source_overlap: Dict[str, int] = {}
        for trend in trend_data.get("trends", []):
            name = trend if isinstance(trend, str) else trend.get("name", "unknown")
            source_overlap[name] = source_overlap.get(name, 0) + 1

        return {
            "cross_references": cross_references,
            "source_overlap": source_overlap,
            "multi_source_trends": [name for name, count in source_overlap.items() if count > 1],
            "reference_count": len(cross_references),
        }

    def _validate_patterns(
        self,
        trend_data: Dict[str, Any],
        cross_ref_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate trend patterns and assign confidence scores."""
        validation_scores: Dict[str, float] = {}
        multi_source = set(cross_ref_data.get("multi_source_trends", []))

        for trend in trend_data.get("trends", []):
            name = trend if isinstance(trend, str) else trend.get("name", "unknown")
            score = trend.get("score", 50.0) if isinstance(trend, dict) else 50.0

            # Boost score if trend appears across multiple sources
            if name in multi_source:
                score = min(score * 1.3, 100.0)

            validation_scores[name] = round(score, 2)

        validated_trends = [name for name, score in validation_scores.items() if score >= 60.0]

        return {
            "validation_scores": validation_scores,
            "validated_trends": validated_trends,
            "validated_count": len(validated_trends),
            "total_evaluated": len(validation_scores),
        }

    def _synthesize_findings(
        self,
        trend_data: Dict[str, Any],
        cross_ref_data: Dict[str, Any],
        validation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synthesize all findings into actionable insights."""
        actionable_insights: List[Dict[str, Any]] = []
        scores = validation_data.get("validation_scores", {})

        for trend_name in validation_data.get("validated_trends", []):
            confidence = scores.get(trend_name, 0.0)
            is_multi_source = trend_name in cross_ref_data.get("multi_source_trends", [])

            actionable_insights.append(
                {
                    "trend": trend_name,
                    "confidence": confidence,
                    "multi_source_validated": is_multi_source,
                    "recommended_action": (
                        "immediate_action"
                        if confidence >= 80.0
                        else "monitor_closely" if confidence >= 60.0 else "watch"
                    ),
                    "priority": (
                        "high" if confidence >= 80.0 else "medium" if confidence >= 60.0 else "low"
                    ),
                }
            )

        # Sort by confidence descending
        actionable_insights.sort(key=lambda i: i["confidence"], reverse=True)

        return {
            "actionable_insights": actionable_insights,
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
            "total_insights": len(actionable_insights),
            "high_priority_count": len([i for i in actionable_insights if i["priority"] == "high"]),
        }


# ---------------------------------------------------------------------------
# CompetitiveIntelligenceWorkflow
# ---------------------------------------------------------------------------


class CompetitiveIntelligenceWorkflow(_ResearchStepMixin, AutonomousWorkflow):
    """
    Competitive Intelligence Workflow.

    Gathers and analyzes competitive intelligence through four stages:
    1. Identify competitors from market and trend data.
    2. Analyze positioning and differentiation.
    3. Benchmark capabilities against identified competitors.
    4. Generate strategic recommendations.

    Produces structured output containing:
        - competitor_profiles
        - market_positioning
        - gaps
        - recommendations
    """

    name = "competitive_intelligence"
    description = "Comprehensive competitive intelligence and benchmarking"
    owner_executive = "Compass"

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the competitive intelligence workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1: Identify competitors ------------------------------------
        step1 = await self._run_step(
            "Identify Competitors",
            "trends",
            self._identify_competitors,
            ctx,
        )
        result.steps.append(step1)

        # Step 2: Analyze positioning -------------------------------------
        step2 = await self._run_step(
            "Analyze Positioning",
            "trends",
            self._analyze_positioning,
            step1.output if step1.success else {},
            ctx,
        )
        result.steps.append(step2)

        # Step 3: Benchmark capabilities ----------------------------------
        step3 = await self._run_step(
            "Benchmark Capabilities",
            "commerce",
            self._benchmark_capabilities,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            ctx,
        )
        result.steps.append(step3)

        # Step 4: Strategic recommendations -------------------------------
        step4 = await self._run_step(
            "Strategic Recommendations",
            "integration",
            self._strategic_recommendations,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Compile summary -------------------------------------------------
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)
        result.summary = {
            "competitor_profiles": (
                step1.output.get("profiles", [])
                if step1.success and isinstance(step1.output, dict)
                else []
            ),
            "market_positioning": (
                step2.output.get("positioning", {})
                if step2.success and isinstance(step2.output, dict)
                else {}
            ),
            "gaps": (
                step3.output.get("gaps", [])
                if step3.success and isinstance(step3.output, dict)
                else []
            ),
            "recommendations": (
                step4.output.get("recommendations", [])
                if step4.success and isinstance(step4.output, dict)
                else []
            ),
        }

        return result

    # -- internal helpers --------------------------------------------------

    async def _identify_competitors(
        self,
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Identify competitors from trend and market data."""
        profiles: List[Dict[str, Any]] = []

        # Use explicitly provided competitors if available
        known_competitors = ctx.get("known_competitors", [])
        for comp in known_competitors:
            name = comp if isinstance(comp, str) else comp.get("name", "unknown")
            profiles.append(
                {
                    "name": name,
                    "source": "provided",
                    "category": "direct",
                }
            )

        # Augment with trend-based competitor discovery
        try:
            niche_data = self._integration.trend_service.identify_niches(
                min_opportunity_score=ctx.get("min_opportunity_score", 30),
            )
            for niche in niche_data.get("niches", []):
                niche_name = niche.get("name", "unknown")
                profiles.append(
                    {
                        "name": niche_name,
                        "source": "trend_analysis",
                        "category": "indirect",
                        "niche_score": niche.get("opportunity_score", 0),
                    }
                )
        except Exception as e:
            logger.warning("Trend-based competitor discovery encountered an issue: %s", e)

        return {
            "profiles": profiles,
            "competitor_count": len(profiles),
            "direct_count": len([p for p in profiles if p.get("category") == "direct"]),
            "indirect_count": len([p for p in profiles if p.get("category") == "indirect"]),
        }

    def _analyze_positioning(
        self,
        competitor_data: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze market positioning of identified competitors."""
        positioning: Dict[str, Any] = {
            "segments": [],
            "differentiation_factors": [],
        }

        our_strengths = ctx.get("our_strengths", [])
        profiles = competitor_data.get("profiles", [])

        for profile in profiles:
            name = profile.get("name", "unknown")
            positioning["segments"].append(
                {
                    "competitor": name,
                    "category": profile.get("category", "unknown"),
                    "estimated_position": (
                        "established" if profile.get("source") == "provided" else "emerging"
                    ),
                }
            )

        if our_strengths:
            positioning["differentiation_factors"] = [
                {"factor": s, "type": "strength"} for s in our_strengths
            ]

        return {
            "positioning": positioning,
            "segments_analyzed": len(positioning["segments"]),
        }

    def _benchmark_capabilities(
        self,
        competitor_data: Dict[str, Any],
        positioning_data: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Benchmark our capabilities against competitors."""
        gaps: List[Dict[str, Any]] = []
        benchmarks: List[Dict[str, Any]] = []

        # Gather our commerce metrics for benchmarking
        our_metrics: Dict[str, Any] = {}
        try:
            margin_data = self._integration.commerce_service.get_margin_analysis()
            our_metrics["margin"] = margin_data.get("average_margin", 0.0)
            our_metrics["product_count"] = margin_data.get("product_count", 0)
        except Exception as e:
            logger.warning("Commerce metrics retrieval encountered an issue: %s", e)

        profiles = competitor_data.get("profiles", [])
        for profile in profiles:
            name = profile.get("name", "unknown")
            benchmark_entry = {
                "competitor": name,
                "our_metrics": our_metrics,
                "comparison": "data_pending",
            }
            benchmarks.append(benchmark_entry)

            # Identify gaps where competitor is direct and we lack data
            if profile.get("category") == "direct" and not our_metrics:
                gaps.append(
                    {
                        "area": "market_data",
                        "competitor": name,
                        "severity": "high",
                        "description": f"Insufficient data to benchmark against {name}",
                    }
                )

        capability_areas = ctx.get(
            "capability_areas",
            [
                "product_range",
                "pricing",
                "market_reach",
                "technology",
            ],
        )
        for area in capability_areas:
            if area not in our_metrics:
                gaps.append(
                    {
                        "area": area,
                        "competitor": "all",
                        "severity": "medium",
                        "description": f"No benchmark data available for {area}",
                    }
                )

        return {
            "benchmarks": benchmarks,
            "gaps": gaps,
            "benchmark_count": len(benchmarks),
            "gap_count": len(gaps),
        }

    def _strategic_recommendations(
        self,
        competitor_data: Dict[str, Any],
        positioning_data: Dict[str, Any],
        benchmark_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate strategic recommendations from competitive analysis."""
        recommendations: List[Dict[str, Any]] = []

        gaps = benchmark_data.get("gaps", [])
        profiles = competitor_data.get("profiles", [])
        positioning = positioning_data.get("positioning", {})

        # Recommendations based on capability gaps
        for gap in gaps:
            recommendations.append(
                {
                    "type": "capability_gap",
                    "priority": "high" if gap.get("severity") == "high" else "medium",
                    "area": gap.get("area", "unknown"),
                    "action": f"Address {gap.get('area', 'unknown')} gap: {gap.get('description', '')}",
                }
            )

        # Recommendations based on market positioning
        direct_competitors = [p for p in profiles if p.get("category") == "direct"]
        if direct_competitors:
            recommendations.append(
                {
                    "type": "competitive_strategy",
                    "priority": "high",
                    "area": "differentiation",
                    "action": (
                        f"Develop differentiation strategy against "
                        f"{len(direct_competitors)} direct competitor(s)"
                    ),
                }
            )

        # Recommendations based on emerging competitors
        indirect_competitors = [p for p in profiles if p.get("category") == "indirect"]
        if indirect_competitors:
            recommendations.append(
                {
                    "type": "market_watch",
                    "priority": "medium",
                    "area": "emerging_threats",
                    "action": (
                        f"Monitor {len(indirect_competitors)} emerging "
                        f"competitor(s) from trend analysis"
                    ),
                }
            )

        differentiation = positioning.get("differentiation_factors", [])
        if differentiation:
            recommendations.append(
                {
                    "type": "leverage_strengths",
                    "priority": "high",
                    "area": "positioning",
                    "action": (
                        f"Leverage {len(differentiation)} identified strength(s) "
                        f"for competitive positioning"
                    ),
                }
            )

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 2))

        return {
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_recommendations": len(recommendations),
        }


# ---------------------------------------------------------------------------
# Research workflow registry
# ---------------------------------------------------------------------------

RESEARCH_WORKFLOWS: Dict[str, type] = {
    "market_intelligence_scan": MarketIntelligenceWorkflow,
    "technology_radar_scan": TechnologyRadarWorkflow,
    "trend_deep_research": TrendResearchWorkflow,
    "competitive_intelligence": CompetitiveIntelligenceWorkflow,
}


# ---------------------------------------------------------------------------
# AutonomousResearchEngine
# ---------------------------------------------------------------------------


class AutonomousResearchEngine:
    """
    Coordinator that manages all autonomous research workflows.

    Provides a unified interface to execute research workflows,
    track results with timestamps, schedule recurring research,
    and aggregate insights across research runs.

    Example:
        ```python
        engine = AutonomousResearchEngine()

        # Run a one-off market scan
        result = await engine.run_market_scan(context={"sources": ["google"]})

        # Schedule recurring research
        engine.schedule_recurring_research("market_intelligence_scan", interval_hours=24)

        # Aggregate recent findings
        summary = engine.get_insights_summary()
        ```
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None):
        """
        Initialize the research engine.

        Args:
            integration: Optional ``ModuleIntegration`` instance.
                         Falls back to the shared singleton if not provided.
        """
        self._integration = integration or get_integration()
        self._history: List[ResearchRecord] = []
        self._results: Dict[str, List[ResearchRecord]] = {}
        self._recurring_schedules: Dict[str, RecurringSchedule] = {}

    # -- public research entry points --------------------------------------

    async def run_market_scan(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Run a market intelligence scan.

        Args:
            context: Optional parameters forwarded to the workflow.

        Returns:
            The workflow result.
        """
        return await self._execute_research("market_intelligence_scan", context)

    async def run_competitive_analysis(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Run a competitive intelligence analysis.

        Args:
            context: Optional parameters forwarded to the workflow.

        Returns:
            The workflow result.
        """
        return await self._execute_research("competitive_intelligence", context)

    async def run_trend_research(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Run deep trend research.

        Args:
            context: Optional parameters forwarded to the workflow.

        Returns:
            The workflow result.
        """
        return await self._execute_research("trend_deep_research", context)

    async def run_technology_scan(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Run a technology radar scan.

        Args:
            context: Optional parameters forwarded to the workflow.

        Returns:
            The workflow result.
        """
        return await self._execute_research("technology_radar_scan", context)

    # -- status and history ------------------------------------------------

    def get_research_status(self) -> Dict[str, Any]:
        """
        Get the current status of the research engine.

        Returns:
            A dictionary containing available workflows, execution counts,
            and recurring schedule information.
        """
        schedule_info: Dict[str, Any] = {}
        for name, sched in self._recurring_schedules.items():
            schedule_info[name] = {
                "interval_hours": sched.interval_hours,
                "enabled": sched.enabled,
                "last_run": sched.last_run.isoformat() if sched.last_run else None,
                "next_run": sched.next_run.isoformat() if sched.next_run else None,
                "is_due": sched.is_due,
            }

        return {
            "available_workflows": list(RESEARCH_WORKFLOWS.keys()),
            "total_executions": len(self._history),
            "executions_by_type": {rtype: len(records) for rtype, records in self._results.items()},
            "recurring_schedules": schedule_info,
            "last_execution": (self._history[-1].to_dict() if self._history else None),
        }

    def get_research_history(
        self,
        limit: int = 20,
        research_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the history of research executions.

        Args:
            limit: Maximum number of records to return.
            research_type: If provided, filter to this research type only.

        Returns:
            A list of serialized ``ResearchRecord`` dictionaries, most
            recent first.
        """
        if research_type and research_type in self._results:
            source = self._results[research_type]
        else:
            source = self._history

        sorted_records = sorted(
            source,
            key=lambda r: r.executed_at,
            reverse=True,
        )
        return [record.to_dict() for record in sorted_records[:limit]]

    # -- scheduling --------------------------------------------------------

    def schedule_recurring_research(
        self,
        research_type: str,
        interval_hours: float,
    ) -> Dict[str, Any]:
        """
        Schedule a research workflow to run on a recurring basis.

        Args:
            research_type: The workflow name to schedule (must be a key in
                           ``RESEARCH_WORKFLOWS``).
            interval_hours: How often the research should run, in hours.

        Returns:
            Confirmation dictionary with schedule details.

        Raises:
            ValueError: If *research_type* is not a known workflow.
        """
        if research_type not in RESEARCH_WORKFLOWS:
            raise ValueError(
                f"Unknown research type: {research_type}. "
                f"Available types: {list(RESEARCH_WORKFLOWS.keys())}"
            )

        schedule = RecurringSchedule(
            research_type=research_type,
            interval_hours=interval_hours,
        )
        self._recurring_schedules[research_type] = schedule

        logger.info(
            "Scheduled recurring research '%s' every %.1f hour(s)",
            research_type,
            interval_hours,
        )

        return {
            "scheduled": True,
            "research_type": research_type,
            "interval_hours": interval_hours,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
        }

    async def run_due_recurring_research(self) -> List[AutonomousWorkflowResult]:
        """
        Execute all recurring research schedules that are due.

        Returns:
            A list of workflow results for every schedule that was executed.
        """
        results: List[AutonomousWorkflowResult] = []

        for name, schedule in self._recurring_schedules.items():
            if schedule.is_due:
                logger.info("Running due recurring research: %s", name)
                try:
                    result = await self._execute_research(name)
                    schedule.last_run = datetime.now(timezone.utc)
                    results.append(result)
                except Exception as e:
                    logger.error("Recurring research '%s' failed: %s", name, e)

        return results

    # -- insights aggregation ----------------------------------------------

    def get_insights_summary(
        self,
        max_age_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """
        Aggregate insights from recent research executions.

        Args:
            max_age_hours: Only consider executions within this many hours.

        Returns:
            A dictionary summarizing recent findings across all
            research types, including top opportunities, risks,
            technology recommendations, and trend insights.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        recent = [r for r in self._history if r.executed_at >= cutoff]

        all_opportunities: List[Dict[str, Any]] = []
        all_risks: List[Dict[str, Any]] = []
        all_tech_recommendations: List[Dict[str, Any]] = []
        all_trend_insights: List[Dict[str, Any]] = []
        all_competitive_recommendations: List[Dict[str, Any]] = []

        for record in recent:
            summary = record.result.summary

            if record.research_type == "market_intelligence_scan":
                opportunities = summary.get("opportunities", {})
                if isinstance(opportunities, dict):
                    all_opportunities.extend(opportunities.get("opportunities", []))
                risk_factors = summary.get("risk_factors", [])
                if isinstance(risk_factors, list):
                    all_risks.extend(risk_factors)

            elif record.research_type == "technology_radar_scan":
                recs = summary.get("adoption_recommendations", [])
                if isinstance(recs, list):
                    all_tech_recommendations.extend(recs)

            elif record.research_type == "trend_deep_research":
                insights = summary.get("actionable_insights", [])
                if isinstance(insights, list):
                    all_trend_insights.extend(insights)

            elif record.research_type == "competitive_intelligence":
                recs = summary.get("recommendations", [])
                if isinstance(recs, list):
                    all_competitive_recommendations.extend(recs)

        return {
            "period_hours": max_age_hours,
            "executions_analyzed": len(recent),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_opportunities": all_opportunities[:10],
            "risk_factors": all_risks[:10],
            "technology_recommendations": all_tech_recommendations[:10],
            "trend_insights": all_trend_insights[:10],
            "competitive_recommendations": all_competitive_recommendations[:10],
            "summary_stats": {
                "total_opportunities": len(all_opportunities),
                "total_risks": len(all_risks),
                "total_tech_recommendations": len(all_tech_recommendations),
                "total_trend_insights": len(all_trend_insights),
                "total_competitive_recommendations": len(all_competitive_recommendations),
            },
        }

    # -- internal ----------------------------------------------------------

    async def _execute_research(
        self,
        research_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """
        Instantiate and execute a research workflow, recording the result.

        Args:
            research_type: Key in ``RESEARCH_WORKFLOWS``.
            context: Optional context forwarded to the workflow.

        Returns:
            The workflow execution result.
        """
        if research_type not in RESEARCH_WORKFLOWS:
            error_result = AutonomousWorkflowResult(
                workflow_name=research_type,
                success=False,
                error=f"Unknown research type: {research_type}",
                completed_at=datetime.now(timezone.utc),
            )
            return error_result

        workflow_class = RESEARCH_WORKFLOWS[research_type]
        workflow = workflow_class(integration=self._integration)

        logger.info("Starting research workflow: %s", research_type)

        try:
            result = await workflow.execute(context)
        except Exception as e:
            logger.error("Research workflow '%s' failed: %s", research_type, e)
            result = AutonomousWorkflowResult(
                workflow_name=research_type,
                success=False,
                error=str(e),
                completed_at=datetime.now(timezone.utc),
            )

        # Store the record
        record = ResearchRecord(
            research_type=research_type,
            result=result,
        )
        self._history.append(record)
        self._results.setdefault(research_type, []).append(record)

        logger.info(
            "Research workflow '%s' completed (success=%s)",
            research_type,
            result.success,
        )

        return result
