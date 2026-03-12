"""
Compass (Compass) Agent - Compass.

Codename: Compass
Core function: Set direction, make tradeoffs, and maintain strategic coherence.

The Compass handles all strategy and content-related tasks:
- Market analysis and competitive intelligence
- Strategic planning and roadmaps
- Content strategy and creation
- Brand positioning and messaging
- Go-to-market planning

Sphere of influence: Market positioning, competitive strategy, strategic planning
cycles, portfolio strategy, KPI selection, strategic narratives.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider

from ag3ntwerk.agents.compass.managers import (
    StrategicPlanningManager,
    MarketIntelligenceManager,
    ContentStrategyManager,
    GoToMarketManager,
)
from ag3ntwerk.agents.compass.specialists import (
    StrategyAnalyst,
    MarketResearcher,
    ContentStrategist,
    BrandStrategist,
    GTMSpecialist,
)


# Strategy task types this agent can handle
STRATEGY_CAPABILITIES = [
    "market_analysis",
    "competitive_analysis",
    "strategic_planning",
    "content_strategy",
    "content_creation",
    "brand_positioning",
    "go_to_market",
    "trend_analysis",
    "swot_analysis",
    "opportunity_assessment",
    "messaging_framework",
    "value_proposition",
]


class Compass(Manager):
    """
    Compass - Compass.

    The Compass is responsible for all strategic planning and content
    operations within the ag3ntwerk system.

    Codename: Compass

    Core Responsibilities:
    - Market and competitive analysis
    - Strategic planning and roadmaps
    - Content strategy and creation
    - Brand positioning and messaging
    - Go-to-market planning

    Example:
        ```python
        cso = Compass(llm_provider=llm)

        task = Task(
            description="Analyze competitor landscape for AI assistants",
            task_type="competitive_analysis",
            context={"industry": "AI/ML", "focus": "developer tools"},
        )
        result = await cso.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Compass",
            name="Compass",
            domain="Strategy, Content, Market Analysis",
            llm_provider=llm_provider,
        )
        self.codename = "Compass"

        self.capabilities = STRATEGY_CAPABILITIES

        # Strategy-specific state
        self._market_insights: Dict[str, Any] = {}
        self._content_calendar: List[Dict[str, Any]] = []
        self._strategic_initiatives: Dict[str, Any] = {}

        # Initialize managers and specialists hierarchy
        self._init_managers()

    def can_handle(self, task: Task) -> bool:
        """Check if this is a strategy-related task."""
        return task.task_type in self.capabilities

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        spm = StrategicPlanningManager(llm_provider=self.llm_provider)
        mim = MarketIntelligenceManager(llm_provider=self.llm_provider)
        csm = ContentStrategyManager(llm_provider=self.llm_provider)
        gtmm = GoToMarketManager(llm_provider=self.llm_provider)

        # Create specialists
        strategy_analyst = StrategyAnalyst(llm_provider=self.llm_provider)
        market_researcher = MarketResearcher(llm_provider=self.llm_provider)
        content_strategist = ContentStrategist(llm_provider=self.llm_provider)
        brand_strategist = BrandStrategist(llm_provider=self.llm_provider)
        gtm_specialist = GTMSpecialist(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        spm.register_subordinate(strategy_analyst)
        mim.register_subordinate(market_researcher)
        csm.register_subordinate(content_strategist)
        csm.register_subordinate(brand_strategist)
        gtmm.register_subordinate(gtm_specialist)

        # Register managers with Compass
        self.register_subordinate(spm)
        self.register_subordinate(mim)
        self.register_subordinate(csm)
        self.register_subordinate(gtmm)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a strategy task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            "market_analysis": self._handle_market_analysis,
            "competitive_analysis": self._handle_competitive_analysis,
            "strategic_planning": self._handle_strategic_planning,
            "content_strategy": self._handle_content_strategy,
            "content_creation": self._handle_content_creation,
            "swot_analysis": self._handle_swot_analysis,
        }
        return handlers.get(task_type)

    async def _handle_market_analysis(self, task: Task) -> TaskResult:
        """Perform market analysis."""
        market = task.context.get("market", "general")
        scope = task.context.get("scope", "comprehensive")

        prompt = f"""As the Compass, perform a market analysis.

Market: {market}
Scope: {scope}
Description: {task.description}
Context: {task.context}

Provide a comprehensive market analysis including:
1. Market size and growth trends
2. Key segments and their characteristics
3. Major players and market shares
4. Entry barriers and opportunities
5. Regulatory considerations
6. Future outlook and predictions"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Market analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "market",
                "market": market,
                "analysis": response,
            },
        )

    async def _handle_competitive_analysis(self, task: Task) -> TaskResult:
        """Analyze competitive landscape."""
        industry = task.context.get("industry", "technology")
        competitors = task.context.get("competitors", [])

        prompt = f"""As the Compass, perform a competitive analysis.

Industry: {industry}
Known Competitors: {competitors if competitors else 'Identify key competitors'}
Description: {task.description}
Context: {task.context}

Provide a competitive analysis including:
1. Key competitors and their positioning
2. Strengths and weaknesses of each
3. Competitive advantages and differentiators
4. Market positioning map
5. Competitive threats and opportunities
6. Recommended strategic responses"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Market analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "competitive",
                "industry": industry,
                "analysis": response,
            },
        )

    async def _handle_strategic_planning(self, task: Task) -> TaskResult:
        """Create strategic plans."""
        timeframe = task.context.get("timeframe", "1 year")
        focus_areas = task.context.get("focus_areas", [])

        prompt = f"""As the Compass, develop a strategic plan.

Timeframe: {timeframe}
Focus Areas: {focus_areas if focus_areas else 'Identify key focus areas'}
Description: {task.description}
Context: {task.context}

Develop a strategic plan including:
1. Vision and strategic objectives
2. Key initiatives and priorities
3. Resource requirements
4. Success metrics and KPIs
5. Risk assessment and mitigation
6. Implementation roadmap
7. Dependencies and critical path"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Strategic planning failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "plan_type": "strategic",
                "timeframe": timeframe,
                "plan": response,
            },
        )

    async def _handle_content_strategy(self, task: Task) -> TaskResult:
        """Develop content strategy."""
        audience = task.context.get("audience", "general")
        channels = task.context.get("channels", [])

        prompt = f"""As the Compass, develop a content strategy.

Target Audience: {audience}
Channels: {channels if channels else 'Recommend appropriate channels'}
Description: {task.description}
Context: {task.context}

Develop a content strategy including:
1. Audience personas and needs
2. Content pillars and themes
3. Channel strategy and mix
4. Content calendar framework
5. Tone and voice guidelines
6. Measurement and optimization approach"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Content strategy development failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "strategy_type": "content",
                "audience": audience,
                "strategy": response,
            },
        )

    async def _handle_content_creation(self, task: Task) -> TaskResult:
        """Create content."""
        content_type = task.context.get("content_type", "article")
        tone = task.context.get("tone", "professional")

        prompt = f"""As the Compass, create content.

Content Type: {content_type}
Tone: {tone}
Description: {task.description}
Context: {task.context}

Create {content_type} content that:
1. Engages the target audience
2. Communicates key messages clearly
3. Aligns with brand voice
4. Includes relevant calls-to-action
5. Is optimized for the intended channel"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Content creation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "content_type": content_type,
                "content": response,
            },
        )

    async def _handle_swot_analysis(self, task: Task) -> TaskResult:
        """Perform SWOT analysis."""
        subject = task.context.get("subject", "organization")

        prompt = f"""As the Compass, perform a SWOT analysis.

Subject: {subject}
Description: {task.description}
Context: {task.context}

Provide a comprehensive SWOT analysis:

STRENGTHS:
- Internal capabilities and advantages

WEAKNESSES:
- Internal limitations and gaps

OPPORTUNITIES:
- External factors that could be leveraged

THREATS:
- External factors that could pose challenges

Include strategic implications and recommended actions for each quadrant."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"SWOT analysis failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": "swot",
                "subject": subject,
                "analysis": response,
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

        prompt = f"""As the Compass (Compass) specializing in strategy and content,
handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough strategy-focused response."""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"LLM handling failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    def add_market_insight(self, key: str, insight: Any) -> None:
        """Add a market insight."""
        self._market_insights[key] = insight

    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status."""
        return {
            "market_insights": len(self._market_insights),
            "content_calendar_items": len(self._content_calendar),
            "strategic_initiatives": len(self._strategic_initiatives),
            "capabilities": self.capabilities,
        }
