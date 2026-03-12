"""
Agent Content Facades - Specialized content interfaces for each agent.

Each agent has domain-specific content needs and workflows:
- Echo: Marketing campaigns, brand content, social media
- Forge: Technical documentation, API specs, architecture
- Keystone: Financial reports, budgets, compliance docs
- Blueprint: Product specs, roadmaps, user research
- Axiom: Sales enablement, pricing, competitive analysis
- Compass: Security policies, compliance, risk assessments
- Index: Data governance, analytics reports, dashboards

These facades provide specialized methods tailored to each agent's domain.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Base Agent Facade
# =============================================================================


class ExecutiveContentFacade(ABC):
    """
    Base class for agent content facades.

    Provides common functionality and defines the interface
    for agent-specific content operations.
    """

    def __init__(
        self,
        nexus_bridge: Any,
        agent_code: str,
        domain: str,
    ):
        """
        Initialize agent facade.

        Args:
            nexus_bridge: NexusBridge instance for content operations
            agent_code: Agent identifier (e.g., "Echo", "Forge")
            domain: Content domain (e.g., "marketing", "technical")
        """
        self.bridge = nexus_bridge
        self.agent_code = agent_code
        self.domain = domain

        logger.info(f"{agent_code} content facade initialized")

    @property
    def content_library(self) -> Optional[Any]:
        """Get the connected Content Library."""
        return self.bridge.content_library if self.bridge else None

    def store_content(
        self,
        title: str,
        body: str,
        content_type: str = "concept",
        topics: Optional[List[str]] = None,
        difficulty: str = "intermediate",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store content in this agent's domain."""
        return self.bridge.store_executive_content(
            agent=self.agent_code,
            title=title,
            body=body,
            content_type=content_type,
            topics=topics,
            difficulty=difficulty,
            metadata=metadata,
        )

    def get_content(
        self,
        topic: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Any]:
        """Get content for this agent."""
        return self.bridge.get_content_for_executive(
            agent=self.agent_code,
            topic=topic,
            content_type=content_type,
            limit=limit,
        )

    def get_analytics(self) -> Dict[str, Any]:
        """Get content analytics for this agent."""
        return self.bridge.get_content_analytics(agent=self.agent_code)

    def request_content_from(
        self,
        source_executive: str,
        topic: str,
        share_type: str = "reference",
    ) -> bool:
        """Request content from another agent."""
        # Find relevant content from source
        source_content = self.bridge.get_content_for_executive(
            agent=source_executive,
            topic=topic,
            limit=5,
        )

        if not source_content:
            return False

        # Share the most relevant content
        result = self.bridge.share_content_between_executives(
            content_id=source_content[0].content_id,
            source_executive=source_executive,
            target_agents=[self.agent_code],
            share_type=share_type,
        )

        return result.get(self.agent_code, False)

    @abstractmethod
    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get content templates specific to this agent's domain."""
        pass

    @abstractmethod
    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard content for this agent's domain."""
        pass


# =============================================================================
# Echo Content Facade - Marketing
# =============================================================================


class CampaignType(Enum):
    """Types of marketing campaigns."""

    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    PRODUCT_LAUNCH = "product_launch"
    CONTENT_MARKETING = "content_marketing"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    EVENT = "event"
    INFLUENCER = "influencer"


