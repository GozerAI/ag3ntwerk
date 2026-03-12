"""
Echo (Echo) Manager Classes.

Middle-management layer for marketing operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CampaignManager(Manager):
    """
    Manages marketing campaigns.

    Handles campaign planning, execution, and optimization.
    Reports to Echo (Echo).

    Responsibilities:
    - Campaign planning and creation
    - Campaign execution management
    - A/B testing coordination
    - Campaign performance optimization
    """

    HANDLED_TASK_TYPES = [
        "campaign_planning",
        "campaign_execution",
        "ab_testing",
        "campaign_optimization",
        "campaign_reporting",
        "email_campaign",
        "campaign_creation",  # Generic campaign creation routing
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="CampaignMgr",
            name="Campaign Manager",
            domain="Marketing Campaigns",
            llm_provider=llm_provider,
        )
        self._campaigns: Dict[str, Any] = {}
        self._tests: Dict[str, Any] = {}

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute campaign management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "campaign_planning": self._handle_planning,
            "campaign_execution": self._handle_execution,
            "ab_testing": self._handle_ab_testing,
            "campaign_optimization": self._handle_optimization,
            "campaign_creation": self._handle_planning,  # Alias to planning
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_planning(self, task: Task) -> TaskResult:
        """Plan marketing campaign."""
        campaign_name = task.context.get("campaign_name", "")
        objectives = task.context.get("objectives", [])
        budget = task.context.get("budget", {})

        prompt = f"""As the Campaign Manager, plan marketing campaign.

Campaign: {campaign_name}
Objectives: {objectives}
Budget: {budget}
Context: {task.description}

Provide campaign plan:
1. Campaign goals and KPIs
2. Target audience definition
3. Channel selection
4. Content requirements
5. Timeline and milestones
6. Budget allocation
7. Resource needs
8. Risk mitigation"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Campaign planning failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "planning_type": "campaign_planning",
                "campaign_name": campaign_name,
                "plan": response,
            },
        )

    async def _handle_execution(self, task: Task) -> TaskResult:
        """Execute campaign."""
        campaign_id = task.context.get("campaign_id", "")
        phase = task.context.get("phase", "launch")

        prompt = f"""As the Campaign Manager, manage campaign execution.

Campaign ID: {campaign_id}
Phase: {phase}
Context: {task.description}

Provide execution guidance:
1. Current phase checklist
2. Deliverables status
3. Launch/activation steps
4. Team coordination needs
5. Quality checks
6. Go/no-go criteria
7. Contingency actions
8. Next phase prep"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Campaign execution failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "execution_type": "campaign_execution",
                "campaign_id": campaign_id,
                "phase": phase,
                "execution": response,
            },
        )

    async def _handle_ab_testing(self, task: Task) -> TaskResult:
        """Design A/B test."""
        test_name = task.context.get("test_name", "")
        hypothesis = task.context.get("hypothesis", "")
        variants = task.context.get("variants", [])

        prompt = f"""As the Campaign Manager, design A/B test.

Test Name: {test_name}
Hypothesis: {hypothesis}
Variants: {variants}
Context: {task.description}

Design A/B test:
1. Test hypothesis
2. Control and variant definitions
3. Sample size calculation
4. Duration recommendation
5. Success metrics
6. Audience targeting
7. Statistical significance threshold
8. Analysis plan"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"A/B testing design failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "test_type": "ab_testing",
                "test_name": test_name,
                "design": response,
            },
        )

    async def _handle_optimization(self, task: Task) -> TaskResult:
        """Optimize campaign."""
        campaign_id = task.context.get("campaign_id", "")
        performance_data = task.context.get("performance_data", {})

        prompt = f"""As the Campaign Manager, optimize campaign.

Campaign ID: {campaign_id}
Performance Data: {performance_data}
Context: {task.description}

Provide optimization plan:
1. Performance assessment
2. Underperforming elements
3. Optimization opportunities
4. Quick wins
5. Medium-term improvements
6. Budget reallocation
7. Creative refreshes
8. Targeting refinements"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Campaign optimization failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "optimization_type": "campaign_optimization",
                "campaign_id": campaign_id,
                "plan": response,
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Campaign Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide campaign-focused analysis."""

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


