"""
Goal Analyzer for the Autonomous Agenda Engine.

This module decomposes goals into executable workstreams by:
1. Parsing goal structure (title, description, milestones)
2. Identifying capability requirements for each milestone
3. Mapping milestones to task types and agents
4. Generating workstreams that can be executed

The GoalAnalyzer uses NLP/keyword extraction to infer task types and
capability requirements from natural language goal descriptions.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.agenda.models import (
    CapabilityRequirement,
    Workstream,
    WorkstreamStatus,
)

logger = get_logger(__name__)


# =============================================================================
# Task Type Keywords for Inference
# =============================================================================

# Keywords that suggest specific task types
TASK_TYPE_KEYWORDS: Dict[str, List[str]] = {
    # Technical tasks -> Forge
    "code_review": ["review", "code review", "pr review", "pull request", "audit code"],
    "code_generation": ["implement", "develop", "build", "create code", "write code", "coding"],
    "architecture": ["architecture", "design system", "system design", "technical design"],
    "deployment": ["deploy", "release", "ship", "launch", "go live", "production"],
    "testing": ["test", "testing", "qa", "quality assurance", "unit test", "integration test"],
    "debugging": ["debug", "fix bug", "troubleshoot", "diagnose"],
    "refactoring": ["refactor", "cleanup", "optimize code", "improve code"],
    # Security tasks -> Sentinel/Citadel
    "security_review": ["security review", "security audit", "vulnerability", "penetration"],
    "security_scan": ["security scan", "scan for vulnerabilities"],
    "access_control": ["access control", "permissions", "rbac", "authentication", "authorization"],
    # Financial tasks -> Keystone
    "budget_analysis": ["budget", "spending", "financial analysis"],
    "cost_optimization": ["cost optimization", "reduce costs", "save money", "cost reduction"],
    "financial_report": ["financial report", "revenue report", "expense report"],
    "roi_analysis": ["roi", "return on investment", "cost benefit"],
    # Strategy tasks -> Compass
    "strategic_analysis": ["strategic", "strategy analysis", "strategic planning"],
    "market_research": ["market research", "market analysis", "market study"],
    "competitive_analysis": ["competitive analysis", "competitor", "competitive landscape"],
    # Research tasks -> Axiom
    "research": ["research", "investigate", "study", "explore", "discovery"],
    "data_analysis": ["data analysis", "analyze data", "data insights"],
    "insights": ["insights", "findings", "conclusions"],
    # Data tasks -> Index
    "data_governance": ["data governance", "data policy", "data standards"],
    "data_quality": ["data quality", "data validation", "data cleaning"],
    "knowledge_management": ["knowledge management", "documentation", "knowledge base"],
    # Compliance tasks -> Accord
    "compliance_check": ["compliance", "regulatory", "compliance check"],
    "audit": ["audit", "auditing", "internal audit"],
    "policy_review": ["policy review", "policy update", "governance"],
    # Risk tasks -> Aegis
    "risk_assessment": ["risk assessment", "risk analysis", "identify risks"],
    "risk_mitigation": ["risk mitigation", "mitigate risks", "risk management"],
    # Marketing tasks -> Echo
    "campaign_creation": ["campaign", "marketing campaign", "promotion"],
    "content_strategy": ["content strategy", "content plan", "content marketing"],
    "brand_analysis": ["brand", "branding", "brand analysis"],
    # Product tasks -> Blueprint
    "product_strategy": ["product strategy", "product vision", "product roadmap"],
    "feature_planning": ["feature", "feature planning", "roadmap", "backlog"],
    "user_research": ["user research", "user feedback", "customer research"],
    # Customer tasks -> Beacon
    "customer_feedback": ["customer feedback", "customer survey", "nps"],
    "customer_success": ["customer success", "customer satisfaction", "retention"],
    # Revenue tasks -> Vector
    "revenue_optimization": ["revenue", "revenue optimization", "monetization"],
    "sales_strategy": ["sales", "sales strategy", "pipeline"],
    # Engineering tasks -> Foundry
    "infrastructure": ["infrastructure", "infra", "servers", "cloud"],
    "devops": ["devops", "ci/cd", "continuous integration", "deployment pipeline"],
    "platform_engineering": ["platform", "platform engineering"],
}

# Agent capabilities mapping (task_type -> agent)
AGENT_CAPABILITIES: Dict[str, str] = {
    # Forge
    "code_review": "Forge",
    "code_generation": "Forge",
    "architecture": "Forge",
    "deployment": "Forge",
    "testing": "Forge",
    "debugging": "Forge",
    "refactoring": "Forge",
    "technical_design": "Forge",
    # Sentinel
    "security_scan": "Sentinel",
    "security_review": "Sentinel",
    "threat_analysis": "Sentinel",
    "access_control": "Sentinel",
    # Citadel
    "vulnerability_check": "Citadel",
    "incident_response": "Citadel",
    # Keystone
    "budget_analysis": "Keystone",
    "cost_optimization": "Keystone",
    "financial_report": "Keystone",
    "roi_analysis": "Keystone",
    # Compass
    "strategic_analysis": "Compass",
    "market_research": "Compass",
    "competitive_analysis": "Compass",
    # Axiom
    "research": "Axiom",
    "data_analysis": "Axiom",
    "insights": "Axiom",
    # Index
    "data_governance": "Index",
    "data_quality": "Index",
    "knowledge_management": "Index",
    # Accord
    "compliance_check": "Accord",
    "audit": "Accord",
    "policy_review": "Accord",
    # Aegis
    "risk_assessment": "Aegis",
    "risk_mitigation": "Aegis",
    # Echo
    "campaign_creation": "Echo",
    "content_strategy": "Echo",
    "brand_analysis": "Echo",
    # Blueprint
    "product_strategy": "Blueprint",
    "feature_planning": "Blueprint",
    "user_research": "Blueprint",
    # Beacon
    "customer_feedback": "Beacon",
    "customer_success": "Beacon",
    # Vector
    "revenue_optimization": "Vector",
    "sales_strategy": "Vector",
    # Foundry
    "infrastructure": "Foundry",
    "devops": "Foundry",
    "platform_engineering": "Foundry",
}

# Tool categories that map to capabilities
TOOL_CATEGORIES: Dict[str, List[str]] = {
    "development": ["code_review", "code_generation", "testing", "debugging"],
    "security": ["security_review", "security_scan", "vulnerability_check"],
    "data": ["data_analysis", "data_governance", "data_quality"],
    "communication": ["campaign_creation", "content_strategy"],
    "analytics": ["research", "insights", "market_research"],
    "infrastructure": ["deployment", "infrastructure", "devops"],
}


# =============================================================================
# Goal Analyzer
# =============================================================================


class GoalAnalyzer:
    """
    Analyzes goals and decomposes them into workstreams.

    The analyzer:
    1. Parses goal structure (title, description, milestones)
    2. Identifies capability requirements for each milestone
    3. Maps milestones to task types and agents
    4. Generates workstreams that can be executed

    Example:
        analyzer = GoalAnalyzer()
        goal = {
            "id": "goal_001",
            "title": "Migrate to Ollama",
            "description": "Replace Claude API with local Ollama",
            "milestones": [
                {"id": "m1", "title": "Setup Ollama", "status": "pending"},
                {"id": "m2", "title": "Benchmark performance", "status": "pending"},
            ]
        }
        workstreams = await analyzer.analyze_goal(goal)
    """

    def __init__(
        self,
        tool_registry=None,
        agent_registry: Optional[Dict[str, Any]] = None,
        custom_task_keywords: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialize the goal analyzer.

        Args:
            tool_registry: Optional ToolRegistry for capability checking
            agent_registry: Optional agent info for capability mapping
            custom_task_keywords: Additional task type keywords to use
        """
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry or {}

        # Merge custom keywords with defaults
        self.task_keywords = TASK_TYPE_KEYWORDS.copy()
        if custom_task_keywords:
            for task_type, keywords in custom_task_keywords.items():
                if task_type in self.task_keywords:
                    self.task_keywords[task_type].extend(keywords)
                else:
                    self.task_keywords[task_type] = keywords

    async def analyze_goal(self, goal: Dict[str, Any]) -> List[Workstream]:
        """
        Decompose a goal into executable workstreams.

        Args:
            goal: Goal dict from state.py with structure:
                {
                    "id": str,
                    "title": str,
                    "description": str,
                    "milestones": [{"id": str, "title": str, "status": str}],
                    "status": str,
                    "progress": float
                }

        Returns:
            List of Workstream objects
        """
        goal_id = goal.get("id", "")
        goal_title = goal.get("title", "")
        goal_description = goal.get("description", "")
        milestones = goal.get("milestones", [])

        workstreams = []

        # If no milestones, create a single workstream from the goal itself
        if not milestones:
            workstream = await self._create_workstream_from_text(
                goal_id=goal_id,
                milestone_id=None,
                title=goal_title,
                description=goal_description,
            )
            workstreams.append(workstream)
        else:
            # Create a workstream for each milestone
            for milestone in milestones:
                # Skip completed milestones
                if milestone.get("status") == "completed":
                    continue

                workstream = await self._create_workstream_from_text(
                    goal_id=goal_id,
                    milestone_id=milestone.get("id"),
                    title=milestone.get("title", ""),
                    description=f"{goal_description}\n\nMilestone: {milestone.get('title', '')}",
                )
                workstreams.append(workstream)

        # Detect dependencies between workstreams
        workstreams = self._detect_workstream_dependencies(workstreams)

        logger.info(f"Analyzed goal '{goal_title}' into {len(workstreams)} workstreams")

        return workstreams

    async def _create_workstream_from_text(
        self,
        goal_id: str,
        milestone_id: Optional[str],
        title: str,
        description: str,
    ) -> Workstream:
        """Create a workstream from title and description text."""
        # Combine title and description for analysis
        full_text = f"{title} {description}".lower()

        # Extract capability requirements
        capabilities = self._extract_capability_requirements(title, description)

        # Infer task types
        task_types = self._infer_task_types(full_text)

        # Map capabilities to agents
        executive_mapping = {}
        for cap in capabilities:
            agent_code = self._map_to_executive(cap)
            if agent_code and cap.task_type:
                executive_mapping[cap.task_type] = agent_code
                cap.agent_code = agent_code

        # Add task type mappings
        for task_type in task_types:
            if task_type not in executive_mapping:
                agent_code = AGENT_CAPABILITIES.get(task_type)
                if agent_code:
                    executive_mapping[task_type] = agent_code

        # Estimate task count
        estimated_task_count = max(len(task_types), len(capabilities), 1)

        # Estimate duration based on task count and complexity
        estimated_duration_hours = self._estimate_duration(task_types, capabilities, description)

        return Workstream(
            goal_id=goal_id,
            milestone_id=milestone_id,
            title=title,
            description=description,
            objective=self._extract_objective(title, description),
            capability_requirements=capabilities,
            executive_mapping=executive_mapping,
            estimated_task_count=estimated_task_count,
            estimated_duration_hours=estimated_duration_hours,
            status=WorkstreamStatus.PENDING,
        )

    def _extract_capability_requirements(
        self,
        title: str,
        description: str,
    ) -> List[CapabilityRequirement]:
        """Extract capability requirements from goal/milestone text."""
        full_text = f"{title} {description}".lower()
        requirements = []
        seen_task_types: Set[str] = set()

        for task_type, keywords in self.task_keywords.items():
            for keyword in keywords:
                if keyword.lower() in full_text and task_type not in seen_task_types:
                    # Check availability
                    is_available, confidence = self._check_capability_availability(task_type)

                    requirement = CapabilityRequirement(
                        name=task_type.replace("_", " ").title(),
                        description=f"Capability to perform {task_type} tasks",
                        task_type=task_type,
                        tool_category=self._get_tool_category(task_type),
                        is_available=is_available,
                        availability_confidence=confidence,
                        inferred_from=keyword,
                    )
                    requirements.append(requirement)
                    seen_task_types.add(task_type)
                    break

        return requirements

    def _map_to_executive(
        self,
        capability: CapabilityRequirement,
    ) -> Optional[str]:
        """Map a capability requirement to the best agent."""
        task_type = capability.task_type

        # First check direct mapping
        if task_type in AGENT_CAPABILITIES:
            return AGENT_CAPABILITIES[task_type]

        # Check agent registry if provided
        if self.agent_registry:
            for agent_code, exec_info in self.agent_registry.items():
                exec_capabilities = exec_info.get("capabilities", [])
                if task_type in exec_capabilities:
                    return agent_code

        return None

    def _infer_task_types(self, text: str) -> List[str]:
        """Infer task types from descriptive text."""
        text_lower = text.lower()
        task_types = []

        for task_type, keywords in self.task_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if task_type not in task_types:
                        task_types.append(task_type)
                    break

        return task_types

    def _check_capability_availability(
        self,
        task_type: str,
    ) -> Tuple[bool, float]:
        """Check if capability is available and return confidence."""
        # Check if we have a tool registry
        if self.tool_registry:
            try:
                # Try to find tools for this task type
                tools = self.tool_registry.find_tools_for_task(task_type)
                if tools:
                    return True, 0.9
            except Exception as e:
                logger.debug("Tool registry lookup failed for task type '%s': %s", task_type, e)

        # Check if we have an agent for this task type
        if task_type in AGENT_CAPABILITIES:
            return True, 0.8

        # Unknown capability
        return False, 0.3

    def _get_tool_category(self, task_type: str) -> Optional[str]:
        """Get the tool category for a task type."""
        for category, task_types in TOOL_CATEGORIES.items():
            if task_type in task_types:
                return category
        return None

    def _extract_objective(self, title: str, description: str) -> str:
        """Extract a clear objective from title and description."""
        # Use title as primary objective
        objective = title

        # If description starts with action verb, use that
        action_verbs = [
            "implement",
            "create",
            "build",
            "develop",
            "deploy",
            "migrate",
            "setup",
            "configure",
            "analyze",
            "review",
            "test",
            "fix",
            "optimize",
            "improve",
            "refactor",
            "design",
            "plan",
        ]

        desc_lower = description.lower().strip()
        for verb in action_verbs:
            if desc_lower.startswith(verb):
                # Use first sentence of description
                first_sentence = description.split(".")[0].strip()
                if len(first_sentence) < 200:
                    objective = first_sentence
                break

        return objective

    def _estimate_duration(
        self,
        task_types: List[str],
        capabilities: List[CapabilityRequirement],
        description: str,
    ) -> float:
        """Estimate duration in hours based on complexity."""
        base_hours = 1.0

        # More task types = more complexity
        base_hours += len(task_types) * 0.5

        # More capabilities = more complexity
        base_hours += len(capabilities) * 0.5

        # Longer description = more complexity
        word_count = len(description.split())
        if word_count > 100:
            base_hours += 1.0
        if word_count > 200:
            base_hours += 1.0

        # Check for complexity indicators
        complexity_keywords = [
            "complex",
            "comprehensive",
            "extensive",
            "complete",
            "full",
            "multiple",
            "various",
            "all",
            "entire",
            "thorough",
        ]
        desc_lower = description.lower()
        for keyword in complexity_keywords:
            if keyword in desc_lower:
                base_hours += 0.5
                break

        return round(base_hours, 1)

    def _detect_workstream_dependencies(
        self,
        workstreams: List[Workstream],
    ) -> List[Workstream]:
        """Detect dependencies between workstreams based on content."""
        # Keywords that suggest ordering
        sequence_keywords = {
            "first": 0,
            "initial": 0,
            "setup": 0,
            "configure": 0,
            "then": 1,
            "after": 1,
            "next": 1,
            "finally": 2,
            "complete": 2,
            "finish": 2,
        }

        # Score each workstream for sequence
        scored = []
        for ws in workstreams:
            text_lower = f"{ws.title} {ws.description}".lower()
            score = 1  # Default middle score

            for keyword, seq_score in sequence_keywords.items():
                if keyword in text_lower:
                    score = seq_score
                    break

            scored.append((score, ws))

        # Sort by score
        scored.sort(key=lambda x: x[0])

        # Set dependencies (each depends on previous)
        for i in range(1, len(scored)):
            current_ws = scored[i][1]
            previous_ws = scored[i - 1][1]
            current_ws.dependency_workstream_ids.append(previous_ws.id)

        return [ws for _, ws in scored]

    async def analyze_multiple_goals(
        self,
        goals: List[Dict[str, Any]],
    ) -> Dict[str, List[Workstream]]:
        """
        Analyze multiple goals and return workstreams grouped by goal.

        Args:
            goals: List of goal dicts

        Returns:
            Dict mapping goal_id to list of workstreams
        """
        result = {}
        for goal in goals:
            goal_id = goal.get("id", "")
            workstreams = await self.analyze_goal(goal)
            result[goal_id] = workstreams
        return result

    def get_all_required_capabilities(
        self,
        workstreams: List[Workstream],
    ) -> List[CapabilityRequirement]:
        """Get all unique capability requirements from workstreams."""
        all_caps = []
        seen_task_types: Set[str] = set()

        for ws in workstreams:
            for cap in ws.capability_requirements:
                if cap.task_type not in seen_task_types:
                    all_caps.append(cap)
                    seen_task_types.add(cap.task_type)

        return all_caps

    def get_agent_summary(
        self,
        workstreams: List[Workstream],
    ) -> Dict[str, Dict[str, Any]]:
        """Get summary of agent involvement across workstreams."""
        summary: Dict[str, Dict[str, Any]] = {}

        for ws in workstreams:
            for task_type, agent_code in ws.executive_mapping.items():
                if agent_code not in summary:
                    summary[agent_code] = {
                        "task_types": [],
                        "workstream_count": 0,
                        "workstream_ids": [],
                    }

                if task_type not in summary[agent_code]["task_types"]:
                    summary[agent_code]["task_types"].append(task_type)

                if ws.id not in summary[agent_code]["workstream_ids"]:
                    summary[agent_code]["workstream_ids"].append(ws.id)
                    summary[agent_code]["workstream_count"] += 1

        return summary
