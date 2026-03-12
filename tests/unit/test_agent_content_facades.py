"""
Tests for Agent Content Facades.

Tests Phase 3: Agent-specific content interfaces.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys

# Add source paths
sys.path.insert(0, "F:\\Projects\\ag3ntwerk\\src")
sys.path.insert(0, "F:\\Projects\\ag3ntwerk\\src\\nexus\\src")

from ag3ntwerk.integrations.agent_content_facades import (
    ExecutiveContentFacade,
    CMOContentFacade,
    CTOContentFacade,
    CFOContentFacade,
    CPOContentFacade,
    CROContentFacade,
    CSOContentFacade,
    CDOContentFacade,
    CampaignType,
    CampaignBrief,
    ArchitectureDecisionRecord,
    create_executive_facade,
    create_all_facades,
)


class MockExecutiveContent:
    """Mock ExecutiveContent for testing."""

    def __init__(self, content_id: str, title: str, **kwargs):
        self.content_id = content_id
        self.title = title
        self.topics = kwargs.get("topics", [])
        self.metadata = kwargs.get("metadata", {})
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.quality_score = kwargs.get("quality_score", 0.8)


class MockNexusBridge:
    """Mock NexusBridge for testing facades."""

    def __init__(self):
        self._content: dict = {}
        self._next_id = 1
        self._content_library = MagicMock()

    @property
    def content_library(self):
        return self._content_library

    def store_executive_content(
        self,
        agent: str,
        title: str,
        body: str,
        content_type: str = "concept",
        topics: list = None,
        difficulty: str = "intermediate",
        metadata: dict = None,
    ) -> str:
        content_id = f"content_{self._next_id}"
        self._next_id += 1
        self._content[content_id] = {
            "agent": agent,
            "title": title,
            "body": body,
            "content_type": content_type,
            "topics": topics or [],
            "metadata": metadata or {},
        }
        return content_id

    def get_content_for_executive(
        self,
        agent: str,
        topic: str = None,
        content_type: str = None,
        limit: int = 20,
    ) -> list:
        results = []
        for cid, content in self._content.items():
            if content["agent"] == agent:
                if topic and topic.lower() not in [t.lower() for t in content["topics"]]:
                    continue
                if content_type and content["content_type"] != content_type:
                    continue
                results.append(
                    MockExecutiveContent(
                        content_id=cid,
                        title=content["title"],
                        topics=content["topics"],
                        metadata=content["metadata"],
                    )
                )
        return results[:limit]

    def get_content_analytics(self, agent: str = None) -> dict:
        return {
            "agent": agent,
            "content_count": len(
                [c for c in self._content.values() if c["agent"] == agent]
            ),
        }

    def share_content_between_executives(
        self,
        content_id: str,
        source_executive: str,
        target_agents: list,
        share_type: str = "reference",
    ) -> dict:
        return {agent_code: True for agent_code in target_agents}


@pytest.fixture
def mock_bridge():
    """Create a mock NexusBridge."""
    return MockNexusBridge()


# =============================================================================
# Echo Facade Tests
# =============================================================================


class TestCMOContentFacade:
    """Tests for Echo marketing content facade."""

    def test_initialization(self, mock_bridge):
        """Test Echo facade initializes correctly."""
        facade = CMOContentFacade(mock_bridge)
        assert facade.agent_code == "Echo"
        assert facade.domain == "marketing"

    def test_get_domain_templates(self, mock_bridge):
        """Test Echo templates are available."""
        facade = CMOContentFacade(mock_bridge)
        templates = facade.get_domain_templates()

        assert len(templates) >= 4
        template_names = [t["name"] for t in templates]
        assert "Campaign Brief" in template_names
        assert "Brand Guidelines" in template_names
        assert "Social Media Post" in template_names

    def test_create_campaign_brief(self, mock_bridge):
        """Test creating a campaign brief."""
        facade = CMOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "campaign_brief",
            name="Q1 Product Launch",
            campaign_type="product_launch",
            objectives=["Increase awareness", "Drive trials"],
            target_audience="Tech professionals 25-45",
            key_messages=["Innovative solution", "Save time"],
            channels=["LinkedIn", "Twitter", "Email"],
        )

        assert content_id is not None
        assert content_id.startswith("content_")

        # Verify campaign was stored
        campaigns = facade.list_campaigns()
        assert len(campaigns) == 1
        assert campaigns[0].name == "Q1 Product Launch"
        assert campaigns[0].campaign_type == CampaignType.PRODUCT_LAUNCH

    def test_create_brand_guideline(self, mock_bridge):
        """Test creating brand guidelines."""
        facade = CMOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "brand_guideline",
            topic="Voice and Tone",
            voice_description="Professional yet approachable",
            tone_examples=["We're here to help", "Let's solve this together"],
            dos=["Use active voice", "Be concise"],
            donts=["Use jargon", "Be condescending"],
        )

        assert content_id is not None

    def test_create_social_post(self, mock_bridge):
        """Test creating social media post template."""
        facade = CMOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "social_post",
            platform="LinkedIn",
            topic="Product Update",
            copy="Excited to announce our latest feature...",
            hashtags=["ProductUpdate", "Innovation"],
            cta="Learn more at our blog",
        )

        assert content_id is not None

    def test_create_blog_outline(self, mock_bridge):
        """Test creating blog post outline."""
        facade = CMOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "blog_outline",
            title="10 Ways to Improve Productivity",
            target_keyword="productivity tips",
            sections=["Understanding Productivity", "Time Management", "Tools"],
            target_length=2000,
        )

        assert content_id is not None


# =============================================================================
# Forge Facade Tests
# =============================================================================


class TestCTOContentFacade:
    """Tests for Forge technical documentation facade."""

    def test_initialization(self, mock_bridge):
        """Test Forge facade initializes correctly."""
        facade = CTOContentFacade(mock_bridge)
        assert facade.agent_code == "Forge"
        assert facade.domain == "technical"

    def test_get_domain_templates(self, mock_bridge):
        """Test Forge templates are available."""
        facade = CTOContentFacade(mock_bridge)
        templates = facade.get_domain_templates()

        template_names = [t["name"] for t in templates]
        assert "API Endpoint" in template_names
        assert "Architecture Decision Record" in template_names
        assert "Runbook" in template_names

    def test_create_api_endpoint(self, mock_bridge):
        """Test creating API endpoint documentation."""
        facade = CTOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "api_endpoint",
            method="POST",
            path="/api/v1/users",
            description="Create a new user account",
            parameters=[
                {"name": "email", "type": "string", "required": "Yes", "description": "User email"},
                {"name": "name", "type": "string", "required": "Yes", "description": "User name"},
            ],
            request_body='{"email": "user@example.com", "name": "John Doe"}',
            response_example='{"id": "123", "email": "user@example.com"}',
            error_codes=[
                {"code": "400", "description": "Invalid request"},
                {"code": "409", "description": "Email already exists"},
            ],
        )

        assert content_id is not None

    def test_create_adr(self, mock_bridge):
        """Test creating Architecture Decision Record."""
        facade = CTOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "adr",
            title="Use PostgreSQL for Primary Database",
            context="We need a reliable, scalable database",
            decision="We will use PostgreSQL 15 as our primary database",
            consequences=["Need DBA expertise", "Strong ACID compliance"],
            alternatives=["MySQL", "MongoDB"],
            status="accepted",
        )

        assert content_id is not None

        # Verify ADR was stored
        adrs = facade.list_adrs()
        assert len(adrs) == 1
        assert adrs[0].title == "Use PostgreSQL for Primary Database"
        assert adrs[0].status == "accepted"

    def test_create_runbook(self, mock_bridge):
        """Test creating a runbook."""
        facade = CTOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "runbook",
            title="Database Failover",
            overview="Steps to failover to standby database",
            prerequisites=["VPN access", "DBA credentials", "Slack channel access"],
            steps=[
                {
                    "title": "Verify Primary Status",
                    "description": "Check primary is down",
                    "command": "pg_isready -h primary",
                },
                {
                    "title": "Promote Standby",
                    "description": "Promote standby to primary",
                    "verification": "Check logs",
                },
            ],
            rollback_steps=["Restore from backup", "DNS rollback"],
            contacts=[{"role": "DBA", "name": "John", "contact": "john@company.com"}],
        )

        assert content_id is not None

    def test_create_incident_report(self, mock_bridge):
        """Test creating incident report."""
        facade = CTOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "incident_report",
            title="API Outage 2024-01-15",
            summary="API was unavailable for 30 minutes",
            timeline=[
                {"time": "10:00", "event": "Alerts triggered"},
                {"time": "10:15", "event": "Root cause identified"},
                {"time": "10:30", "event": "Service restored"},
            ],
            impact="100 customers affected",
            root_cause="Database connection pool exhausted",
            action_items=[
                {
                    "action": "Increase pool size",
                    "owner": "DevOps",
                    "due": "2024-01-20",
                    "status": "Open",
                },
            ],
            severity="high",
        )

        assert content_id is not None

    def test_adr_numbering(self, mock_bridge):
        """Test ADRs are numbered sequentially."""
        facade = CTOContentFacade(mock_bridge)

        facade.create_standard_content(
            "adr", title="First", context="", decision="", consequences=[]
        )
        facade.create_standard_content(
            "adr", title="Second", context="", decision="", consequences=[]
        )

        adrs = facade.list_adrs()
        assert adrs[0].adr_id == "ADR-0001"
        assert adrs[1].adr_id == "ADR-0002"


# =============================================================================
# Keystone Facade Tests
# =============================================================================


class TestCFOContentFacade:
    """Tests for Keystone financial content facade."""

    def test_initialization(self, mock_bridge):
        """Test Keystone facade initializes correctly."""
        facade = CFOContentFacade(mock_bridge)
        assert facade.agent_code == "Keystone"
        assert facade.domain == "financial"

    def test_create_budget_proposal(self, mock_bridge):
        """Test creating budget proposal."""
        facade = CFOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "budget_proposal",
            title="Engineering Q1 Budget",
            department="Engineering",
            total_amount=500000,
            categories=[
                {"name": "Salaries", "amount": 350000},
                {"name": "Infrastructure", "amount": 100000},
                {"name": "Tools", "amount": 50000},
            ],
            justification="Support growth initiatives",
            fiscal_year="FY2024",
        )

        assert content_id is not None

    def test_create_financial_report(self, mock_bridge):
        """Test creating financial report."""
        facade = CFOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "financial_report",
            title="Monthly Revenue Report",
            report_type="p_and_l",
            period="January 2024",
            executive_summary="Revenue exceeded targets by 15%",
            key_metrics=[
                {"name": "Revenue", "value": "$1.2M", "change": 15, "target": "$1M"},
                {"name": "Gross Margin", "value": "72%", "change": 2, "target": "70%"},
            ],
            analysis="Strong performance driven by enterprise deals",
            recommendations=["Invest in enterprise sales", "Expand APAC"],
        )

        assert content_id is not None

    def test_create_cost_analysis(self, mock_bridge):
        """Test creating cost analysis."""
        facade = CFOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "cost_analysis",
            title="Cloud Infrastructure Optimization",
            scope="AWS infrastructure costs",
            current_costs=[
                {"item": "EC2 Instances", "monthly": 15000},
                {"item": "RDS", "monthly": 5000},
            ],
            proposed_changes=["Right-size instances", "Use reserved capacity"],
            projected_savings=60000,
            risks=["Potential performance impact"],
        )

        assert content_id is not None


# =============================================================================
# Blueprint Facade Tests
# =============================================================================


class TestCPOContentFacade:
    """Tests for Blueprint product content facade."""

    def test_initialization(self, mock_bridge):
        """Test Blueprint facade initializes correctly."""
        facade = CPOContentFacade(mock_bridge)
        assert facade.agent_code == "Blueprint"
        assert facade.domain == "product"

    def test_create_prd(self, mock_bridge):
        """Test creating Product Requirements Document."""
        facade = CPOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "prd",
            title="User Authentication Redesign",
            problem_statement="Users struggle with password management",
            goals=["Reduce login friction", "Improve security"],
            requirements=[
                {"description": "Support SSO", "priority": "High"},
                {"description": "Add 2FA", "priority": "High"},
            ],
            success_metrics=["50% reduction in password resets", "90% adoption of 2FA"],
            timeline="Q2 2024",
        )

        assert content_id is not None

    def test_create_feature_spec(self, mock_bridge):
        """Test creating feature specification."""
        facade = CPOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "feature_spec",
            title="Dark Mode",
            overview="Add dark mode theme support",
            user_stories=[
                {"role": "user", "want": "toggle dark mode", "benefit": "reduce eye strain"},
            ],
            acceptance_criteria=[
                "Toggle persists across sessions",
                "All screens support dark mode",
            ],
            design_notes="Follow Material Design guidelines",
            dependencies=["Theme system refactor"],
        )

        assert content_id is not None

    def test_create_release_notes(self, mock_bridge):
        """Test creating release notes."""
        facade = CPOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "release_notes",
            version="2.5.0",
            release_date="2024-01-20",
            features=["Dark mode support", "SSO integration"],
            improvements=["Faster page load times", "Better error messages"],
            fixes=["Fixed login timeout issue", "Corrected date formatting"],
            known_issues=["Dark mode not yet supported in reports"],
        )

        assert content_id is not None


# =============================================================================
# Axiom Facade Tests
# =============================================================================


class TestCROContentFacade:
    """Tests for Axiom sales content facade."""

    def test_initialization(self, mock_bridge):
        """Test Axiom facade initializes correctly."""
        facade = CROContentFacade(mock_bridge)
        assert facade.agent_code == "Axiom"
        assert facade.domain == "revenue"

    def test_create_sales_playbook(self, mock_bridge):
        """Test creating sales playbook."""
        facade = CROContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "sales_playbook",
            title="Enterprise Sales",
            target_segment="Fortune 500",
            qualification_criteria=["Budget > $100K", "Decision maker engaged"],
            common_objections=[
                {"objection": "Too expensive", "response": "Consider TCO and ROI"},
            ],
            value_propositions=["50% faster implementation", "Dedicated support"],
        )

        assert content_id is not None

    def test_create_competitive_analysis(self, mock_bridge):
        """Test creating competitive analysis."""
        facade = CROContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "competitive_analysis",
            title="Q1 2024 Landscape",
            competitors=[
                {
                    "name": "Competitor A",
                    "positioning": "Enterprise focus",
                    "strengths": ["Brand", "Features"],
                    "weaknesses": ["Price", "Support"],
                    "pricing": "$$$",
                },
            ],
            our_strengths=["Customer support", "Integration ecosystem"],
            our_weaknesses=["Brand awareness"],
            positioning_statement="The most customer-centric solution",
        )

        assert content_id is not None

    def test_create_battlecard(self, mock_bridge):
        """Test creating competitive battlecard."""
        facade = CROContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "battlecard",
            competitor="Competitor X",
            quick_facts=["Founded 2010", "500 employees", "$50M ARR"],
            win_themes=["Better support", "Faster implementation"],
            landmines=["Don't mention feature X", "Avoid price comparison"],
            knockout_questions=["How do they handle scale?", "What's their SLA?"],
        )

        assert content_id is not None


# =============================================================================
# Compass Facade Tests
# =============================================================================


class TestCSOContentFacade:
    """Tests for Compass security content facade."""

    def test_initialization(self, mock_bridge):
        """Test Compass facade initializes correctly."""
        facade = CSOContentFacade(mock_bridge)
        assert facade.agent_code == "Compass"
        assert facade.domain == "security"

    def test_create_security_policy(self, mock_bridge):
        """Test creating security policy."""
        facade = CSOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "security_policy",
            title="Password Policy",
            purpose="Ensure strong authentication",
            scope="All employees and contractors",
            policy_statements=["Minimum 12 characters", "Must include special characters"],
            responsibilities=[
                {"role": "Employees", "responsibility": "Follow password requirements"},
                {"role": "IT", "responsibility": "Enforce policy technically"},
            ],
            enforcement="Non-compliance may result in account suspension",
        )

        assert content_id is not None

    def test_create_risk_assessment(self, mock_bridge):
        """Test creating risk assessment."""
        facade = CSOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "risk_assessment",
            title="Customer Data Storage",
            asset="Customer database containing PII",
            threats=[
                {"name": "Data breach", "likelihood": "Medium", "impact": "High", "risk": "High"},
                {"name": "Insider threat", "likelihood": "Low", "impact": "High", "risk": "Medium"},
            ],
            vulnerabilities=["Aging encryption", "Limited access logging"],
            controls=[
                {"control": "Encryption at rest", "type": "Technical", "status": "Implemented"},
                {"control": "Access reviews", "type": "Administrative", "status": "Proposed"},
            ],
            overall_risk="High",
        )

        assert content_id is not None

    def test_create_incident_response_plan(self, mock_bridge):
        """Test creating incident response plan."""
        facade = CSOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "incident_response",
            incident_type="Data Breach",
            detection_steps=["Monitor SIEM alerts", "Review access logs"],
            containment_steps=["Isolate affected systems", "Block compromised accounts"],
            eradication_steps=["Remove malware", "Patch vulnerabilities"],
            recovery_steps=["Restore from backup", "Verify integrity"],
            contacts=[
                {"role": "Incident Commander", "name": "Jane Doe", "contact": "555-0100"},
            ],
        )

        assert content_id is not None


# =============================================================================
# Index Facade Tests
# =============================================================================


class TestCDOContentFacade:
    """Tests for Index data content facade."""

    def test_initialization(self, mock_bridge):
        """Test Index facade initializes correctly."""
        facade = CDOContentFacade(mock_bridge)
        assert facade.agent_code == "Index"
        assert facade.domain == "data"

    def test_create_data_dictionary(self, mock_bridge):
        """Test creating data dictionary entry."""
        facade = CDOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "data_dictionary",
            dataset="customers",
            fields=[
                {
                    "name": "id",
                    "type": "UUID",
                    "description": "Primary key",
                    "nullable": "No",
                    "example": "abc-123",
                },
                {
                    "name": "email",
                    "type": "VARCHAR(255)",
                    "description": "Customer email",
                    "nullable": "No",
                    "example": "user@example.com",
                },
            ],
            source_system="CRM",
            update_frequency="Real-time",
            owner="Data Engineering",
        )

        assert content_id is not None

    def test_create_analytics_spec(self, mock_bridge):
        """Test creating analytics specification."""
        facade = CDOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "analytics_spec",
            title="Revenue Dashboard",
            purpose="Track monthly revenue metrics",
            metrics=[
                {"name": "MRR", "calculation": "SUM(subscriptions)", "format": "Currency"},
                {"name": "Churn Rate", "calculation": "Churned/Total", "format": "Percentage"},
            ],
            dimensions=["Time", "Region", "Product"],
            filters=["Date Range", "Customer Segment"],
            data_sources=["Billing System", "CRM"],
        )

        assert content_id is not None

    def test_create_data_quality_report(self, mock_bridge):
        """Test creating data quality report."""
        facade = CDOContentFacade(mock_bridge)

        content_id = facade.create_standard_content(
            "data_quality_report",
            dataset="orders",
            period="January 2024",
            quality_metrics=[
                {"name": "Completeness", "score": 98, "target": 95},
                {"name": "Accuracy", "score": 92, "target": 95},
            ],
            issues=[
                {
                    "issue": "Missing customer IDs",
                    "severity": "High",
                    "records": "150",
                    "status": "Open",
                },
            ],
            actions=["Implement validation rules", "Add data quality alerts"],
        )

        assert content_id is not None


# =============================================================================
# Factory Tests
# =============================================================================


class TestFacadeFactory:
    """Tests for facade factory functions."""

    def test_create_executive_facade_cmo(self, mock_bridge):
        """Test creating Echo facade via factory."""
        facade = create_executive_facade("Echo", mock_bridge)
        assert isinstance(facade, CMOContentFacade)

    def test_create_executive_facade_cto(self, mock_bridge):
        """Test creating Forge facade via factory."""
        facade = create_executive_facade("Forge", mock_bridge)
        assert isinstance(facade, CTOContentFacade)

    def test_create_executive_facade_case_insensitive(self, mock_bridge):
        """Test factory is case insensitive."""
        facade = create_executive_facade("keystone", mock_bridge)
        assert isinstance(facade, CFOContentFacade)

    def test_create_executive_facade_invalid(self, mock_bridge):
        """Test factory returns None for invalid agent."""
        facade = create_executive_facade("INVALID", mock_bridge)
        assert facade is None

    def test_create_all_facades(self, mock_bridge):
        """Test creating all facades at once."""
        facades = create_all_facades(mock_bridge)

        assert len(facades) == 7
        assert "Echo" in facades
        assert "Forge" in facades
        assert "Keystone" in facades
        assert "Blueprint" in facades
        assert "Axiom" in facades
        assert "Compass" in facades
        assert "Index" in facades

        assert isinstance(facades["Echo"], CMOContentFacade)
        assert isinstance(facades["Forge"], CTOContentFacade)


# =============================================================================
# Integration Tests
# =============================================================================


class TestFacadeIntegration:
    """Integration tests across facades."""

    def test_cross_executive_content_request(self, mock_bridge):
        """Test requesting content from another agent."""
        cto_facade = CTOContentFacade(mock_bridge)
        cmo_facade = CMOContentFacade(mock_bridge)

        # Forge creates API documentation
        cto_facade.create_standard_content(
            "api_endpoint",
            method="GET",
            path="/api/products",
            description="List all products",
            parameters=[],
        )

        # Echo requests content from Forge
        # (This would work if we had content matching "api")
        result = cmo_facade.request_content_from(
            source_executive="Forge",
            topic="api",
            share_type="reference",
        )

        # Note: In this mock setup, the share will succeed
        # In real usage, content would need to exist

    def test_facade_analytics(self, mock_bridge):
        """Test getting analytics through facade."""
        facade = CTOContentFacade(mock_bridge)

        # Create some content
        facade.create_standard_content(
            "adr", title="Test", context="", decision="", consequences=[]
        )

        analytics = facade.get_analytics()
        assert "agent" in analytics
        assert analytics["agent"] == "Forge"

    def test_facade_content_retrieval(self, mock_bridge):
        """Test retrieving content through facade."""
        facade = CPOContentFacade(mock_bridge)

        # Create content
        facade.create_standard_content(
            "prd",
            title="Test Feature",
            problem_statement="Problem",
            goals=["Goal 1"],
            requirements=[],
            success_metrics=[],
            timeline="Q1",
        )

        # Retrieve content
        content = facade.get_content(topic="prd")
        assert len(content) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
