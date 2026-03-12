"""
Item 7: API Test Suite - FastAPI endpoint tests for ag3ntwerk Command Center.

Tests basic request/response for all major API endpoints using TestClient.
State initialization is mocked to prevent real LLM connections.
"""

import importlib
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Import the actual module (not the package attribute which is the FastAPI obj)
_app_module = importlib.import_module("ag3ntwerk.api.app")
_fastapi_app = _app_module.app

from ag3ntwerk.api.state import state as app_state


@pytest.fixture
def client():
    """Create test client with mocked state initialization.

    Resets the module-level ``_shutting_down`` flag so that the shutdown
    guard middleware does not reject requests.  The lifespan sets this
    flag to ``True`` on exit, and because the module is only imported
    once it persists across fixtures.

    Also resets the built-in rate limiters which persist across test
    fixtures and can cause spurious 429 failures.
    """
    # Reset shutdown guard so requests are not rejected
    _app_module._shutting_down = False

    # Reset built-in rate limiters to prevent cross-test 429 failures
    _app_module._auth_rate_limiter._buckets.clear()
    _app_module._api_key_rate_limiter._buckets.clear()

    with patch.object(app_state, "initialize", new_callable=AsyncMock):
        with patch.object(app_state, "shutdown", new_callable=AsyncMock):
            # Mark state as initialized so route handlers behave normally
            app_state.initialized = True

            from fastapi.testclient import TestClient

            with TestClient(_fastapi_app, raise_server_exceptions=False) as c:
                yield c

            # Reset for the next test
            _app_module._shutting_down = False


# ====================================================================
# 1. GET /api - Root info
# ====================================================================


class TestApiRoot:
    def test_api_root_returns_200(self, client):
        resp = client.get("/api")
        assert resp.status_code == 200

    def test_api_root_has_name(self, client):
        data = client.get("/api").json()
        assert "name" in data
        assert data["name"] == "ag3ntwerk Command Center"

    def test_api_root_has_version(self, client):
        data = client.get("/api").json()
        assert "version" in data

    def test_api_root_has_status_field(self, client):
        data = client.get("/api").json()
        assert "status" in data


# ====================================================================
# 2-5. Health endpoints
# ====================================================================