class ContentManager(Manager):
    """
    Manages content marketing.

    Handles content strategy, creation, and distribution.
    Reports to Echo (Echo).

    Responsibilities:
    - Content strategy development
    - Editorial calendar management
    - Content creation coordination
    - SEO optimization
    """

    HANDLED_TASK_TYPES = [
        "content_strategy",
        "editorial_planning",
        "content_creation",
        "seo_optimization",
        "content_distribution",
        "content_performance",
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="ContentMgr",
            name="Content Manager",
            domain="Content Marketing",
            llm_provider=llm_provider,
        )
        self._content_library: Dict[str, Any] = {}
        self._calendar: Dict[str, Any] = {}

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute content management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "content_strategy": self._handle_strategy,
            "editorial_planning": self._handle_editorial,
            "content_creation": self._handle_creation,
            "seo_optimization": self._handle_seo,
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_strategy(self, task: Task) -> TaskResult:
        """Develop content strategy."""
        audience = task.context.get("audience", "")
        goals = task.context.get("goals", [])

        prompt = f"""As the Content Manager, develop content strategy.

Target Audience: {audience}
Goals: {goals}
Context: {task.description}

Develop content strategy:
1. Content pillars
2. Content types and formats
3. Audience personas
4. Value proposition per content type
5. Distribution channels
6. Content calendar framework
7. Resource requirements
8. Success metrics"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Content strategy failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "strategy_type": "content_strategy",
                "strategy": response,
            },
        )

    async def _handle_editorial(self, task: Task) -> TaskResult:
        """Plan editorial calendar."""
        period = task.context.get("period", "monthly")
        themes = task.context.get("themes", [])

        prompt = f"""As the Content Manager, plan editorial calendar.

Period: {period}
Themes: {themes}
Context: {task.description}

Create editorial plan:
1. Content themes
2. Publication schedule
3. Content formats
4. Author assignments
5. Review workflow
6. Promotion schedule
7. Key dates and events
8. Buffer content"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Editorial planning failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "planning_type": "editorial_planning",
                "period": period,
                "plan": response,
            },
        )

    async def _handle_creation(self, task: Task) -> TaskResult:
        """Coordinate content creation."""
        content_type = task.context.get("content_type", "")
        topic = task.context.get("topic", "")
        brief = task.context.get("brief", {})

        prompt = f"""As the Content Manager, coordinate content creation.

Content Type: {content_type}
Topic: {topic}
Brief: {brief}
Context: {task.description}

Provide content guidance:
1. Content brief expansion
2. Key messages
3. Target keywords
4. Outline/structure
5. Research requirements
6. Visual/media needs
7. Call-to-action
8. Review criteria"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Content creation coordination failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "creation_type": "content_creation",
                "content_type": content_type,
                "topic": topic,
                "guidance": response,
            },
        )

    async def _handle_seo(self, task: Task) -> TaskResult:
        """Optimize for SEO."""
        content = task.context.get("content", "")
        keywords = task.context.get("keywords", [])

        prompt = f"""As the Content Manager, optimize for SEO.

Content: {content[:500] if content else 'Provide content'}
Target Keywords: {keywords}
Context: {task.description}

Provide SEO optimization:
1. Keyword analysis
2. Title optimization
3. Meta description
4. Header structure (H1, H2, H3)
5. Internal linking opportunities
6. Content length recommendations
7. Readability improvements
8. Technical SEO checklist"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"SEO optimization failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "optimization_type": "seo_optimization",
                "keywords": keywords,
                "optimization": response,
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Content Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide content-focused analysis."""

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


class BrandManager(Manager):
    """
    Manages brand strategy and assets.

    Handles brand identity, messaging, and guidelines.
    Reports to Echo (Echo).

    Responsibilities:
    - Brand identity management
    - Messaging framework development
    - Brand guidelines enforcement
    - Brand health monitoring
    """

    HANDLED_TASK_TYPES = [
        "brand_identity",
        "messaging_framework",
        "brand_guidelines",
        "brand_health",
        "brand_audit",
        "brand_positioning",
        "brand_strategy",  # Generic brand strategy routing
        "market_analysis",  # Market analysis routing
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="BrandMgr",
            name="Brand Manager",
            domain="Brand Strategy",
            llm_provider=llm_provider,
        )
        self._brand_assets: Dict[str, Any] = {}
        self._guidelines: Dict[str, Any] = {}

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute brand management task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "brand_identity": self._handle_identity,
            "messaging_framework": self._handle_messaging,
            "brand_guidelines": self._handle_guidelines,
            "brand_health": self._handle_health,
            "brand_strategy": self._handle_identity,  # Alias to identity
            "market_analysis": self._handle_health,  # Use health analysis as base
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_identity(self, task: Task) -> TaskResult:
        """Develop brand identity."""
        brand_name = task.context.get("brand_name", "")
        values = task.context.get("values", [])

        prompt = f"""As the Brand Manager, develop brand identity.

