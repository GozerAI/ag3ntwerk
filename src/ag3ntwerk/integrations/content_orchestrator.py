"""
Content Orchestrator Bridge - Integration between ag3ntwerk and AI Platform.

This module provides a bridge connecting ag3ntwerk agents to the
ai-platform-unified content generation systems:
- Blueprint-based ebook generation
- Workflow automation
- Content orchestration

Primary users:
- Echo (Echo): Marketing content, campaigns
- Beacon (Beacon): Customer communications
- Blueprint (Blueprint): Product documentation

Features:
- Blueprint-driven content generation
- Multi-step workflow execution
- Content status tracking
- Quality scoring
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content that can be generated."""

    EBOOK = "ebook"
    BLOG_POST = "blog_post"
    EMAIL_CAMPAIGN = "email_campaign"
    SOCIAL_MEDIA = "social_media"
    PRODUCT_DESCRIPTION = "product_description"
    LANDING_PAGE = "landing_page"
    NEWSLETTER = "newsletter"
    PRESS_RELEASE = "press_release"
    CASE_STUDY = "case_study"
    WHITE_PAPER = "white_paper"
    VIDEO_SCRIPT = "video_script"
    AD_COPY = "ad_copy"


class ContentStatus(Enum):
    """Status of content generation."""

    PENDING = "pending"
    RESEARCHING = "researching"
    OUTLINING = "outlining"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    EDITING = "editing"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WorkflowStatus(Enum):
    """Status of workflow execution."""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ContentRequest:
    """Request for content generation."""

    id: UUID = field(default_factory=uuid4)
    content_type: ContentType = ContentType.BLOG_POST
    title: str = ""
    description: str = ""
    target_audience: Optional[str] = None
    tone: str = "professional"
    keywords: List[str] = field(default_factory=list)
    length: str = "medium"  # short, medium, long
    format_requirements: Dict[str, Any] = field(default_factory=dict)
    due_date: Optional[datetime] = None
    priority: int = 5  # 1-10, higher is more urgent
    requester: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ContentPiece:
    """A generated piece of content."""

    id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)
    content_type: ContentType = ContentType.BLOG_POST
    title: str = ""
    content: str = ""
    status: ContentStatus = ContentStatus.PENDING
    quality_score: Optional[float] = None
    word_count: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "content_type": self.content_type.value,
            "title": self.title,
            "status": self.status.value,
            "quality_score": self.quality_score,
            "word_count": self.word_count,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class BlueprintSpec:
    """Specification for blueprint-based generation."""

    id: str
    name: str
    description: str
    content_type: ContentType
    template_structure: Dict[str, Any] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)
    default_settings: Dict[str, Any] = field(default_factory=dict)
    artifact_types: List[str] = field(default_factory=list)


