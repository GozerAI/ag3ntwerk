"""
Expert Panel Bridge - Integration between ag3ntwerk and AI Platform Expert Systems.

This module provides a bridge connecting ag3ntwerk agents to the
ai-platform-unified expert panel and consensus systems:
- Multi-expert opinion gathering
- Consensus building
- Decision support
- Strategic recommendations

Primary users:
- CEO (Apex): Strategic decisions
- Nexus (Nexus): Operational decisions
- All agents: Cross-functional decisions

Features:
- Multi-expert opinion synthesis
- Weighted consensus calculation
- Conflict detection and resolution
- Decision audit trail
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ExpertType(Enum):
    """Types of experts available in the panel."""

    RESEARCH = "research"
    ANALYST = "analyst"
    ENGINEER = "engineer"
    STRATEGIST = "strategist"
    CRITIC = "critic"
    FINANCIAL = "financial"
    LEGAL = "legal"
    OPERATIONS = "operations"
    MARKETING = "marketing"
    TECHNICAL = "technical"


class ConsensusStrategy(Enum):
    """Strategies for reaching consensus."""

    MAJORITY = "majority"  # Simple majority
    WEIGHTED = "weighted"  # Weighted by confidence
    UNANIMOUS = "unanimous"  # All must agree
    SYNTHESIZED = "synthesized"  # AI synthesis of all views
    AGENT = "agent"  # Final call by designated leader


class DecisionUrgency(Enum):
    """Urgency level for decisions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(Enum):
    """Status of a decision request."""

    PENDING = "pending"
    GATHERING_OPINIONS = "gathering_opinions"
    BUILDING_CONSENSUS = "building_consensus"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class ExpertProfile:
    """Profile of an expert in the panel."""

    id: str
    expert_type: ExpertType
    name: str
    domain: str
    weight: float = 1.0  # Influence weight
    reliability_score: float = 0.8
    specializations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpertOpinion:
    """Opinion from an expert on a decision."""

    id: UUID = field(default_factory=uuid4)
    expert_id: str = ""
    expert_type: ExpertType = ExpertType.ANALYST
    opinion: str = ""
    position: str = ""  # support, oppose, neutral, conditional
    confidence: float = 0.7
    reasoning: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # Conditions for support
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "expert_id": self.expert_id,
            "expert_type": self.expert_type.value,
            "position": self.position,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "concerns": self.concerns,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ConsensusResult:
    """Result of consensus building."""

    id: UUID = field(default_factory=uuid4)
    decision_id: UUID = field(default_factory=uuid4)
    strategy_used: ConsensusStrategy = ConsensusStrategy.WEIGHTED
    consensus_reached: bool = False
    final_position: str = ""  # approve, reject, defer, conditional
    confidence_score: float = 0.0
    agreement_level: float = 0.0  # 0-1, how much experts agree
    synthesis: str = ""  # Synthesized recommendation
    key_agreements: List[str] = field(default_factory=list)
    key_disagreements: List[str] = field(default_factory=list)
    unresolved_concerns: List[str] = field(default_factory=list)
    conditions_for_approval: List[str] = field(default_factory=list)
    participating_experts: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "decision_id": str(self.decision_id),
            "strategy_used": self.strategy_used.value,
            "consensus_reached": self.consensus_reached,
            "final_position": self.final_position,
            "confidence_score": self.confidence_score,
            "agreement_level": self.agreement_level,
            "synthesis": self.synthesis,
            "key_agreements": self.key_agreements,
            "key_disagreements": self.key_disagreements,
            "conditions_for_approval": self.conditions_for_approval,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DecisionRequest:
    """A request for a decision from the expert panel."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    context: str = ""
    options: List[str] = field(default_factory=list)
    requester: str = ""
    urgency: DecisionUrgency = DecisionUrgency.MEDIUM
    status: DecisionStatus = DecisionStatus.PENDING
    required_experts: List[ExpertType] = field(default_factory=list)
    opinions: List[ExpertOpinion] = field(default_factory=list)
    consensus: Optional[ConsensusResult] = None
    final_decision: Optional[str] = None
    decision_maker: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "options": self.options,
            "requester": self.requester,
            "urgency": self.urgency.value,
            "status": self.status.value,
            "opinions_count": len(self.opinions),
            "has_consensus": self.consensus is not None,
            "final_decision": self.final_decision,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


class ExpertPanelBridge:
    """
    Bridge between ag3ntwerk agents and AI Platform expert systems.

    This bridge enables:
    1. CEO/Nexus - Strategic and operational decision support
    2. All agents - Cross-functional decision making
    3. Complex decisions - Multi-expert consensus

    Usage:
        bridge = ExpertPanelBridge()
        bridge.connect_platform(ai_platform, expert_panel, consensus_engine)

        # Create decision request
        decision = await bridge.create_decision_request(
            title="Market Expansion Strategy",
            description="Should we expand into the European market?",
            options=["Expand now", "Delay 6 months", "Focus on APAC first"],
            required_experts=[ExpertType.STRATEGIST, ExpertType.FINANCIAL],
        )

        # Gather opinions
        opinions = await bridge.gather_opinions(decision.id)

        # Build consensus
        consensus = await bridge.build_consensus(decision.id)

        # Get final recommendation
        recommendation = bridge.get_recommendation(decision.id)
    """

    # Default expert weights
    DEFAULT_EXPERT_WEIGHTS = {
        ExpertType.STRATEGIST: 1.2,
        ExpertType.FINANCIAL: 1.1,
        ExpertType.RESEARCH: 1.0,
        ExpertType.ANALYST: 1.0,
        ExpertType.ENGINEER: 0.9,
        ExpertType.OPERATIONS: 0.9,
        ExpertType.MARKETING: 0.9,
        ExpertType.CRITIC: 0.8,
        ExpertType.LEGAL: 1.1,
        ExpertType.TECHNICAL: 0.9,
    }

    # Consensus thresholds
    CONSENSUS_THRESHOLD = 0.7  # 70% agreement for consensus
    HIGH_CONFIDENCE_THRESHOLD = 0.8

    def __init__(
        self,
        ceo: Optional[Any] = None,
        coo: Optional[Any] = None,
    ):
        """
        Initialize the Expert Panel bridge.

        Args:
            ceo: Optional Chief Agent Officer instance
            coo: Optional Nexus instance
        """
        self._ceo = ceo
        self._coo = coo

        # AI Platform connections
        self._ai_platform: Optional[Any] = None
        self._expert_panel: Optional[Any] = None
        self._consensus_engine: Optional[Any] = None

        # Expert profiles
        self._experts: Dict[str, ExpertProfile] = {}
        self._init_default_experts()

        # Decision tracking
        self._decisions: Dict[UUID, DecisionRequest] = {}
        self._decision_history: List[Dict[str, Any]] = []

        # Custom opinion handlers
        self._opinion_handlers: Dict[ExpertType, Callable] = {}

        # Metrics
        self._metrics = {
            "decisions_requested": 0,
            "decisions_resolved": 0,
            "consensus_reached_count": 0,
            "avg_agreement_level": 0.0,
            "avg_resolution_time_hours": 0.0,
        }

        logger.info("ExpertPanelBridge initialized")

    def _init_default_experts(self) -> None:
        """Initialize default expert profiles."""
        default_experts = [
            ExpertProfile(
                id="research_expert",
                expert_type=ExpertType.RESEARCH,
                name="Research Expert",
                domain="Research and Analysis",
                specializations=["data analysis", "literature review", "methodology"],
            ),
            ExpertProfile(
                id="analyst_expert",
                expert_type=ExpertType.ANALYST,
                name="Business Analyst",
                domain="Business Analysis",
                specializations=["market analysis", "competitive intelligence", "metrics"],
            ),
            ExpertProfile(
                id="engineer_expert",
                expert_type=ExpertType.ENGINEER,
                name="Engineering Expert",
                domain="Technical Implementation",
                specializations=["system design", "scalability", "technical feasibility"],
            ),
            ExpertProfile(
                id="strategist_expert",
                expert_type=ExpertType.STRATEGIST,
                name="Strategy Expert",
                domain="Strategic Planning",
                specializations=["long-term planning", "competitive positioning", "growth"],
            ),
            ExpertProfile(
                id="critic_expert",
                expert_type=ExpertType.CRITIC,
                name="Critical Reviewer",
                domain="Critical Analysis",
                specializations=["risk identification", "devil's advocate", "edge cases"],
            ),
            ExpertProfile(
                id="financial_expert",
                expert_type=ExpertType.FINANCIAL,
                name="Financial Expert",
                domain="Financial Analysis",
                specializations=["ROI analysis", "budgeting", "financial risk"],
            ),
        ]

        for expert in default_experts:
            self._experts[expert.id] = expert

    def connect_platform(
        self,
        ai_platform: Any = None,
        expert_panel: Any = None,
        consensus_engine: Any = None,
    ) -> None:
        """
        Connect to AI Platform expert systems.

        Args:
            ai_platform: UnifiedAIPlatform instance
            expert_panel: Expert panel for opinions
            consensus_engine: ConsensusEngine for agreement
        """
        if ai_platform:
            self._ai_platform = ai_platform
            logger.info("Connected UnifiedAIPlatform")
        if expert_panel:
            self._expert_panel = expert_panel
            logger.info("Connected Expert Panel")
        if consensus_engine:
            self._consensus_engine = consensus_engine
            logger.info("Connected Consensus Engine")

    def connect_executives(
        self,
        ceo: Any = None,
        coo: Any = None,
    ) -> None:
        """Connect ag3ntwerk agents to the bridge."""
        if ceo:
            self._ceo = ceo
            logger.info("Connected CEO (Apex) to expert panel")
        if coo:
            self._coo = coo
            logger.info("Connected Nexus (Nexus) to expert panel")

    def register_expert(self, expert: ExpertProfile) -> None:
        """Register a new expert profile."""
        self._experts[expert.id] = expert
        logger.info(f"Registered expert: {expert.name}")

    def register_opinion_handler(
        self,
        expert_type: ExpertType,
        handler: Callable,
    ) -> None:
        """Register custom opinion handler for an expert type."""
        self._opinion_handlers[expert_type] = handler

    async def create_decision_request(
        self,
        title: str,
        description: str,
        options: Optional[List[str]] = None,
        context: str = "",
        requester: str = "",
        urgency: DecisionUrgency = DecisionUrgency.MEDIUM,
        required_experts: Optional[List[ExpertType]] = None,
    ) -> DecisionRequest:
        """
        Create a new decision request.

        Args:
            title: Decision title
            description: Detailed description
            options: Available options to choose from
            context: Additional context
            requester: Who requested the decision
            urgency: Decision urgency level
            required_experts: Required expert types

        Returns:
            Created DecisionRequest
        """
        decision = DecisionRequest(
            title=title,
            description=description,
            context=context,
            options=options or [],
            requester=requester,
            urgency=urgency,
            required_experts=required_experts
            or [
                ExpertType.STRATEGIST,
                ExpertType.ANALYST,
                ExpertType.CRITIC,
            ],
        )

        self._decisions[decision.id] = decision
        self._metrics["decisions_requested"] += 1

        logger.info(f"Created decision request: {title}")
        return decision

    async def gather_opinions(
        self,
        decision_id: UUID,
        expert_types: Optional[List[ExpertType]] = None,
    ) -> List[ExpertOpinion]:
        """
        Gather opinions from experts on a decision.

        Args:
            decision_id: Decision identifier
            expert_types: Optional specific expert types to consult

        Returns:
            List of expert opinions
        """
        if decision_id not in self._decisions:
            raise ValueError(f"Unknown decision: {decision_id}")

        decision = self._decisions[decision_id]
        decision.status = DecisionStatus.GATHERING_OPINIONS

        types_to_consult = expert_types or decision.required_experts
        opinions = []

        for expert_type in types_to_consult:
            # Find expert of this type
            expert = self._get_expert_by_type(expert_type)
            if not expert:
                continue

            opinion = await self._get_expert_opinion(expert, decision)
            if opinion:
                opinions.append(opinion)
                decision.opinions.append(opinion)

        return opinions

    def _get_expert_by_type(self, expert_type: ExpertType) -> Optional[ExpertProfile]:
        """Get an expert by type."""
        for expert in self._experts.values():
            if expert.expert_type == expert_type:
                return expert
        return None

    async def _get_expert_opinion(
        self,
        expert: ExpertProfile,
        decision: DecisionRequest,
    ) -> Optional[ExpertOpinion]:
        """Get opinion from a specific expert."""

        # Check for custom handler
        if expert.expert_type in self._opinion_handlers:
            try:
                handler = self._opinion_handlers[expert.expert_type]
                result = await handler(decision, expert)
                return self._parse_opinion_result(result, expert)
            except Exception as e:
                logger.error(f"Custom opinion handler failed: {e}")

        # Use expert panel if available
        if self._expert_panel:
            try:
                result = await self._expert_panel.generate_opinion(
                    expert_type=expert.expert_type.value,
                    topic=decision.title,
                    context=f"{decision.description}\n\nOptions: {decision.options}",
                )
                return self._parse_opinion_result(result, expert)
            except Exception as e:
                logger.error(f"Expert panel opinion failed: {e}")

        # Use AI Platform if available
        if self._ai_platform:
            try:
                prompt = self._build_opinion_prompt(expert, decision)
                result = await self._ai_platform.query(prompt)
                return self._parse_ai_opinion(result, expert)
            except Exception as e:
                logger.error(f"AI Platform opinion failed: {e}")

        # Generate basic opinion
        return self._generate_basic_opinion(expert, decision)

    def _build_opinion_prompt(
        self,
        expert: ExpertProfile,
        decision: DecisionRequest,
    ) -> str:
        """Build prompt for AI-generated opinion."""
        return f"""You are a {expert.name} with expertise in {expert.domain}.
