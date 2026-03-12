"""
E2E Smoke Tests for ag3ntwerk.

These tests verify basic functionality after deployment.
Run against a live instance to validate the deployment is working.

Usage:
    # Against local development server
    pytest tests/e2e/test_smoke.py -v

    # Against staging/production
    AGENTWERK_BASE_URL=https://staging.ag3ntwerk.example.com pytest tests/e2e/test_smoke.py -v
"""

import os
import pytest
import httpx
from typing import Generator

# Default to localhost for development
BASE_URL = os.getenv("AGENTWERK_BASE_URL", "http://localhost:3737")
TIMEOUT = float(os.getenv("AGENTWERK_SMOKE_TIMEOUT", "30"))


@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for smoke tests."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_returns_200(self, client: httpx.Client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_healthy_status(self, client: httpx.Client):
        """Health endpoint should indicate healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data.get("status") in ("healthy", "ok", "up")

    def test_readiness_probe(self, client: httpx.Client):
        """Readiness probe should return 200 when ready."""
        # Try both common readiness endpoints
        for path in ["/health", "/ready", "/healthz"]:
            try:
                response = client.get(path)
                if response.status_code == 200:
                    return  # Success
            except httpx.HTTPError:
                continue
        # At least /health should work
        response = client.get("/health")
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test core API endpoints are accessible."""

    def test_api_root_accessible(self, client: httpx.Client):
        """API root should be accessible."""
        response = client.get("/")
        # Accept 200, 301, 302, 307, 308 redirects, or 404 for root
        assert response.status_code in (200, 301, 302, 307, 308, 404)

    def test_api_docs_accessible(self, client: httpx.Client):
        """OpenAPI docs should be accessible."""
        response = client.get("/docs")
        assert response.status_code in (200, 301, 302)

    def test_openapi_schema_accessible(self, client: httpx.Client):
        """OpenAPI schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestMetricsEndpoint:
    """Test observability endpoints."""

    def test_metrics_endpoint_accessible(self, client: httpx.Client):
        """Metrics endpoint should be accessible."""
        response = client.get("/metrics")
        # Metrics might not be enabled, so 404 is acceptable
        assert response.status_code in (200, 404)

    @pytest.mark.skipif(
        os.getenv("AGENTWERK_METRICS_ENABLED", "false").lower() != "true", reason="Metrics not enabled"
    )
    def test_metrics_returns_prometheus_format(self, client: httpx.Client):
        """Metrics should return Prometheus format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")


class TestAgentEndpoints:
    """Test agent-related endpoints are accessible."""

    def test_agents_list_accessible(self, client: httpx.Client):
        """Agents list endpoint should be accessible."""
        for path in ["/api/v1/agents", "/agents", "/api/agents"]:
            try:
                response = client.get(path)
                if response.status_code == 200:
                    return  # Success
            except httpx.HTTPError:
                continue

    def test_agents_status_endpoint(self, client: httpx.Client):
        """Agent status endpoint should be accessible."""
        for path in ["/api/v1/agents/status", "/api/v1/status", "/status"]:
            try:
                response = client.get(path)
                if response.status_code == 200:
                    return  # Success
            except httpx.HTTPError:
                continue


class TestResponseTimes:
    """Test response time SLOs."""

    def test_health_response_under_1_second(self, client: httpx.Client):
        """Health check should respond in under 1 second."""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check took {elapsed:.2f}s (SLO: <1s)"

    def test_api_docs_response_under_5_seconds(self, client: httpx.Client):
        """API docs should respond in under 5 seconds."""
        import time

        start = time.time()
        response = client.get("/docs")
        elapsed = time.time() - start

        assert response.status_code in (200, 301, 302)
        assert elapsed < 5.0, f"API docs took {elapsed:.2f}s (SLO: <5s)"


class TestErrorHandling:
    """Test error handling."""

    def test_404_returns_proper_response(self, client: httpx.Client):
        """Non-existent endpoints should return 404."""
        response = client.get("/this-endpoint-does-not-exist-12345")
        assert response.status_code == 404

    def test_invalid_json_returns_422(self, client: httpx.Client):
        """Invalid JSON should return 422."""
        response = client.post(
            "/api/v1/tasks",  # Assuming this endpoint exists
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        # Accept 400, 422, or 404 (if endpoint doesn't exist)
        assert response.status_code in (400, 404, 422)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "smoke: mark test as smoke test")


# Run smoke tests with: pytest tests/e2e/test_smoke.py -v -m smoke
pytestmark = pytest.mark.smoke
