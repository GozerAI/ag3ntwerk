"""
ag3ntwerk Agent Modules.

Integrated autonomous modules that provide agents with direct tool access:

- trends: Trend analysis, niche identification, market intelligence (Echo, Blueprint, Axiom)
- commerce: Shopify/Medusa storefront management, pricing, inventory (Axiom, Keystone)
- brand: Brand suite, guidelines, asset management (Echo, Beacon)
- scheduler: Autonomous task scheduling and execution (Nexus)
- workbench: Development environments, sandboxed runtimes, code execution (Forge, Foundry)
- vls: Vertical Launch System for autonomous vertical discovery and monetization (Nexus, CEO)
- distributed: Fleet orchestration, network discovery, distributed task allocation (Nexus, Forge)
- research_automation: Market intelligence, competitive analysis, technology radar (Compass, Forge)
- data_harvesting: Multi-source data collection, quality auditing, scheduling (Index)
- security_automation: Security scanning, threat assessment, compliance auditing (Citadel)

Each module is designed to be owned by specific agents while being
accessible to others as needed for cross-functional collaboration.
"""

from typing import Dict, Any, List

# Module registry for discovery
MODULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "trends": {
        "name": "Trend Intelligence",
        "description": "Market trend analysis, niche identification, opportunity detection",
        "primary_owners": ["Echo", "Blueprint"],
        "secondary_owners": ["Axiom", "CEO"],
        "capabilities": [
            "trend_collection",
            "trend_analysis",
            "niche_identification",
            "opportunity_scoring",
            "drift_detection",
            "cross_platform_correlation",
        ],
    },
    "commerce": {
        "name": "Commerce Operations",
        "description": "Multi-storefront management, pricing optimization, inventory control",
        "primary_owners": ["Vector", "Keystone"],
        "secondary_owners": ["Echo", "Nexus"],
        "capabilities": [
            "product_management",
            "pricing_optimization",
            "inventory_tracking",
            "margin_analysis",
            "storefront_analytics",
            "order_management",
        ],
    },
    "brand": {
        "name": "Brand Suite",
        "description": "Brand guidelines, asset management, consistency enforcement",
        "primary_owners": ["Echo", "Beacon"],
        "secondary_owners": ["Blueprint"],
        "capabilities": [
            "brand_guidelines",
            "asset_management",
            "brand_audit",
            "consistency_check",
            "style_enforcement",
        ],
    },
    "scheduler": {
        "name": "Autonomous Scheduler",
        "description": "Task scheduling, autonomous execution, reporting automation",
        "primary_owners": ["Nexus"],
        "secondary_owners": ["CEO"],
        "capabilities": [
            "task_scheduling",
            "autonomous_execution",
            "report_generation",
            "workflow_automation",
            "alert_management",
        ],
    },
    "workbench": {
        "name": "Development Workbench",
        "description": "Sandboxed development environments, code execution, IDE integration",
        "primary_owners": ["Forge", "Foundry"],
        "secondary_owners": ["Nexus", "Blueprint"],
        "capabilities": [
            "workspace_management",
            "sandboxed_execution",
            "code_preview",
            "runtime_isolation",
            "port_exposure",
            "ide_integration",
        ],
    },
    "vls": {
        "name": "Vertical Launch System",
        "description": "Autonomous vertical discovery and monetization pipeline with evidence-based gating",
        "primary_owners": ["Nexus", "CEO"],
        "secondary_owners": ["Echo", "Keystone", "Blueprint", "Forge", "Vector", "Aegis", "Index", "Foundry"],
        "capabilities": [
            "vertical_discovery",
            "market_intelligence",
            "economics_validation",
            "blueprint_generation",
            "infrastructure_deployment",
            "buyer_acquisition",
            "lead_monetization",
            "knowledge_capture",
            "pipeline_orchestration",
            "stop_loss_monitoring",
        ],
    },
    "metacognition": {
        "name": "Metacognition & Self-Differentiation",
        "description": "Personality profiles, agent-level and system-level reflection, adaptive heuristics, and personality evolution",
        "primary_owners": ["Overwatch", "Nexus"],
        "secondary_owners": [
            "Forge",
            "Keystone",
            "Echo",
            "Sentinel",
            "Blueprint",
            "Axiom",
            "Index",
            "Foundry",
            "Citadel",
            "Beacon",
            "Compass",
            "Vector",
            "Aegis",
            "Accord",
        ],
        "capabilities": [
            "personality_profiling",
            "agent_reflection",
            "system_reflection",
            "heuristic_evaluation",
            "heuristic_tuning",
            "trait_evolution",
            "personality_persistence",
            "temporal_trait_tracking",
            "personality_coherence",
            "cross_agent_learning",
            "team_composition_learning",
            "trait_map_optimization",
        ],
    },
    "distributed": {
        "name": "Distributed Fleet Orchestration",
        "description": "Network-aware resource discovery, fleet coordination, and distributed task allocation",
        "primary_owners": ["Nexus", "Forge"],
        "secondary_owners": ["Foundry", "Citadel", "Index"],
        "capabilities": [
            "network_discovery",
            "device_enrollment",
            "resource_profiling",
            "capability_scoring",
            "workload_distribution",
            "fleet_coordination",
            "health_monitoring",
            "node_provisioning",
        ],
    },
    "swarm_bridge": {
        "name": "Swarm Bridge",
        "description": "Delegates coding tasks to the Claude Swarm for execution by local LLMs with model-agnostic tool calling",
        "primary_owners": ["Forge", "Foundry"],
        "secondary_owners": ["Nexus", "Citadel", "Index", "Overwatch"],
        "capabilities": [
            "swarm_task_delegation",
            "model_selection",
            "tool_calling",
            "routing_feedback",
            "code_review_delegation",
            "security_scan_delegation",
        ],
    },
    "research_automation": {
        "name": "Autonomous Research",
        "description": "Market intelligence, competitive analysis, technology radar, and trend deep research",
        "primary_owners": ["Compass", "Forge"],
        "secondary_owners": ["Echo", "Blueprint", "CEO"],
        "capabilities": [
            "market_intelligence_scan",
            "competitive_analysis",
            "technology_radar",
            "trend_deep_research",
            "research_scheduling",
            "insights_aggregation",
        ],
    },
    "data_harvesting": {
        "name": "Autonomous Data Harvesting",
        "description": "Multi-source data collection, quality auditing, and harvest scheduling",
        "primary_owners": ["Index"],
        "secondary_owners": ["Forge", "Foundry", "Nexus"],
        "capabilities": [
            "source_management",
            "harvest_execution",
            "data_quality_reporting",
            "harvest_scheduling",
            "source_monitoring",
        ],
    },
    "security_automation": {
        "name": "Security Automation",
        "description": "Security scanning, threat assessment, compliance auditing, and continuous monitoring",
        "primary_owners": ["Citadel"],
        "secondary_owners": ["Forge", "Sentinel", "Nexus"],
        "capabilities": [
            "security_scanning",
            "threat_assessment",
            "compliance_auditing",
            "alert_management",
            "continuous_monitoring",
            "access_review",
        ],
    },
}