@dataclass
class WorkflowStep:
    """A step in a content workflow."""

    id: str
    name: str
    action: str
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.QUEUED
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ContentWorkflow:
    """A content generation workflow."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.QUEUED
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentOrchestratorBridge:
    """
    Bridge between ag3ntwerk agents and AI Platform content systems.

    This bridge enables:
    1. Echo - Marketing content generation
    2. Beacon - Customer communications
    3. Blueprint - Product documentation

    Usage:
        bridge = ContentOrchestratorBridge()
        bridge.connect_platform(ai_platform)

        # Request content
        request = ContentRequest(
            content_type=ContentType.BLOG_POST,
            title="AI in Healthcare",
            target_audience="Healthcare professionals",
        )
        content = await bridge.generate_content(request)

        # Run workflow
        workflow = await bridge.run_workflow("blog_pipeline", context)
    """

    # Quality thresholds
    QUALITY_THRESHOLD_PUBLISH = 0.8
    QUALITY_THRESHOLD_REVIEW = 0.6

    # Content length guidelines (word counts)
    LENGTH_GUIDELINES = {
        "short": {"min": 100, "max": 500},
        "medium": {"min": 500, "max": 1500},
        "long": {"min": 1500, "max": 5000},
    }

    def __init__(
        self,
        cmo: Optional[Any] = None,
        cco: Optional[Any] = None,
        cpo: Optional[Any] = None,
    ):
        """
        Initialize the Content Orchestrator bridge.

        Args:
            cmo: Optional Echo instance
            cco: Optional Beacon instance
            cpo: Optional Blueprint instance
        """
        self._cmo = cmo
        self._cco = cco
        self._cpo = cpo

        # AI Platform connection
        self._ai_platform: Optional[Any] = None
        self._content_orchestrator: Optional[Any] = None
        self._blueprint_engine: Optional[Any] = None

        # Content storage
        self._requests: Dict[UUID, ContentRequest] = {}
        self._content: Dict[UUID, ContentPiece] = {}
        self._workflows: Dict[UUID, ContentWorkflow] = {}

        # Blueprints registry
        self._blueprints: Dict[str, BlueprintSpec] = {}

        # Workflow templates
        self._workflow_templates: Dict[str, List[WorkflowStep]] = {
            "blog_pipeline": [
                WorkflowStep(id="research", name="Research Topic", action="research"),
                WorkflowStep(
                    id="outline", name="Create Outline", action="outline", depends_on=["research"]
                ),
                WorkflowStep(
                    id="draft", name="Write Draft", action="draft", depends_on=["outline"]
                ),
                WorkflowStep(
                    id="review", name="Review Draft", action="review", depends_on=["draft"]
                ),
                WorkflowStep(id="edit", name="Edit Content", action="edit", depends_on=["review"]),
                WorkflowStep(id="publish", name="Publish", action="publish", depends_on=["edit"]),
            ],
            "email_campaign": [
                WorkflowStep(id="segment", name="Define Segment", action="segment"),
                WorkflowStep(
                    id="subject",
                    name="Generate Subjects",
                    action="subject_lines",
                    depends_on=["segment"],
                ),
                WorkflowStep(
                    id="body", name="Write Body", action="email_body", depends_on=["subject"]
                ),
                WorkflowStep(
                    id="preview", name="Generate Preview", action="preview", depends_on=["body"]
                ),
                WorkflowStep(
                    id="test", name="A/B Test Setup", action="ab_test", depends_on=["preview"]
                ),
            ],
            "ebook_pipeline": [
                WorkflowStep(id="blueprint", name="Load Blueprint", action="load_blueprint"),
                WorkflowStep(
                    id="research",
                    name="Research Topics",
                    action="deep_research",
                    depends_on=["blueprint"],
                ),
                WorkflowStep(
                    id="outline",
                    name="Create Book Outline",
                    action="book_outline",
                    depends_on=["research"],
                ),
                WorkflowStep(
                    id="chapters",
                    name="Generate Chapters",
                    action="generate_chapters",
                    depends_on=["outline"],
                ),
                WorkflowStep(
                    id="continuity",
                    name="Check Continuity",
                    action="continuity_check",
                    depends_on=["chapters"],
                ),
                WorkflowStep(
                    id="edit",
                    name="Editorial Review",
                    action="editorial_review",
                    depends_on=["continuity"],
                ),
                WorkflowStep(
                    id="format", name="Format Output", action="format_ebook", depends_on=["edit"]
                ),
            ],
        }

        # Metrics
        self._metrics = {
            "content_requests": 0,
            "content_generated": 0,
            "workflows_started": 0,
            "workflows_completed": 0,
            "total_words_generated": 0,
            "avg_quality_score": 0.0,
        }

        logger.info("ContentOrchestratorBridge initialized")

    def connect_platform(
        self,
        ai_platform: Any,
        content_orchestrator: Optional[Any] = None,
        blueprint_engine: Optional[Any] = None,
    ) -> None:
        """
        Connect to AI Platform systems.

        Args:
            ai_platform: UnifiedAIPlatform instance
            content_orchestrator: Optional ContentOrchestrator instance
            blueprint_engine: Optional BlueprintEbookPipeline instance
        """
        self._ai_platform = ai_platform
        self._content_orchestrator = content_orchestrator
        self._blueprint_engine = blueprint_engine
        logger.info("Connected to AI Platform")

    def connect_executives(
        self,
        cmo: Any = None,
        cco: Any = None,
        cpo: Any = None,
    ) -> None:
        """Connect ag3ntwerk agents to the bridge."""
        if cmo:
            self._cmo = cmo
            logger.info("Connected Echo (Echo) to content orchestrator")
        if cco:
            self._cco = cco
            logger.info("Connected Beacon (Beacon) to content orchestrator")
        if cpo:
            self._cpo = cpo
            logger.info("Connected Blueprint (Blueprint) to content orchestrator")

    def register_blueprint(self, blueprint: BlueprintSpec) -> None:
        """Register a content blueprint."""
        self._blueprints[blueprint.id] = blueprint
        logger.info(f"Registered blueprint: {blueprint.id}")

    async def generate_content(
        self,
        request: ContentRequest,
    ) -> ContentPiece:
        """
        Generate content based on a request.

        Args:
            request: Content generation request

        Returns:
            Generated ContentPiece
        """
        self._metrics["content_requests"] += 1
        self._requests[request.id] = request

        # Create initial content piece
        content = ContentPiece(
            request_id=request.id,
            content_type=request.content_type,
            title=request.title,
            status=ContentStatus.PENDING,
        )

        # Use AI Platform if available
        if self._ai_platform:
            try:
                content.status = ContentStatus.DRAFTING

                # Build prompt based on content type
                prompt = self._build_generation_prompt(request)

                # Generate content via AI Platform
                result = await self._ai_platform.query(
                    prompt=prompt,
                    strategy="default",
                )

                content.content = result if isinstance(result, str) else str(result)
                content.word_count = len(content.content.split())
                content.status = ContentStatus.REVIEWING

                # Score quality
                content.quality_score = await self._score_content(content)

                if content.quality_score >= self.QUALITY_THRESHOLD_PUBLISH:
                    content.status = ContentStatus.APPROVED
                elif content.quality_score >= self.QUALITY_THRESHOLD_REVIEW:
                    content.status = ContentStatus.REVIEWING
                else:
                    content.status = ContentStatus.EDITING

            except Exception as e:
                logger.error(f"Content generation failed: {e}")
                content.status = ContentStatus.PENDING
                content.metadata["error"] = str(e)
        else:
            # Placeholder content when no platform
            content.content = f"[Generated content for: {request.title}]"
            content.word_count = 5
            content.status = ContentStatus.PENDING

        content.updated_at = datetime.now(timezone.utc)
        self._content[content.id] = content

        self._metrics["content_generated"] += 1
        self._metrics["total_words_generated"] += content.word_count

        return content

    def _build_generation_prompt(self, request: ContentRequest) -> str:
        """Build generation prompt based on content request."""
        length_guide = self.LENGTH_GUIDELINES.get(request.length, self.LENGTH_GUIDELINES["medium"])

        prompt = f"""Generate {request.content_type.value.replace('_', ' ')} content.

