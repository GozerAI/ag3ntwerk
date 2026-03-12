"""
Tests for NexusBridge Nexus Content Orchestration features.

Tests Phase 2 integration: Nexus coordination of content across agents.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys

# Add source paths
sys.path.insert(0, "F:\\Projects\\ag3ntwerk\\src")
sys.path.insert(0, "F:\\Projects\\ag3ntwerk\\src\\nexus\\src")

from ag3ntwerk.integrations.nexus_bridge import (
    NexusBridge,
    ExecutiveContentDomain,
    ExecutiveContent,
    ContentRequest,
)


class MockContentItem:
    """Mock ContentItem for testing."""

    def __init__(
        self,
        content_id: str,
        title: str,
        content_body: str = "Test content body",
        content_type: MagicMock = None,
        topics: list = None,
        tags: list = None,
        quality_score: float = 0.8,
        created_at: datetime = None,
        metadata: dict = None,
    ):
        self.content_id = content_id
        self.title = title
        self.content_body = content_body
        self.content_type = content_type or MagicMock(value="concept")
        self.topics = topics or ["test-topic"]
        self.tags = tags or []
        self.quality_metrics = MagicMock(quality_score=quality_score)
        self.created_at = created_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}


class MockContentLibrary:
    """Mock ContentLibrary for testing NexusBridge."""

    def __init__(self):
        self._content: dict = {}
        self._next_id = 1

    def create_content(self, content):
        content.content_id = f"content_{self._next_id}"
        self._next_id += 1
        self._content[content.content_id] = content
        return content

    def get_content(self, content_id: str):
        return self._content.get(content_id)

    def update_content(self, content_id: str, updates: dict):
        content = self._content.get(content_id)
        if content:
            for key, value in updates.items():
                setattr(content, key, value)
            return content
        return None

    def search_content(self, query: str, filters=None):
        results = []
        for content in self._content.values():
            if query.lower() in content.title.lower() or any(
                query.lower() in t.lower() for t in content.topics
            ):
                results.append(content)
        return results

    def list_content(self, filters=None, limit: int = 20):
        return list(self._content.values())[:limit]

    def get_learning_path(self, content_id: str):
        return [content_id]

    def get_library_statistics(self):
        return {
            "total_content": len(self._content),
            "total_views": 0,
        }

    def record_content_interaction(self, **kwargs):
        return True


@pytest.fixture
def mock_content_library():
    """Create a mock content library with some test content."""
    library = MockContentLibrary()

    # Add test content for different agents
    test_items = [
        MockContentItem(
            content_id="cmo_1",
            title="Marketing Strategy Guide",
            topics=["marketing", "strategy"],
            tags=["domain:marketing", "agent:cmo"],
            quality_score=0.85,
            metadata={"agent": "Echo", "domain": "marketing"},
        ),
        MockContentItem(
            content_id="cto_1",
            title="API Design Best Practices",
            topics=["api", "architecture"],
            tags=["domain:technical", "agent:cto"],
            quality_score=0.9,
            metadata={"agent": "Forge", "domain": "technical"},
        ),
        MockContentItem(
            content_id="cto_2",
            title="Code Review Guidelines",
            topics=["code", "review"],
            tags=["domain:technical", "agent:cto"],
            quality_score=0.4,  # Low quality for testing
            metadata={"agent": "Forge", "domain": "technical"},
        ),
        MockContentItem(
            content_id="cfo_1",
            title="Budget Planning Process",
            topics=["budget", "financial"],
            tags=["domain:financial", "agent:cfo"],
            quality_score=0.75,
            metadata={"agent": "Keystone", "domain": "financial"},
        ),
    ]

    for item in test_items:
        library._content[item.content_id] = item

    return library


@pytest.fixture
def nexus_bridge(mock_content_library):
    """Create NexusBridge with mock content library."""
    bridge = NexusBridge(content_library=mock_content_library)
    return bridge


class TestExecutiveContentDomain:
    """Tests for ExecutiveContentDomain enum."""

    def test_domain_values(self):
        """Test that all agent domains have correct values."""
        assert ExecutiveContentDomain.Echo.value == "marketing"
        assert ExecutiveContentDomain.Forge.value == "technical"
        assert ExecutiveContentDomain.Keystone.value == "financial"
        assert ExecutiveContentDomain.Blueprint.value == "product"
        assert ExecutiveContentDomain.Nexus.value == "operational"
        assert ExecutiveContentDomain.Axiom.value == "revenue"
        assert ExecutiveContentDomain.Compass.value == "security"
        assert ExecutiveContentDomain.Index.value == "data"
        assert ExecutiveContentDomain.GENERAL.value == "general"

    def test_get_agent_domain(self, nexus_bridge):
        """Test mapping agents to domains."""
        assert nexus_bridge.get_agent_domain("Echo") == ExecutiveContentDomain.Echo
        assert nexus_bridge.get_agent_domain("Forge") == ExecutiveContentDomain.Forge
        assert (
            nexus_bridge.get_agent_domain("keystone") == ExecutiveContentDomain.Keystone
        )  # Case insensitive
        assert nexus_bridge.get_agent_domain("UNKNOWN") == ExecutiveContentDomain.GENERAL


class TestCOOWorkflowOrchestration:
    """Tests for Nexus content workflow orchestration."""

    def test_orchestrate_create_workflow(self, nexus_bridge):
        """Test creating a content creation workflow."""
        result = nexus_bridge.orchestrate_content_workflow(
            workflow_type="create",
            topic="New Product Launch",
            agents=["Echo", "Forge", "Blueprint"],
            metadata={"campaign": "Q1-2024"},
        )

        assert result["workflow_type"] == "create"
        assert result["topic"] == "New Product Launch"
        assert result["status"] == "initiated"
        assert "workflow_id" in result
        assert "assignments" in result
        assert len(result["assignments"]) == 3
        assert "Echo" in result["assignments"]
        assert "Forge" in result["assignments"]
        assert "Blueprint" in result["assignments"]

    def test_orchestrate_review_workflow(self, nexus_bridge):
        """Test creating a review workflow with cross-agent assignments."""
        result = nexus_bridge.orchestrate_content_workflow(
            workflow_type="review",
            topic="API Documentation",
            agents=["Forge", "Blueprint", "Echo"],
        )

        assert result["workflow_type"] == "review"
        assert len(result["assignments"]) == 3
        # Verify cross-review (each reviews the next)
        for exec_code in result["assignments"]:
            assert any("Review content from" in task for task in result["assignments"][exec_code])

    def test_orchestrate_update_workflow(self, nexus_bridge):
        """Test creating an update workflow."""
        result = nexus_bridge.orchestrate_content_workflow(
            workflow_type="update",
            topic="marketing",
            agents=["Echo"],
        )

        assert result["workflow_type"] == "update"
        # Echo should have update tasks for their marketing content
        if "Echo" in result["assignments"]:
            assert any("Update" in task for task in result["assignments"]["Echo"])

    def test_orchestrate_distribute_workflow(self, nexus_bridge):
        """Test creating a content distribution workflow."""
        result = nexus_bridge.orchestrate_content_workflow(
            workflow_type="distribute",
            topic="Brand Guidelines",
            agents=["Echo", "Forge", "Blueprint"],  # Echo is source
        )

        assert result["workflow_type"] == "distribute"
        # First agent is source, others receive
        assert "Forge" in result["assignments"]
        assert "Blueprint" in result["assignments"]
        assert any(
            "review and adapt content from echo" in task.lower()
            for task in result["assignments"].get("Forge", [])
        )


class TestContentAssignment:
    """Tests for content assignment to agents."""

    def test_assign_content_for_review(self, nexus_bridge, mock_content_library):
        """Test assigning content to an agent for review."""
        result = nexus_bridge.assign_content_to_executive(
            content_id="cto_1",
            target_agent="Echo",
            assignment_type="review",
            notes="Please review for marketing alignment",
        )

        assert result is True

        # Verify assignment metadata was added
        content = mock_content_library.get_content("cto_1")
        assert "assignments" in content.metadata
        assert len(content.metadata["assignments"]) > 0
        assignment = content.metadata["assignments"][-1]
        assert assignment["assigned_to"] == "Echo"
        assert assignment["assignment_type"] == "review"
        assert "marketing alignment" in assignment["notes"]

    def test_assign_nonexistent_content(self, nexus_bridge):
        """Test assigning non-existent content fails gracefully."""
        result = nexus_bridge.assign_content_to_executive(
            content_id="nonexistent",
            target_agent="Echo",
            assignment_type="review",
        )

        assert result is False


class TestContentSharing:
    """Tests for sharing content between agents."""

    def test_share_content_reference(self, nexus_bridge, mock_content_library):
        """Test sharing content as a reference."""
        result = nexus_bridge.share_content_between_executives(
            content_id="cto_1",
            source_executive="Forge",
            target_agents=["Echo", "Blueprint"],
            share_type="reference",
        )

        assert result["Echo"] is True
        assert result["Blueprint"] is True

        # Verify tags were added
        content = mock_content_library.get_content("cto_1")
        assert "shared-with:echo" in content.tags
        assert "shared-with:blueprint" in content.tags

    def test_share_content_copy(self, nexus_bridge, mock_content_library):
        """Test sharing content as a copy."""
        # Add ContentBuilder mock
        with patch.object(nexus_bridge, "_get_content_builder") as mock_builder:
            builder_instance = MagicMock()
            builder_instance.with_title.return_value = builder_instance
            builder_instance.with_body.return_value = builder_instance
            builder_instance.with_topics.return_value = builder_instance
            builder_instance.with_difficulty.return_value = builder_instance
            builder_instance.with_tags.return_value = builder_instance
            builder_instance.build.return_value = MockContentItem(
                content_id="new_copy",
                title="API Design Best Practices (from Forge)",
                topics=["api", "architecture"],
            )
            mock_builder.return_value = MagicMock(return_value=builder_instance)

            result = nexus_bridge.share_content_between_executives(
                content_id="cto_1",
                source_executive="Forge",
                target_agents=["Echo"],
                share_type="copy",
            )

            # The copy should create new content
            assert "Echo" in result

    def test_share_nonexistent_content(self, nexus_bridge):
        """Test sharing non-existent content fails gracefully."""
        result = nexus_bridge.share_content_between_executives(
            content_id="nonexistent",
            source_executive="Forge",
            target_agents=["Echo"],
            share_type="reference",
        )

        assert result["Echo"] is False


class TestExecutiveDashboard:
    """Tests for agent content dashboard."""

    def test_get_full_dashboard(self, nexus_bridge):
        """Test getting dashboard for all agents."""
        dashboard = nexus_bridge.get_agent_content_dashboard()

        assert "generated_at" in dashboard
        assert "agents" in dashboard
        assert "summary" in dashboard
        assert dashboard["summary"]["total_content"] >= 0
        assert "content_by_domain" in dashboard["summary"]

    def test_get_single_agent_dashboard(self, nexus_bridge):
        """Test getting dashboard for a single agent."""
        dashboard = nexus_bridge.get_agent_content_dashboard(agent="Forge")

        assert "agents" in dashboard
        # Should only have Forge data
        assert len(dashboard["agents"]) <= 1


class TestContentGapAnalysis:
    """Tests for identifying content gaps."""

    def test_identify_gaps(self, nexus_bridge):
        """Test identifying content gaps for topics."""
        gaps = nexus_bridge.identify_content_gaps(
            topics=["machine-learning", "blockchain", "marketing"]
        )

        assert "topics_analyzed" in gaps
        assert "machine-learning" in gaps["topics_analyzed"]
        assert "gaps_by_executive" in gaps
        assert "recommendations" in gaps

        # machine-learning and blockchain should show as gaps
        # since we only have marketing, api, budget content
        found_ml_gap = False
        for exec_gaps in gaps["gaps_by_executive"].values():
            if "machine-learning" in exec_gaps:
                found_ml_gap = True
                break
        assert found_ml_gap


class TestQualityReport:
    """Tests for content quality reporting."""

    def test_get_quality_report(self, nexus_bridge):
        """Test generating quality report."""
        report = nexus_bridge.get_content_quality_report()

        assert "generated_at" in report
        assert "by_executive" in report
        assert "low_quality_content" in report
        assert "high_quality_content" in report
        assert "recommendations" in report

        # We have one low-quality item (cto_2 with 0.4 score)
        low_quality_ids = [c["content_id"] for c in report["low_quality_content"]]
        assert "cto_2" in low_quality_ids

        # High quality should include cto_1 (0.9) and cmo_1 (0.85)
        high_quality_ids = [c["content_id"] for c in report["high_quality_content"]]
        assert "cto_1" in high_quality_ids or "cmo_1" in high_quality_ids


class TestContentDelegation:
    """Tests for Nexus content creation delegation."""

    def test_delegate_to_specific_executives(self, nexus_bridge):
        """Test delegating content creation to specific agents."""
        result = nexus_bridge.delegate_content_creation(
            topic="New API Documentation",
            target_agents=["Forge", "Blueprint"],
            content_types=["concept", "procedure"],
            priority="high",
        )

        assert result["topic"] == "New API Documentation"
        assert result["priority"] == "high"
        assert result["total_assignments"] == 4  # 2 execs × 2 types

        # Verify delegations
        exec_assignments = {d["agent"] for d in result["delegations"]}
        assert "Forge" in exec_assignments
        assert "Blueprint" in exec_assignments

    def test_delegate_auto_select_executives(self, nexus_bridge):
        """Test automatic agent selection for delegation."""
        result = nexus_bridge.delegate_content_creation(
            topic="Marketing campaign strategy",
            content_types=["concept"],
        )

        # Should auto-select Echo based on "marketing" keyword
        exec_assignments = {d["agent"] for d in result["delegations"]}
        assert "Echo" in exec_assignments

    def test_delegate_technical_topic(self, nexus_bridge):
        """Test delegation routes technical topics to Forge."""
        result = nexus_bridge.delegate_content_creation(
            topic="API architecture design",
            content_types=["procedure"],
        )

        exec_assignments = {d["agent"] for d in result["delegations"]}
        assert "Forge" in exec_assignments

    def test_delegate_tracks_requests(self, nexus_bridge):
        """Test that delegation tracks content requests."""
        initial_requests = len(nexus_bridge._content_requests)

        nexus_bridge.delegate_content_creation(
            topic="Test Topic",
            target_agents=["Echo"],
            content_types=["concept"],
        )

        # Should have added one request
        assert len(nexus_bridge._content_requests) == initial_requests + 1


class TestContentSync:
    """Tests for syncing content across domains."""

    def test_sync_content_across_domains(self, nexus_bridge):
        """Test syncing content from one domain to others."""
        result = nexus_bridge.sync_content_across_domains(
            source_domain="technical",
            target_domains=["marketing", "product"],
            topics=None,  # Sync all
        )

        assert result["source_domain"] == "technical"
        assert result["source_executive"] == "Forge"
        assert result["content_synced"] >= 0
        assert "target_results" in result

    def test_sync_with_topic_filter(self, nexus_bridge):
        """Test syncing only specific topics."""
        result = nexus_bridge.sync_content_across_domains(
            source_domain="technical",
            target_domains=["marketing"],
            topics=["api"],
        )

        assert result["source_domain"] == "technical"
        # Should only sync API-related content

    def test_sync_invalid_domain(self, nexus_bridge):
        """Test syncing from invalid domain fails gracefully."""
        result = nexus_bridge.sync_content_across_domains(
            source_domain="invalid_domain",
            target_domains=["marketing"],
        )

        assert "error" in result


class TestSelectExecutivesForTopic:
    """Tests for automatic agent selection."""

    def test_select_for_marketing_topic(self, nexus_bridge):
        """Test Echo selected for marketing topics."""
        selected = nexus_bridge._select_executives_for_topic("social media marketing campaign")
        assert "Echo" in selected

    def test_select_for_technical_topic(self, nexus_bridge):
        """Test Forge selected for technical topics."""
        selected = nexus_bridge._select_executives_for_topic("API development guidelines")
        assert "Forge" in selected

    def test_select_for_financial_topic(self, nexus_bridge):
        """Test Keystone selected for financial topics."""
        selected = nexus_bridge._select_executives_for_topic("budget allocation process")
        assert "Keystone" in selected

    def test_select_for_security_topic(self, nexus_bridge):
        """Test Compass selected for security topics."""
        selected = nexus_bridge._select_executives_for_topic("security compliance audit")
        assert "Compass" in selected

    def test_select_defaults_to_coo(self, nexus_bridge):
        """Test Nexus is default for unmatched topics."""
        selected = nexus_bridge._select_executives_for_topic("random unrelated topic xyz")
        assert "Nexus" in selected

    def test_select_multiple_executives(self, nexus_bridge):
        """Test multiple agents selected for cross-domain topics."""
        selected = nexus_bridge._select_executives_for_topic(
            "product marketing campaign for new feature"
        )
        # Should match both Echo (marketing, campaign) and Blueprint (product, feature)
        assert "Echo" in selected or "Blueprint" in selected


class TestIntegration:
    """Integration tests for Nexus orchestration features."""

    def test_full_content_workflow(self, nexus_bridge, mock_content_library):
        """Test a complete content workflow from creation to sharing."""
        # 1. Nexus identifies content gaps
        gaps = nexus_bridge.identify_content_gaps(topics=["devops", "deployment"])

        # 2. Nexus delegates content creation
        delegation = nexus_bridge.delegate_content_creation(
            topic="DevOps Best Practices",
            target_agents=["Forge"],
            content_types=["concept", "procedure"],
        )

        assert delegation["total_assignments"] == 2

        # 3. Simulate content creation (Forge creates content)
        # In real scenario, Forge would use create_executive_content

        # 4. Nexus assigns content for review
        assigned = nexus_bridge.assign_content_to_executive(
            content_id="cto_1",
            target_agent="Blueprint",
            assignment_type="review",
            notes="Review from product perspective",
        )

        assert assigned is True

        # 5. Nexus shares approved content
        shared = nexus_bridge.share_content_between_executives(
            content_id="cto_1",
            source_executive="Forge",
            target_agents=["Echo", "Blueprint"],
            share_type="reference",
        )

        assert shared["Echo"] is True
        assert shared["Blueprint"] is True

        # 6. Generate quality report
        report = nexus_bridge.get_content_quality_report()
        assert "by_executive" in report

        # 7. Get dashboard
        dashboard = nexus_bridge.get_agent_content_dashboard()
        assert dashboard["summary"]["total_content"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