Specializations: {', '.join(expert.specializations)}

Decision to evaluate:
Title: {decision.title}
Description: {decision.description}
Context: {decision.context}
Options: {decision.options}
Urgency: {decision.urgency.value}

Provide your expert opinion including:
1. Your position (support/oppose/neutral/conditional)
2. Confidence level (0-1)
3. Key reasoning
4. Supporting evidence
5. Concerns or risks
6. Conditions for approval (if conditional)
7. Specific recommendations

Be thorough but concise."""

    def _parse_opinion_result(
        self,
        result: Any,
        expert: ExpertProfile,
    ) -> ExpertOpinion:
        """Parse opinion result from handler or panel."""
        if isinstance(result, dict):
            return ExpertOpinion(
                expert_id=expert.id,
                expert_type=expert.expert_type,
                opinion=result.get("opinion", ""),
                position=result.get("position", "neutral"),
                confidence=result.get("confidence", 0.7),
                reasoning=result.get("reasoning", ""),
                supporting_evidence=result.get("evidence", []),
                concerns=result.get("concerns", []),
                conditions=result.get("conditions", []),
                recommendations=result.get("recommendations", []),
            )
        return ExpertOpinion(
            expert_id=expert.id,
            expert_type=expert.expert_type,
            opinion=str(result),
            position="neutral",
            confidence=0.5,
        )

    def _parse_ai_opinion(
        self,
        result: Any,
        expert: ExpertProfile,
    ) -> ExpertOpinion:
        """Parse AI-generated opinion."""
        content = str(result)

        # Try to extract position
        position = "neutral"
        if "support" in content.lower():
            position = "support"
        elif "oppose" in content.lower():
            position = "oppose"
        elif "conditional" in content.lower():
            position = "conditional"

        return ExpertOpinion(
            expert_id=expert.id,
            expert_type=expert.expert_type,
            opinion=content[:500] if len(content) > 500 else content,
            position=position,
            confidence=0.7,
            reasoning=content,
        )

    def _generate_basic_opinion(
        self,
        expert: ExpertProfile,
        decision: DecisionRequest,
    ) -> ExpertOpinion:
        """Generate basic opinion when no AI available."""
        return ExpertOpinion(
            expert_id=expert.id,
            expert_type=expert.expert_type,
            opinion=f"{expert.name} analysis of: {decision.title}",
            position="neutral",
            confidence=0.5,
            reasoning="Basic analysis without AI assistance",
            recommendations=[
                "Consider all options carefully",
                f"Evaluate from {expert.domain} perspective",
            ],
        )

    async def build_consensus(
        self,
        decision_id: UUID,
        strategy: ConsensusStrategy = ConsensusStrategy.WEIGHTED,
    ) -> ConsensusResult:
        """
        Build consensus from gathered opinions.

        Args:
            decision_id: Decision identifier
            strategy: Consensus building strategy

        Returns:
            ConsensusResult with synthesized recommendation
        """
        if decision_id not in self._decisions:
            raise ValueError(f"Unknown decision: {decision_id}")

        decision = self._decisions[decision_id]
        decision.status = DecisionStatus.BUILDING_CONSENSUS

        opinions = decision.opinions
        if not opinions:
            return ConsensusResult(
                decision_id=decision_id,
                strategy_used=strategy,
                consensus_reached=False,
                final_position="no_opinions",
                synthesis="No expert opinions available",
            )

        # Use consensus engine if available
        if self._consensus_engine:
            try:
                result = await self._consensus_engine.consensus(
                    topic=decision.title,
                    opinions=[o.to_dict() for o in opinions],
                    strategy=strategy.value,
                )
                consensus = self._parse_consensus_result(result, decision_id, strategy)
                decision.consensus = consensus
                return consensus
            except Exception as e:
                logger.error(f"Consensus engine failed: {e}")

        # Build consensus manually
        consensus = self._calculate_consensus(opinions, decision_id, strategy)
        decision.consensus = consensus

        if consensus.consensus_reached:
            self._metrics["consensus_reached_count"] += 1
            decision.status = DecisionStatus.AWAITING_APPROVAL

        # Update metrics
        self._update_agreement_metrics(consensus.agreement_level)

        return consensus

    def _parse_consensus_result(
        self,
        result: Any,
        decision_id: UUID,
        strategy: ConsensusStrategy,
    ) -> ConsensusResult:
        """Parse consensus result from engine."""
        if isinstance(result, dict):
            return ConsensusResult(
                decision_id=decision_id,
                strategy_used=strategy,
                consensus_reached=result.get("consensus_reached", False),
                final_position=result.get("position", ""),
                confidence_score=result.get("confidence", 0.0),
                agreement_level=result.get("agreement", 0.0),
                synthesis=result.get("synthesis", ""),
                key_agreements=result.get("agreements", []),
                key_disagreements=result.get("disagreements", []),
                conditions_for_approval=result.get("conditions", []),
            )
        return ConsensusResult(
            decision_id=decision_id,
            strategy_used=strategy,
            synthesis=str(result),
        )

    def _calculate_consensus(
        self,
        opinions: List[ExpertOpinion],
        decision_id: UUID,
        strategy: ConsensusStrategy,
    ) -> ConsensusResult:
        """Calculate consensus from opinions manually."""
        if not opinions:
            return ConsensusResult(decision_id=decision_id, strategy_used=strategy)

        # Count positions
        position_weights: Dict[str, float] = {
            "support": 0.0,
            "oppose": 0.0,
            "neutral": 0.0,
            "conditional": 0.0,
        }

        total_weight = 0.0
        concerns = []
        agreements = []
        conditions = []

        for opinion in opinions:
            # Get expert weight
            expert = self._experts.get(opinion.expert_id)
            weight = self.DEFAULT_EXPERT_WEIGHTS.get(opinion.expert_type, 1.0)
            if expert:
                weight *= expert.reliability_score

            # Weight by confidence
            if strategy == ConsensusStrategy.WEIGHTED:
                weight *= opinion.confidence

            position_weights[opinion.position] = (
                position_weights.get(opinion.position, 0.0) + weight
            )
            total_weight += weight

            # Collect insights
            concerns.extend(opinion.concerns)
            if opinion.position in ["support", "conditional"]:
                agreements.append(f"{opinion.expert_type.value}: {opinion.reasoning[:100]}")
            conditions.extend(opinion.conditions)

        # Normalize weights
        if total_weight > 0:
            for pos in position_weights:
                position_weights[pos] /= total_weight

        # Determine final position
        if strategy == ConsensusStrategy.UNANIMOUS:
            if position_weights["support"] == 1.0:
                final_position = "approve"
            elif position_weights["oppose"] == 1.0:
                final_position = "reject"
            else:
                final_position = "no_consensus"
        else:
            max_position = max(position_weights, key=position_weights.get)
            final_position = {
                "support": "approve",
                "oppose": "reject",
                "neutral": "defer",
                "conditional": "conditional_approve",
            }.get(max_position, "defer")

        # Calculate agreement level
        max_weight = max(position_weights.values())
        agreement_level = max_weight

        # Determine if consensus reached
        consensus_reached = (
            agreement_level >= self.CONSENSUS_THRESHOLD or strategy == ConsensusStrategy.AGENT
        )

        # Calculate confidence
        confidence = sum(
            o.confidence * self.DEFAULT_EXPERT_WEIGHTS.get(o.expert_type, 1.0) for o in opinions
        ) / len(opinions)

        return ConsensusResult(
            decision_id=decision_id,
            strategy_used=strategy,
            consensus_reached=consensus_reached,
            final_position=final_position,
            confidence_score=confidence,
            agreement_level=agreement_level,
            synthesis=self._synthesize_opinions(opinions),
            key_agreements=list(set(agreements))[:5],
            key_disagreements=list(set(concerns))[:5],
            unresolved_concerns=list(set(concerns)),
            conditions_for_approval=list(set(conditions)),
            participating_experts=[o.expert_id for o in opinions],
        )

    def _synthesize_opinions(self, opinions: List[ExpertOpinion]) -> str:
        """Synthesize opinions into a summary."""
        support_count = len([o for o in opinions if o.position == "support"])
        oppose_count = len([o for o in opinions if o.position == "oppose"])
        total = len(opinions)

        synthesis = f"Panel of {total} experts: {support_count} support, {oppose_count} oppose. "

        # Add key reasoning
        key_reasons = [o.reasoning[:100] for o in opinions if o.reasoning][:3]
        if key_reasons:
            synthesis += "Key considerations: " + "; ".join(key_reasons)

        return synthesis

    def _update_agreement_metrics(self, agreement_level: float) -> None:
        """Update average agreement metrics."""
        count = self._metrics["consensus_reached_count"]
        current_avg = self._metrics["avg_agreement_level"]

        if count > 0:
            self._metrics["avg_agreement_level"] = (
                current_avg * (count - 1) + agreement_level
            ) / count
        else:
            self._metrics["avg_agreement_level"] = agreement_level

    def approve_decision(
        self,
        decision_id: UUID,
        decision_maker: str,
        final_decision: str,
    ) -> bool:
        """
        Approve a decision with final call.

        Args:
            decision_id: Decision identifier
            decision_maker: Who is making the final decision
            final_decision: The final decision

        Returns:
            True if approved successfully
        """
        if decision_id not in self._decisions:
            return False

        decision = self._decisions[decision_id]
        decision.status = DecisionStatus.APPROVED
        decision.final_decision = final_decision
        decision.decision_maker = decision_maker
        decision.decided_at = datetime.now(timezone.utc)

        self._metrics["decisions_resolved"] += 1

        # Add to history
        self._decision_history.append(
            {
                "decision_id": str(decision_id),
                "title": decision.title,
                "final_decision": final_decision,
                "decision_maker": decision_maker,
                "consensus_reached": (
                    decision.consensus.consensus_reached if decision.consensus else False
                ),
                "decided_at": decision.decided_at.isoformat(),
            }
        )

        logger.info(f"Decision approved: {decision.title} -> {final_decision}")
        return True

    def get_recommendation(self, decision_id: UUID) -> Dict[str, Any]:
        """
        Get final recommendation for a decision.

        Args:
            decision_id: Decision identifier

        Returns:
            Recommendation dictionary
        """
        if decision_id not in self._decisions:
            return {"error": "Decision not found"}

        decision = self._decisions[decision_id]

        recommendation = {
            "decision_id": str(decision_id),
            "title": decision.title,
            "status": decision.status.value,
            "opinions_count": len(decision.opinions),
        }

        if decision.consensus:
            recommendation.update(
                {
                    "consensus_reached": decision.consensus.consensus_reached,
                    "recommended_position": decision.consensus.final_position,
                    "confidence": decision.consensus.confidence_score,
                    "agreement_level": decision.consensus.agreement_level,
                    "synthesis": decision.consensus.synthesis,
                    "conditions": decision.consensus.conditions_for_approval,
                    "concerns": decision.consensus.unresolved_concerns,
                }
            )

        if decision.final_decision:
            recommendation["final_decision"] = decision.final_decision
            recommendation["decision_maker"] = decision.decision_maker

        return recommendation

    def get_decisions_for_ceo(self) -> Dict[str, Any]:
        """
        Get decision data formatted for CEO.

        Returns:
            Data structured for CEO consumption
        """
        pending = [
            d.to_dict()
            for d in self._decisions.values()
            if d.status
            in [
                DecisionStatus.PENDING,
                DecisionStatus.GATHERING_OPINIONS,
                DecisionStatus.BUILDING_CONSENSUS,
                DecisionStatus.AWAITING_APPROVAL,
            ]
        ]

        return {
            "summary": {
                "total_decisions": len(self._decisions),
                "pending_decisions": len(pending),
                "decisions_resolved": self._metrics["decisions_resolved"],
                "consensus_rate": (
                    self._metrics["consensus_reached_count"]
                    / max(1, self._metrics["decisions_resolved"])
                ),
            },
            "pending_decisions": pending,
            "recent_decisions": self._decision_history[-10:],
            "expert_panel_size": len(self._experts),
            "metrics": self._metrics,
        }

    def get_decisions_for_coo(self) -> Dict[str, Any]:
        """
        Get decision data formatted for Nexus.

        Returns:
            Data structured for Nexus consumption
        """
        by_urgency = {}
        for d in self._decisions.values():
            urg = d.urgency.value
            if urg not in by_urgency:
                by_urgency[urg] = []
            by_urgency[urg].append(d.to_dict())

        return {
            "summary": {
                "total_decisions": len(self._decisions),
                "critical_pending": len(
                    [
                        d
                        for d in self._decisions.values()
                        if d.urgency == DecisionUrgency.CRITICAL
                        and d.status != DecisionStatus.APPROVED
                    ]
                ),
                "high_priority_pending": len(
                    [
                        d
                        for d in self._decisions.values()
                        if d.urgency == DecisionUrgency.HIGH and d.status != DecisionStatus.APPROVED
                    ]
                ),
            },
            "by_urgency": by_urgency,
            "expert_utilization": {
                expert.expert_type.value: sum(
                    1
                    for d in self._decisions.values()
                    for o in d.opinions
                    if o.expert_type == expert.expert_type
                )
                for expert in self._experts.values()
            },
            "metrics": self._metrics,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "ceo_connected": self._ceo is not None,
            "coo_connected": self._coo is not None,
            "ai_platform_connected": self._ai_platform is not None,
            "expert_panel_connected": self._expert_panel is not None,
            "consensus_engine_connected": self._consensus_engine is not None,
            "registered_experts": len(self._experts),
            "active_decisions": len(
                [
                    d
                    for d in self._decisions.values()
                    if d.status not in [DecisionStatus.APPROVED, DecisionStatus.REJECTED]
                ]
            ),
            **self._metrics,
        }
