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

Sphere of influence: Customer experience, retention, advocacy,
voice of customer, customer journey, support operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.beacon.managers import (
    CustomerSuccessManager,
    FeedbackManager,
    SupportManager,
)
from ag3ntwerk.agents.beacon.specialists import (
    FeedbackCollector,
    SatisfactionAnalyst,
    SupportTriager,
    CustomerAdvocate,
    ChurnAnalyst,
    OnboardingSpecialist,
)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Customer management task types
CUSTOMER_CAPABILITIES = [
    "feedback_collection",
    "satisfaction_tracking",
    "support_escalation",
    "customer_health_scoring",
    "onboarding_optimization",
    "customer_journey_mapping",
    "churn_analysis",
    "nps_analysis",
    "csat_analysis",
    "voice_of_customer",
    "customer_advocacy",
    "retention_strategy",
    # Manager-level task types
    "customer_health_review",
    "success_planning",
    "customer_segmentation",
    "expansion_planning",
    "renewal_management",
    "feedback_aggregation",
    "feedback_analysis",
    "feedback_reporting",
    "sentiment_analysis",
    "feedback_prioritization",
    "support_operations",
    "ticket_management",
    "support_metrics",
    "support_optimization",
    "support_staffing",
    # Specialist-level task types
    "feedback_gathering",
    "feedback_categorization",
    "survey_creation",
    "interview_synthesis",
    "nps_calculation",
    "csat_calculation",
    "ces_calculation",
    "satisfaction_reporting",
    "ticket_triage",
    "ticket_classification",
    "priority_assessment",
    "escalation_handling",
    "customer_research",
    "advocacy_planning",
    "case_study_creation",
    "reference_management",
    "churn_prediction",
    "churn_risk_scoring",
    "retention_analysis",
    "win_back_strategy",
    "onboarding_design",
    "onboarding_optimization",
    "onboarding_tracking",
    "time_to_value_analysis",
]

# Routing from task types to managers
MANAGER_ROUTING = {
    # CustomerSuccessManager tasks
    "customer_health_scoring": "CSM",
    "customer_health_review": "CSM",
    "success_planning": "CSM",
    "customer_segmentation": "CSM",
    "expansion_planning": "CSM",
    "renewal_management": "CSM",
    "retention_strategy": "CSM",
    "customer_journey_mapping": "CSM",
    "onboarding_optimization": "CSM",
    # FeedbackManager tasks
    "feedback_collection": "FM",
    "feedback_aggregation": "FM",
    "feedback_analysis": "FM",
    "feedback_reporting": "FM",
    "sentiment_analysis": "FM",
    "feedback_prioritization": "FM",
    "voice_of_customer": "FM",
    "nps_analysis": "FM",
    "csat_analysis": "FM",
    "satisfaction_tracking": "FM",
    # SupportManager tasks
    "support_escalation": "SM",
    "support_operations": "SM",
    "ticket_management": "SM",
    "support_metrics": "SM",
    "support_optimization": "SM",
    "support_staffing": "SM",
}


