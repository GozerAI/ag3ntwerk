"""End-to-end integration tests for the metacognition pipeline (Phase 5)."""

import os
import pytest
from datetime import datetime, timezone, timedelta

from ag3ntwerk.modules.metacognition.service import (
    MetacognitionService,
    TraitSnapshot,
    TraitMapUpdate,
)
from ag3ntwerk.learning.facades.metacognition_facade import MetacognitionFacade


def _make_populated_service():
    """Create a service with 4 agents and skewed task outcomes."""
    svc = MetacognitionService()
    svc._auto_save = False

    svc.register_agent(
        "Forge",
        seed_traits={
            "thoroughness": 0.9,
            "creativity": 0.4,
            "risk": 0.2,
            "assertiveness": 0.5,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "Keystone",
        seed_traits={
            "thoroughness": 0.7,
            "creativity": 0.3,
            "risk": 0.3,
            "assertiveness": 0.6,
            "collaboration": 0.5,
            "adaptability": 0.5,
            "decision": "analytical",
            "communication": "direct",
        },
    )
    svc.register_agent(
        "Echo",
        seed_traits={
            "thoroughness": 0.4,
            "creativity": 0.9,
            "risk": 0.7,
            "assertiveness": 0.5,
            "collaboration": 0.7,
            "adaptability": 0.8,
            "decision": "intuitive",
            "communication": "collaborative",
        },
    )
    svc.register_agent(
        "Index",
        seed_traits={
            "thoroughness": 0.3,
            "creativity": 0.8,
            "risk": 0.8,
            "assertiveness": 0.4,
            "collaboration": 0.6,
            "adaptability": 0.9,
            "decision": "intuitive",
            "communication": "collaborative",
        },
    )

    # Forge and Keystone succeed at code_review, Echo and Index fail
    for i in range(15):
        svc._task_outcomes.append(
            {
                "agent_code": "Forge",
                "task_type": "code_review",
                "success": True,
                "task_id": f"cr-cto-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "Keystone",
                "task_type": "code_review",
                "success": True,
                "task_id": f"cr-cfo-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "Echo",
                "task_type": "code_review",
                "success": False,
                "task_id": f"cr-cmo-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )
        svc._task_outcomes.append(
            {
                "agent_code": "Index",
                "task_type": "code_review",
                "success": False,
                "task_id": f"cr-cdo-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )

    # Echo succeeds at market_research, others don't participate much
    for i in range(15):
        svc._task_outcomes.append(
            {
                "agent_code": "Echo",
                "task_type": "market_research",
                "success": True,
                "task_id": f"mr-cmo-{i}",
                "duration_ms": 100,
                "timestamp": "2025-01-01T00:00:00",
            }
        )

    return svc


class TestFullPipelineFlow:

    def test_register_outcomes_snapshots_trends_coherence(self):
        """Full pipeline: register → outcomes → snapshots → trends → coherence → stats."""
        svc = _make_populated_service()

        # Take trait snapshots
        snaps = svc.record_trait_snapshot()
        assert len(snaps) == 4

        # Add more snapshots with time gaps to enable trend classification
        for i in range(5):
            for agent in ["Forge", "Keystone", "Echo", "Index"]:
                svc._trait_snapshots.append(
                    TraitSnapshot(
                        agent_code=agent,
                        trait_values={
                            "thoroughness": svc._profiles[agent].get_trait("thoroughness").value
                            + i * 0.01
                        },
                        trait_baselines={
                            "thoroughness": svc._profiles[agent].get_trait("thoroughness").baseline
                        },
                        timestamp=datetime.now(timezone.utc) - timedelta(seconds=500 - i * 100),
                    )
                )

        # Classify trends
        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification in ("improving", "stable", "declining", "oscillating")

        # Compute coherence
        report = svc.compute_coherence("Forge")
        assert report is not None
        assert 0.0 <= report.coherence_score <= 1.0
        assert report.health_classification in ("healthy", "drifting", "oscillating", "degrading")

        # Stats should be comprehensive
        stats = svc.get_stats()
        assert stats["total_trait_snapshots"] > 0
        assert "agent_health" in stats
        assert len(stats["registered_agents"]) == 4


class TestCrossAgentLearningFlow:

    def test_peer_recommendations_target_underperformers(self):
        """Peer recommendations should target agents who underperform."""
        svc = _make_populated_service()

        # Echo is an underperformer on code_review
        recs = svc.generate_peer_recommendations("Echo")
        assert len(recs) > 0
        assert all(r.target_agent == "Echo" for r in recs)

        # Forge is a top performer — should get no recommendations for code_review
        recs_cto = svc.generate_peer_recommendations("Forge")
        code_review_recs = [r for r in recs_cto if r.task_type == "code_review"]
        assert len(code_review_recs) == 0


class TestTeamLearningFlow:

    def test_team_stats_and_recommendation(self):
        """Record team outcomes → get stats → get recommendation."""
        svc = _make_populated_service()

        # Record team outcomes
        for i in range(10):
            svc.record_team_outcome(
                ["Forge", "Keystone"],
                "code_review",
                success=True,
                task_id=f"team-{i}",
            )
        for i in range(10):
            svc.record_team_outcome(
                ["Echo", "Index"],
                "code_review",
                success=i < 3,
                task_id=f"team-fail-{i}",
            )

        # Get team stats
        stats = svc.get_team_stats()
        assert stats["total_team_outcomes"] == 20
        assert len(stats["compositions"]) >= 1

        # Best team should be Forge+Keystone
        best = max(stats["compositions"], key=lambda c: c["success_rate"])
        assert best["success_rate"] == 1.0

        # Recommend learned team
        result = svc.recommend_learned_team("code_review", team_size=2)
        assert result["source"] == "learned"
        assert result["success_rate"] == 1.0

        # Get best pairs
        pairs = svc.get_best_pairs()
        assert len(pairs) >= 2
        assert pairs[0]["success_rate"] >= pairs[1]["success_rate"]


class TestTraitMapOptimizationFlow:

    def test_apply_validate_cycle(self):
        """Feed outcomes → apply suggestions → validate updates."""
        svc = _make_populated_service()

        # Try to apply trait map suggestions
        suggestions = svc.suggest_trait_map_updates(min_correlation=0.5)
        if not suggestions:
            pytest.skip("Attribution did not produce suggestions")

        updates = svc.apply_trait_map_suggestions(min_confidence=0.5)
        assert len(updates) > 0

        # Learned map should be populated
        learned = svc.get_learned_trait_map()
        assert len(learned) > 0

        # Get effective traits — should merge learned into static
        static = {"thoroughness": 0.5, "creativity": 0.5}
        effective = svc.get_effective_traits("code_review", static)
        # If code_review has a learned thoroughness, it should override static
        if "code_review" in learned and "thoroughness" in learned["code_review"]:
            assert effective["thoroughness"] == learned["code_review"]["thoroughness"]


class TestCoherenceWithDrift:

    def test_coherence_degrades_with_extreme_traits(self):
        """Extreme trait values should lower coherence score."""
        svc = MetacognitionService()
        svc._auto_save = False

        # Register with moderate traits — should be healthy
        svc.register_agent(
            "Forge",
            seed_traits={
                "thoroughness": 0.5,
                "creativity": 0.5,
                "risk": 0.5,
                "assertiveness": 0.5,
                "collaboration": 0.5,
                "adaptability": 0.5,
                "decision": "analytical",
                "communication": "direct",
            },
        )
        healthy_report = svc.compute_coherence("Forge")
        assert healthy_report.coherence_score == 1.0

        # Register with extreme traits — should have tensions
        svc.register_agent(
            "Axiom",
            seed_traits={
                "thoroughness": 0.95,
                "creativity": 0.5,
                "risk": 0.95,
                "assertiveness": 0.95,
                "collaboration": 0.95,
                "adaptability": 0.05,
                "decision": "analytical",
                "communication": "direct",
            },
        )
        extreme_report = svc.compute_coherence("Axiom")
        assert extreme_report.coherence_score < healthy_report.coherence_score
        assert len(extreme_report.tensions) > 0


class TestPersistenceRoundTrip:

    def test_full_pipeline_save_load(self, tmp_path):
        """Full pipeline → save → load → verify state restored."""
        svc1 = _make_populated_service()

        # Take snapshots
        svc1.record_trait_snapshot()

        # Record team outcomes
        for i in range(10):
            svc1.record_team_outcome(["Forge", "Keystone"], "code_review", success=True)

        # Apply trait map suggestions if possible
        svc1.apply_trait_map_suggestions(min_confidence=0.5)

        # Generate peer recommendations
        svc1.generate_peer_recommendations("Echo")

        # Save
        path = str(tmp_path / "state.json")
        svc1.save_phase5_state(path)

        # Load into fresh service
        svc2 = MetacognitionService()
        svc2._auto_save = False
        counts = svc2.load_phase5_state(path)

        assert counts["snapshots"] == len(svc1._trait_snapshots)
        assert counts["team_outcomes"] == len(svc1._team_outcomes)
        assert counts["peer_recommendations"] == len(svc1._peer_recommendations)


class TestFacadePhaseRun:

    def test_run_metacognition_phase_returns_all_keys(self):
        """Facade's run_metacognition_phase should return all Phase 5 keys."""
        svc = _make_populated_service()
        facade = MetacognitionFacade()
        facade.connect_service(svc)

        result = facade.run_metacognition_phase()
        assert "trait_snapshots_taken" in result
        assert "heuristics_shared" in result
        assert "trait_map_updates_applied" in result
        assert "trait_map_validations" in result
        assert "outcomes_processed" in result
        assert "heuristics_tuned" in result


class TestTemporalTrendThroughSnapshots:

    def test_known_improving_pattern(self):
        """Inject snapshots with known improving pattern → verify classification."""
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")

        # Inject steadily increasing values
        for i in range(10):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5 + i * 0.03},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=1000 - i * 100),
                )
            )

        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "improving"
        assert trend.velocity > 0

    def test_known_declining_pattern(self):
        """Inject snapshots with known declining pattern → verify classification."""
        svc = MetacognitionService()
        svc._auto_save = False
        svc.register_agent("Forge")

        for i in range(10):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.8 - i * 0.03},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=1000 - i * 100),
                )
            )

        trend = svc.classify_trait_trend("Forge", "thoroughness")
        assert trend is not None
        assert trend.classification == "declining"
        assert trend.velocity < 0