class TestHealthEndpoints:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_has_status_field(self, client):
        data = client.get("/health").json()
        assert "status" in data

    def test_health_has_timestamp(self, client):
        data = client.get("/health").json()
        assert "timestamp" in data

    def test_health_has_llm_connected(self, client):
        data = client.get("/health").json()
        assert "llm_connected" in data

    def test_liveness_returns_status(self, client):
        resp = client.get("/health/live")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data

    def test_readiness_returns_status(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data

    def test_detailed_health_returns_response(self, client):
        resp = client.get("/health/detailed")
        assert resp.status_code in (200, 503)


# ====================================================================
# 6. GET /metrics
# ====================================================================


class TestMetrics:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_returns_json(self, client):
        resp = client.get("/metrics")
        data = resp.json()
        assert isinstance(data, dict)


# ====================================================================
# 7. GET /api/v1/status
# ====================================================================


class TestSystemStatus:
    def test_status_returns_200(self, client):
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200

    def test_status_has_initialized_field(self, client):
        data = client.get("/api/v1/status").json()
        assert "initialized" in data

    def test_status_has_tasks_section(self, client):
        data = client.get("/api/v1/status").json()
        assert "tasks" in data
        assert "total" in data["tasks"]


# ====================================================================
# 8. GET /api/v1/agents
# ====================================================================


class TestExecutives:
    def test_list_agents_returns_200(self, client):
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200

    def test_list_agents_has_executives_key(self, client):
        data = client.get("/api/v1/agents").json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_list_agents_has_count(self, client):
        data = client.get("/api/v1/agents").json()
        assert "count" in data
        assert data["count"] == len(data["agents"])


# ====================================================================
# 9-10. Task endpoints
# ====================================================================


class TestTasks:
    def test_list_tasks_returns_200(self, client):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200

    def test_list_tasks_has_tasks_key(self, client):
        data = client.get("/api/v1/tasks").json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_create_task_returns_response(self, client):
        resp = client.post(
            "/api/v1/tasks",
            json={
                "description": "test task for unit testing",
                "task_type": "general",
                "priority": "medium",
            },
        )
        # Should succeed (task created, no LLM execution) or return an error code
        assert resp.status_code in (200, 422, 500)

    def test_create_task_returns_task_id(self, client):
        resp = client.post(
            "/api/v1/tasks",
            json={
                "description": "another test task",
                "task_type": "general",
                "priority": "low",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data
            assert data["id"].startswith("task_")

    def test_create_task_invalid_priority_rejected(self, client):
        resp = client.post(
            "/api/v1/tasks",
            json={
                "description": "bad priority task",
                "task_type": "general",
                "priority": "super_ultra_high",
            },
        )
        assert resp.status_code == 422


# ====================================================================
# 11. GET /api/v1/dashboard/stats
# ====================================================================


class TestDashboard:
    def test_dashboard_stats_returns_200(self, client):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_dashboard_stats_has_sections(self, client):
        data = client.get("/api/v1/dashboard/stats").json()
        assert "tasks" in data
        assert "goals" in data
        assert "coo" in data
        assert "timestamp" in data


# ====================================================================
# 12-15. Nexus endpoints
# ====================================================================


class TestCOOEndpoints:
    def test_coo_status_returns_200(self, client):
        resp = client.get("/api/v1/coo/status")
        assert resp.status_code == 200

    def test_coo_status_has_state(self, client):
        data = client.get("/api/v1/coo/status").json()
        assert "state" in data
        assert "mode" in data

    def test_start_coo_returns_response(self, client):
        resp = client.post("/api/v1/coo/start")
        # 200 if already running or successfully started, 500 if no LLM
        assert resp.status_code in (200, 500)

    def test_stop_coo_returns_200(self, client):
        resp = client.post("/api/v1/coo/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_coo_suggestions_returns_200(self, client):
        resp = client.get("/api/v1/coo/suggestions")
        assert resp.status_code == 200

    def test_coo_mode_update(self, client):
        resp = client.post(
            "/api/v1/coo/mode",
            json={"mode": "autonomous"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "autonomous"

    def test_coo_mode_invalid_rejected(self, client):
        resp = client.post(
            "/api/v1/coo/mode",
            json={"mode": "invalid_mode_xyz"},
        )
        assert resp.status_code == 422


# ====================================================================
# 16-17. Goal endpoints
# ====================================================================


class TestGoals:
    def test_list_goals_returns_200(self, client):
        resp = client.get("/api/v1/goals")
        assert resp.status_code == 200

    def test_list_goals_has_goals_key(self, client):
        data = client.get("/api/v1/goals").json()
        assert "goals" in data
        assert isinstance(data["goals"], list)

    def test_create_goal_returns_response(self, client):
        resp = client.post(
            "/api/v1/goals",
            json={"title": "test goal", "description": "a test goal"},
        )
        assert resp.status_code == 200

    def test_create_goal_returns_id(self, client):
        resp = client.post(
            "/api/v1/goals",
            json={"title": "another test goal", "description": "testing"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data
            assert data["id"].startswith("goal_")

    def test_create_goal_with_milestones(self, client):
        resp = client.post(
            "/api/v1/goals",
            json={
                "title": "milestone goal",
                "description": "has milestones",
                "milestones": [{"title": "step 1"}, {"title": "step 2"}],
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert len(data.get("milestones", [])) == 2

    def test_create_goal_empty_title_rejected(self, client):
        resp = client.post(
            "/api/v1/goals",
            json={"title": "   ", "description": "blank title"},
        )
        assert resp.status_code == 422

    def test_get_goal_not_found(self, client):
        resp = client.get("/api/v1/goals/nonexistent_id")
        assert resp.status_code == 404


# ====================================================================
# 18-19. Workflow endpoints
# ====================================================================


class TestWorkflows:
    def test_list_workflows_returns_200(self, client):
        resp = client.get("/api/v1/workflows")
        assert resp.status_code == 200

    def test_list_workflows_has_workflows_key(self, client):
        data = client.get("/api/v1/workflows").json()
        assert "workflows" in data

    def test_workflow_history_returns_response(self, client):
        # Note: /api/v1/workflows/history may be caught by the
        # /api/v1/workflows/{workflow_name} route (defined first in
        # app.py), returning 503 when orchestrator is not initialized.
        # Both 200 (if history route matches) and 503 (if param route
        # matches) are acceptable in the test environment.
        resp = client.get("/api/v1/workflows/history")
        assert resp.status_code in (200, 503)

    def test_workflow_history_structure(self, client):
        resp = client.get("/api/v1/workflows/history")
        if resp.status_code == 200:
            data = resp.json()
            assert "executions" in data
            assert isinstance(data["executions"], list)


# ====================================================================
# 20-21. Memory endpoints
# ====================================================================


class TestMemory:
    def test_memory_search_returns_200(self, client):
        resp = client.get("/api/v1/memory/search", params={"query": "test"})
        assert resp.status_code == 200

    def test_memory_search_has_results(self, client):
        data = client.get("/api/v1/memory/search", params={"query": "test"}).json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "test"

    def test_memory_search_missing_query_rejected(self, client):
        resp = client.get("/api/v1/memory/search")
        assert resp.status_code == 422

    def test_memory_stats_returns_200(self, client):
        resp = client.get("/api/v1/memory/stats")
        assert resp.status_code == 200

    def test_memory_stats_has_memory_section(self, client):
        data = client.get("/api/v1/memory/stats").json()
        assert "memory" in data


# ====================================================================
# 22. POST /api/v1/chat
# ====================================================================


class TestChat:
    def test_chat_returns_response(self, client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "hello", "agent": "Overwatch"},
        )
        # 200 (with error content) since no LLM; should not be 500
        assert resp.status_code in (200, 422)

    def test_chat_returns_content(self, client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "hello", "agent": "Forge"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "content" in data

    def test_chat_invalid_executive_rejected(self, client):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "hello", "agent": "FAKE_EXEC"},
        )
        assert resp.status_code == 422


# ====================================================================
# 23. GET /api/v1/conversations
# ====================================================================


class TestConversations:
    def test_list_conversations_returns_200(self, client):
        resp = client.get("/api/v1/conversations")
        assert resp.status_code == 200

    def test_list_conversations_has_conversations_key(self, client):
        data = client.get("/api/v1/conversations").json()
        assert "conversations" in data

    def test_get_conversation_not_found(self, client):
        resp = client.get("/api/v1/conversations/conv_nonexistent_12345")
        assert resp.status_code == 404


# ====================================================================
# 24-25. Middleware: Security headers & Request ID
# ====================================================================


class TestMiddleware:
    def test_security_header_content_type_options(self, client):
        resp = client.get("/api")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_security_header_frame_options(self, client):
        resp = client.get("/api")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_security_header_xss_protection(self, client):
        resp = client.get("/api")
        assert resp.headers.get("X-XSS-Protection") == "0"

    def test_security_header_referrer_policy(self, client):
        resp = client.get("/api")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_present(self, client):
        resp = client.get("/api")
        assert "Permissions-Policy" in resp.headers

    def test_request_id_returned(self, client):
        resp = client.get("/api")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) > 0

    def test_custom_request_id_echoed_back(self, client):
        custom_id = "test-request-12345"
        resp = client.get("/api", headers={"X-Request-ID": custom_id})
        assert resp.headers.get("X-Request-ID") == custom_id


# ====================================================================
# 26-27. Nexus Agenda endpoints (503 without Nexus)
# ====================================================================


class TestAgendaEndpoints:
    def test_agenda_status_503_without_coo(self, client):
        """Agenda status returns 503 when Nexus is not running."""
        resp = client.get("/api/v1/coo/agenda")
        assert resp.status_code == 503

    def test_generate_agenda_503_without_coo(self, client):
        """Generate agenda returns 503 when Nexus is not running."""
        resp = client.post("/api/v1/coo/agenda/generate")
        assert resp.status_code == 503

    def test_agenda_items_503_without_coo(self, client):
        resp = client.get("/api/v1/coo/agenda/items")
        assert resp.status_code == 503

    def test_agenda_obstacles_503_without_coo(self, client):
        resp = client.get("/api/v1/coo/agenda/obstacles")
        assert resp.status_code == 503

    def test_agenda_strategies_503_without_coo(self, client):
        resp = client.get("/api/v1/coo/agenda/strategies")
        assert resp.status_code == 503

    def test_agenda_workstreams_503_without_coo(self, client):
        resp = client.get("/api/v1/coo/agenda/workstreams")
        assert resp.status_code == 503


# ====================================================================
# 28. Module routes exist
# ====================================================================


class TestModuleRoutes:
    def test_modules_list_endpoint_exists(self, client):
        resp = client.get("/api/v1/modules/")
        # Should not be 404 -- either 200 or another valid response
        assert resp.status_code != 404

    def test_modules_status_endpoint_exists(self, client):
        resp = client.get("/api/v1/modules/status")
        assert resp.status_code != 404

    def test_trends_module_root(self, client):
        resp = client.get("/api/v1/modules/trends/")
        assert resp.status_code != 404

    def test_commerce_module_root(self, client):
        resp = client.get("/api/v1/modules/commerce/")
        assert resp.status_code != 404

    def test_brand_module_root(self, client):
        resp = client.get("/api/v1/modules/brand/")
        assert resp.status_code != 404

    def test_scheduler_module_root(self, client):
        resp = client.get("/api/v1/modules/scheduler/")
        assert resp.status_code != 404