class Beacon(Manager):
    """
    Beacon - Beacon.

    The Beacon is responsible for customer relationships and success
    within the ag3ntwerk system. It manages customer experience,
    collects feedback, and advocates for customer needs.

    Codename: Beacon

    Core Responsibilities:
    - Customer success and health monitoring
    - Feedback collection and categorization
    - Support escalation and issue triage
    - Satisfaction tracking (NPS, CSAT, CES)
    - Customer advocacy in product planning

    Example:
        ```python
        cco = Beacon(llm_provider=llm)

        task = Task(
            description="Analyze customer feedback for Q4",
            task_type="feedback_collection",
            context={"feedback_data": feedback_list, "quarter": "Q4 2025"},
        )
        result = await cco.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Beacon",
            name="Beacon",
            domain="Customer Success, Experience, Support",
            llm_provider=llm_provider,
        )
        self.codename = "Beacon"

        self.capabilities = CUSTOMER_CAPABILITIES

        # Customer-specific state
        self._customers: Dict[str, Any] = {}
        self._feedback: Dict[str, Any] = {}
        self._health_scores: Dict[str, float] = {}
        self._nps_scores: List[Dict[str, Any]] = []

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        cs_mgr = CustomerSuccessManager(llm_provider=self.llm_provider)
        feedback_mgr = FeedbackManager(llm_provider=self.llm_provider)
        support_mgr = SupportManager(llm_provider=self.llm_provider)

        # Create specialists
        feedback_collector = FeedbackCollector(llm_provider=self.llm_provider)
        satisfaction_analyst = SatisfactionAnalyst(llm_provider=self.llm_provider)
        support_triager = SupportTriager(llm_provider=self.llm_provider)
        customer_advocate = CustomerAdvocate(llm_provider=self.llm_provider)
        churn_analyst = ChurnAnalyst(llm_provider=self.llm_provider)
        onboarding_spec = OnboardingSpecialist(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        cs_mgr.register_subordinate(churn_analyst)
        cs_mgr.register_subordinate(onboarding_spec)
        feedback_mgr.register_subordinate(feedback_collector)
        feedback_mgr.register_subordinate(satisfaction_analyst)
        feedback_mgr.register_subordinate(customer_advocate)
        support_mgr.register_subordinate(support_triager)

        # Register managers with Beacon
        self.register_subordinate(cs_mgr)
        self.register_subordinate(feedback_mgr)
        self.register_subordinate(support_mgr)

    def _route_to_manager(self, task_type: str) -> Optional[str]:
        """Route task to appropriate manager."""
        return MANAGER_ROUTING.get(task_type)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a customer-related task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a customer management task, routing through managers when appropriate."""
        task.status = TaskStatus.IN_PROGRESS

        # First, try to route through a manager
        manager_code = self._route_to_manager(task.task_type)
        if manager_code and manager_code in self._subordinates:
            return await self.delegate(task, manager_code)

        # Fall back to direct handlers
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        # Fallback to LLM-based handling
        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "feedback_collection": self._handle_feedback_collection,
            "satisfaction_tracking": self._handle_satisfaction_tracking,
            "support_escalation": self._handle_support_escalation,
            "customer_health_scoring": self._handle_health_scoring,
            "onboarding_optimization": self._handle_onboarding,
            "churn_analysis": self._handle_churn_analysis,
            "nps_analysis": self._handle_nps_analysis,
            "voice_of_customer": self._handle_voice_of_customer,
        }
        return handlers.get(task_type)

    async def _handle_feedback_collection(self, task: Task) -> TaskResult:
        """Collect and categorize customer feedback."""
        feedback_data = task.context.get("feedback_data", [])
        source = task.context.get("source", "mixed")
        product_id = task.context.get("product_id", "")

        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider for feedback analysis",
            )

        prompt = f"""As the Beacon (Beacon), analyze customer feedback.

Feedback Data:
{feedback_data}

Source: {source}
Product: {product_id}
Context: {task.description}

Analyze and categorize the feedback:

1. FEEDBACK SUMMARY
   - Total feedback items: count
   - Sources breakdown
   - Time period covered

2. CATEGORIZATION
   - Feature Requests: [list with frequency]
   - Bug Reports: [list with severity]
   - Usability Issues: [list]
   - Praise/Positive: [list]
   - General Feedback: [list]

3. SENTIMENT ANALYSIS
   - Overall sentiment: Positive/Neutral/Negative with score
   - Sentiment trends
   - Key emotional drivers

4. PRIORITY RECOMMENDATIONS
   - High priority items (action required)
   - Medium priority items
   - Low priority/nice-to-have

5. ACTIONABLE INSIGHTS
   - Top 3 feature requests for Blueprint (Blueprint)
   - Top 3 issues for Forge (Forge)
   - Customer pain points

6. VOICE OF CUSTOMER QUOTES
   - Select impactful quotes for stakeholders"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Feedback collection failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "collection_type": "feedback_collection",
                "source": source,
                "product_id": product_id,
                "analysis": response,
                "collected_at": _utcnow().isoformat(),
            },
            metrics={"task_type": "feedback_collection"},
        )

    async def _handle_satisfaction_tracking(self, task: Task) -> TaskResult:
        """Track customer satisfaction metrics."""
        metrics_data = task.context.get("metrics", {})
        period = task.context.get("period", "monthly")
        product_id = task.context.get("product_id", "")

        prompt = f"""As the Beacon (Beacon), track satisfaction metrics.

