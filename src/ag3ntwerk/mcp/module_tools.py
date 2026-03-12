"""
MCP Module Tools - Exposes module functionality via MCP.

Provides direct access to trends, commerce, brand, and scheduler
modules through MCP tools.
"""

import json
import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from ag3ntwerk.modules.trends import TrendService
from ag3ntwerk.modules.commerce import CommerceService
from ag3ntwerk.modules.brand import BrandService
from ag3ntwerk.modules.scheduler import SchedulerService

logger = logging.getLogger(__name__)


def _error_response(error: Exception, context: str = "") -> str:
    """Create a standardized error response."""
    error_type = type(error).__name__
    error_msg = str(error)

    response = {
        "success": False,
        "error": {
            "type": error_type,
            "message": error_msg,
            "context": context,
        },
    }

    logger.error(f"MCP Handler Error [{context}]: {error_type}: {error_msg}")

    return json.dumps(response, indent=2)


# =============================================================================
# Tool Definitions
# =============================================================================

TREND_TOOLS = [
    Tool(
        name="trends_run_analysis",
        description="Run trend analysis cycle - collects and analyzes current market trends.",
        inputSchema={
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sources to collect from (google, reddit, hackernews, producthunt)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="trends_get_trending",
        description="Get currently trending topics with optional filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (technology, business, marketing, etc.)",
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum trend score (0-100)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of trends to return",
                    "default": 20,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="trends_identify_niches",
        description="Identify profitable niche opportunities based on current trends.",
        inputSchema={
            "type": "object",
            "properties": {
                "min_opportunity_score": {
                    "type": "number",
                    "description": "Minimum opportunity score (0-100)",
                    "default": 50,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="trends_get_correlations",
        description="Find correlations between trends.",
        inputSchema={
            "type": "object",
            "properties": {
                "trend_id": {
                    "type": "string",
                    "description": "Optional specific trend ID to find correlations for",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="trends_executive_report",
        description="Get trend intelligence report tailored for a specific agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_code": {
                    "type": "string",
                    "description": "Agent code (Echo, Blueprint, Axiom, CEO)",
                    "default": "Echo",
                },
            },
            "required": [],
        },
    ),
]

COMMERCE_TOOLS = [
    Tool(
        name="commerce_list_storefronts",
        description="List all connected storefronts (Shopify and Medusa).",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="commerce_get_storefront",
        description="Get details about a specific storefront.",
        inputSchema={
            "type": "object",
            "properties": {
                "storefront_id": {
                    "type": "string",
                    "description": "Storefront ID",
                },
            },
            "required": ["storefront_id"],
        },
    ),
    Tool(
        name="commerce_get_products",
        description="Get products from a storefront.",
        inputSchema={
            "type": "object",
            "properties": {
                "storefront_id": {
                    "type": "string",
                    "description": "Storefront ID",
                },
                "collection": {
                    "type": "string",
                    "description": "Filter by collection",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum products to return",
                    "default": 50,
                },
            },
            "required": ["storefront_id"],
        },
    ),
    Tool(
        name="commerce_update_price",
        description="Update product pricing.",
        inputSchema={
            "type": "object",
            "properties": {
                "storefront_id": {
                    "type": "string",
                    "description": "Storefront ID",
                },
                "product_id": {
                    "type": "string",
                    "description": "Product ID",
                },
                "new_price": {
                    "type": "number",
                    "description": "New price",
                },
            },
            "required": ["storefront_id", "product_id", "new_price"],
        },
    ),
    Tool(
        name="commerce_get_margin_analysis",
        description="Get margin analysis for products.",
        inputSchema={
            "type": "object",
            "properties": {
                "storefront_id": {
                    "type": "string",
                    "description": "Optional storefront ID filter",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="commerce_optimize_pricing",
        description="Get pricing optimization recommendations.",
        inputSchema={
            "type": "object",
            "properties": {
                "storefront_id": {
                    "type": "string",
                    "description": "Storefront ID",
                },
                "target_margin": {
                    "type": "number",
                    "description": "Target margin percentage",
                    "default": 40.0,
                },
                "strategy": {
                    "type": "string",
                    "description": "Pricing strategy (cost_plus, competitive, value_based, premium, penetration)",
                    "default": "cost_plus",
                },
            },
            "required": ["storefront_id"],
        },
    ),
    Tool(
        name="commerce_get_low_stock",
        description="Get products with low inventory.",
        inputSchema={
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "integer",
                    "description": "Low stock threshold",
                    "default": 10,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="commerce_executive_report",
        description="Get commerce report tailored for a specific agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_code": {
                    "type": "string",
                    "description": "Agent code (Axiom, Keystone, Echo, Nexus)",
                    "default": "Axiom",
                },
            },
            "required": [],
        },
    ),
]

BRAND_TOOLS = [
    Tool(
        name="brand_create_identity",
        description="Create a new brand identity.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Brand name",
                },
                "tagline": {
                    "type": "string",
                    "description": "Brand tagline",
                },
                "mission": {
                    "type": "string",
                    "description": "Mission statement",
                },
                "primary_tone": {
                    "type": "string",
                    "description": "Primary tone (professional, friendly, authoritative, playful, inspirational, casual)",
                    "default": "professional",
                },
                "primary_color": {
                    "type": "string",
                    "description": "Primary brand color (hex)",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="brand_get_identity",
        description="Get current brand identity.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="brand_validate_content",
        description="Validate content against brand guidelines.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text content to validate",
                },
                "content_type": {
                    "type": "string",
                    "description": "Content type (social_media, email, website, blog, advertising)",
                    "default": "website",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="brand_check_consistency",
        description="Check brand consistency across content samples.",
        inputSchema={
            "type": "object",
            "properties": {
                "samples": {
                    "type": "string",
                    "description": "JSON array of content samples [{type, text, name}]",
                },
            },
            "required": ["samples"],
        },
    ),
    Tool(
        name="brand_add_guideline",
        description="Add a brand guideline.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Guideline category (logo, color, voice, typography, imagery)",
                },
                "title": {
                    "type": "string",
                    "description": "Guideline title",
                },
                "description": {
                    "type": "string",
                    "description": "Full description",
                },
                "rule_type": {
                    "type": "string",
                    "description": "Type (guideline, requirement, prohibition)",
                    "default": "guideline",
                },
            },
            "required": ["category", "title", "description"],
        },
    ),
    Tool(
        name="brand_get_guidelines",
        description="Get brand guidelines.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="brand_get_kit",
        description="Get complete brand kit for export/sharing.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="brand_executive_report",
        description="Get brand report tailored for a specific agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_code": {
                    "type": "string",
                    "description": "Agent code (Echo, Beacon, Blueprint)",
                    "default": "Echo",
                },
            },
            "required": [],
        },
    ),
]

SCHEDULER_TOOLS = [
    Tool(
        name="scheduler_schedule_task",
        description="Schedule a new automated task.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Task name",
                },
                "handler_name": {
                    "type": "string",
                    "description": "Handler to execute",
                },
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
                "frequency": {
                    "type": "string",
                    "description": "Frequency (hourly, daily, weekly, monthly, on_demand)",
                    "default": "daily",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (low, normal, high, critical)",
                    "default": "normal",
                },
                "owner_executive": {
                    "type": "string",
                    "description": "Agent owner code",
                    "default": "Nexus",
                },
                "hour": {
                    "type": "integer",
                    "description": "Hour to run (0-23)",
                    "default": 0,
                },
                "minute": {
                    "type": "integer",
                    "description": "Minute to run (0-59)",
                    "default": 0,
                },
            },
            "required": ["name", "handler_name"],
        },
    ),
    Tool(
        name="scheduler_schedule_from_template",
        description="Schedule a task from a pre-defined template.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_name": {
                    "type": "string",
                    "description": "Template name (daily_trend_scan, hourly_pricing_check, daily_inventory_alert, weekly_brand_audit, daily_executive_report)",
                },
            },
            "required": ["template_name"],
        },
    ),
    Tool(
        name="scheduler_list_tasks",
        description="List scheduled tasks.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner_executive": {
                    "type": "string",
                    "description": "Filter by owner",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (active, paused, completed)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="scheduler_run_task",
        description="Run a scheduled task immediately.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to run",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="scheduler_enable_task",
        description="Enable a paused task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="scheduler_disable_task",
        description="Disable/pause a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="scheduler_list_workflows",
        description="List available workflows.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner_executive": {
                    "type": "string",
                    "description": "Filter by owner",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="scheduler_execute_workflow",
        description="Execute a workflow.",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "Workflow ID",
                },
                "context": {
                    "type": "string",
                    "description": "JSON string with initial context",
                    "default": "{}",
                },
            },
            "required": ["workflow_id"],
        },
    ),
    Tool(
        name="scheduler_run_autonomous_cycle",
        description="Run an autonomous operational cycle - executes due tasks.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="scheduler_executive_report",
        description="Get scheduler report tailored for a specific agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_code": {
                    "type": "string",
                    "description": "Agent code (Nexus, CEO, Keystone, Axiom, Echo)",
                    "default": "Nexus",
                },
            },
            "required": [],
        },
    ),
]

