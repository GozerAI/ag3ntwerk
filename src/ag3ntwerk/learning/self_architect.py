"""
Self-architecture for the ag3ntwerk learning system.

Enables the system to modify its own structure based on performance,
proposing new agents, merges, and splits to optimize the hierarchy.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .models import TaskOutcomeRecord
from .outcome_tracker import OutcomeTracker
from .pattern_store import PatternStore


class ProposalType(str, Enum):
    """Types of architectural proposals."""

    ADD_AGENT = "add_agent"
    REMOVE_AGENT = "remove_agent"
    MERGE_AGENTS = "merge_agents"
    SPLIT_AGENT = "split_agent"
    REASSIGN_CAPABILITY = "reassign_capability"
    ADD_CAPABILITY = "add_capability"


class ProposalStatus(str, Enum):
    """Status of an architectural proposal."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"


class BottleneckType(str, Enum):
    """Types of bottlenecks detected."""

    CAPACITY = "capacity"
    LATENCY = "latency"
    FAILURE_RATE = "failure_rate"
    SKILL_GAP = "skill_gap"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""

    agent_code: str
    task_count: int
    success_rate: float
    avg_duration_ms: float
    utilization: float
    failure_rate: float
    task_types: List[str]
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "task_count": self.task_count,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "utilization": self.utilization,
            "failure_rate": self.failure_rate,
            "task_types": self.task_types,
            "capabilities": self.capabilities,
        }


@dataclass
class Bottleneck:
    """A detected bottleneck in the system."""

    bottleneck_type: BottleneckType
    agent_code: str
    severity: float
    task_types_affected: List[str]
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bottleneck_type": self.bottleneck_type.value,
            "agent_code": self.agent_code,
            "severity": self.severity,
            "task_types_affected": self.task_types_affected,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class UnderutilizedAgent:
    """An agent with low utilization."""

    agent_code: str
    utilization: float
    task_count: int
    potential_merge_candidates: List[str]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "utilization": self.utilization,
            "task_count": self.task_count,
            "potential_merge_candidates": self.potential_merge_candidates,
            "reason": self.reason,
        }


@dataclass
class CapabilityGapInfo:
    """Information about a missing capability."""

    task_type: str
    volume: int
    failure_rate: float
    suggested_capability: str
    suggested_agent: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "volume": self.volume,
            "failure_rate": self.failure_rate,
            "suggested_capability": self.suggested_capability,
            "suggested_agent": self.suggested_agent,
        }


@dataclass
class AgentProposal:
    """Proposal to add a new agent."""

    agent_code: str
    agent_type: str  # agent, manager, specialist
    parent_code: Optional[str]
    capabilities: List[str]
    task_types: List[str]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "agent_type": self.agent_type,
            "parent_code": self.parent_code,
            "capabilities": self.capabilities,
            "task_types": self.task_types,
            "reason": self.reason,
        }


@dataclass
class MergeProposal:
    """Proposal to merge agents."""

    source_agents: List[str]
    target_agent: str
    combined_capabilities: List[str]
    estimated_efficiency_gain: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_agents": self.source_agents,
            "target_agent": self.target_agent,
            "combined_capabilities": self.combined_capabilities,
            "estimated_efficiency_gain": self.estimated_efficiency_gain,
            "reason": self.reason,
        }


@dataclass
class SplitProposal:
    """Proposal to split an agent."""

    source_agent: str
    new_agents: List[AgentProposal]
    task_distribution: Dict[str, List[str]]
    estimated_throughput_gain: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_agent": self.source_agent,
            "new_agents": [a.to_dict() for a in self.new_agents],
            "task_distribution": self.task_distribution,
            "estimated_throughput_gain": self.estimated_throughput_gain,
            "reason": self.reason,
        }


@dataclass
class ArchitectureProposal:
    """Complete architecture modification proposal."""

    proposal_id: str
    proposal_type: ProposalType
    status: ProposalStatus
    created_at: datetime
    agents_to_add: List[AgentProposal] = field(default_factory=list)
    agents_to_merge: List[MergeProposal] = field(default_factory=list)
    agents_to_split: List[SplitProposal] = field(default_factory=list)
    agents_to_remove: List[str] = field(default_factory=list)
    estimated_improvement: float = 0.0
    risk_assessment: str = ""
    implementation_steps: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "agents_to_add": [a.to_dict() for a in self.agents_to_add],
            "agents_to_merge": [m.to_dict() for m in self.agents_to_merge],
            "agents_to_split": [s.to_dict() for s in self.agents_to_split],
            "agents_to_remove": self.agents_to_remove,
            "estimated_improvement": self.estimated_improvement,
            "risk_assessment": self.risk_assessment,
            "implementation_steps": self.implementation_steps,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None,
        }