Metrics Data:
{metrics_data}

Period: {period}
Product: {product_id}
Context: {task.description}

Provide satisfaction report:

1. KEY METRICS SUMMARY
   - NPS Score: [score] (trend: up/down/stable)
   - CSAT Score: [score] (trend)
   - CES Score: [score] (trend)
   - Response Rate: [percentage]

2. NPS BREAKDOWN
   - Promoters (9-10): X%
   - Passives (7-8): X%
   - Detractors (0-6): X%

3. TREND ANALYSIS
   - Month-over-month changes
   - Notable shifts
   - Seasonal patterns

4. SEGMENT ANALYSIS
   - By customer tier
   - By product usage
   - By geography (if applicable)

5. KEY DRIVERS
   - What's driving satisfaction
   - What's driving dissatisfaction

6. RECOMMENDATIONS
   - Immediate actions
   - Medium-term initiatives
   - Long-term strategy

7. BENCHMARK COMPARISON
   - Industry benchmarks
   - Historical performance"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Satisfaction tracking failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "tracking_type": "satisfaction_tracking",
                "period": period,
                "product_id": product_id,
                "report": response,
                "tracked_at": _utcnow().isoformat(),
            },
        )

    async def _handle_support_escalation(self, task: Task) -> TaskResult:
        """Handle support ticket escalation and triage."""
        tickets = task.context.get("tickets", [])
        urgency = task.context.get("urgency", "normal")

        prompt = f"""As the Beacon (Beacon), handle support escalation.

Support Tickets:
{tickets}

Urgency Level: {urgency}
Context: {task.description}

Provide escalation analysis:

1. TRIAGE SUMMARY
   - Total tickets: count
   - By severity: Critical/High/Medium/Low
   - By category: Bug/Feature/Question/Other

2. ESCALATION DECISIONS
   For each critical/high ticket:
   - Ticket ID
   - Issue summary
   - Escalation target (Forge, Blueprint, etc.)
   - Urgency justification
   - Recommended response

3. PATTERN RECOGNITION
   - Common issues identified
   - Root cause hypotheses
   - Systemic problems

4. CUSTOMER IMPACT
   - Customers affected
   - Revenue at risk
   - SLA implications

5. RECOMMENDED ACTIONS
   - Immediate responses needed
   - Follow-up required
   - Process improvements

6. COMMUNICATION TEMPLATES
   - Customer acknowledgment
   - Status update template
   - Resolution template"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Support escalation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "escalation_type": "support_escalation",
                "urgency": urgency,
                "triage_results": response,
            },
        )

    async def _handle_health_scoring(self, task: Task) -> TaskResult:
        """Score customer health and identify at-risk accounts."""
        customers = task.context.get("customers", [])
        metrics = task.context.get("health_metrics", {})

        prompt = f"""As the Beacon (Beacon), score customer health.

Customers:
{customers}

Health Metrics:
{metrics}

Context: {task.description}

Provide customer health analysis:

1. HEALTH SCORE DISTRIBUTION
   - Healthy (80-100): X customers
   - Moderate (60-79): X customers
   - At Risk (40-59): X customers
   - Critical (<40): X customers

2. AT-RISK CUSTOMERS (Critical + At Risk)
   For each:
   - Customer name/ID
   - Health score
   - Risk factors
   - Recommended intervention
   - Owner/account manager

3. HEALTH DRIVERS
   - Usage frequency
   - Feature adoption
   - Support ticket volume
   - Payment history
   - Engagement metrics