def get_modules_for_executive(agent_code: str) -> List[str]:
    """Get modules available to an agent."""
    modules = []
    for module_id, info in MODULE_REGISTRY.items():
        if agent_code in info["primary_owners"] or agent_code in info["secondary_owners"]:
            modules.append(module_id)
    return modules


def get_module_info(module_id: str) -> Dict[str, Any]:
    """Get information about a module."""
    return MODULE_REGISTRY.get(module_id, {})


# Import services for easy access
from ag3ntwerk.modules.trends import TrendService
from ag3ntwerk.modules.commerce import CommerceService
from ag3ntwerk.modules.brand import BrandService
from ag3ntwerk.modules.scheduler import SchedulerService
from ag3ntwerk.modules.workbench import WorkbenchService
from ag3ntwerk.modules.vls import VLSService
from ag3ntwerk.modules.integration import (
    ModuleIntegration,
    EchoModuleHandler,
    VectorModuleHandler,
    NexusModuleHandler,
    CompassModuleHandler,
    IndexModuleHandler,
    CitadelModuleHandler,
    OverwatchModuleHandler,
    ForgeModuleHandler,
    KeystoneModuleHandler,
    SentinelModuleHandler,
    BlueprintModuleHandler,
    AxiomModuleHandler,
    FoundryModuleHandler,
    BeaconModuleHandler,
    AegisModuleHandler,
    AccordModuleHandler,
    get_integration,
)


__all__ = [
    # Registry
    "MODULE_REGISTRY",
    "get_modules_for_executive",
    "get_module_info",
    # Services
    "TrendService",
    "CommerceService",
    "BrandService",
    "SchedulerService",
    "WorkbenchService",
    "VLSService",
    # Integration
    "ModuleIntegration",
    "EchoModuleHandler",
    "VectorModuleHandler",
    "NexusModuleHandler",
    "CompassModuleHandler",
    "IndexModuleHandler",
    "CitadelModuleHandler",
    "OverwatchModuleHandler",
    "ForgeModuleHandler",
    "KeystoneModuleHandler",
    "SentinelModuleHandler",
    "BlueprintModuleHandler",
    "AxiomModuleHandler",
    "FoundryModuleHandler",
    "BeaconModuleHandler",
    "AegisModuleHandler",
    "AccordModuleHandler",
    "get_integration",
]