class SelfArchitect:
    """
    Enables the system to modify its own architecture.

    Analyzes system performance to:
    - Identify bottlenecks requiring new agents
    - Find underutilized agents for merging
    - Detect overloaded agents for splitting
    - Propose capability reassignments
    """

    # Thresholds for detection
    BOTTLENECK_UTILIZATION_THRESHOLD = 0.85
    BOTTLENECK_FAILURE_RATE_THRESHOLD = 0.25
    UNDERUTILIZED_THRESHOLD = 0.15
    MIN_TASK_COUNT_FOR_ANALYSIS = 50

    # Improvement thresholds
    MIN_IMPROVEMENT_FOR_PROPOSAL = 0.1  # 10% minimum improvement

    def __init__(
        self,
        db: Any,
        outcome_tracker: OutcomeTracker,
        pattern_store: PatternStore,
    ):
        self._db = db
        self._outcome_tracker = outcome_tracker
        self._pattern_store = pattern_store
        self._agent_capacities: Dict[str, float] = {}

    async def evaluate_architecture(
        self,
        window_hours: int = 168,
    ) -> ArchitectureProposal:
        """
        Evaluate current architecture and propose improvements.

        Args:
            window_hours: Time window for analysis

        Returns:
            ArchitectureProposal with suggested changes
        """
        import uuid

        # Identify issues
        bottlenecks = await self._identify_bottlenecks(window_hours)
        underutilized = await self._identify_underutilized(window_hours)
        missing_capabilities = await self._identify_gaps(window_hours)

        # Generate proposals based on issues
        agents_to_add = self._propose_new_agents(missing_capabilities, bottlenecks)
        agents_to_merge = self._propose_merges(underutilized)
        agents_to_split = self._propose_splits(bottlenecks)

        # Calculate estimated improvement
        estimated_improvement = self._estimate_improvement(
            bottlenecks, agents_to_add, agents_to_merge, agents_to_split
        )

        # Determine primary proposal type
        if agents_to_add:
            proposal_type = ProposalType.ADD_AGENT
        elif agents_to_merge:
            proposal_type = ProposalType.MERGE_AGENTS
        elif agents_to_split:
            proposal_type = ProposalType.SPLIT_AGENT
        else:
            proposal_type = ProposalType.ADD_CAPABILITY

        # Generate implementation steps
        implementation_steps = self._generate_implementation_steps(
            agents_to_add, agents_to_merge, agents_to_split
        )

        # Risk assessment
        risk_assessment = self._assess_risk(agents_to_add, agents_to_merge, agents_to_split)

        return ArchitectureProposal(
            proposal_id=str(uuid.uuid4()),
            proposal_type=proposal_type,
            status=ProposalStatus.PROPOSED,
            created_at=datetime.now(timezone.utc),
            agents_to_add=agents_to_add,
            agents_to_merge=agents_to_merge,
            agents_to_split=agents_to_split,
            estimated_improvement=estimated_improvement,
            risk_assessment=risk_assessment,
            implementation_steps=implementation_steps,
        )

    async def _identify_bottlenecks(
        self,
        window_hours: int,
    ) -> List[Bottleneck]:
        """Identify performance bottlenecks."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = """
            SELECT
                agent_code,
                task_type,
                COUNT(*) as task_count,
                AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                AVG(duration_ms) as avg_duration,
                SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failure_count
            FROM learning_outcomes
            WHERE created_at >= ?
            GROUP BY agent_code, task_type
            HAVING task_count >= ?
        """

        rows = await self._db.fetch_all(
            query, [cutoff.isoformat(), self.MIN_TASK_COUNT_FOR_ANALYSIS]
        )

        bottlenecks = []
        for row in rows:
            agent_code = row["agent_code"]
            task_type = row["task_type"]
            task_count = row["task_count"]
            success_rate = row["success_rate"] or 0.0
            failure_rate = 1.0 - success_rate

            # Check for failure rate bottleneck
            if failure_rate > self.BOTTLENECK_FAILURE_RATE_THRESHOLD:
                severity = min(1.0, failure_rate / 0.5)
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_type=BottleneckType.FAILURE_RATE,
                        agent_code=agent_code,
                        severity=severity,
                        task_types_affected=[task_type],
                        description=f"High failure rate ({failure_rate:.1%}) for {task_type}",
                    )
                )

            # Check for capacity bottleneck (high volume)
            capacity = self._agent_capacities.get(agent_code, 100.0)
            hourly_rate = task_count / window_hours
            utilization = hourly_rate / capacity if capacity > 0 else 1.0

            if utilization > self.BOTTLENECK_UTILIZATION_THRESHOLD:
                severity = min(1.0, (utilization - 0.85) / 0.15)
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_type=BottleneckType.CAPACITY,
                        agent_code=agent_code,
                        severity=severity,
                        task_types_affected=[task_type],
                        description=f"High utilization ({utilization:.1%}) for {task_type}",
                    )
                )

        return bottlenecks

    async def _identify_underutilized(
        self,
        window_hours: int,
    ) -> List[UnderutilizedAgent]:
        """Identify underutilized agents."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = """
            SELECT
                agent_code,
                COUNT(*) as task_count,
                AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate
            FROM learning_outcomes
            WHERE created_at >= ?
            GROUP BY agent_code
        """

        rows = await self._db.fetch_all(query, [cutoff.isoformat()])

        underutilized = []
        all_agents = [row["agent_code"] for row in rows]

        for row in rows:
            agent_code = row["agent_code"]
            task_count = row["task_count"]
            capacity = self._agent_capacities.get(agent_code, 100.0)
            hourly_rate = task_count / window_hours
            utilization = hourly_rate / capacity if capacity > 0 else 0.0

            if utilization < self.UNDERUTILIZED_THRESHOLD:
                # Find potential merge candidates (similar agents)
                candidates = [a for a in all_agents if a != agent_code]

                underutilized.append(
                    UnderutilizedAgent(
                        agent_code=agent_code,
                        utilization=utilization,
                        task_count=task_count,
                        potential_merge_candidates=candidates[:3],
                        reason=f"Low utilization ({utilization:.1%})",
                    )
                )

        return underutilized

    async def _identify_gaps(
        self,
        window_hours: int,
    ) -> List[CapabilityGapInfo]:
        """Identify capability gaps."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Find task types with high failure rates
        query = """
            SELECT
                task_type,
                COUNT(*) as volume,
                AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate
            FROM learning_outcomes
            WHERE created_at >= ?
            GROUP BY task_type
            HAVING volume >= ? AND success_rate < 0.7
            ORDER BY volume DESC
            LIMIT 10
        """

        rows = await self._db.fetch_all(
            query, [cutoff.isoformat(), self.MIN_TASK_COUNT_FOR_ANALYSIS // 2]
        )

        gaps = []
        for row in rows:
            task_type = row["task_type"]
            volume = row["volume"]
            success_rate = row["success_rate"] or 0.0
            failure_rate = 1.0 - success_rate

            # Suggest a capability based on task type
            suggested_capability = f"enhanced_{task_type}_handling"

            gaps.append(
                CapabilityGapInfo(
                    task_type=task_type,
                    volume=volume,
                    failure_rate=failure_rate,
                    suggested_capability=suggested_capability,
                    suggested_agent=None,  # To be determined
                )
            )

        return gaps

    def _propose_new_agents(
        self,
        missing_capabilities: List[CapabilityGapInfo],
        bottlenecks: List[Bottleneck],
    ) -> List[AgentProposal]:
        """Propose new agents based on gaps and bottlenecks."""
        proposals = []

        # Propose specialist agents for capability gaps
        for gap in missing_capabilities:
            if gap.failure_rate > 0.4 and gap.volume > 100:
                agent_code = f"SPEC_{gap.task_type.upper()[:6]}"
                proposals.append(
                    AgentProposal(
                        agent_code=agent_code,
                        agent_type="specialist",
                        parent_code=None,  # To be assigned to appropriate manager
                        capabilities=[gap.suggested_capability],
                        task_types=[gap.task_type],
                        reason=f"High failure rate ({gap.failure_rate:.1%}) and volume ({gap.volume}) for {gap.task_type}",
                    )
                )

        # Propose load-sharing agents for capacity bottlenecks
        capacity_bottlenecks = [
            b for b in bottlenecks if b.bottleneck_type == BottleneckType.CAPACITY
        ]
        agents_with_bottlenecks: Set[str] = set()

        for bottleneck in capacity_bottlenecks:
            if bottleneck.agent_code not in agents_with_bottlenecks and bottleneck.severity > 0.5:
                agents_with_bottlenecks.add(bottleneck.agent_code)
                new_code = f"{bottleneck.agent_code}_2"
                proposals.append(
                    AgentProposal(
                        agent_code=new_code,
                        agent_type="specialist",
                        parent_code=bottleneck.agent_code,
                        capabilities=[],  # Same as parent
                        task_types=bottleneck.task_types_affected,
                        reason=f"Load sharing for overloaded {bottleneck.agent_code}",
                    )
                )

        return proposals

    def _propose_merges(
        self,
        underutilized: List[UnderutilizedAgent],
    ) -> List[MergeProposal]:
        """Propose agent merges for underutilized agents."""
        proposals = []
        merged_agents: Set[str] = set()

        for agent in underutilized:
            if agent.agent_code in merged_agents:
                continue

            if agent.utilization < 0.1 and agent.potential_merge_candidates:
                # Find best merge candidate
                candidate = agent.potential_merge_candidates[0]
                if candidate not in merged_agents:
                    merged_agents.add(agent.agent_code)
                    merged_agents.add(candidate)

                    proposals.append(
                        MergeProposal(
                            source_agents=[agent.agent_code, candidate],
                            target_agent=candidate,  # Keep the one with more activity
                            combined_capabilities=[],  # Would combine capabilities
                            estimated_efficiency_gain=0.15,  # Estimate
                            reason=f"Low utilization: {agent.agent_code} ({agent.utilization:.1%})",
                        )
                    )

        return proposals

    def _propose_splits(
        self,
        bottlenecks: List[Bottleneck],
    ) -> List[SplitProposal]:
        """Propose agent splits for overloaded agents."""
        proposals = []
        split_agents: Set[str] = set()

        # Group bottlenecks by agent
        agent_bottlenecks: Dict[str, List[Bottleneck]] = {}
        for bottleneck in bottlenecks:
            if bottleneck.agent_code not in agent_bottlenecks:
                agent_bottlenecks[bottleneck.agent_code] = []
            agent_bottlenecks[bottleneck.agent_code].append(bottleneck)

        for agent_code, agent_bns in agent_bottlenecks.items():
            if agent_code in split_agents:
                continue

            # If agent has multiple bottlenecked task types, consider split
            if len(agent_bns) >= 2:
                split_agents.add(agent_code)

                # Split by task type
                task_groups = []
                for i, bn in enumerate(agent_bns[:2]):
                    task_groups.append(bn.task_types_affected)

                new_agents = [
                    AgentProposal(
                        agent_code=f"{agent_code}_A",
                        agent_type="specialist",
                        parent_code=None,
                        capabilities=[],
                        task_types=task_groups[0] if task_groups else [],
                        reason="Split from overloaded agent",
                    ),
                    AgentProposal(
                        agent_code=f"{agent_code}_B",
                        agent_type="specialist",
                        parent_code=None,
                        capabilities=[],
                        task_types=task_groups[1] if len(task_groups) > 1 else [],
                        reason="Split from overloaded agent",
                    ),
                ]

                proposals.append(
                    SplitProposal(
                        source_agent=agent_code,
                        new_agents=new_agents,
                        task_distribution={
                            f"{agent_code}_A": task_groups[0] if task_groups else [],
                            f"{agent_code}_B": task_groups[1] if len(task_groups) > 1 else [],
                        },
                        estimated_throughput_gain=0.3,  # Estimate
                        reason=f"Multiple bottlenecks detected for {agent_code}",
                    )
                )

        return proposals

    def _estimate_improvement(
        self,
        bottlenecks: List[Bottleneck],
        agents_to_add: List[AgentProposal],
        agents_to_merge: List[MergeProposal],
        agents_to_split: List[SplitProposal],
    ) -> float:
        """Estimate overall improvement from proposals."""
        improvement = 0.0

        # Each resolved bottleneck contributes to improvement
        if bottlenecks:
            bottleneck_contribution = min(0.3, len(bottlenecks) * 0.05)
            improvement += bottleneck_contribution

        # New agents can improve throughput
        improvement += len(agents_to_add) * 0.1

        # Merges improve efficiency
        for merge in agents_to_merge:
            improvement += merge.estimated_efficiency_gain

        # Splits improve throughput
        for split in agents_to_split:
            improvement += split.estimated_throughput_gain

        return min(1.0, improvement)

    def _generate_implementation_steps(
        self,
        agents_to_add: List[AgentProposal],
        agents_to_merge: List[MergeProposal],
        agents_to_split: List[SplitProposal],
    ) -> List[str]:
        """Generate implementation steps for the proposal."""
        steps = []

        # Steps for adding agents
        for agent in agents_to_add:
            steps.append(f"1. Create {agent.agent_type} agent: {agent.agent_code}")
            steps.append(
                f"   - Configure capabilities: {', '.join(agent.capabilities) or 'inherit from parent'}"
            )
            steps.append(f"   - Assign task types: {', '.join(agent.task_types)}")
            if agent.parent_code:
                steps.append(f"   - Register under parent: {agent.parent_code}")

        # Steps for merges
        for merge in agents_to_merge:
            steps.append(
                f"2. Merge agents: {', '.join(merge.source_agents)} -> {merge.target_agent}"
            )
            steps.append(f"   - Transfer capabilities and patterns")
            steps.append(f"   - Update routing rules")
            steps.append(f"   - Decommission merged agents")

        # Steps for splits
        for split in agents_to_split:
            steps.append(f"3. Split agent: {split.source_agent}")
            for new_agent in split.new_agents:
                steps.append(
                    f"   - Create {new_agent.agent_code} with tasks: {', '.join(new_agent.task_types)}"
                )
            steps.append(f"   - Update routing to distribute load")

        if not steps:
            steps.append("No structural changes recommended at this time")

        return steps

    def _assess_risk(
        self,
        agents_to_add: List[AgentProposal],
        agents_to_merge: List[MergeProposal],
        agents_to_split: List[SplitProposal],
    ) -> str:
        """Assess risk level of the proposal."""
        risk_factors = []

        if agents_to_merge:
            risk_factors.append("Agent merges may cause temporary routing disruptions")

        if agents_to_split:
            risk_factors.append("Agent splits require careful load balancing")

        if len(agents_to_add) > 3:
            risk_factors.append("Adding many agents at once increases complexity")

        if not risk_factors:
            return "Low risk: No structural changes or minimal additions"

        return f"Medium risk: {'; '.join(risk_factors)}"

    async def approve_proposal(
        self,
        proposal_id: str,
        approved_by: str,
    ) -> bool:
        """Approve an architecture proposal."""
        await self._db.execute(
            """
            UPDATE architecture_proposals
            SET status = ?, approved_by = ?, approved_at = ?
            WHERE id = ?
            """,
            [
                ProposalStatus.APPROVED.value,
                approved_by,
                datetime.now(timezone.utc).isoformat(),
                proposal_id,
            ],
        )
        return True

    async def reject_proposal(
        self,
        proposal_id: str,
        rejected_by: str,
        reason: str = "",
    ) -> bool:
        """Reject an architecture proposal."""
        await self._db.execute(
            """
            UPDATE architecture_proposals
            SET status = ?, rejection_reason = ?
            WHERE id = ?
            """,
            [ProposalStatus.REJECTED.value, reason, proposal_id],
        )
        return True

    async def save_proposal(self, proposal: ArchitectureProposal) -> None:
        """Save a proposal to the database."""
        await self._db.execute(
            """
            INSERT INTO architecture_proposals (
                id, proposal_type, status, created_at,
                agents_to_add_json, agents_to_merge_json, agents_to_split_json,
                agents_to_remove_json, estimated_improvement, risk_assessment,
                implementation_steps_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                proposal.proposal_id,
                proposal.proposal_type.value,
                proposal.status.value,
                proposal.created_at.isoformat(),
                json.dumps([a.to_dict() for a in proposal.agents_to_add]),
                json.dumps([m.to_dict() for m in proposal.agents_to_merge]),
                json.dumps([s.to_dict() for s in proposal.agents_to_split]),
                json.dumps(proposal.agents_to_remove),
                proposal.estimated_improvement,
                proposal.risk_assessment,
                json.dumps(proposal.implementation_steps),
            ],
        )

    async def get_proposal(self, proposal_id: str) -> Optional[ArchitectureProposal]:
        """Get a proposal by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM architecture_proposals WHERE id = ?",
            [proposal_id],
        )
        if not row:
            return None

        return self._row_to_proposal(row)

    async def get_pending_proposals(self) -> List[ArchitectureProposal]:
        """Get all pending proposals."""
        rows = await self._db.fetch_all(
            "SELECT * FROM architecture_proposals WHERE status = ?",
            [ProposalStatus.PROPOSED.value],
        )
        return [self._row_to_proposal(row) for row in rows]

    def _row_to_proposal(self, row: Dict[str, Any]) -> ArchitectureProposal:
        """Convert database row to proposal."""
        agents_to_add_data = json.loads(row.get("agents_to_add_json", "[]"))
        agents_to_merge_data = json.loads(row.get("agents_to_merge_json", "[]"))
        agents_to_split_data = json.loads(row.get("agents_to_split_json", "[]"))

        agents_to_add = [
            AgentProposal(
                agent_code=a["agent_code"],
                agent_type=a["agent_type"],
                parent_code=a.get("parent_code"),
                capabilities=a.get("capabilities", []),
                task_types=a.get("task_types", []),
                reason=a.get("reason", ""),
            )
            for a in agents_to_add_data
        ]

        agents_to_merge = [
            MergeProposal(
                source_agents=m["source_agents"],
                target_agent=m["target_agent"],
                combined_capabilities=m.get("combined_capabilities", []),
                estimated_efficiency_gain=m.get("estimated_efficiency_gain", 0.0),
                reason=m.get("reason", ""),
            )
            for m in agents_to_merge_data
        ]

        agents_to_split = []
        for s in agents_to_split_data:
            new_agents = [
                AgentProposal(
                    agent_code=a["agent_code"],
                    agent_type=a["agent_type"],
                    parent_code=a.get("parent_code"),
                    capabilities=a.get("capabilities", []),
                    task_types=a.get("task_types", []),
                    reason=a.get("reason", ""),
                )
                for a in s.get("new_agents", [])
            ]
            agents_to_split.append(
                SplitProposal(
                    source_agent=s["source_agent"],
                    new_agents=new_agents,
                    task_distribution=s.get("task_distribution", {}),
                    estimated_throughput_gain=s.get("estimated_throughput_gain", 0.0),
                    reason=s.get("reason", ""),
                )
            )

        return ArchitectureProposal(
            proposal_id=row["id"],
            proposal_type=ProposalType(row["proposal_type"]),
            status=ProposalStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            agents_to_add=agents_to_add,
            agents_to_merge=agents_to_merge,
            agents_to_split=agents_to_split,
            agents_to_remove=json.loads(row.get("agents_to_remove_json", "[]")),
            estimated_improvement=row.get("estimated_improvement", 0.0),
            risk_assessment=row.get("risk_assessment", ""),
            implementation_steps=json.loads(row.get("implementation_steps_json", "[]")),
            approved_by=row.get("approved_by"),
            approved_at=(
                datetime.fromisoformat(row["approved_at"]) if row.get("approved_at") else None
            ),
            implemented_at=(
                datetime.fromisoformat(row["implemented_at"]) if row.get("implemented_at") else None
            ),
        )

    def set_agent_capacity(self, agent_code: str, capacity: float) -> None:
        """Set capacity for an agent."""
        self._agent_capacities[agent_code] = capacity

    async def get_stats(self) -> Dict[str, Any]:
        """Get self-architect statistics."""
        total_row = await self._db.fetch_one("SELECT COUNT(*) as count FROM architecture_proposals")
        approved_row = await self._db.fetch_one(
            "SELECT COUNT(*) as count FROM architecture_proposals WHERE status = ?",
            [ProposalStatus.APPROVED.value],
        )
        implemented_row = await self._db.fetch_one(
            "SELECT COUNT(*) as count FROM architecture_proposals WHERE status = ?",
            [ProposalStatus.IMPLEMENTED.value],
        )

        return {
            "total_proposals": total_row["count"] if total_row else 0,
            "approved_proposals": approved_row["count"] if approved_row else 0,
            "implemented_proposals": implemented_row["count"] if implemented_row else 0,
            "agent_capacities": dict(self._agent_capacities),
        }