@dataclass
class CampaignBrief:
    """Marketing campaign brief."""

    campaign_id: str
    name: str
    campaign_type: CampaignType
    objectives: List[str]
    target_audience: str
    key_messages: List[str]
    channels: List[str]
    budget_notes: str = ""
    timeline: str = ""
    success_metrics: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CMOContentFacade(ExecutiveContentFacade):
    """
    Echo Content Facade - Marketing content management.

    Specialized for:
    - Campaign briefs and plans
    - Brand guidelines
    - Social media content
    - Content marketing materials
    - Marketing analytics
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Echo", "marketing")
        self._campaigns: Dict[str, CampaignBrief] = {}

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get marketing content templates."""
        return [
            {
                "name": "Campaign Brief",
                "content_type": "procedure",
                "structure": ["objectives", "audience", "messages", "channels", "metrics"],
            },
            {
                "name": "Brand Guidelines",
                "content_type": "concept",
                "structure": ["voice", "tone", "visual_identity", "usage_rules"],
            },
            {
                "name": "Social Media Post",
                "content_type": "concept",
                "structure": ["platform", "copy", "hashtags", "cta", "visual_notes"],
            },
            {
                "name": "Email Campaign",
                "content_type": "procedure",
                "structure": ["subject", "preview", "body", "cta", "segments"],
            },
            {
                "name": "Content Calendar",
                "content_type": "procedure",
                "structure": ["dates", "topics", "channels", "owners", "status"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard marketing content."""
        creators = {
            "campaign_brief": self._create_campaign_brief,
            "brand_guideline": self._create_brand_guideline,
            "social_post": self._create_social_post,
            "blog_outline": self._create_blog_outline,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_campaign_brief(
        self,
        name: str,
        campaign_type: str,
        objectives: List[str],
        target_audience: str,
        key_messages: List[str],
        channels: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a campaign brief."""
        brief = CampaignBrief(
            campaign_id=str(uuid4()),
            name=name,
            campaign_type=CampaignType(campaign_type),
            objectives=objectives,
            target_audience=target_audience,
            key_messages=key_messages,
            channels=channels,
            **{k: v for k, v in kwargs.items() if k in CampaignBrief.__dataclass_fields__},
        )

        self._campaigns[brief.campaign_id] = brief

        body = f"""# Campaign Brief: {name}

## Campaign Type
{campaign_type.replace('_', ' ').title()}

## Objectives
{chr(10).join(f'- {obj}' for obj in objectives)}

## Target Audience
{target_audience}

## Key Messages
{chr(10).join(f'- {msg}' for msg in key_messages)}

## Channels
{chr(10).join(f'- {ch}' for ch in channels)}

## Success Metrics
{chr(10).join(f'- {m}' for m in brief.success_metrics) if brief.success_metrics else 'TBD'}
"""

        return self.store_content(
            title=f"Campaign Brief: {name}",
            body=body,
            content_type="procedure",
            topics=["campaign", campaign_type, "marketing"],
            metadata={
                "campaign_id": brief.campaign_id,
                "campaign_type": campaign_type,
                "target_audience": target_audience,
            },
        )

    def _create_brand_guideline(
        self,
        topic: str,
        voice_description: str,
        tone_examples: List[str],
        dos: List[str],
        donts: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a brand guideline document."""
        body = f"""# Brand Guidelines: {topic}

## Brand Voice
{voice_description}

## Tone Examples
{chr(10).join(f'- {ex}' for ex in tone_examples)}

## Do's
{chr(10).join(f'✓ {d}' for d in dos)}

## Don'ts
{chr(10).join(f'✗ {d}' for d in donts)}
"""

        return self.store_content(
            title=f"Brand Guidelines: {topic}",
            body=body,
            content_type="concept",
            topics=["brand", "guidelines", topic.lower()],
            metadata={"guideline_type": topic},
        )

    def _create_social_post(
        self, platform: str, topic: str, copy: str, hashtags: List[str], cta: str = "", **kwargs
    ) -> Optional[str]:
        """Create a social media post template."""
        body = f"""# Social Media Post: {platform}

## Topic
{topic}

## Copy
{copy}

## Hashtags
{' '.join(f'#{h}' for h in hashtags)}

## Call to Action
{cta if cta else 'N/A'}

## Platform Notes
Platform: {platform}
Character Limit: {'280' if platform.lower() == 'twitter' else 'Varies'}
"""

        return self.store_content(
            title=f"Social Post: {topic} ({platform})",
            body=body,
            content_type="concept",
            topics=["social", platform.lower(), topic.lower()],
            metadata={"platform": platform},
        )

    def _create_blog_outline(
        self,
        title: str,
        target_keyword: str,
        sections: List[str],
        target_length: int = 1500,
        **kwargs,
    ) -> Optional[str]:
        """Create a blog post outline."""
        body = f"""# Blog Outline: {title}

## Target Keyword
{target_keyword}

## Target Length
{target_length} words

## Outline

### Introduction
- Hook
- Problem statement
- What readers will learn

{chr(10).join(f'### {section}' + chr(10) + '- Key points' + chr(10) + '- Supporting evidence' for section in sections)}

### Conclusion
- Summary
- Call to action
- Next steps

## SEO Notes
- Primary keyword: {target_keyword}
- Include in H1, first paragraph, and conclusion
"""

        return self.store_content(
            title=f"Blog Outline: {title}",
            body=body,
            content_type="procedure",
            topics=["blog", "content", target_keyword.lower()],
            metadata={"target_keyword": target_keyword, "target_length": target_length},
        )

    def get_campaign(self, campaign_id: str) -> Optional[CampaignBrief]:
        """Get a campaign brief by ID."""
        return self._campaigns.get(campaign_id)

    def list_campaigns(self) -> List[CampaignBrief]:
        """List all campaign briefs."""
        return list(self._campaigns.values())

    def get_content_calendar(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get content scheduled in a date range."""
        content = self.get_content(content_type="procedure", limit=50)

        calendar = []
        for item in content:
            if "calendar" in item.title.lower() or "schedule" in item.metadata.get(
                "content_subtype", ""
            ):
                calendar.append(
                    {
                        "content_id": item.content_id,
                        "title": item.title,
                        "created_at": item.created_at,
                        "topics": item.topics,
                    }
                )

        return calendar


# =============================================================================
# Forge Content Facade - Technical
# =============================================================================


class DocumentationType(Enum):
    """Types of technical documentation."""

    API_REFERENCE = "api_reference"
    ARCHITECTURE = "architecture"
    RUNBOOK = "runbook"
    ADR = "adr"  # Architecture Decision Record
    TECHNICAL_SPEC = "technical_spec"
    CODE_REVIEW = "code_review"
    INCIDENT_REPORT = "incident_report"
    ONBOARDING = "onboarding"


@dataclass
class ArchitectureDecisionRecord:
    """Architecture Decision Record (ADR)."""

    adr_id: str
    title: str
    status: str  # proposed, accepted, deprecated, superseded
    context: str
    decision: str
    consequences: List[str]
    alternatives_considered: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CTOContentFacade(ExecutiveContentFacade):
    """
    Forge Content Facade - Technical documentation management.

    Specialized for:
    - API documentation
    - Architecture Decision Records (ADRs)
    - Technical specifications
    - Runbooks and playbooks
    - Code review guidelines
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Forge", "technical")
        self._adrs: Dict[str, ArchitectureDecisionRecord] = {}
        self._next_adr_number = 1

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get technical documentation templates."""
        return [
            {
                "name": "API Endpoint",
                "content_type": "procedure",
                "structure": ["method", "path", "params", "request", "response", "errors"],
            },
            {
                "name": "Architecture Decision Record",
                "content_type": "concept",
                "structure": ["context", "decision", "consequences", "alternatives"],
            },
            {
                "name": "Technical Specification",
                "content_type": "concept",
                "structure": ["overview", "requirements", "design", "interfaces", "testing"],
            },
            {
                "name": "Runbook",
                "content_type": "procedure",
                "structure": ["overview", "prerequisites", "steps", "rollback", "contacts"],
            },
            {
                "name": "Incident Report",
                "content_type": "concept",
                "structure": ["summary", "timeline", "impact", "root_cause", "action_items"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard technical content."""
        creators = {
            "api_endpoint": self._create_api_endpoint,
            "adr": self._create_adr,
            "runbook": self._create_runbook,
            "tech_spec": self._create_tech_spec,
            "incident_report": self._create_incident_report,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_api_endpoint(
        self,
        method: str,
        path: str,
        description: str,
        parameters: List[Dict[str, str]],
        request_body: Optional[str] = None,
        response_example: Optional[str] = None,
        error_codes: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> Optional[str]:
        """Create API endpoint documentation."""
        params_section = ""
        if parameters:
            params_section = "## Parameters\n\n| Name | Type | Required | Description |\n|------|------|----------|-------------|\n"
            for p in parameters:
                params_section += f"| {p.get('name', '')} | {p.get('type', '')} | {p.get('required', 'No')} | {p.get('description', '')} |\n"

        errors_section = ""
        if error_codes:
            errors_section = "## Error Codes\n\n| Code | Description |\n|------|-------------|\n"
            for e in error_codes:
                errors_section += f"| {e.get('code', '')} | {e.get('description', '')} |\n"

        body = f"""# {method.upper()} {path}

## Description
{description}

{params_section}

## Request
```json
{request_body if request_body else '{}'}
```

## Response
```json
{response_example if response_example else '{}'}
```

{errors_section}
"""

        return self.store_content(
            title=f"API: {method.upper()} {path}",
            body=body,
            content_type="procedure",
            topics=["api", method.lower(), path.split("/")[1] if "/" in path else "endpoint"],
            metadata={"method": method, "path": path, "doc_type": "api_reference"},
        )

    def _create_adr(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: List[str],
        alternatives: Optional[List[str]] = None,
        status: str = "proposed",
        **kwargs,
    ) -> Optional[str]:
        """Create an Architecture Decision Record."""
        adr_number = self._next_adr_number
        self._next_adr_number += 1

        adr = ArchitectureDecisionRecord(
            adr_id=f"ADR-{adr_number:04d}",
            title=title,
            status=status,
            context=context,
            decision=decision,
            consequences=consequences,
            alternatives_considered=alternatives or [],
        )

        self._adrs[adr.adr_id] = adr

        body = f"""# {adr.adr_id}: {title}

## Status
{status.upper()}

## Context
{context}

## Decision
{decision}

## Consequences
{chr(10).join(f'- {c}' for c in consequences)}

## Alternatives Considered
{chr(10).join(f'- {a}' for a in (alternatives or ['None documented'])) }

---
Date: {adr.created_at.strftime('%Y-%m-%d')}
"""

        return self.store_content(
            title=f"{adr.adr_id}: {title}",
            body=body,
            content_type="concept",
            topics=["adr", "architecture", "decision"],
            metadata={"adr_id": adr.adr_id, "status": status, "doc_type": "adr"},
        )

    def _create_runbook(
        self,
        title: str,
        overview: str,
        prerequisites: List[str],
        steps: List[Dict[str, str]],
        rollback_steps: Optional[List[str]] = None,
        contacts: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> Optional[str]:
        """Create a runbook/playbook."""
        prereq_section = "\n".join(f"- [ ] {p}" for p in prerequisites)

        steps_section = ""
        for i, step in enumerate(steps, 1):
            steps_section += f"\n### Step {i}: {step.get('title', 'Untitled')}\n\n"
            steps_section += f"{step.get('description', '')}\n\n"
            if step.get("command"):
                steps_section += f"```bash\n{step['command']}\n```\n\n"
            if step.get("verification"):
                steps_section += f"**Verification:** {step['verification']}\n\n"

        rollback_section = ""
        if rollback_steps:
            rollback_section = "## Rollback Procedure\n\n" + "\n".join(
                f"{i}. {s}" for i, s in enumerate(rollback_steps, 1)
            )

        contacts_section = ""
        if contacts:
            contacts_section = (
                "## Contacts\n\n| Role | Name | Contact |\n|------|------|--------|\n"
            )
            for c in contacts:
                contacts_section += (
                    f"| {c.get('role', '')} | {c.get('name', '')} | {c.get('contact', '')} |\n"
                )

        body = f"""# Runbook: {title}

## Overview
{overview}

## Prerequisites
{prereq_section}

## Procedure
{steps_section}

{rollback_section}

{contacts_section}
"""

        return self.store_content(
            title=f"Runbook: {title}",
            body=body,
            content_type="procedure",
            topics=["runbook", "operations", title.lower().split()[0]],
            metadata={"doc_type": "runbook"},
        )

    def _create_tech_spec(
        self,
        title: str,
        overview: str,
        requirements: List[str],
        design: str,
        interfaces: Optional[List[Dict[str, str]]] = None,
        testing_strategy: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """Create a technical specification."""
        req_section = "\n".join(f"- {r}" for r in requirements)

        interface_section = ""
        if interfaces:
            interface_section = "## Interfaces\n\n"
            for iface in interfaces:
                interface_section += f"### {iface.get('name', 'Interface')}\n"
                interface_section += f"{iface.get('description', '')}\n\n"

        body = f"""# Technical Specification: {title}

## Overview
{overview}

## Requirements
{req_section}

## Design
{design}

{interface_section}

## Testing Strategy
{testing_strategy if testing_strategy else 'TBD'}

## Open Questions
- [ ]

## References
-
"""

        return self.store_content(
            title=f"Tech Spec: {title}",
            body=body,
            content_type="concept",
            topics=["specification", "design", title.lower().split()[0]],
            metadata={"doc_type": "technical_spec"},
        )

    def _create_incident_report(
        self,
        title: str,
        summary: str,
        timeline: List[Dict[str, str]],
        impact: str,
        root_cause: str,
        action_items: List[Dict[str, str]],
        severity: str = "medium",
        **kwargs,
    ) -> Optional[str]:
        """Create an incident report."""
        timeline_section = "## Timeline\n\n| Time | Event |\n|------|-------|\n"
        for event in timeline:
            timeline_section += f"| {event.get('time', '')} | {event.get('event', '')} |\n"

        actions_section = "## Action Items\n\n| Action | Owner | Due Date | Status |\n|--------|-------|----------|--------|\n"
        for action in action_items:
            actions_section += f"| {action.get('action', '')} | {action.get('owner', '')} | {action.get('due', '')} | {action.get('status', 'Open')} |\n"

        body = f"""# Incident Report: {title}

## Summary
{summary}

**Severity:** {severity.upper()}

{timeline_section}

## Impact
{impact}

## Root Cause
{root_cause}

{actions_section}

## Lessons Learned
-

## Prevention Measures
-
"""

        return self.store_content(
            title=f"Incident: {title}",
            body=body,
            content_type="concept",
            topics=["incident", "postmortem", severity],
            metadata={"doc_type": "incident_report", "severity": severity},
        )

    def get_adr(self, adr_id: str) -> Optional[ArchitectureDecisionRecord]:
        """Get an ADR by ID."""
        return self._adrs.get(adr_id)

    def list_adrs(self, status: Optional[str] = None) -> List[ArchitectureDecisionRecord]:
        """List ADRs, optionally filtered by status."""
        adrs = list(self._adrs.values())
        if status:
            adrs = [a for a in adrs if a.status == status]
        return adrs

    def get_api_docs(self) -> List[Any]:
        """Get all API documentation."""
        content = self.get_content(topic="api", limit=100)
        return [c for c in content if c.metadata.get("doc_type") == "api_reference"]


# =============================================================================
# Keystone Content Facade - Financial
# =============================================================================


class FinancialReportType(Enum):
    """Types of financial reports."""

    BUDGET = "budget"
    FORECAST = "forecast"
    VARIANCE = "variance"
    CASH_FLOW = "cash_flow"
    P_AND_L = "p_and_l"
    BALANCE_SHEET = "balance_sheet"
    COMPLIANCE = "compliance"
    AUDIT = "audit"


class CFOContentFacade(ExecutiveContentFacade):
    """
    Keystone Content Facade - Financial content management.

    Specialized for:
    - Budget documents
    - Financial reports
    - Compliance documentation
    - Audit materials
    - Cost analysis
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Keystone", "financial")

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get financial content templates."""
        return [
            {
                "name": "Budget Proposal",
                "content_type": "procedure",
                "structure": ["summary", "categories", "justification", "timeline", "approval"],
            },
            {
                "name": "Financial Report",
                "content_type": "concept",
                "structure": ["executive_summary", "metrics", "analysis", "recommendations"],
            },
            {
                "name": "Cost Analysis",
                "content_type": "concept",
                "structure": ["scope", "current_costs", "proposed_changes", "savings", "risks"],
            },
            {
                "name": "Compliance Checklist",
                "content_type": "procedure",
                "structure": ["requirements", "status", "evidence", "gaps", "remediation"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard financial content."""
        creators = {
            "budget_proposal": self._create_budget_proposal,
            "financial_report": self._create_financial_report,
            "cost_analysis": self._create_cost_analysis,
            "compliance_doc": self._create_compliance_doc,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_budget_proposal(
        self,
        title: str,
        department: str,
        total_amount: float,
        categories: List[Dict[str, Any]],
        justification: str,
        fiscal_year: str,
        **kwargs,
    ) -> Optional[str]:
        """Create a budget proposal document."""
        categories_section = "## Budget Categories\n\n| Category | Amount | % of Total |\n|----------|--------|------------|\n"
        for cat in categories:
            pct = (cat.get("amount", 0) / total_amount * 100) if total_amount > 0 else 0
            categories_section += (
                f"| {cat.get('name', '')} | ${cat.get('amount', 0):,.2f} | {pct:.1f}% |\n"
            )

        body = f"""# Budget Proposal: {title}

## Overview
- **Department:** {department}
- **Fiscal Year:** {fiscal_year}
- **Total Budget:** ${total_amount:,.2f}

{categories_section}

## Justification
{justification}

## Approval Chain
- [ ] Department Head
- [ ] Finance Review
- [ ] Keystone Approval
- [ ] Agent Approval

## Notes
-
"""

        return self.store_content(
            title=f"Budget: {title} ({fiscal_year})",
            body=body,
            content_type="procedure",
            topics=["budget", department.lower(), fiscal_year],
            metadata={
                "doc_type": "budget",
                "department": department,
                "total_amount": total_amount,
                "fiscal_year": fiscal_year,
            },
        )

    def _create_financial_report(
        self,
        title: str,
        report_type: str,
        period: str,
        executive_summary: str,
        key_metrics: List[Dict[str, Any]],
        analysis: str,
        recommendations: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a financial report."""
        metrics_section = "## Key Metrics\n\n| Metric | Value | Change | Target |\n|--------|-------|--------|--------|\n"
        for m in key_metrics:
            change = m.get("change", "N/A")
            if isinstance(change, (int, float)):
                change = f"{change:+.1f}%"
            metrics_section += f"| {m.get('name', '')} | {m.get('value', '')} | {change} | {m.get('target', 'N/A')} |\n"

        body = f"""# Financial Report: {title}

## Report Details
- **Type:** {report_type.replace('_', ' ').title()}
- **Period:** {period}
- **Generated:** {datetime.now().strftime('%Y-%m-%d')}

## Agent Summary
{executive_summary}

{metrics_section}

## Analysis
{analysis}

## Recommendations
{chr(10).join(f'{i}. {r}' for i, r in enumerate(recommendations, 1))}

## Appendix
- Supporting data available upon request
"""

        return self.store_content(
            title=f"Financial Report: {title} ({period})",
            body=body,
            content_type="concept",
            topics=["financial", "report", report_type],
            metadata={"doc_type": "financial_report", "report_type": report_type, "period": period},
        )

    def _create_cost_analysis(
        self,
        title: str,
        scope: str,
        current_costs: List[Dict[str, Any]],
        proposed_changes: List[str],
        projected_savings: float,
        risks: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a cost analysis document."""
        costs_section = (
            "## Current Costs\n\n| Item | Monthly | Annual |\n|------|---------|--------|\n"
        )
        total_monthly = 0
        for c in current_costs:
            monthly = c.get("monthly", 0)
            annual = monthly * 12
            total_monthly += monthly
            costs_section += f"| {c.get('item', '')} | ${monthly:,.2f} | ${annual:,.2f} |\n"
        costs_section += (
            f"| **Total** | **${total_monthly:,.2f}** | **${total_monthly*12:,.2f}** |\n"
        )

        body = f"""# Cost Analysis: {title}

## Scope
{scope}

{costs_section}

## Proposed Changes
{chr(10).join(f'- {c}' for c in proposed_changes)}

## Projected Impact
- **Annual Savings:** ${projected_savings:,.2f}
- **ROI Timeline:** {kwargs.get('roi_timeline', 'TBD')}

## Risks
{chr(10).join(f'- {r}' for r in risks)}

## Recommendation
{kwargs.get('recommendation', 'Pending analysis completion')}
"""

        return self.store_content(
            title=f"Cost Analysis: {title}",
            body=body,
            content_type="concept",
            topics=["cost", "analysis", "optimization"],
            metadata={"doc_type": "cost_analysis", "projected_savings": projected_savings},
        )

    def _create_compliance_doc(
        self,
        title: str,
        regulation: str,
        requirements: List[Dict[str, Any]],
        current_status: str,
        gaps: List[str],
        remediation_plan: List[Dict[str, str]],
        **kwargs,
    ) -> Optional[str]:
        """Create a compliance documentation."""
        req_section = "## Requirements Status\n\n| Requirement | Status | Evidence | Notes |\n|-------------|--------|----------|-------|\n"
        for r in requirements:
            req_section += f"| {r.get('requirement', '')} | {r.get('status', 'Pending')} | {r.get('evidence', 'None')} | {r.get('notes', '')} |\n"

        remediation_section = "## Remediation Plan\n\n| Gap | Action | Owner | Target Date |\n|-----|--------|-------|-------------|\n"
        for r in remediation_plan:
            remediation_section += f"| {r.get('gap', '')} | {r.get('action', '')} | {r.get('owner', '')} | {r.get('target_date', '')} |\n"

        body = f"""# Compliance Documentation: {title}

## Overview
- **Regulation:** {regulation}
- **Current Status:** {current_status}
- **Last Review:** {datetime.now().strftime('%Y-%m-%d')}

{req_section}

## Identified Gaps
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- No gaps identified'}

{remediation_section}

## Audit Trail
- Document created: {datetime.now().strftime('%Y-%m-%d')}
"""

        return self.store_content(
            title=f"Compliance: {title}",
            body=body,
            content_type="procedure",
            topics=["compliance", regulation.lower(), "audit"],
            metadata={"doc_type": "compliance", "regulation": regulation, "status": current_status},
        )


# =============================================================================
# Blueprint Content Facade - Product
# =============================================================================


class CPOContentFacade(ExecutiveContentFacade):
    """
    Blueprint Content Facade - Product documentation management.

    Specialized for:
    - Product requirements documents (PRDs)
    - Feature specifications
    - Roadmap items
    - User research findings
    - Release notes
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Blueprint", "product")

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get product content templates."""
        return [
            {
                "name": "Product Requirements Document",
                "content_type": "concept",
                "structure": ["problem", "goals", "requirements", "success_metrics", "timeline"],
            },
            {
                "name": "Feature Specification",
                "content_type": "procedure",
                "structure": [
                    "overview",
                    "user_stories",
                    "acceptance_criteria",
                    "design",
                    "dependencies",
                ],
            },
            {
                "name": "User Research Summary",
                "content_type": "concept",
                "structure": ["methodology", "participants", "findings", "recommendations"],
            },
            {
                "name": "Release Notes",
                "content_type": "concept",
                "structure": ["version", "features", "improvements", "fixes", "known_issues"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard product content."""
        creators = {
            "prd": self._create_prd,
            "feature_spec": self._create_feature_spec,
            "user_research": self._create_user_research,
            "release_notes": self._create_release_notes,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_prd(
        self,
        title: str,
        problem_statement: str,
        goals: List[str],
        requirements: List[Dict[str, str]],
        success_metrics: List[str],
        timeline: str,
        **kwargs,
    ) -> Optional[str]:
        """Create a Product Requirements Document."""
        req_section = "## Requirements\n\n| ID | Requirement | Priority | Status |\n|----|--------------|---------|---------|\n"
        for i, r in enumerate(requirements, 1):
            req_section += f"| R{i} | {r.get('description', '')} | {r.get('priority', 'Medium')} | {r.get('status', 'Proposed')} |\n"

        body = f"""# PRD: {title}

## Problem Statement
{problem_statement}

## Goals
{chr(10).join(f'- {g}' for g in goals)}

{req_section}

## Success Metrics
{chr(10).join(f'- {m}' for m in success_metrics)}

## Timeline
{timeline}

## Open Questions
-

## Stakeholders
- Product: Blueprint
- Engineering: Forge
- Design:
"""

        return self.store_content(
            title=f"PRD: {title}",
            body=body,
            content_type="concept",
            topics=["prd", "requirements", title.lower().split()[0]],
            metadata={"doc_type": "prd"},
        )

    def _create_feature_spec(
        self,
        title: str,
        overview: str,
        user_stories: List[Dict[str, str]],
        acceptance_criteria: List[str],
        design_notes: str,
        dependencies: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a feature specification."""
        stories_section = "## User Stories\n\n"
        for story in user_stories:
            stories_section += f"**As a** {story.get('role', 'user')}, "
            stories_section += f"**I want** {story.get('want', '')}, "
            stories_section += f"**so that** {story.get('benefit', '')}.\n\n"

        body = f"""# Feature Specification: {title}

## Overview
{overview}

{stories_section}

## Acceptance Criteria
{chr(10).join(f'- [ ] {ac}' for ac in acceptance_criteria)}

## Design Notes
{design_notes}

## Dependencies
{chr(10).join(f'- {d}' for d in dependencies) if dependencies else '- None identified'}

## Out of Scope
-

## Risks
-
"""

        return self.store_content(
            title=f"Feature: {title}",
            body=body,
            content_type="procedure",
            topics=["feature", "specification", title.lower().split()[0]],
            metadata={"doc_type": "feature_spec"},
        )

    def _create_user_research(
        self,
        title: str,
        methodology: str,
        participants: int,
        findings: List[Dict[str, str]],
        recommendations: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create user research findings."""
        findings_section = "## Key Findings\n\n"
        for i, f in enumerate(findings, 1):
            findings_section += f"### Finding {i}: {f.get('title', 'Untitled')}\n"
            findings_section += f"{f.get('description', '')}\n\n"
            if f.get("quote"):
                findings_section += f"> \"{f['quote']}\"\n\n"

        body = f"""# User Research: {title}

## Study Details
- **Methodology:** {methodology}
- **Participants:** {participants}
- **Date:** {datetime.now().strftime('%Y-%m-%d')}

{findings_section}

## Recommendations
{chr(10).join(f'{i}. {r}' for i, r in enumerate(recommendations, 1))}

## Next Steps
-

## Raw Data
Available upon request.
"""

        return self.store_content(
            title=f"Research: {title}",
            body=body,
            content_type="concept",
            topics=["research", "user", methodology.lower()],
            metadata={"doc_type": "user_research", "participants": participants},
        )

    def _create_release_notes(
        self,
        version: str,
        release_date: str,
        features: List[str],
        improvements: List[str],
        fixes: List[str],
        known_issues: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[str]:
        """Create release notes."""
        body = f"""# Release Notes - v{version}

**Release Date:** {release_date}

## New Features
{chr(10).join(f'- {f}' for f in features) if features else '- No new features'}

## Improvements
{chr(10).join(f'- {i}' for i in improvements) if improvements else '- No improvements'}

## Bug Fixes
{chr(10).join(f'- {f}' for f in fixes) if fixes else '- No bug fixes'}

## Known Issues
{chr(10).join(f'- {i}' for i in known_issues) if known_issues else '- None'}

## Upgrade Notes
-

## Documentation
- Updated user guide available at [link]
"""

        return self.store_content(
            title=f"Release Notes v{version}",
            body=body,
            content_type="concept",
            topics=["release", "notes", version],
            metadata={"doc_type": "release_notes", "version": version},
        )


# =============================================================================
# Axiom Content Facade - Revenue/Sales
# =============================================================================


class CROContentFacade(ExecutiveContentFacade):
    """
    Axiom Content Facade - Revenue and sales content management.

    Specialized for:
    - Sales playbooks
    - Pricing guides
    - Competitive analysis
    - Sales enablement materials
    - Revenue forecasts
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Axiom", "revenue")

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get sales/revenue content templates."""
        return [
            {
                "name": "Sales Playbook",
                "content_type": "procedure",
                "structure": ["overview", "qualification", "objections", "pricing", "closing"],
            },
            {
                "name": "Competitive Analysis",
                "content_type": "concept",
                "structure": [
                    "competitors",
                    "comparison",
                    "strengths",
                    "weaknesses",
                    "positioning",
                ],
            },
            {
                "name": "Pricing Guide",
                "content_type": "procedure",
                "structure": ["tiers", "features", "discounts", "negotiation", "approval"],
            },
            {
                "name": "Deal Review",
                "content_type": "concept",
                "structure": ["opportunity", "stakeholders", "timeline", "risks", "next_steps"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard sales content."""
        creators = {
            "sales_playbook": self._create_sales_playbook,
            "competitive_analysis": self._create_competitive_analysis,
            "pricing_guide": self._create_pricing_guide,
            "battlecard": self._create_battlecard,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_sales_playbook(
        self,
        title: str,
        target_segment: str,
        qualification_criteria: List[str],
        common_objections: List[Dict[str, str]],
        value_propositions: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a sales playbook."""
        objections_section = "## Handling Objections\n\n"
        for obj in common_objections:
            objections_section += f"### \"{obj.get('objection', '')}\"\n"
            objections_section += f"**Response:** {obj.get('response', '')}\n\n"

        body = f"""# Sales Playbook: {title}

## Target Segment
{target_segment}

## Qualification Criteria (BANT)
{chr(10).join(f'- [ ] {c}' for c in qualification_criteria)}

## Value Propositions
{chr(10).join(f'{i}. {v}' for i, v in enumerate(value_propositions, 1))}

{objections_section}

## Discovery Questions
1.
2.
3.

## Demo Flow
1.
2.
3.

## Closing Techniques
-
"""

        return self.store_content(
            title=f"Playbook: {title}",
            body=body,
            content_type="procedure",
            topics=["sales", "playbook", target_segment.lower()],
            metadata={"doc_type": "sales_playbook", "segment": target_segment},
        )

    def _create_competitive_analysis(
        self,
        title: str,
        competitors: List[Dict[str, Any]],
        our_strengths: List[str],
        our_weaknesses: List[str],
        positioning_statement: str,
        **kwargs,
    ) -> Optional[str]:
        """Create competitive analysis."""
        comp_section = "## Competitor Overview\n\n"
        for comp in competitors:
            comp_section += f"### {comp.get('name', 'Competitor')}\n"
            comp_section += f"- **Positioning:** {comp.get('positioning', '')}\n"
            comp_section += f"- **Strengths:** {', '.join(comp.get('strengths', []))}\n"
            comp_section += f"- **Weaknesses:** {', '.join(comp.get('weaknesses', []))}\n"
            comp_section += f"- **Pricing:** {comp.get('pricing', 'Unknown')}\n\n"

        body = f"""# Competitive Analysis: {title}

{comp_section}

## Our Strengths
{chr(10).join(f'✓ {s}' for s in our_strengths)}

## Areas for Improvement
{chr(10).join(f'- {w}' for w in our_weaknesses)}

## Positioning Statement
{positioning_statement}

## Win/Loss Analysis
- Win Rate vs Competition: TBD
- Common Win Themes:
- Common Loss Themes:

## Recommended Talking Points
1.
2.
3.
"""

        return self.store_content(
            title=f"Competitive Analysis: {title}",
            body=body,
            content_type="concept",
            topics=["competitive", "analysis", "sales"],
            metadata={"doc_type": "competitive_analysis"},
        )

    def _create_pricing_guide(
        self,
        title: str,
        tiers: List[Dict[str, Any]],
        discount_policy: str,
        approval_thresholds: List[Dict[str, Any]],
        **kwargs,
    ) -> Optional[str]:
        """Create pricing guide."""
        tiers_section = (
            "## Pricing Tiers\n\n| Tier | Price | Features |\n|------|-------|----------|\n"
        )
        for tier in tiers:
            features = ", ".join(tier.get("features", [])[:3])
            tiers_section += (
                f"| {tier.get('name', '')} | ${tier.get('price', 0):,.2f}/mo | {features} |\n"
            )

        approval_section = (
            "## Discount Approvals\n\n| Discount | Approver |\n|----------|----------|\n"
        )
        for thresh in approval_thresholds:
            approval_section += f"| {thresh.get('discount', '')} | {thresh.get('approver', '')} |\n"

        body = f"""# Pricing Guide: {title}

{tiers_section}

## Discount Policy
{discount_policy}

{approval_section}

## Negotiation Guidelines
-

## Competitive Pricing Notes
-
"""

        return self.store_content(
            title=f"Pricing Guide: {title}",
            body=body,
            content_type="procedure",
            topics=["pricing", "sales", "guide"],
            metadata={"doc_type": "pricing_guide"},
        )

    def _create_battlecard(
        self,
        competitor: str,
        quick_facts: List[str],
        win_themes: List[str],
        landmines: List[str],
        knockout_questions: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a competitive battlecard."""
        body = f"""# Battlecard: vs {competitor}

## Quick Facts
{chr(10).join(f'- {f}' for f in quick_facts)}

## How We Win
{chr(10).join(f'✓ {w}' for w in win_themes)}

## Landmines to Avoid
{chr(10).join(f'⚠ {l}' for l in landmines)}

## Knockout Questions
{chr(10).join(f'{i}. "{q}"' for i, q in enumerate(knockout_questions, 1))}

## Trap Setting Questions
1.
2.

## Key Differentiators
| Area | Us | {competitor} |
|------|-----|-------------|
| | | |

## Proof Points
-
"""

        return self.store_content(
            title=f"Battlecard: vs {competitor}",
            body=body,
            content_type="procedure",
            topics=["battlecard", "competitive", competitor.lower()],
            metadata={"doc_type": "battlecard", "competitor": competitor},
        )


# =============================================================================
# Compass Content Facade - Security
# =============================================================================


class CSOContentFacade(ExecutiveContentFacade):
    """
    Compass Content Facade - Security content management.

    Specialized for:
    - Security policies
    - Compliance documentation
    - Risk assessments
    - Incident response plans
    - Security training materials
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Compass", "security")

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get security content templates."""
        return [
            {
                "name": "Security Policy",
                "content_type": "procedure",
                "structure": ["purpose", "scope", "policy", "responsibilities", "enforcement"],
            },
            {
                "name": "Risk Assessment",
                "content_type": "concept",
                "structure": ["asset", "threats", "vulnerabilities", "impact", "controls"],
            },
            {
                "name": "Incident Response Plan",
                "content_type": "procedure",
                "structure": ["detection", "containment", "eradication", "recovery", "lessons"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard security content."""
        creators = {
            "security_policy": self._create_security_policy,
            "risk_assessment": self._create_risk_assessment,
            "incident_response": self._create_incident_response_plan,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_security_policy(
        self,
        title: str,
        purpose: str,
        scope: str,
        policy_statements: List[str],
        responsibilities: List[Dict[str, str]],
        enforcement: str,
        **kwargs,
    ) -> Optional[str]:
        """Create a security policy document."""
        resp_section = (
            "## Responsibilities\n\n| Role | Responsibility |\n|------|----------------|\n"
        )
        for r in responsibilities:
            resp_section += f"| {r.get('role', '')} | {r.get('responsibility', '')} |\n"

        body = f"""# Security Policy: {title}

## Purpose
{purpose}

## Scope
{scope}

## Policy
{chr(10).join(f'{i}. {p}' for i, p in enumerate(policy_statements, 1))}

{resp_section}

## Enforcement
{enforcement}

## Related Policies
-

## Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {datetime.now().strftime('%Y-%m-%d')} | Compass | Initial version |
"""

        return self.store_content(
            title=f"Policy: {title}",
            body=body,
            content_type="procedure",
            topics=["security", "policy", title.lower().split()[0]],
            metadata={"doc_type": "security_policy"},
        )

    def _create_risk_assessment(
        self,
        title: str,
        asset: str,
        threats: List[Dict[str, Any]],
        vulnerabilities: List[str],
        controls: List[Dict[str, str]],
        overall_risk: str,
        **kwargs,
    ) -> Optional[str]:
        """Create a risk assessment."""
        threats_section = "## Threat Analysis\n\n| Threat | Likelihood | Impact | Risk Level |\n|--------|------------|--------|------------|\n"
        for t in threats:
            threats_section += f"| {t.get('name', '')} | {t.get('likelihood', 'Medium')} | {t.get('impact', 'Medium')} | {t.get('risk', 'Medium')} |\n"

        controls_section = (
            "## Controls\n\n| Control | Type | Status |\n|---------|------|--------|\n"
        )
        for c in controls:
            controls_section += f"| {c.get('control', '')} | {c.get('type', 'Technical')} | {c.get('status', 'Proposed')} |\n"

        body = f"""# Risk Assessment: {title}

## Asset Information
{asset}

{threats_section}

## Vulnerabilities
{chr(10).join(f'- {v}' for v in vulnerabilities)}

{controls_section}

## Overall Risk Rating
**{overall_risk.upper()}**

## Recommendations
1.
2.
3.

## Review Schedule
- Next Review: {kwargs.get('next_review', 'TBD')}
"""

        return self.store_content(
            title=f"Risk Assessment: {title}",
            body=body,
            content_type="concept",
            topics=["risk", "assessment", "security"],
            metadata={"doc_type": "risk_assessment", "overall_risk": overall_risk},
        )

    def _create_incident_response_plan(
        self,
        incident_type: str,
        detection_steps: List[str],
        containment_steps: List[str],
        eradication_steps: List[str],
        recovery_steps: List[str],
        contacts: List[Dict[str, str]],
        **kwargs,
    ) -> Optional[str]:
        """Create an incident response plan."""
        contacts_section = (
            "## Emergency Contacts\n\n| Role | Name | Contact |\n|------|------|--------|\n"
        )
        for c in contacts:
            contacts_section += (
                f"| {c.get('role', '')} | {c.get('name', '')} | {c.get('contact', '')} |\n"
            )

        body = f"""# Incident Response Plan: {incident_type}

## 1. Detection
{chr(10).join(f'{i}. {s}' for i, s in enumerate(detection_steps, 1))}

## 2. Containment
{chr(10).join(f'{i}. {s}' for i, s in enumerate(containment_steps, 1))}

## 3. Eradication
{chr(10).join(f'{i}. {s}' for i, s in enumerate(eradication_steps, 1))}

## 4. Recovery
{chr(10).join(f'{i}. {s}' for i, s in enumerate(recovery_steps, 1))}

## 5. Post-Incident
- [ ] Document timeline
- [ ] Conduct lessons learned
- [ ] Update playbook
- [ ] Brief stakeholders

{contacts_section}

## Escalation Matrix
| Severity | Response Time | Escalation |
|----------|--------------|------------|
| Critical | 15 minutes | Compass, CEO |
| High | 1 hour | Compass |
| Medium | 4 hours | Security Team |
| Low | 24 hours | Security Team |
"""

        return self.store_content(
            title=f"IRP: {incident_type}",
            body=body,
            content_type="procedure",
            topics=["incident", "response", incident_type.lower()],
            metadata={"doc_type": "incident_response_plan", "incident_type": incident_type},
        )


# =============================================================================
# Index Content Facade - Data
# =============================================================================


class CDOContentFacade(ExecutiveContentFacade):
    """
    Index Content Facade - Data governance content management.

    Specialized for:
    - Data governance policies
    - Data dictionary entries
    - Analytics reports
    - Data quality documentation
    - Dashboard specifications
    """

    def __init__(self, nexus_bridge: Any):
        super().__init__(nexus_bridge, "Index", "data")

    def get_domain_templates(self) -> List[Dict[str, Any]]:
        """Get data content templates."""
        return [
            {
                "name": "Data Dictionary Entry",
                "content_type": "concept",
                "structure": ["field", "type", "description", "source", "quality"],
            },
            {
                "name": "Analytics Report Spec",
                "content_type": "procedure",
                "structure": ["purpose", "metrics", "dimensions", "filters", "visualization"],
            },
            {
                "name": "Data Quality Report",
                "content_type": "concept",
                "structure": ["dataset", "metrics", "issues", "trends", "actions"],
            },
        ]

    def create_standard_content(self, content_subtype: str, **kwargs) -> Optional[str]:
        """Create standard data content."""
        creators = {
            "data_dictionary": self._create_data_dictionary,
            "analytics_spec": self._create_analytics_spec,
            "data_quality_report": self._create_data_quality_report,
            "dashboard_spec": self._create_dashboard_spec,
        }

        creator = creators.get(content_subtype)
        if creator:
            return creator(**kwargs)
        return None

    def _create_data_dictionary(
        self,
        dataset: str,
        fields: List[Dict[str, Any]],
        source_system: str,
        update_frequency: str,
        owner: str,
        **kwargs,
    ) -> Optional[str]:
        """Create a data dictionary entry."""
        fields_section = "## Fields\n\n| Field | Type | Description | Nullable | Example |\n|-------|------|-------------|----------|--------|\n"
        for f in fields:
            fields_section += f"| {f.get('name', '')} | {f.get('type', '')} | {f.get('description', '')} | {f.get('nullable', 'Yes')} | {f.get('example', '')} |\n"

        body = f"""# Data Dictionary: {dataset}

## Overview
- **Source System:** {source_system}
- **Update Frequency:** {update_frequency}
- **Data Owner:** {owner}
- **Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

{fields_section}

## Relationships
-

## Data Quality Rules
-

## Access Notes
-
"""

        return self.store_content(
            title=f"Data Dictionary: {dataset}",
            body=body,
            content_type="concept",
            topics=["data", "dictionary", dataset.lower()],
            metadata={"doc_type": "data_dictionary", "dataset": dataset, "owner": owner},
        )

    def _create_analytics_spec(
        self,
        title: str,
        purpose: str,
        metrics: List[Dict[str, str]],
        dimensions: List[str],
        filters: List[str],
        data_sources: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create an analytics report specification."""
        metrics_section = (
            "## Metrics\n\n| Metric | Calculation | Format |\n|--------|-------------|--------|\n"
        )
        for m in metrics:
            metrics_section += (
                f"| {m.get('name', '')} | {m.get('calculation', '')} | {m.get('format', '')} |\n"
            )

        body = f"""# Analytics Specification: {title}

## Purpose
{purpose}

{metrics_section}

## Dimensions
{chr(10).join(f'- {d}' for d in dimensions)}

## Filters
{chr(10).join(f'- {f}' for f in filters)}

## Data Sources
{chr(10).join(f'- {s}' for s in data_sources)}

## Visualization
- Chart Type: {kwargs.get('chart_type', 'TBD')}
- Refresh: {kwargs.get('refresh', 'Daily')}

## Access
- Audience: {kwargs.get('audience', 'All')}
"""

        return self.store_content(
            title=f"Analytics: {title}",
            body=body,
            content_type="procedure",
            topics=["analytics", "report", title.lower().split()[0]],
            metadata={"doc_type": "analytics_spec"},
        )

    def _create_data_quality_report(
        self,
        dataset: str,
        period: str,
        quality_metrics: List[Dict[str, Any]],
        issues: List[Dict[str, str]],
        actions: List[str],
        **kwargs,
    ) -> Optional[str]:
        """Create a data quality report."""
        metrics_section = "## Quality Metrics\n\n| Metric | Score | Target | Status |\n|--------|-------|--------|--------|\n"
        for m in quality_metrics:
            status = "✓" if m.get("score", 0) >= m.get("target", 0) else "✗"
            metrics_section += f"| {m.get('name', '')} | {m.get('score', '')}% | {m.get('target', '')}% | {status} |\n"

        issues_section = "## Issues Identified\n\n| Issue | Severity | Records Affected | Status |\n|-------|----------|------------------|--------|\n"
        for i in issues:
            issues_section += f"| {i.get('issue', '')} | {i.get('severity', 'Medium')} | {i.get('records', 'Unknown')} | {i.get('status', 'Open')} |\n"

        body = f"""# Data Quality Report: {dataset}

## Report Period
{period}

{metrics_section}

{issues_section}

## Recommended Actions
{chr(10).join(f'{i}. {a}' for i, a in enumerate(actions, 1))}

## Trend Analysis
- Overall quality trend: {kwargs.get('trend', 'Stable')}

## Next Review
{kwargs.get('next_review', 'Next month')}
"""

        return self.store_content(
            title=f"Data Quality: {dataset} ({period})",
            body=body,
            content_type="concept",
            topics=["data", "quality", dataset.lower()],
            metadata={"doc_type": "data_quality_report", "dataset": dataset, "period": period},
        )

    def _create_dashboard_spec(
        self,
        title: str,
        purpose: str,
        audience: str,
        kpis: List[Dict[str, str]],
        sections: List[Dict[str, Any]],
        **kwargs,
    ) -> Optional[str]:
        """Create a dashboard specification."""
        kpi_section = "## Key Performance Indicators\n\n| KPI | Definition | Target |\n|-----|------------|--------|\n"
        for k in kpis:
            kpi_section += (
                f"| {k.get('name', '')} | {k.get('definition', '')} | {k.get('target', '')} |\n"
            )

        sections_text = "## Dashboard Sections\n\n"
        for s in sections:
            sections_text += f"### {s.get('name', 'Section')}\n"
            sections_text += f"- **Visualizations:** {', '.join(s.get('charts', []))}\n"
            sections_text += f"- **Metrics:** {', '.join(s.get('metrics', []))}\n\n"

        body = f"""# Dashboard Specification: {title}

## Purpose
{purpose}

## Target Audience
{audience}

{kpi_section}

{sections_text}

## Technical Requirements
- Refresh Rate: {kwargs.get('refresh_rate', 'Daily')}
- Data Sources: {', '.join(kwargs.get('data_sources', ['TBD']))}
- Access Level: {kwargs.get('access_level', 'All users')}

## Mockup
[Link to mockup]
"""

        return self.store_content(
            title=f"Dashboard: {title}",
            body=body,
            content_type="procedure",
            topics=["dashboard", "analytics", title.lower().split()[0]],
            metadata={"doc_type": "dashboard_spec", "audience": audience},
        )


# =============================================================================
# Facade Factory
# =============================================================================


def create_executive_facade(
    agent_code: str,
    nexus_bridge: Any,
) -> Optional[ExecutiveContentFacade]:
    """
    Factory function to create agent content facades.

    Args:
        agent_code: Agent identifier (Echo, Forge, etc.)
        nexus_bridge: NexusBridge instance

    Returns:
        Appropriate agent facade or None
    """
    facades = {
        "Echo": CMOContentFacade,
        "Forge": CTOContentFacade,
        "Keystone": CFOContentFacade,
        "Blueprint": CPOContentFacade,
        "Axiom": CROContentFacade,
        "Compass": CSOContentFacade,
        "Index": CDOContentFacade,
    }

    # Case-insensitive lookup: try exact match first, then title-case
    facade_class = facades.get(agent_code)
    if not facade_class:
        normalized = agent_code.strip().title() if agent_code else ""
        facade_class = facades.get(normalized)
    if facade_class:
        return facade_class(nexus_bridge)

    logger.warning(f"No facade available for agent: {agent_code}")
    return None


def create_all_facades(nexus_bridge: Any) -> Dict[str, ExecutiveContentFacade]:
    """
    Create facades for all agents.

    Args:
        nexus_bridge: NexusBridge instance

    Returns:
        Dict mapping agent code to facade
    """
    agents = ["Echo", "Forge", "Keystone", "Blueprint", "Axiom", "Compass", "Index"]
    return {code: create_executive_facade(code, nexus_bridge) for code in agents}
