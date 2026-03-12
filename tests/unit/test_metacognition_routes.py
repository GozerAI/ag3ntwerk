"""Tests for metacognition API routes (Phase 2, Step 5)."""

import pytest
from fastapi.testclient import TestClient

from ag3ntwerk.api.metacognition_routes import router, set_metacognition_service
from ag3ntwerk.modules.metacognition.service import MetacognitionService


@pytest.fixture
def client():
    """Create test client with metacognition routes."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    svc = MetacognitionService()
    for code in ["Forge", "Echo", "Keystone"]:
        svc.register_agent(code)

    # Process some outcomes so there's data
    svc.on_task_completed(
        agent_code="Forge",
        task_id="t1",
        task_type="code_review",
        success=True,
        duration_ms=100.0,
    )
    svc.on_task_completed(
        agent_code="Echo",
        task_id="t2",
        task_type="marketing_campaign",
        success=False,
        error="budget exceeded",
    )

    set_metacognition_service(svc)
    yield TestClient(app)
    set_metacognition_service(None)


@pytest.fixture
def empty_client():
    """Create test client without a service."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    set_metacognition_service(None)
    yield TestClient(app)


# =========================================================================
# Status
# =========================================================================


class TestStatusEndpoint:
    def test_get_status(self, client):
        resp = client.get("/metacognition/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "registered_agents" in data
        assert "Forge" in data["registered_agents"]
        assert data["total_reflections"] >= 2

    def test_status_503_when_no_service(self, empty_client):
        resp = empty_client.get("/metacognition/status")
        assert resp.status_code == 503


# =========================================================================
# Profiles
# =========================================================================


class TestProfileEndpoints:
    def test_get_all_profiles(self, client):
        resp = client.get("/metacognition/profiles")
        assert resp.status_code == 200
        data = resp.json()
        assert "Forge" in data
        assert "agent_code" in data["Forge"]

    def test_get_single_profile(self, client):
        resp = client.get("/metacognition/profiles/Forge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_code"] == "Forge"
        assert "risk_tolerance" in data

    def test_get_unknown_profile_404(self, client):
        resp = client.get("/metacognition/profiles/UNKNOWN")
        assert resp.status_code == 404


# =========================================================================
# Reflection
# =========================================================================


class TestReflectionEndpoints:
    def test_trigger_system_reflection(self, client):
        resp = client.post("/metacognition/reflect")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_health_score" in data

    def test_get_reflections(self, client):
        resp = client.get("/metacognition/reflections/Forge")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_reflections_unknown_agent_404(self, client):
        resp = client.get("/metacognition/reflections/UNKNOWN")
        assert resp.status_code == 404

    def test_get_reflections_with_limit(self, client):
        resp = client.get("/metacognition/reflections/Forge?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 1


# =========================================================================
# Heuristics
# =========================================================================


class TestHeuristicEndpoints:
    def test_get_heuristic_stats(self, client):
        resp = client.get("/metacognition/heuristics/Forge")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_code" in data
        assert data["agent_code"] == "Forge"
        assert "total_heuristics" in data

    def test_get_heuristics_unknown_agent_404(self, client):
        resp = client.get("/metacognition/heuristics/UNKNOWN")
        assert resp.status_code == 404


# =========================================================================
# Compatibility
# =========================================================================


class TestCompatibilityEndpoints:
    def test_get_compatibility_matrix(self, client):
        resp = client.get("/metacognition/compatibility")
        assert resp.status_code == 200
        data = resp.json()
        assert "Forge" in data
        assert "Echo" in data["Forge"]

    def test_get_pairwise_compatibility(self, client):
        resp = client.get("/metacognition/compatibility/Forge/Echo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_a"] == "Forge"
        assert data["agent_b"] == "Echo"
        assert 0.0 <= data["overall_score"] <= 1.0

    def test_pairwise_unknown_agent_404(self, client):
        resp = client.get("/metacognition/compatibility/Forge/UNKNOWN")
        assert resp.status_code == 404