Brand Name: {brand_name}
Values: {values}
Context: {task.description}

Develop brand identity:
1. Brand purpose and mission
2. Brand vision
3. Core values
4. Brand personality
5. Brand voice and tone
6. Visual identity elements
7. Brand story
8. Emotional benefits"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Brand identity development failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "identity_type": "brand_identity",
                "brand_name": brand_name,
                "identity": response,
            },
        )

    async def _handle_messaging(self, task: Task) -> TaskResult:
        """Create messaging framework."""
        audience = task.context.get("audience", "")
        key_messages = task.context.get("key_messages", [])

        prompt = f"""As the Brand Manager, create messaging framework.

Target Audience: {audience}
Key Messages: {key_messages}
Context: {task.description}

Create messaging framework:
1. Core value proposition
2. Key messages by audience
3. Proof points
4. Elevator pitch
5. Taglines and slogans
6. Message hierarchy
7. Competitive differentiation
8. Usage guidelines"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Messaging framework failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "framework_type": "messaging_framework",
                "framework": response,
            },
        )

    async def _handle_guidelines(self, task: Task) -> TaskResult:
        """Create brand guidelines."""
        brand = task.context.get("brand", {})
        scope = task.context.get("scope", "full")

        prompt = f"""As the Brand Manager, create brand guidelines.

Brand: {brand}
Scope: {scope}
Context: {task.description}