Title: {request.title}
Description: {request.description}

Target Audience: {request.target_audience or 'General audience'}
Tone: {request.tone}
Keywords to include: {', '.join(request.keywords) if request.keywords else 'None specified'}

Length Guidelines:
- Minimum words: {length_guide['min']}
- Maximum words: {length_guide['max']}

Additional Requirements:
{self._format_requirements(request.format_requirements)}

Generate high-quality, engaging content that:
1. Is well-structured and easy to read
2. Addresses the target audience appropriately
3. Includes all specified keywords naturally
4. Follows the tone guidelines
5. Is original and valuable"""

        return prompt

    def _format_requirements(self, requirements: Dict[str, Any]) -> str:
        """Format requirements for prompt."""
        if not requirements:
            return "- No additional requirements"

        lines = []
        for key, value in requirements.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    async def _score_content(self, content: ContentPiece) -> float:
        """Score content quality."""
        score = 0.5  # Base score

        # Length scoring
        request = self._requests.get(content.request_id)
        if request:
            length_guide = self.LENGTH_GUIDELINES.get(
                request.length, self.LENGTH_GUIDELINES["medium"]
            )
            if length_guide["min"] <= content.word_count <= length_guide["max"]:
                score += 0.2
            elif content.word_count >= length_guide["min"] * 0.8:
                score += 0.1

        # Structure scoring (has paragraphs, headings, etc.)
        if "\n\n" in content.content:  # Has paragraphs
            score += 0.1
        if "#" in content.content or "**" in content.content:  # Has formatting
            score += 0.1

        # Use AI Platform for deeper scoring if available
        if self._ai_platform and request:
            try:
                score_prompt = f"""Rate the quality of this {content.content_type.value} content on a scale of 0-1.

Content:
{content.content[:2000]}

Criteria:
- Relevance to topic: {request.title}
- Writing quality and clarity
- Engagement and readability
- Structure and organization
- Value to target audience: {request.target_audience}

