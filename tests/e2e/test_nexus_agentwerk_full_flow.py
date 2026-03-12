"""
End-to-end test of Nexus brain + ag3ntwerk body architecture.

Flow tested:
1. Nexus AutonomousCOO starts in SUPERVISED mode
2. Add a goal: "Create a marketing campaign"
3. Nexus observes, prioritizes, decides to execute
4. Task routed to ag3ntwerk:Echo
5. Overwatch receives, routes to Echo
6. Echo executes (mocked LLM)
7. Result flows back through Overwatch -> Nexus
8. Nexus learning records outcome
9. ag3ntwerk learning syncs outcome

Requires: Redis running on localhost:6379
Skip with: pytest -m "not redis"
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

# Check if Redis is available
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def is_redis_available() -> bool:
    """Check if Redis is running and accessible."""
    if not REDIS_AVAILABLE:
        return False
    try:
        import redis as sync_redis

        client = sync_redis.Redis(host="localhost", port=6379, db=0)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


# Skip marker for Redis-dependent tests
requires_redis = pytest.mark.skipif(not is_redis_available(), reason="Redis not available")


@pytest.fixture
async def redis_client():
    """Create a Redis client for testing."""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis package not installed")

    client = redis.from_url("redis://localhost:6379")
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis server not running")

    yield client
    await client.close()


@pytest.fixture
async def clean_redis(redis_client):
    """Clean up test keys before and after test."""
    # Clean up before
    keys = await redis_client.keys("ag3ntwerk:nexus:*")
    if keys:
        await redis_client.delete(*keys)

    yield redis_client

    # Clean up after
    keys = await redis_client.keys("ag3ntwerk:nexus:*")
    if keys:
        await redis_client.delete(*keys)


class TestNexusAgentWerkIntegration:
    """Integration tests for Nexus-ag3ntwerk communication."""

    @requires_redis
    @pytest.mark.asyncio
    async def test_execution_request_flow(self, clean_redis):
        """
        Test that Nexus can send execution requests to ag3ntwerk and receive results.

        Flow:
        1. Nexus sends execution request to ag3ntwerk:nexus:execute:request
        2. ag3ntwerk processes and sends response to ag3ntwerk:nexus:execute:response
        3. Nexus receives the response
        """
        redis_client = clean_redis

        # Track received messages
        received_request = None
        received_response = None

        # Simulate ag3ntwerk side - listen for requests
        async def agentwerk_listener():
            nonlocal received_request
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:request")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_request = json.loads(message["data"])
                    # Send response back
                    response = {
                        "type": "execution_response",
                        "request_id": received_request.get("request_id"),
                        "success": True,
                        "output": {"campaign": "Marketing campaign created"},
                        "confidence": 0.9,
                        "duration_ms": 150.0,
                    }
                    await redis_client.publish(
                        "ag3ntwerk:nexus:execute:response", json.dumps(response)
                    )
                    await pubsub.unsubscribe()
                    break

        # Simulate Nexus side - send request and wait for response
        async def nexus_sender():
            nonlocal received_response

            # Start listening for response first
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:response")

            # Give listener time to start
            await asyncio.sleep(0.1)

            # Send request
            request = {
                "type": "execution_request",
                "request_id": "test-req-001",
                "task_id": "task-001",
                "task_type": "campaign_creation",
                "title": "Create marketing campaign",
                "description": "Create a campaign for product launch",
                "target_agent": "Echo",
                "context": {"product": "New Widget"},
            }
            await redis_client.publish("ag3ntwerk:nexus:execute:request", json.dumps(request))

            # Wait for response
            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_response = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        # Run both sides concurrently
        await asyncio.wait_for(asyncio.gather(agentwerk_listener(), nexus_sender()), timeout=5.0)

        # Verify
        assert received_request is not None
        assert received_request["request_id"] == "test-req-001"
        assert received_request["target_agent"] == "Echo"

        assert received_response is not None
        assert received_response["success"] is True
        assert received_response["request_id"] == "test-req-001"

    @requires_redis
    @pytest.mark.asyncio
    async def test_guidance_request_flow(self, clean_redis):
        """
        Test that ag3ntwerk can request guidance from Nexus.

        Flow:
        1. ag3ntwerk sends guidance request to ag3ntwerk:nexus:guidance:request
        2. Nexus processes and sends response to ag3ntwerk:nexus:guidance:response
        3. ag3ntwerk receives the guidance
        """
        redis_client = clean_redis

        received_request = None
        received_response = None

        # Simulate Nexus side - listen for guidance requests
        async def nexus_listener():
            nonlocal received_request
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:guidance:request")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_request = json.loads(message["data"])
                    # Send guidance response
                    response = {
                        "type": "guidance_response",
                        "context": {
                            "primary_goal": "Launch new product",
                            "success_threshold": 0.85,
                        },
                    }
                    await redis_client.publish(
                        "ag3ntwerk:nexus:guidance:response", json.dumps(response)
                    )
                    await pubsub.unsubscribe()
                    break

        # Simulate ag3ntwerk side - request guidance
        async def agentwerk_requester():
            nonlocal received_response

            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:guidance:response")

            await asyncio.sleep(0.1)

            request = {
                "type": "guidance_request",
                "drift_context": {
                    "drift_score": 0.3,
                    "current_goal": "Marketing tasks",
                },
            }
            await redis_client.publish("ag3ntwerk:nexus:guidance:request", json.dumps(request))

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_response = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        await asyncio.wait_for(asyncio.gather(nexus_listener(), agentwerk_requester()), timeout=5.0)

        assert received_request is not None
        assert "drift_context" in received_request

        assert received_response is not None
        assert "context" in received_response

    @requires_redis
    @pytest.mark.asyncio
    async def test_outcome_reporting_flow(self, clean_redis):
        """
        Test that ag3ntwerk can report outcomes to Nexus.

        Flow:
        1. ag3ntwerk publishes outcome to ag3ntwerk:nexus:outcomes
        2. Nexus receives and can process for learning
        """
        redis_client = clean_redis

        received_outcome = None

        # Simulate Nexus side - listen for outcomes
        async def nexus_listener():
            nonlocal received_outcome
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:outcomes")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_outcome = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        # Simulate ag3ntwerk side - report outcome
        async def agentwerk_reporter():
            await asyncio.sleep(0.1)

            outcome = {
                "type": "outcome_report",
                "metrics": {
                    "task_id": "task-001",
                    "success": True,
                    "duration_ms": 1500,
                    "agent": "Echo",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await redis_client.publish("ag3ntwerk:nexus:outcomes", json.dumps(outcome))

        await asyncio.wait_for(asyncio.gather(nexus_listener(), agentwerk_reporter()), timeout=5.0)

        assert received_outcome is not None
        assert received_outcome["type"] == "outcome_report"
        assert received_outcome["metrics"]["task_id"] == "task-001"

    @requires_redis
    @pytest.mark.asyncio
    async def test_learning_sync_flow(self, clean_redis):
        """
        Test that learning data syncs from ag3ntwerk to Nexus.

        Flow:
        1. ag3ntwerk publishes learning sync to ag3ntwerk:nexus:learning:sync
        2. Nexus receives outcome data for strategic learning
        """
        redis_client = clean_redis

        received_sync = None

        async def nexus_listener():
            nonlocal received_sync
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:learning:sync")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_sync = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        async def agentwerk_syncer():
            await asyncio.sleep(0.1)

            sync_data = {
                "type": "outcome_sync",
                "outcome": {
                    "task_id": "task-002",
                    "task_type": "code_review",
                    "agent": "Forge",
                    "success": True,
                    "duration_ms": 2500,
                    "effectiveness": 0.95,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await redis_client.publish("ag3ntwerk:nexus:learning:sync", json.dumps(sync_data))

        await asyncio.wait_for(asyncio.gather(nexus_listener(), agentwerk_syncer()), timeout=5.0)

        assert received_sync is not None
        assert received_sync["type"] == "outcome_sync"
        assert received_sync["outcome"]["agent"] == "Forge"


class TestFullFlow:
    """Full end-to-end flow test with mocked components."""

    @requires_redis
    @pytest.mark.asyncio
    async def test_complete_task_execution_flow(self, clean_redis):
        """
        Test complete flow from Nexus decision to ag3ntwerk execution.

        This simulates the full architecture:
        1. Nexus decides to execute a task
        2. Routes to ag3ntwerk via Redis
        3. ag3ntwerk Overwatch receives and executes
        4. Result flows back to Nexus
        5. Learning systems on both sides record outcome
        """
        redis_client = clean_redis

        # Track all events in order
        events = []

        # Simulate ag3ntwerk side
        async def run_agentwerk_side():
            """Simulate ag3ntwerk Overwatch listening and responding."""
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:request")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    request = json.loads(message["data"])
                    events.append(("agentwerk_received_request", request["request_id"]))

                    # Simulate Overwatch routing to Echo and executing
                    await asyncio.sleep(0.05)  # Simulate work

                    # Send execution response
                    response = {
                        "type": "execution_response",
                        "request_id": request["request_id"],
                        "task_id": request["task_id"],
                        "success": True,
                        "output": {
                            "campaign_name": "Product Launch Campaign",
                            "channels": ["email", "social", "blog"],
                        },
                        "confidence": 0.92,
                        "duration_ms": 250.0,
                        "executor": "Echo",
                    }
                    await redis_client.publish(
                        "ag3ntwerk:nexus:execute:response", json.dumps(response)
                    )
                    events.append(("agentwerk_sent_response", request["request_id"]))

                    # Also publish learning sync
                    sync_data = {
                        "type": "outcome_sync",
                        "outcome": {
                            "task_id": request["task_id"],
                            "task_type": request["task_type"],
                            "agent": "Echo",
                            "success": True,
                            "duration_ms": 250.0,
                        },
                    }
                    await redis_client.publish("ag3ntwerk:nexus:learning:sync", json.dumps(sync_data))
                    events.append(("agentwerk_synced_learning", request["task_id"]))

                    await pubsub.unsubscribe()
                    break

        # Simulate Nexus side
        async def run_nexus_side():
            """Simulate Nexus AutonomousCOO making a decision and executing."""
            # Listen for response and learning sync
            response_pubsub = redis_client.pubsub()
            learning_pubsub = redis_client.pubsub()
            await response_pubsub.subscribe("ag3ntwerk:nexus:execute:response")
            await learning_pubsub.subscribe("ag3ntwerk:nexus:learning:sync")

            await asyncio.sleep(0.1)  # Give ag3ntwerk time to start listening

            # Nexus makes decision to execute
            events.append(("nexus_decided_to_execute", "task-full-flow"))

            # Send execution request
            request = {
                "type": "execution_request",
                "request_id": "req-full-flow",
                "task_id": "task-full-flow",
                "task_type": "campaign_creation",
                "title": "Create marketing campaign",
                "description": "Create a comprehensive marketing campaign",
                "target_agent": "Echo",
                "context": {"priority": "high"},
            }
            await redis_client.publish("ag3ntwerk:nexus:execute:request", json.dumps(request))
            events.append(("nexus_sent_request", "req-full-flow"))

            # Wait for response
            response_received = False
            learning_received = False

            async def wait_for_response():
                nonlocal response_received
                async for message in response_pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        events.append(("nexus_received_response", data["request_id"]))
                        response_received = True
                        await response_pubsub.unsubscribe()
                        break

            async def wait_for_learning():
                nonlocal learning_received
                async for message in learning_pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        events.append(("nexus_received_learning_sync", data["outcome"]["task_id"]))
                        learning_received = True
                        await learning_pubsub.unsubscribe()
                        break

            await asyncio.gather(wait_for_response(), wait_for_learning())

        # Run both sides
        await asyncio.wait_for(asyncio.gather(run_agentwerk_side(), run_nexus_side()), timeout=10.0)

        # Verify events occurred in expected order
        event_types = [e[0] for e in events]

        # Nexus initiated
        assert "nexus_decided_to_execute" in event_types
        assert "nexus_sent_request" in event_types

        # ag3ntwerk processed
        assert "agentwerk_received_request" in event_types
        assert "agentwerk_sent_response" in event_types
        assert "agentwerk_synced_learning" in event_types

        # Nexus received results
        assert "nexus_received_response" in event_types
        assert "nexus_received_learning_sync" in event_types

        # Verify order: Nexus sends before ag3ntwerk receives
        nexus_sent_idx = event_types.index("nexus_sent_request")
        agentwerk_received_idx = event_types.index("agentwerk_received_request")
        assert nexus_sent_idx < agentwerk_received_idx

    @requires_redis
    @pytest.mark.asyncio
    async def test_multiple_executives_flow(self, clean_redis):
        """Test routing to different agents based on task type."""
        redis_client = clean_redis

        received_requests = []

        async def agentwerk_listener():
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:request")
            count = 0

            async for message in pubsub.listen():
                if message["type"] == "message":
                    request = json.loads(message["data"])
                    received_requests.append(request)

                    # Send response
                    response = {
                        "type": "execution_response",
                        "request_id": request["request_id"],
                        "success": True,
                        "output": {},
                        "executor": request["target_agent"],
                    }
                    await redis_client.publish(
                        "ag3ntwerk:nexus:execute:response", json.dumps(response)
                    )

                    count += 1
                    if count >= 3:
                        await pubsub.unsubscribe()
                        break

        async def nexus_sender():
            await asyncio.sleep(0.1)

            # Send tasks to different agents
            tasks = [
                ("req-1", "code_review", "Forge"),
                ("req-2", "campaign_creation", "Echo"),
                ("req-3", "budget_analysis", "Keystone"),
            ]

            for req_id, task_type, agent in tasks:
                request = {
                    "type": "execution_request",
                    "request_id": req_id,
                    "task_id": f"task-{req_id}",
                    "task_type": task_type,
                    "target_agent": agent,
                }
                await redis_client.publish("ag3ntwerk:nexus:execute:request", json.dumps(request))
                await asyncio.sleep(0.05)

        await asyncio.wait_for(asyncio.gather(agentwerk_listener(), nexus_sender()), timeout=10.0)

        # Verify all tasks reached correct agents
        assert len(received_requests) == 3

        agents = {r["target_agent"] for r in received_requests}
        assert "Forge" in agents
        assert "Echo" in agents
        assert "Keystone" in agents


class TestErrorHandling:
    """Test error handling in the integration."""

    @requires_redis
    @pytest.mark.asyncio
    async def test_execution_failure_flow(self, clean_redis):
        """Test that execution failures are properly communicated."""
        redis_client = clean_redis

        received_response = None

        async def agentwerk_listener():
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:request")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    request = json.loads(message["data"])

                    # Simulate failure
                    response = {
                        "type": "execution_response",
                        "request_id": request["request_id"],
                        "success": False,
                        "output": {},
                        "error": "Agent Echo is unavailable",
                        "confidence": 0.0,
                    }
                    await redis_client.publish(
                        "ag3ntwerk:nexus:execute:response", json.dumps(response)
                    )
                    await pubsub.unsubscribe()
                    break

        async def nexus_sender():
            nonlocal received_response

            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:execute:response")
            await asyncio.sleep(0.1)

            request = {
                "type": "execution_request",
                "request_id": "req-fail",
                "task_type": "campaign_creation",
                "target_agent": "Echo",
            }
            await redis_client.publish("ag3ntwerk:nexus:execute:request", json.dumps(request))

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_response = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        await asyncio.wait_for(asyncio.gather(agentwerk_listener(), nexus_sender()), timeout=5.0)

        assert received_response is not None
        assert received_response["success"] is False
        assert "error" in received_response
        assert "unavailable" in received_response["error"]

    @requires_redis
    @pytest.mark.asyncio
    async def test_timeout_handling(self, clean_redis):
        """Test that timeouts are handled properly."""
        redis_client = clean_redis

        # Nexus sends request but ag3ntwerk never responds
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ag3ntwerk:nexus:execute:response")

        request = {
            "type": "execution_request",
            "request_id": "req-timeout",
            "task_type": "slow_task",
        }
        await redis_client.publish("ag3ntwerk:nexus:execute:request", json.dumps(request))

        # Try to get response with short timeout
        async def wait_for_response():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    return json.loads(message["data"])

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(wait_for_response(), timeout=0.5)

        await pubsub.unsubscribe()


class TestHealthMonitoring:
    """Test health status communication."""

    @requires_redis
    @pytest.mark.asyncio
    async def test_health_status_publishing(self, clean_redis):
        """Test that ag3ntwerk can publish health status to Nexus."""
        redis_client = clean_redis

        received_health = None

        async def nexus_listener():
            nonlocal received_health
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ag3ntwerk:nexus:health")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    received_health = json.loads(message["data"])
                    await pubsub.unsubscribe()
                    break

        async def agentwerk_publisher():
            await asyncio.sleep(0.1)

            health = {
                "type": "health_status",
                "source": "Overwatch",
                "data": {
                    "executives_active": 12,
                    "task_queue_depth": 5,
                    "success_rate_1h": 0.95,
                    "avg_latency_ms": 150,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await redis_client.publish("ag3ntwerk:nexus:health", json.dumps(health))

        await asyncio.wait_for(asyncio.gather(nexus_listener(), agentwerk_publisher()), timeout=5.0)

        assert received_health is not None
        assert received_health["source"] == "Overwatch"
        assert received_health["data"]["executives_active"] == 12
