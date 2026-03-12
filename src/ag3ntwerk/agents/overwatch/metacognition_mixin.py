"""Metacognition integration mixin for Overwatch."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.base import Manager

if TYPE_CHECKING:
    from ag3ntwerk.core.base import Task

logger = get_logger(__name__)


class MetacognitionMixin:
    """Metacognition integration for Overwatch."""

    # Maps common task types to desired personality trait profiles
    TASK_TRAIT_MAP: Dict[str, Dict[str, float]] = {
        "security_review": {"thoroughness": 0.9, "risk_tolerance": 0.2, "assertiveness": 0.6},
        "security_scan": {"thoroughness": 0.9, "risk_tolerance": 0.1, "vigilance": 0.9},
        "security_audit": {"thoroughness": 0.95, "risk_tolerance": 0.1, "collaboration": 0.4},
        "code_review": {"thoroughness": 0.8, "creativity": 0.4, "assertiveness": 0.5},
        "architecture_design": {"creativity": 0.8, "thoroughness": 0.7, "risk_tolerance": 0.5},
        "market_research": {"creativity": 0.7, "adaptability": 0.7, "thoroughness": 0.6},
        "marketing_campaign": {"creativity": 0.9, "audience_empathy": 0.8, "narrative_craft": 0.7},
        "brand_strategy": {"creativity": 0.8, "collaboration": 0.7, "assertiveness": 0.6},
        "financial_analysis": {
            "thoroughness": 0.9,
            "fiscal_conservatism": 0.8,
            "margin_sensitivity": 0.9,
        },
        "budget_review": {"thoroughness": 0.9, "risk_tolerance": 0.2, "assertiveness": 0.5},
        "risk_assessment": {"thoroughness": 0.9, "risk_tolerance": 0.1, "assertiveness": 0.6},
        "compliance_audit": {"thoroughness": 0.95, "risk_tolerance": 0.1, "collaboration": 0.4},
        "product_planning": {"creativity": 0.7, "collaboration": 0.8, "thoroughness": 0.6},
        "data_analysis": {"thoroughness": 0.8, "creativity": 0.4, "adaptability": 0.5},
        "strategic_planning": {"creativity": 0.6, "thoroughness": 0.7, "collaboration": 0.7},
        "incident_response": {"assertiveness": 0.8, "risk_tolerance": 0.4, "adaptability": 0.8},
        "engineering_review": {"thoroughness": 0.85, "creativity": 0.5, "collaboration": 0.6},
        "innovation_research": {"creativity": 0.9, "risk_tolerance": 0.7, "adaptability": 0.8},
        "communication_plan": {"collaboration": 0.9, "creativity": 0.7, "assertiveness": 0.5},
        "revenue_optimization": {"assertiveness": 0.7, "thoroughness": 0.7, "risk_tolerance": 0.5},
    }

    def _infer_task_traits(self, task: "Task") -> Dict[str, float]:
        """
        Extract desired personality traits for a task from context, learned map, or TASK_TRAIT_MAP.
        """
        # Check for explicit traits in task context
        if task.context and task.context.get("_desired_traits"):
            return task.context["_desired_traits"]

        # Check learned trait map via metacognition service
        if self._metacognition_service is not None:
            static = self.TASK_TRAIT_MAP.get(task.task_type, {})
            return self._metacognition_service.get_effective_traits(task.task_type, static)

        return self.TASK_TRAIT_MAP.get(task.task_type, {})

    def _personality_score_agents(
        self,
        task: "Task",
        candidates: List[str],
    ) -> Optional[str]:
        """
        Score candidate agents by personality fit and return the best match.

        Returns best agent code if score > 0.6, else None.
        """
        if not self._metacognition_service:
            return None

        task_traits = self._infer_task_traits(task)
        if not task_traits:
            return None

        scores = self._metacognition_service.score_agents_for_task(
            task_traits,
            candidates,
            task_type=task.task_type,
        )
        if scores and scores[0][1] > 0.6:
            return scores[0][0]

        return None

    def _filter_conflicting_agents(
        self,
        task: "Task",
        candidates: List[str],
    ) -> List[str]:
        """Remove candidates with high-severity conflicts against currently active agents."""
        if not self._metacognition_service or len(candidates) <= 1:
            return candidates
        active_agents = [
            t.assigned_to
            for t in self._active_tasks.values()
            if t.assigned_to and t.assigned_to in self._subordinates
        ]
        if not active_agents:
            return candidates
        safe = []
        for candidate in candidates:
            conflicts = self._metacognition_service.detect_team_conflicts(
                active_agents + [candidate]
            )
            high = any(c.severity > 0.5 for c in conflicts if candidate in c.agents_involved)
            if not high:
                safe.append(candidate)
        return safe if safe else candidates  # Never filter to zero

    async def _route_collaborative_task(
        self,
        task: "Task",
        team_size: int = 2,
    ) -> List[str]:
        """Form optimal team using personality dynamics for collaborative tasks."""
        if not self._metacognition_service:
            best = await self._route_task(task)
            return [best] if best else []

        # Phase 5: Check learned team compositions first
        if self._metacognition_service is not None:
            learned = self._metacognition_service.recommend_learned_team(
                task.task_type,
                team_size,
            )
            if not learned.get("fallback_used") and learned.get("success_rate", 0) > 0.7:
                team = [c for c in learned["team"] if c in self._subordinates]
                if len(team) >= team_size:
                    return team

        task_traits = self._infer_task_traits(task)
        suggestion = self._metacognition_service.suggest_team_for_task(task_traits, team_size)
        team = [c for c in suggestion.suggested_agents if c in self._subordinates]
        # Check team for conflicts, log warnings
        if len(team) > 1:
            conflicts = self._metacognition_service.detect_team_conflicts(team)
            high = [c for c in conflicts if c.severity > 0.5]
            if high:
                task.context = task.context or {}
                task.context["_team_conflicts"] = [c.to_dict() for c in high]
        return team

    def connect_metacognition(self, service: Any) -> None:
        """
        Connect the metacognition service and register all agents.

        Registers all subordinate agents with personality seeds,
        and attaches personality profiles to agent instances.

        Args:
            service: MetacognitionService instance
        """
        self._metacognition_service = service

        # Load persisted profiles first (skip agents already loaded)
        service.load_on_startup()

        # Register all subordinate agents
        for agent_code, exec_agent in self._subordinates.items():
            if not service.is_registered(agent_code):
                profile = service.register_agent(agent_code)
            else:
                profile = service.get_profile(agent_code)

            # Attach metacognition components to agent instance
            exec_agent.attach_metacognition(
                personality=profile,
                heuristic_engine=service.get_heuristic_engine(agent_code),
                reflector=service.get_reflector(agent_code),
            )

            # Propagate metacognition service to the agent (if it's a Manager)
            if isinstance(exec_agent, Manager):
                exec_agent.connect_metacognition_service(service)

            # Propagate to sub-managers under each agent
            if isinstance(exec_agent, Manager):
                for mgr in exec_agent._subordinates.values():
                    if isinstance(mgr, Manager):
                        mgr.connect_metacognition_service(service)
                        if not mgr._heuristic_engine:
                            mgr._heuristic_engine = service.get_heuristic_engine(agent_code)

        # Register Overwatch itself
        if not service.is_registered("Overwatch"):
            profile = service.register_agent("Overwatch")
            self.personality = profile
        else:
            self.personality = service.get_profile("Overwatch")

        logger.info(
            f"Connected metacognition service with "
            f"{len(service.get_all_profiles())} agent profiles"
        )

    def disconnect_metacognition(self) -> None:
        """Disconnect the metacognition service."""
        self._metacognition_service = None
        logger.info("Disconnected metacognition service")

    def is_metacognition_enabled(self) -> bool:
        """Check if metacognition service is connected."""
        return self._metacognition_service is not None

    def trigger_system_reflection(self) -> Optional[Dict[str, Any]]:
        """
        Trigger a system-level metacognition reflection.

        Gathers health, profiles, outcomes, drift, and conflict data,
        then delegates to the SystemReflector. Stores active conflicts
        for routing decisions and auto-saves profiles.

        Returns:
            SystemReflection dict (with conflicts), or None if not connected
        """
        if not self._metacognition_service:
            return None

        # Gather agent health
        agent_health = {}
        if self._health_router:
            agent_health = self._health_router.get_all_health()

        # Gather drift summary
        drift_summary = self._drift_monitor.get_drift_summary()

        # Auto-respond to critical drift
        drift_responses = []
        if self._metacognition_service is not None:
            drift_responses = self._metacognition_service.respond_to_drift()

        # Detect active conflicts
        active_codes = list(self._subordinates.keys())
        conflicts = self._metacognition_service.detect_team_conflicts(active_codes)
        conflict_dicts = [
            {
                "description": c.description,
                "recommendation": c.recommendation,
                "severity": c.severity,
            }
            for c in conflicts
            if c.severity > 0.4
        ]

        reflection = self._metacognition_service.system_reflect(
            agent_health=agent_health,
            drift_summary=drift_summary,
            compatibility_issues=conflict_dicts,
        )

        # Store conflicts for routing decisions
        self._active_conflicts = conflicts

        # Auto-save profiles after reflection
        self._metacognition_service.save_if_auto()

        result = reflection.to_dict()
        result["conflicts"] = [c.to_dict() for c in conflicts]
        result["drift_responses"] = [r.to_dict() for r in drift_responses]
        result["metacognition_insights"] = self._get_metacognition_insights()
        return result

    def _get_metacognition_insights(self) -> Dict[str, Any]:
        """Get Phase 5 metacognition insights for Nexus/reflection integration."""
        if not self._metacognition_service:
            return {}
        svc = self._metacognition_service
        return {
            "agent_health": {
                code: svc.classify_agent_health(code) for code in svc.get_all_profiles()
            },
            "trend_summary": svc.get_trend_summary(),
            "team_stats": svc.get_team_stats(),
            "learned_trait_map": svc.get_learned_trait_map(),
            "total_trait_snapshots": len(svc._trait_snapshots),
            "total_peer_recommendations": len(svc._peer_recommendations),
        }

    def get_metacognition_status(self) -> Dict[str, Any]:
        """
        Get metacognition status including personality summaries,
        reflection counts, and heuristic stats.
        """
        if not self._metacognition_service:
            return {"enabled": False}

        return {
            "enabled": True,
            **self._metacognition_service.get_stats(),
        }