4. CHURN PROBABILITY
   - Customers likely to churn
   - Warning signs
   - Time to act

5. EXPANSION OPPORTUNITIES
   - Healthy customers for upsell
   - Cross-sell opportunities
   - Advocacy candidates

6. ACTION PLAN
   - Immediate interventions
   - Proactive outreach
   - Success team priorities"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Customer health scoring failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "scoring_type": "customer_health_scoring",
                "health_analysis": response,
                "scored_at": _utcnow().isoformat(),
            },
        )

    async def _handle_onboarding(self, task: Task) -> TaskResult:
        """Optimize customer onboarding experience."""
        onboarding_data = task.context.get("onboarding_data", {})
        funnel_metrics = task.context.get("funnel_metrics", {})

        prompt = f"""As the Beacon (Beacon), optimize onboarding.

Onboarding Data:
{onboarding_data}

Funnel Metrics:
{funnel_metrics}

Context: {task.description}

Provide onboarding optimization plan:

1. CURRENT STATE ANALYSIS
   - Onboarding completion rate
   - Time to first value
   - Drop-off points
   - Common blockers

2. FUNNEL ANALYSIS
   - Step-by-step conversion
   - Where users get stuck
   - Feature adoption sequence

3. PAIN POINTS
   - User-reported issues
   - Observed friction
   - Missing guidance

4. OPTIMIZATION RECOMMENDATIONS
   - Quick wins (implement now)
   - Medium-term improvements
   - Long-term enhancements

5. SUCCESS METRICS
   - Target completion rate
   - Target time-to-value
   - Key milestones

6. IMPLEMENTATION PLAN
   - Prioritized changes
   - A/B test opportunities
   - Measurement approach"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Onboarding optimization failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "optimization_type": "onboarding_optimization",
                "recommendations": response,
            },
        )

    async def _handle_churn_analysis(self, task: Task) -> TaskResult:
        """Analyze customer churn patterns and prevention."""
        churned_customers = task.context.get("churned_customers", [])
        churn_period = task.context.get("period", "last_quarter")

        prompt = f"""As the Beacon (Beacon), analyze churn.

Churned Customers:
{churned_customers}

Period: {churn_period}
Context: {task.description}

Provide churn analysis:

1. CHURN SUMMARY
   - Total churned: count
   - Churn rate: percentage
   - Revenue impact
   - Trend vs previous period

2. CHURN REASONS
   - Primary reasons (ranked)
   - Secondary factors
   - Customer-stated vs observed

3. CUSTOMER SEGMENTS
   - By tier/value
   - By tenure
   - By product usage
   - By acquisition channel

4. EARLY WARNING SIGNALS
   - Behaviors before churn
   - Timeline to churn
   - Intervention windows

5. PREVENTION STRATEGIES
   - For each churn reason:
     - Prevention tactic
     - Success likelihood
     - Resource required

6. WIN-BACK OPPORTUNITIES
   - Re-engageable customers
   - Outreach strategy
   - Timing recommendations

7. PRODUCT FEEDBACK
   - Issues for Forge (Forge)
   - Features for Blueprint (Blueprint)"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Churn analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "churn_analysis",
                "period": churn_period,
                "analysis": response,
            },
        )

    async def _handle_nps_analysis(self, task: Task) -> TaskResult:
        """Analyze Net Promoter Score data."""
        nps_data = task.context.get("nps_data", [])
        benchmark = task.context.get("benchmark", 50)

        prompt = f"""As the Beacon (Beacon), analyze NPS.

NPS Data:
{nps_data}

Industry Benchmark: {benchmark}
Context: {task.description}

Provide NPS analysis:

1. NPS SCORE CALCULATION
   - Current NPS: [score]
   - Promoters: X% (9-10)
   - Passives: X% (7-8)
   - Detractors: X% (0-6)

2. TREND ANALYSIS
   - Historical comparison
   - Movement drivers
   - Statistical significance

3. VERBATIM ANALYSIS
   - Promoter themes (what they love)
   - Detractor themes (what needs work)
   - Passive themes (what would tip them)

4. SEGMENT INSIGHTS
   - Best performing segments
   - Worst performing segments
   - Actionable differences

5. COMPETITIVE POSITION
   - vs benchmark
   - vs historical best
   - Gap analysis

6. IMPROVEMENT PLAN
   - Convert passives to promoters
   - Reduce detractor creation
   - Amplify promoter voices

7. FOLLOW-UP RECOMMENDATIONS
   - Close the loop actions
   - Escalation triggers"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"NPS analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "nps_analysis",
                "nps_report": response,
            },
        )

    async def _handle_voice_of_customer(self, task: Task) -> TaskResult:
        """Synthesize voice of customer for product planning."""
        all_feedback = task.context.get("feedback", [])
        target_audience = task.context.get("audience", "product_team")

        prompt = f"""As the Beacon (Beacon), synthesize voice of customer.

