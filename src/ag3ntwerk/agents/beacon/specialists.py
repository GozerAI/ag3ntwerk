"""
Beacon (Beacon) Specialist Classes.

Individual contributor specialists for customer operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class FeedbackCollector(Specialist):
    """
    Specialist for feedback collection.

    Gathers and aggregates customer feedback from multiple sources.
    """

    HANDLED_TASK_TYPES = [
        "feedback_gathering",
        "survey_analysis",
        "interview_synthesis",
        "feedback_aggregation",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="FeedbackCollector",
            name="Feedback Collector",
            domain="Feedback Collection",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute feedback collection task."""
        task.status = TaskStatus.IN_PROGRESS

        sources = task.context.get("sources", [])

        prompt = f"""As a Feedback Collector specialist:

Task Type: {task.task_type}
Description: {task.description}
Sources: {sources}
Context: {task.context}

Collect and summarize feedback:
1. Feedback by source
2. Key themes
3. Quote highlights
4. Volume metrics
5. Urgency indicators"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "collection_type": task.task_type,
                "feedback_summary": response,
                "collected_at": _utcnow().isoformat(),
            },
        )


class SatisfactionAnalyst(Specialist):
    """
    Specialist for satisfaction analysis.

    Analyzes NPS, CSAT, and other satisfaction metrics.
    """

    HANDLED_TASK_TYPES = [
        "nps_analysis",
        "csat_analysis",
        "ces_analysis",
        "satisfaction_trending",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="SatisfactionAnalyst",
            name="Satisfaction Analyst",
            domain="Satisfaction Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute satisfaction analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        metrics = task.context.get("metrics", {})
        benchmark = task.context.get("benchmark", None)

        prompt = f"""As a Satisfaction Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Metrics: {metrics}
Benchmark: {benchmark}

Provide satisfaction analysis:
1. Score calculation
2. Trend analysis
3. Segment breakdown
4. Key drivers
5. Improvement recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": task.task_type,
                "analysis": response,
            },
        )


class SupportTriager(Specialist):
    """
    Specialist for support ticket triage.

    Classifies and routes support tickets appropriately.
    """

    HANDLED_TASK_TYPES = [
        "ticket_classification",
        "priority_assignment",
        "ticket_routing",
        "auto_response",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="SupportTriager",
            name="Support Triager",
            domain="Support Triage",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute support triage task."""
        task.status = TaskStatus.IN_PROGRESS

        ticket = task.context.get("ticket", {})

        prompt = f"""As a Support Triager specialist:

Task Type: {task.task_type}
Description: {task.description}
Ticket: {ticket}

Provide triage decision:
1. Category: [Bug/Feature/Question/Account/Other]
2. Priority: [Critical/High/Medium/Low]
3. Route to: [Support/Engineering/Product/Account]
4. Suggested response template
5. Escalation needed: [Yes/No]"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "triage_type": task.task_type,
                "ticket_id": ticket.get("id", "unknown"),
                "triage": response,
            },
        )


class CustomerAdvocate(Specialist):
    """
    Specialist for customer advocacy.

    Represents voice of customer in product decisions.
    """

    HANDLED_TASK_TYPES = [
        "voice_of_customer",
        "customer_advocacy",
        "feedback_synthesis",
        "stakeholder_brief",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="CustomerAdvocate",
            name="Customer Advocate",
            domain="Customer Advocacy",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute customer advocacy task."""
        task.status = TaskStatus.IN_PROGRESS

        customer_data = task.context.get("customer_data", {})
        audience = task.context.get("audience", "product_team")

        prompt = f"""As a Customer Advocate specialist:

Task Type: {task.task_type}
Description: {task.description}
Customer Data: {customer_data}
Target Audience: {audience}

Create advocacy output:
1. Customer perspective summary
2. Key needs and pain points
3. Success stories
4. Risk areas
5. Recommendations for {audience}"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "advocacy_type": task.task_type,
                "audience": audience,
                "advocacy": response,
            },
        )


class ChurnAnalyst(Specialist):
    """
    Specialist for churn analysis and prevention.

    Analyzes churn patterns and recommends interventions.
    """

    HANDLED_TASK_TYPES = [
        "churn_prediction",
        "churn_analysis",
        "retention_strategy",
        "winback_planning",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="ChurnAnalyst",
            name="Churn Analyst",
            domain="Churn Analysis",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute churn analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        customer_data = task.context.get("customer_data", [])
        churn_data = task.context.get("churn_data", [])

        prompt = f"""As a Churn Analyst specialist:

Task Type: {task.task_type}
Description: {task.description}
Customer Data: {customer_data}
Churn Data: {churn_data}

Provide churn analysis:
1. Churn risk scores
2. Warning signals
3. Root causes
4. Prevention strategies
5. Win-back opportunities"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": task.task_type,
                "churn_analysis": response,
            },
        )


class OnboardingSpecialist(Specialist):
    """
    Specialist for customer onboarding.

    Optimizes onboarding experience and time-to-value.
    """

    HANDLED_TASK_TYPES = [
        "onboarding_design",
        "onboarding_optimization",
        "activation_tracking",
        "time_to_value_analysis",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="OnboardingSpec",
            name="Onboarding Specialist",
            domain="Customer Onboarding",
            capabilities=self.HANDLED_TASK_TYPES,
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if this specialist handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute onboarding task."""
        task.status = TaskStatus.IN_PROGRESS

        onboarding_data = task.context.get("onboarding_data", {})
        customer_type = task.context.get("customer_type", "standard")

        prompt = f"""As an Onboarding Specialist:

Task Type: {task.task_type}
Description: {task.description}
Onboarding Data: {onboarding_data}
Customer Type: {customer_type}

Provide onboarding analysis:
1. Current journey assessment
2. Drop-off points
3. Time-to-value metrics
4. Improvement recommendations
5. Success milestones"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "onboarding_type": task.task_type,
                "customer_type": customer_type,
                "analysis": response,
            },
        )
