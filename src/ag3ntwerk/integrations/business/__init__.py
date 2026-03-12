"""
Business Integrations for ag3ntwerk.

This package provides integrations for business operations:
- CRM: Salesforce/HubSpot integration
- Payments: Stripe integration
- Project Management: Jira/Linear integration
- Workflow: Zapier/n8n integration
"""

from ag3ntwerk.integrations.business.crm import (
    CRMIntegration,
    CRMProvider,
    Contact,
    Deal,
    Company,
)
from ag3ntwerk.integrations.business.payments import (
    PaymentIntegration,
    StripeConfig,
    Customer,
    Invoice,
    Subscription,
)
from ag3ntwerk.integrations.business.projects import (
    ProjectIntegration,
    ProjectProvider,
    JiraConfig,
    LinearConfig,
    ProjectIssue,
    Sprint,
)
from ag3ntwerk.integrations.business.workflows import (
    WorkflowIntegration,
    WorkflowProvider,
    Workflow,
    WorkflowRun,
)

__all__ = [
    "CRMIntegration",
    "CRMProvider",
    "Contact",
    "Deal",
    "Company",
    "PaymentIntegration",
    "StripeConfig",
    "Customer",
    "Invoice",
    "Subscription",
    "ProjectIntegration",
    "ProjectProvider",
    "JiraConfig",
    "LinearConfig",
    "ProjectIssue",
    "Sprint",
    "WorkflowIntegration",
    "WorkflowProvider",
    "Workflow",
    "WorkflowRun",
]