Create brand guidelines:
1. Logo usage rules
2. Color palette
3. Typography system
4. Imagery style
5. Voice and tone guide
6. Do's and don'ts
7. Application examples
8. Approval process"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Brand guidelines creation failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "guidelines_type": "brand_guidelines",
                "scope": scope,
                "guidelines": response,
            },
        )

    async def _handle_health(self, task: Task) -> TaskResult:
        """Assess brand health."""
        metrics = task.context.get("metrics", {})
        benchmarks = task.context.get("benchmarks", {})

        prompt = f"""As the Brand Manager, assess brand health.

Brand Metrics: {metrics}
Benchmarks: {benchmarks}
Context: {task.description}

Provide brand health assessment:
1. Brand awareness metrics
2. Brand perception scores
3. Net Promoter Score
4. Brand equity valuation
5. Competitive positioning
6. Sentiment analysis
7. Recommendations
8. Action plan"""

        try:
            response = await self.reason(prompt, task.context)
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Brand health assessment failed: {e}",
            )

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "assessment_type": "brand_health",
                "assessment": response,
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Brand Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide brand-focused analysis."""

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


class SocialDistributionManager(Manager):
    """
    Manages social media distribution through real platform APIs.

    Bridges the Echo's social media strategy to actual platform
    publishing via the SocialDistributionGateway.
    Reports to Echo (Echo).

    Responsibilities:
    - Multi-platform content distribution
    - Content adaptation per platform
    - Social media analytics retrieval
    - Post scheduling and lifecycle management
    """

    HANDLED_TASK_TYPES = [
        "social_distribute",
        "social_publish",
        "social_schedule",
        "social_analytics",
        "social_metrics",
    ]

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        social_gateway=None,
    ):
        super().__init__(
            code="SocialDistMgr",
            name="Social Distribution Manager",
            domain="Social Media Distribution",
            llm_provider=llm_provider,
        )
        self._gateway = social_gateway

    @property
    def gateway(self):
        """Access the social distribution gateway."""
        return self._gateway

    @gateway.setter
    def gateway(self, value):
        """Set the social distribution gateway."""
        self._gateway = value

    def can_handle(self, task: Task) -> bool:
        """Check if this manager handles the task type."""
        return task.task_type in self.HANDLED_TASK_TYPES

    async def execute(self, task: Task) -> TaskResult:
        """Execute social distribution task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "social_distribute": self._handle_distribute,
            "social_publish": self._handle_distribute,
            "social_schedule": self._handle_schedule,
            "social_analytics": self._handle_analytics,
            "social_metrics": self._handle_metrics,
        }

        handler = handlers.get(task.task_type)
        if handler:
            return await handler(task)

        return await self._execute_with_llm(task)

    async def _handle_distribute(self, task: Task) -> TaskResult:
        """Distribute content to social platforms."""
        if not self._gateway:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="SocialDistributionGateway not configured",
            )

        from ag3ntwerk.models.social import Platform, SocialPost

        content = task.context.get("content", "")
        platforms = task.context.get("platforms", [])
        link = task.context.get("link")
        campaign_id = task.context.get("campaign_id")

        if not content:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No content provided for distribution",
            )

        # Parse platform strings to enums
        target_platforms = []
        for p in platforms:
            try:
                target_platforms.append(Platform(p))
            except ValueError:
                logger.warning("Unknown platform: %s", p)

        if not target_platforms:
            target_platforms = self._gateway.registered_platforms

        post = SocialPost(
            platform=target_platforms[0] if target_platforms else Platform.LINKEDIN,
            content=content,
            link=link,
            campaign_id=campaign_id,
        )

        try:
            results = await self._gateway.distribute(
                post,
                platforms=target_platforms,
                adapt_content=self.llm_provider is not None,
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                output={
                    "distribution_type": "social_distribute",
                    "results": {p.value: r for p, r in results.items()},
                    "platforms_targeted": [p.value for p in target_platforms],
                },
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Social distribution failed: {e}",
            )

    async def _handle_schedule(self, task: Task) -> TaskResult:
        """Schedule content for later distribution."""
        if not self._gateway:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="SocialDistributionGateway not configured",
            )

        from ag3ntwerk.models.social import Platform, SocialPost

        content = task.context.get("content", "")
        platforms = task.context.get("platforms", [])
        scheduled_time = task.context.get("scheduled_time")

        if not scheduled_time:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No scheduled_time provided",
            )

        if isinstance(scheduled_time, str):
            scheduled_time = datetime.fromisoformat(scheduled_time)

        target_platforms = []
        for p in platforms:
            try:
                target_platforms.append(Platform(p))
            except ValueError:
                pass

        if not target_platforms:
            target_platforms = self._gateway.registered_platforms

        post = SocialPost(
            platform=target_platforms[0] if target_platforms else Platform.LINKEDIN,
            content=content,
            scheduled_time=scheduled_time,
        )

        try:
            results = await self._gateway.distribute(
                post,
                platforms=target_platforms,
                adapt_content=False,
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                output={
                    "schedule_type": "social_schedule",
                    "scheduled_time": scheduled_time.isoformat(),
                    "results": {p.value: r for p, r in results.items()},
                },
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Social scheduling failed: {e}",
            )

    async def _handle_analytics(self, task: Task) -> TaskResult:
        """Get analytics for a specific post."""
        if not self._gateway:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="SocialDistributionGateway not configured",
            )

        from ag3ntwerk.models.social import Platform

        post_id = task.context.get("post_id", "")
        platform = task.context.get("platform", "")

        if not post_id or not platform:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="post_id and platform are required",
            )

        try:
            platform_enum = Platform(platform)
        except ValueError:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Unknown platform: {platform}",
            )

        analytics = await self._gateway.get_post_analytics(post_id, platform_enum)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analytics_type": "social_analytics",
                "post_id": post_id,
                "platform": platform,
                "analytics": analytics,
            },
        )

    async def _handle_metrics(self, task: Task) -> TaskResult:
        """Get profile-level metrics from all platforms."""
        if not self._gateway:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="SocialDistributionGateway not configured",
            )

        metrics = await self._gateway.get_all_metrics()

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "metrics_type": "social_metrics",
                "platforms": {p.value: m for p, m in metrics.items()},
            },
        )

    async def _execute_with_llm(self, task: Task) -> TaskResult:
        """Execute task using LLM."""
        prompt = f"""As the Social Distribution Manager, handle this task:

Task: {task.description}
Type: {task.task_type}
Context: {task.context}

Provide social-distribution-focused analysis."""

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