# All module tools combined
MODULE_TOOLS = TREND_TOOLS + COMMERCE_TOOLS + BRAND_TOOLS + SCHEDULER_TOOLS


# =============================================================================
# Tool Handlers
# =============================================================================


class ModuleToolHandler:
    """
    Handles MCP tool calls for ag3ntwerk modules.

    Provides a unified interface to trends, commerce, brand, and scheduler
    module functionality.
    """

    def __init__(self):
        """Initialize module services."""
        self._trend_service: Optional[TrendService] = None
        self._commerce_service: Optional[CommerceService] = None
        self._brand_service: Optional[BrandService] = None
        self._scheduler_service: Optional[SchedulerService] = None

    @property
    def trend_service(self) -> TrendService:
        """Lazy-load trend service."""
        if self._trend_service is None:
            self._trend_service = TrendService()
        return self._trend_service

    @property
    def commerce_service(self) -> CommerceService:
        """Lazy-load commerce service."""
        if self._commerce_service is None:
            self._commerce_service = CommerceService()
        return self._commerce_service

    @property
    def brand_service(self) -> BrandService:
        """Lazy-load brand service."""
        if self._brand_service is None:
            self._brand_service = BrandService()
        return self._brand_service

    @property
    def scheduler_service(self) -> SchedulerService:
        """Lazy-load scheduler service."""
        if self._scheduler_service is None:
            self._scheduler_service = SchedulerService()
        return self._scheduler_service

    def get_handler(self, tool_name: str):
        """Get handler for a tool."""
        handlers = {
            # Trends
            "trends_run_analysis": self._handle_trends_run_analysis,
            "trends_get_trending": self._handle_trends_get_trending,
            "trends_identify_niches": self._handle_trends_identify_niches,
            "trends_get_correlations": self._handle_trends_get_correlations,
            "trends_executive_report": self._handle_trends_executive_report,
            # Commerce
            "commerce_list_storefronts": self._handle_commerce_list_storefronts,
            "commerce_get_storefront": self._handle_commerce_get_storefront,
            "commerce_get_products": self._handle_commerce_get_products,
            "commerce_update_price": self._handle_commerce_update_price,
            "commerce_get_margin_analysis": self._handle_commerce_get_margin_analysis,
            "commerce_optimize_pricing": self._handle_commerce_optimize_pricing,
            "commerce_get_low_stock": self._handle_commerce_get_low_stock,
            "commerce_executive_report": self._handle_commerce_executive_report,
            # Brand
            "brand_create_identity": self._handle_brand_create_identity,
            "brand_get_identity": self._handle_brand_get_identity,
            "brand_validate_content": self._handle_brand_validate_content,
            "brand_check_consistency": self._handle_brand_check_consistency,
            "brand_add_guideline": self._handle_brand_add_guideline,
            "brand_get_guidelines": self._handle_brand_get_guidelines,
            "brand_get_kit": self._handle_brand_get_kit,
            "brand_executive_report": self._handle_brand_executive_report,
            # Scheduler
            "scheduler_schedule_task": self._handle_scheduler_schedule_task,
            "scheduler_schedule_from_template": self._handle_scheduler_schedule_from_template,
            "scheduler_list_tasks": self._handle_scheduler_list_tasks,
            "scheduler_run_task": self._handle_scheduler_run_task,
            "scheduler_enable_task": self._handle_scheduler_enable_task,
            "scheduler_disable_task": self._handle_scheduler_disable_task,
            "scheduler_list_workflows": self._handle_scheduler_list_workflows,
            "scheduler_execute_workflow": self._handle_scheduler_execute_workflow,
            "scheduler_run_autonomous_cycle": self._handle_scheduler_run_autonomous_cycle,
            "scheduler_executive_report": self._handle_scheduler_executive_report,
        }
        return handlers.get(tool_name)

    # -------------------------------------------------------------------------
    # Trend Handlers
    # -------------------------------------------------------------------------

    async def _handle_trends_run_analysis(self, args: Dict[str, Any]) -> str:
        """Run trend analysis."""
        try:
            sources = args.get("sources", [])
            result = await self.trend_service.run_analysis_cycle(sources=sources or None)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "trends_run_analysis")

    async def _handle_trends_get_trending(self, args: Dict[str, Any]) -> str:
        """Get trending topics."""
        try:
            category = args.get("category")
            min_score = args.get("min_score", 0)
            limit = args.get("limit", 20)

            result = await self.trend_service.get_trending(
                category=category,
                min_score=min_score,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "trends_get_trending")

    async def _handle_trends_identify_niches(self, args: Dict[str, Any]) -> str:
        """Identify niche opportunities."""
        try:
            min_score = args.get("min_opportunity_score", 50)
            result = await self.trend_service.identify_niches(min_opportunity_score=min_score)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "trends_identify_niches")

    async def _handle_trends_get_correlations(self, args: Dict[str, Any]) -> str:
        """Get trend correlations."""
        try:
            trend_id = args.get("trend_id")
            result = await self.trend_service.get_correlations(trend_id=trend_id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "trends_get_correlations")

    async def _handle_trends_executive_report(self, args: Dict[str, Any]) -> str:
        """Get agent trend report."""
        try:
            agent_code = args.get("agent_code", "Echo")
            result = await self.trend_service.get_agent_report(agent_code)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "trends_executive_report")

    # -------------------------------------------------------------------------
    # Commerce Handlers
    # -------------------------------------------------------------------------

    async def _handle_commerce_list_storefronts(self, args: Dict[str, Any]) -> str:
        """List storefronts."""
        try:
            result = self.commerce_service.list_storefronts()
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_list_storefronts")

    async def _handle_commerce_get_storefront(self, args: Dict[str, Any]) -> str:
        """Get storefront details."""
        try:
            storefront_id = args.get("storefront_id", "")
            if not storefront_id:
                return json.dumps({"error": "storefront_id is required"}, indent=2)

            result = self.commerce_service.get_storefront(storefront_id)
            if result is None:
                return json.dumps({"error": f"Storefront not found: {storefront_id}"}, indent=2)

            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_get_storefront")

    async def _handle_commerce_get_products(self, args: Dict[str, Any]) -> str:
        """Get products."""
        try:
            storefront_id = args.get("storefront_id", "")
            if not storefront_id:
                return json.dumps({"error": "storefront_id is required"}, indent=2)

            collection = args.get("collection")
            limit = args.get("limit", 50)

            result = await self.commerce_service.get_products(
                storefront_key=storefront_id,
                limit=limit,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_get_products")

    async def _handle_commerce_update_price(self, args: Dict[str, Any]) -> str:
        """Update product price."""
        try:
            storefront_id = args.get("storefront_id", "")
            product_id = args.get("product_id", "")
            new_price = args.get("new_price", 0)

            if not storefront_id:
                return json.dumps({"error": "storefront_id is required"}, indent=2)
            if not product_id:
                return json.dumps({"error": "product_id is required"}, indent=2)
            if new_price <= 0:
                return json.dumps({"error": "new_price must be positive"}, indent=2)

            # Note: This requires variant_id which isn't in the tool schema
            # For now, return an indication that more info is needed
            return json.dumps(
                {
                    "error": "Price update requires variant_id. Use commerce API directly.",
                    "storefront_id": storefront_id,
                    "product_id": product_id,
                    "new_price": new_price,
                },
                indent=2,
            )
        except Exception as e:
            return _error_response(e, "commerce_update_price")

    async def _handle_commerce_get_margin_analysis(self, args: Dict[str, Any]) -> str:
        """Get margin analysis."""
        try:
            storefront_id = args.get("storefront_id")
            result = await self.commerce_service.get_margin_analysis(storefront_key=storefront_id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_get_margin_analysis")

    async def _handle_commerce_optimize_pricing(self, args: Dict[str, Any]) -> str:
        """Get pricing optimization."""
        try:
            storefront_id = args.get("storefront_id", "")
            if not storefront_id:
                return json.dumps({"error": "storefront_id is required"}, indent=2)

            target_margin = args.get("target_margin", 40.0)
            strategy = args.get("strategy", "cost_plus")

            result = await self.commerce_service.optimize_pricing(
                storefront_key=storefront_id,
                target_margin=target_margin,
                strategy=strategy,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_optimize_pricing")

    async def _handle_commerce_get_low_stock(self, args: Dict[str, Any]) -> str:
        """Get low stock products."""
        try:
            threshold = args.get("threshold", 10)
            result = self.commerce_service.get_low_stock_alerts(threshold=threshold)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_get_low_stock")

    async def _handle_commerce_executive_report(self, args: Dict[str, Any]) -> str:
        """Get agent commerce report."""
        try:
            agent_code = args.get("agent_code", "Axiom")
            result = await self.commerce_service.get_agent_report(agent_code)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "commerce_executive_report")

    # -------------------------------------------------------------------------
    # Brand Handlers
    # -------------------------------------------------------------------------

    async def _handle_brand_create_identity(self, args: Dict[str, Any]) -> str:
        """Create brand identity."""
        try:
            name = args.get("name", "")
            if not name:
                return json.dumps({"error": "name is required"}, indent=2)

            result = self.brand_service.create_identity(
                name=name,
                tagline=args.get("tagline", ""),
                mission=args.get("mission", ""),
                primary_tone=args.get("primary_tone", "professional"),
                primary_color=args.get("primary_color"),
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_create_identity")

    async def _handle_brand_get_identity(self, args: Dict[str, Any]) -> str:
        """Get brand identity."""
        try:
            result = self.brand_service.get_identity()
            if result is None:
                return json.dumps({"message": "No brand identity created yet"}, indent=2)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_get_identity")

    async def _handle_brand_validate_content(self, args: Dict[str, Any]) -> str:
        """Validate content against brand."""
        try:
            content = args.get("content", "")
            if not content:
                return json.dumps({"error": "content is required"}, indent=2)

            content_type = args.get("content_type", "website")

            result = self.brand_service.validate_content(
                content=content,
                content_type=content_type,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_validate_content")

    async def _handle_brand_check_consistency(self, args: Dict[str, Any]) -> str:
        """Check brand consistency."""
        try:
            samples_str = args.get("samples", "[]")
            try:
                samples = json.loads(samples_str)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in samples"}, indent=2)

            if not samples:
                return json.dumps({"error": "samples array is empty"}, indent=2)

            result = self.brand_service.check_consistency(samples)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_check_consistency")

    async def _handle_brand_add_guideline(self, args: Dict[str, Any]) -> str:
        """Add brand guideline."""
        try:
            category = args.get("category", "")
            title = args.get("title", "")
            description = args.get("description", "")

            if not category:
                return json.dumps({"error": "category is required"}, indent=2)
            if not title:
                return json.dumps({"error": "title is required"}, indent=2)
            if not description:
                return json.dumps({"error": "description is required"}, indent=2)

            guideline_id = self.brand_service.add_guideline(
                category=category,
                title=title,
                description=description,
                rule_type=args.get("rule_type", "guideline"),
            )
            return json.dumps({"success": True, "guideline_id": guideline_id}, indent=2)
        except Exception as e:
            return _error_response(e, "brand_add_guideline")

    async def _handle_brand_get_guidelines(self, args: Dict[str, Any]) -> str:
        """Get brand guidelines."""
        try:
            category = args.get("category")
            result = self.brand_service.get_guidelines(category=category)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_get_guidelines")

    async def _handle_brand_get_kit(self, args: Dict[str, Any]) -> str:
        """Get brand kit."""
        try:
            result = self.brand_service.get_brand_kit()
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_get_kit")

    async def _handle_brand_executive_report(self, args: Dict[str, Any]) -> str:
        """Get agent brand report."""
        try:
            agent_code = args.get("agent_code", "Echo")
            result = self.brand_service.get_agent_report(agent_code)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "brand_executive_report")

    # -------------------------------------------------------------------------
    # Scheduler Handlers
    # -------------------------------------------------------------------------

    async def _handle_scheduler_schedule_task(self, args: Dict[str, Any]) -> str:
        """Schedule a task."""
        try:
            name = args.get("name", "")
            handler_name = args.get("handler_name", "")

            if not name:
                return json.dumps({"error": "name is required"}, indent=2)
            if not handler_name:
                return json.dumps({"error": "handler_name is required"}, indent=2)

            task_id = self.scheduler_service.schedule_task(
                name=name,
                handler_name=handler_name,
                description=args.get("description", ""),
                frequency=args.get("frequency", "daily"),
                priority=args.get("priority", "normal"),
                owner_executive=args.get("owner_executive", "Nexus"),
                hour=args.get("hour", 0),
                minute=args.get("minute", 0),
            )
            return json.dumps({"success": True, "task_id": task_id}, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_schedule_task")

    async def _handle_scheduler_schedule_from_template(self, args: Dict[str, Any]) -> str:
        """Schedule from template."""
        try:
            template_name = args.get("template_name", "")
            if not template_name:
                return json.dumps({"error": "template_name is required"}, indent=2)

            task_id = self.scheduler_service.schedule_from_template(template_name)
            return json.dumps({"success": True, "task_id": task_id}, indent=2)
        except ValueError as e:
            return json.dumps({"success": False, "error": str(e)}, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_schedule_from_template")

    async def _handle_scheduler_list_tasks(self, args: Dict[str, Any]) -> str:
        """List scheduled tasks."""
        try:
            result = self.scheduler_service.list_tasks(
                owner_executive=args.get("owner_executive"),
                category=args.get("category"),
                status=args.get("status"),
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_list_tasks")

    async def _handle_scheduler_run_task(self, args: Dict[str, Any]) -> str:
        """Run task immediately."""
        try:
            task_id = args.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id is required"}, indent=2)

            result = await self.scheduler_service.run_task_now(task_id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_run_task")

    async def _handle_scheduler_enable_task(self, args: Dict[str, Any]) -> str:
        """Enable task."""
        try:
            task_id = args.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id is required"}, indent=2)

            success = self.scheduler_service.enable_task(task_id)
            return json.dumps({"success": success}, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_enable_task")

    async def _handle_scheduler_disable_task(self, args: Dict[str, Any]) -> str:
        """Disable task."""
        try:
            task_id = args.get("task_id", "")
            if not task_id:
                return json.dumps({"error": "task_id is required"}, indent=2)

            success = self.scheduler_service.disable_task(task_id)
            return json.dumps({"success": success}, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_disable_task")

    async def _handle_scheduler_list_workflows(self, args: Dict[str, Any]) -> str:
        """List workflows."""
        try:
            result = self.scheduler_service.list_workflows(
                owner_executive=args.get("owner_executive"),
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_list_workflows")

    async def _handle_scheduler_execute_workflow(self, args: Dict[str, Any]) -> str:
        """Execute workflow."""
        try:
            workflow_id = args.get("workflow_id", "")
            if not workflow_id:
                return json.dumps({"error": "workflow_id is required"}, indent=2)

            context_str = args.get("context", "{}")

            try:
                context = json.loads(context_str) if context_str else {}
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON in context"}, indent=2)

            result = await self.scheduler_service.execute_workflow(
                workflow_id=workflow_id,
                initial_context=context,
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_execute_workflow")

    async def _handle_scheduler_run_autonomous_cycle(self, args: Dict[str, Any]) -> str:
        """Run autonomous cycle."""
        try:
            result = await self.scheduler_service.run_autonomous_cycle()
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_run_autonomous_cycle")

    async def _handle_scheduler_executive_report(self, args: Dict[str, Any]) -> str:
        """Get agent scheduler report."""
        try:
            agent_code = args.get("agent_code", "Nexus")
            result = self.scheduler_service.get_agent_report(agent_code)
            return json.dumps(result, indent=2)
        except Exception as e:
            return _error_response(e, "scheduler_executive_report")