All Customer Feedback:
{all_feedback}

Target Audience: {target_audience}
Context: {task.description}

Create Voice of Customer report:

1. AGENT SUMMARY
   - Key customer sentiment
   - Critical needs
   - Major opportunities

2. CUSTOMER PAIN POINTS (Ranked)
   - Pain point
   - Frequency
   - Impact
   - Customer quotes

3. FEATURE REQUESTS (Ranked)
   - Request
   - Demand level
   - Business impact
   - Customer quotes

4. PRAISE AND SUCCESS STORIES
   - What's working well
   - Customer wins
   - Testimonial opportunities

5. COMPETITIVE INSIGHTS
   - Competitor mentions
   - Comparative feedback
   - Switching triggers

6. PRODUCT RECOMMENDATIONS
   For Blueprint (Blueprint):
   - Priority features
   - UX improvements

   For Forge (Forge):
   - Technical issues
   - Performance concerns

7. CUSTOMER ADVISORY
   - Suggested focus groups
   - Beta candidates
   - Reference customers"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Voice of customer failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "voc_type": "voice_of_customer",
                "audience": target_audience,
                "report": response,
            },
        )

    async def _handle_with_llm(self, task: Task) -> TaskResult:
        """Handle task using LLM when no specific handler exists."""
        if not self.llm_provider:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No LLM provider and no handler for task type",
            )

        prompt = f"""As the Beacon (Beacon) - Beacon, specializing in
customer success and experience, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough customer-focused response with actionable insights."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM execution failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # State management methods

    def add_customer(self, customer_id: str, data: Dict[str, Any]) -> None:
        """Add a customer to tracking."""
        self._customers[customer_id] = {
            **data,
            "added_at": _utcnow().isoformat(),
        }

    def add_feedback(self, feedback_id: str, feedback: Dict[str, Any]) -> None:
        """Add feedback to collection."""
        self._feedback[feedback_id] = {
            **feedback,
            "received_at": _utcnow().isoformat(),
        }

    def set_health_score(self, customer_id: str, score: float) -> None:
        """Set customer health score."""
        self._health_scores[customer_id] = max(0.0, min(100.0, score))

    def record_nps(self, customer_id: str, score: int, comment: str = "") -> None:
        """Record NPS response."""
        self._nps_scores.append(
            {
                "customer_id": customer_id,
                "score": max(0, min(10, score)),
                "comment": comment,
                "recorded_at": _utcnow().isoformat(),
            }
        )

    def get_customer_status(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """Get customer status."""
        if customer_id:
            return {
                "customer": self._customers.get(customer_id),
                "health_score": self._health_scores.get(customer_id),
                "feedback": [
                    f for f in self._feedback.values() if f.get("customer_id") == customer_id
                ],
                "nps": [n for n in self._nps_scores if n.get("customer_id") == customer_id],
            }

        return {
            "total_customers": len(self._customers),
            "total_feedback": len(self._feedback),
            "nps_responses": len(self._nps_scores),
            "average_health_score": (
                sum(self._health_scores.values()) / len(self._health_scores)
                if self._health_scores
                else 0
            ),
            "capabilities": self.capabilities,
        }
