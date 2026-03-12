"""
Beacon (Beacon) Agent - Beacon.

Codename: Beacon
Core function: Customer relationships, satisfaction, and feedback.

The Beacon handles all customer-focused tasks:
- Customer success and health scoring
- Feedback collection and analysis
- Support escalation and triage
- Onboarding optimization
- Satisfaction tracking (NPS, CSAT)
"""

from ag3ntwerk.agents.beacon.agent import Beacon
from ag3ntwerk.agents.beacon.managers import (
    CustomerSuccessManager,
    FeedbackManager,
    SupportManager,
)
from ag3ntwerk.agents.beacon.specialists import (
    ChurnAnalyst,
    CustomerAdvocate,
    FeedbackCollector,
    OnboardingSpecialist,
    SatisfactionAnalyst,
    SupportTriager,
)
from ag3ntwerk.agents.beacon.models import (
    # Enums
    CustomerHealthStatus,
    TicketStatus,
    TicketPriority,
    FeedbackType,
    FeedbackSentiment,
    OnboardingStage,
    # Dataclasses
    Customer,
    SupportTicket,
    Feedback,
    HealthScore,
    OnboardingPlan,
    ChurnRisk,
    CustomerMetrics,
    # Capabilities
    CUSTOMER_DOMAIN_CAPABILITIES,
)

# Codename alias
Beacon = Beacon

__all__ = [
    # Agent
    "Beacon",
    "Beacon",
    # Managers
    "CustomerSuccessManager",
    "FeedbackManager",
    "SupportManager",
    # Specialists
    "FeedbackCollector",
    "SatisfactionAnalyst",
    "SupportTriager",
    "CustomerAdvocate",
    "ChurnAnalyst",
    "OnboardingSpecialist",
    # Enums
    "CustomerHealthStatus",
    "TicketStatus",
    "TicketPriority",
    "FeedbackType",
    "FeedbackSentiment",
    "OnboardingStage",
    # Dataclasses
    "Customer",
    "SupportTicket",
    "Feedback",
    "HealthScore",
    "OnboardingPlan",
    "ChurnRisk",
    "CustomerMetrics",
    # Capabilities
    "CUSTOMER_DOMAIN_CAPABILITIES",
]