Return only a decimal number between 0 and 1."""

                result = await self._ai_platform.query(score_prompt)
                try:
                    ai_score = float(str(result).strip())
                    score = (score + ai_score) / 2
                except ValueError:
                    pass
            except Exception as e:
                # AI scoring failed, use heuristic score only
                logger.debug(f"AI content scoring failed: {e}")

        return min(1.0, max(0.0, score))

    async def run_workflow(
        self,
        workflow_name: str,
        context: Dict[str, Any],
    ) -> ContentWorkflow:
        """
        Run a content generation workflow.

        Args:
            workflow_name: Name of workflow template
            context: Workflow context and inputs

        Returns:
            ContentWorkflow with execution status
        """
        if workflow_name not in self._workflow_templates:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        # Create workflow instance
        template_steps = self._workflow_templates[workflow_name]
        workflow = ContentWorkflow(
            name=workflow_name,
            steps=[
                WorkflowStep(
                    id=s.id,
                    name=s.name,
                    action=s.action,
                    config=s.config.copy(),
                    depends_on=s.depends_on.copy(),
                )
                for s in template_steps
            ],
            context=context,
        )

        self._workflows[workflow.id] = workflow
        self._metrics["workflows_started"] += 1

        # Execute workflow
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)

        try:
            for i, step in enumerate(workflow.steps):
                workflow.current_step = i

                # Check dependencies
                deps_met = all(
                    self._get_step_by_id(workflow, dep).status == WorkflowStatus.COMPLETED
                    for dep in step.depends_on
                )

                if not deps_met:
                    step.status = WorkflowStatus.FAILED
                    step.error = "Dependencies not met"
                    continue

                # Execute step
                step.status = WorkflowStatus.RUNNING
                try:
                    result = await self._execute_workflow_step(step, workflow.context)
                    step.result = result
                    step.status = WorkflowStatus.COMPLETED

                    # Update context with result
                    workflow.context[f"{step.id}_result"] = result
                except Exception as e:
                    step.status = WorkflowStatus.FAILED
                    step.error = str(e)
                    logger.error(f"Workflow step {step.id} failed: {e}")

            # Check final status
            all_completed = all(s.status == WorkflowStatus.COMPLETED for s in workflow.steps)
            workflow.status = WorkflowStatus.COMPLETED if all_completed else WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)

            if all_completed:
                self._metrics["workflows_completed"] += 1

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["error"] = str(e)
            logger.error(f"Workflow {workflow.name} failed: {e}")

        return workflow

    def _get_step_by_id(self, workflow: ContentWorkflow, step_id: str) -> WorkflowStep:
        """Get workflow step by ID."""
        for step in workflow.steps:
            if step.id == step_id:
                return step
        raise ValueError(f"Step not found: {step_id}")

    async def _execute_workflow_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a single workflow step."""
        action = step.action

        # Map actions to handlers
        handlers: Dict[str, Callable] = {
            "research": self._action_research,
            "outline": self._action_outline,
            "draft": self._action_draft,
            "review": self._action_review,
            "edit": self._action_edit,
            "publish": self._action_publish,
            "segment": self._action_segment,
            "subject_lines": self._action_subject_lines,
            "email_body": self._action_email_body,
            "load_blueprint": self._action_load_blueprint,
            "deep_research": self._action_deep_research,
            "book_outline": self._action_book_outline,
            "generate_chapters": self._action_generate_chapters,
            "continuity_check": self._action_continuity_check,
            "editorial_review": self._action_editorial_review,
            "format_ebook": self._action_format_ebook,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(context, step.config)

        return {"status": "completed", "action": action}

    # Workflow action handlers
    async def _action_research(self, context: Dict, config: Dict) -> Dict:
        """Research action handler."""
        topic = context.get("topic", context.get("title", ""))
        if self._ai_platform:
            result = await self._ai_platform.research(topic)
            return {"research": result}
        return {"research": f"Research on: {topic}"}

    async def _action_outline(self, context: Dict, config: Dict) -> Dict:
        """Outline action handler."""
        research = context.get("research_result", {}).get("research", "")
        return {"outline": f"Outline based on research: {research[:100]}..."}

    async def _action_draft(self, context: Dict, config: Dict) -> Dict:
        """Draft action handler."""
        outline = context.get("outline_result", {}).get("outline", "")
        return {"draft": f"Draft based on outline: {outline[:100]}..."}

    async def _action_review(self, context: Dict, config: Dict) -> Dict:
        """Review action handler."""
        return {"review": "Content reviewed", "score": 0.8}

    async def _action_edit(self, context: Dict, config: Dict) -> Dict:
        """Edit action handler."""
        return {"edited": True, "changes": 5}

    async def _action_publish(self, context: Dict, config: Dict) -> Dict:
        """Publish action handler."""
        return {"published": True, "url": "https://example.com/content"}

    async def _action_segment(self, context: Dict, config: Dict) -> Dict:
        """Segment action handler."""
        return {"segments": ["segment_1", "segment_2"]}

    async def _action_subject_lines(self, context: Dict, config: Dict) -> Dict:
        """Subject lines action handler."""
        return {"subjects": ["Subject A", "Subject B", "Subject C"]}

    async def _action_email_body(self, context: Dict, config: Dict) -> Dict:
        """Email body action handler."""
        return {"body": "Email body content..."}

    async def _action_load_blueprint(self, context: Dict, config: Dict) -> Dict:
        """Load blueprint action handler."""
        blueprint_id = context.get("blueprint_id", "default")
        if self._blueprint_engine:
            return {"blueprint": await self._blueprint_engine.load_blueprint(blueprint_id)}
        return {"blueprint_id": blueprint_id}

    async def _action_deep_research(self, context: Dict, config: Dict) -> Dict:
        """Deep research action handler."""
        return {"research": "Comprehensive research results..."}

    async def _action_book_outline(self, context: Dict, config: Dict) -> Dict:
        """Book outline action handler."""
        return {"chapters": ["Chapter 1", "Chapter 2", "Chapter 3"]}

    async def _action_generate_chapters(self, context: Dict, config: Dict) -> Dict:
        """Generate chapters action handler."""
        return {"chapters_generated": 3, "word_count": 15000}

    async def _action_continuity_check(self, context: Dict, config: Dict) -> Dict:
        """Continuity check action handler."""
        return {"continuity_score": 0.95, "issues": []}

    async def _action_editorial_review(self, context: Dict, config: Dict) -> Dict:
        """Editorial review action handler."""
        return {"reviewed": True, "quality_score": 0.88}

    async def _action_format_ebook(self, context: Dict, config: Dict) -> Dict:
        """Format ebook action handler."""
        return {"format": "epub", "file_size": "2.5MB"}

    def get_content_for_cmo(self) -> Dict[str, Any]:
        """
        Get content data formatted for Echo marketing analysis.

        Returns:
            Data structured for Echo consumption
        """
        content_by_type = {}
        for c in self._content.values():
            ct = c.content_type.value
            if ct not in content_by_type:
                content_by_type[ct] = []
            content_by_type[ct].append(c.to_dict())

        status_counts = {}
        for c in self._content.values():
            status = c.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "summary": {
                "total_content": len(self._content),
                "total_requests": len(self._requests),
                "pending_requests": len(
                    [
                        r
                        for r in self._requests.values()
                        if r.id
                        not in [
                            c.request_id
                            for c in self._content.values()
                            if c.status in [ContentStatus.APPROVED, ContentStatus.PUBLISHED]
                        ]
                    ]
                ),
            },
            "by_type": {ct: len(items) for ct, items in content_by_type.items()},
            "by_status": status_counts,
            "recent_content": [
                c.to_dict()
                for c in sorted(
                    self._content.values(),
                    key=lambda x: x.created_at,
                    reverse=True,
                )[:10]
            ],
            "workflows": {
                "active": len(
                    [w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING]
                ),
                "completed": len(
                    [w for w in self._workflows.values() if w.status == WorkflowStatus.COMPLETED]
                ),
            },
            "metrics": self._metrics,
        }

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get content pieces pending approval."""
        return [
            {
                **c.to_dict(),
                "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
            }
            for c in self._content.values()
            if c.status == ContentStatus.REVIEWING
        ]

    def approve_content(self, content_id: UUID) -> bool:
        """Approve content for publishing."""
        if content_id not in self._content:
            return False

        content = self._content[content_id]
        content.status = ContentStatus.APPROVED
        content.updated_at = datetime.now(timezone.utc)
        return True

    def publish_content(self, content_id: UUID) -> bool:
        """Publish approved content."""
        if content_id not in self._content:
            return False

        content = self._content[content_id]
        if content.status != ContentStatus.APPROVED:
            return False

        content.status = ContentStatus.PUBLISHED
        content.published_at = datetime.now(timezone.utc)
        content.updated_at = datetime.now(timezone.utc)
        return True

    @property
    def stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "platform_connected": self._ai_platform is not None,
            "cmo_connected": self._cmo is not None,
            "cco_connected": self._cco is not None,
            "cpo_connected": self._cpo is not None,
            "registered_blueprints": len(self._blueprints),
            "workflow_templates": list(self._workflow_templates.keys()),
            **self._metrics,
        }
