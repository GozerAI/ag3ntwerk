"""
Application state management for ag3ntwerk API.

Centralizes initialization, health-check registration, shutdown,
and in-memory task/workflow storage.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from ag3ntwerk.core.logging import get_logger
from ag3ntwerk.core.config import get_config, validate_config_or_raise, log_config_summary
from ag3ntwerk.core.health import get_health_aggregator
from ag3ntwerk.core.http_client import shutdown_http_clients, get_http_client_pool
from ag3ntwerk.core.shutdown import get_shutdown_manager
from ag3ntwerk.persistence.database import get_database, close_database, DatabaseManager
from ag3ntwerk.core.queue import get_task_queue, shutdown_queue, TaskQueue

logger = get_logger(__name__)

# All workflow classes imported once here — keeps app.py clean
from ag3ntwerk.orchestration import (
    Orchestrator,
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
    StrategicPlanningWorkflow,
    SecurityAuditWorkflow,
    CustomerOnboardingWorkflow,
    DataQualityWorkflow,
    RevenueGrowthWorkflow,
    ComplianceAuditWorkflow,
    ResearchInitiativeWorkflow,
    RiskAssessmentWorkflow,
    MarketingCampaignWorkflow,
    SprintPlanningWorkflow,
    TechnologyMigrationWorkflow,
    KnowledgeTransferWorkflow,
    CustomerChurnAnalysisWorkflow,
    OperationsReviewWorkflow,
    TechDebtReviewWorkflow,
    FinancialCloseWorkflow,
    CodeQualityWorkflow,
    FeaturePrioritizationWorkflow,
    ThreatMonitoringWorkflow,
    DataPipelineMonitoringWorkflow,
    ExperimentCycleWorkflow,
    CustomerHealthReviewWorkflow,
    RevenueAnalysisWorkflow,
    RiskMonitoringWorkflow,
    ComplianceMonitoringWorkflow,
    BrandHealthWorkflow,
    InfrastructureHealthWorkflow,
    KnowledgeMaintenanceWorkflow,
    StrategicReviewWorkflow,
)

_ALL_WORKFLOWS = [
    # Original
    ProductLaunchWorkflow,
    IncidentResponseWorkflow,
    BudgetApprovalWorkflow,
    FeatureReleaseWorkflow,
    # Cross-functional
    StrategicPlanningWorkflow,
    SecurityAuditWorkflow,
    CustomerOnboardingWorkflow,
    DataQualityWorkflow,
    RevenueGrowthWorkflow,
    ComplianceAuditWorkflow,
    ResearchInitiativeWorkflow,
    RiskAssessmentWorkflow,
    MarketingCampaignWorkflow,
    SprintPlanningWorkflow,
    TechnologyMigrationWorkflow,
    KnowledgeTransferWorkflow,
    CustomerChurnAnalysisWorkflow,
    # Single-agent internal
    OperationsReviewWorkflow,
    TechDebtReviewWorkflow,
    FinancialCloseWorkflow,
    CodeQualityWorkflow,
    FeaturePrioritizationWorkflow,
    ThreatMonitoringWorkflow,
    DataPipelineMonitoringWorkflow,
    ExperimentCycleWorkflow,
    CustomerHealthReviewWorkflow,
    RevenueAnalysisWorkflow,
    RiskMonitoringWorkflow,
    ComplianceMonitoringWorkflow,
    BrandHealthWorkflow,
    InfrastructureHealthWorkflow,
    KnowledgeMaintenanceWorkflow,
    StrategicReviewWorkflow,
]


class AppState:
    """Global application state."""

    def __init__(self):
        self.registry = None
        self.coo = None
        self.llm_provider = None
        self.orchestrator = None
        self.database: Optional[DatabaseManager] = None
        self.task_queue: Optional[TaskQueue] = None
        self.agenda_engine = None  # Autonomous Agenda Engine
        self.workbench_service = None  # Workbench development environment service
        self.ollama_manager = None  # Local LLM manager
        self.initialized = False
        self.websocket_clients: List[WebSocket] = []
        self._init_lock = asyncio.Lock()
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._task_counter = 0
        self._workflow_executions: Dict[str, Dict[str, Any]] = {}
        # Goals storage
        self._goals: Dict[str, Dict[str, Any]] = {}
        self._goal_counter = 0
        # Nexus state
        self._coo_mode = "supervised"
        self._coo_start_time: Optional[datetime] = None
        self._coo_successful_executions = 0
        self._coo_failed_executions = 0

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self):
        """Initialize the ag3ntwerk system."""
        async with self._init_lock:
            if self.initialized:
                return

            try:
                logger.info("Initializing ag3ntwerk Command Center", component="app_state")
                self._validate_config()
                config = get_config()
                await self._init_database()
                await self._init_task_queue()
                await self._init_ollama()  # Start Ollama for local LLM
                await self._init_llm(config)
                self._init_registry()
                self._init_coo()
                await self._init_agenda_engine()  # Initialize Autonomous Agenda Engine
                await self._init_workbench()  # Initialize Workbench service
                self._init_orchestrator()
                self._register_health_checks()
                self._seed_initial_goals()

                self.initialized = True
                logger.info(
                    "ag3ntwerk Command Center initialized successfully",
                    component="app_state",
                    llm_connected=self.llm_provider is not None,
                    coo_ready=self.coo is not None,
                    agenda_engine_ready=self.agenda_engine is not None,
                    workbench_ready=self.workbench_service is not None,
                    ollama_running=self.ollama_manager is not None,
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize ag3ntwerk",
                    component="app_state",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                self.initialized = True  # Run in limited mode

    def _validate_config(self):
        try:
            validate_config_or_raise()
            log_config_summary()
        except Exception as e:
            logger.warning(
                "Configuration validation warning",
                error=str(e),
                component="config",
            )

    async def _init_database(self):
        """Initialize SQLite database for persistence."""
        try:
            self.database = await get_database()
            logger.info(
                "Database initialized",
                component="database",
                backend=self.database.config.backend.value,
            )
        except Exception as e:
            logger.warning(
                "Could not initialize database",
                error=str(e),
                component="database",
            )
            logger.info("Running without persistence", component="database")
            self.database = None

    async def _init_task_queue(self):
        """Initialize SQLite-backed task queue."""
        try:
            # Use a dedicated file for the task queue
            queue_db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "task_queue.db",
            )
            os.makedirs(os.path.dirname(queue_db_path), exist_ok=True)
            self.task_queue = await get_task_queue(db_path=queue_db_path)
            logger.info(
                "Task queue initialized",
                component="task_queue",
                db_path=queue_db_path,
            )
        except Exception as e:
            logger.warning(
                "Could not initialize task queue",
                error=str(e),
                component="task_queue",
            )
            self.task_queue = None

    async def _init_ollama(self):
        """Initialize Ollama local LLM manager.

        Ollama provides local LLM inference, eliminating the need for
        external API calls and reducing costs.
        """
        try:
            # Try to import from nexus services
            import sys
            from pathlib import Path

            # Add nexus to path if needed
            nexus_path = Path(__file__).parent.parent.parent.parent / "nexus" / "src"
            if str(nexus_path) not in sys.path:
                sys.path.insert(0, str(nexus_path))

            from nexus.services.ollama_manager import OllamaManager

            self.ollama_manager = OllamaManager(
                host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                auto_start=True,
                startup_timeout=30.0,  # Shorter timeout during app init
            )

            # Check if already running, start if not
            is_healthy = await self.ollama_manager.check_health()

            if is_healthy:
                logger.info(
                    "Ollama already running",
                    component="ollama",
                    host=self.ollama_manager.host,
                )
            else:
                # Try to start Ollama
                started = await self.ollama_manager.start()
                if started:
                    logger.info(
                        "Ollama started successfully",
                        component="ollama",
                        host=self.ollama_manager.host,
                    )
                else:
                    logger.warning(
                        "Could not start Ollama - will try external LLM providers",
                        component="ollama",
                    )
                    self.ollama_manager = None

            # Start health monitoring if Ollama is running
            if self.ollama_manager and self.ollama_manager.is_running:
                await self.ollama_manager.start_health_monitoring()

        except ImportError as e:
            logger.info(
                "Ollama manager not available",
                component="ollama",
                reason=str(e),
            )
            self.ollama_manager = None

        except Exception as e:
            logger.warning(
                "Could not initialize Ollama",
                component="ollama",
                error=str(e),
            )
            self.ollama_manager = None

    async def _init_llm(self, config):
        from ag3ntwerk.llm import get_provider

        try:
            self.llm_provider = get_provider(
                provider_type=config.llm.provider,
                base_url=config.llm.base_url,
                api_key=config.llm.api_key,
                default_model=config.llm.default_model,
                timeout=config.llm.timeout,
            )

            connected = await self.llm_provider.connect()
            if not connected:
                msg = f"Failed to connect to LLM provider '{config.llm.provider}' at {config.llm.base_url}"
                if config.is_production():
                    raise RuntimeError(msg)
                logger.warning(msg)
                self.llm_provider = None
            else:
                logger.info("Connected to LLM provider", provider=config.llm.provider)
        except Exception as e:
            logger.warning(
                "Could not connect to LLM provider",
                provider=config.llm.provider,
                error=str(e),
            )
            logger.info("Running in limited mode", llm_available=False)
            self.llm_provider = None

    def _init_registry(self):
        from ag3ntwerk.orchestration import AgentRegistry

        self.registry = AgentRegistry(
            llm_provider=self.llm_provider,
            auto_register=True,
        )
        logger.info("Agent registry initialized", component="registry")

    def _init_coo(self):
        if not self.llm_provider:
            return
        try:
            from ag3ntwerk.initialization import create_overwatch_with_agents

            self.coo = create_overwatch_with_agents(llm_provider=self.llm_provider)
            logger.info(
                "Agent initialized and ready",
                agent="Overwatch",
                codename="Overwatch",
                subordinates_registered=len(self.coo.subordinates),
            )
        except Exception as e:
            logger.warning(
                "Could not initialize agent",
                agent="Overwatch",
                error=str(e),
            )
            self.coo = None

    async def _init_agenda_engine(self):
        """Initialize the Autonomous Agenda Engine and connect to Nexus.

        The agenda engine provides:
        - Goal-based agenda generation with obstacle detection
        - Strategy generation for overcoming blockers
        - Human-in-the-loop checkpoints for risky operations
        - Prioritized, balanced task scheduling
        """
        if not self.coo:
            logger.info(
                "Skipping agenda engine initialization - Nexus not available",
                component="agenda_engine",
            )
            return

        try:
            from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

            # Create config with sensible defaults
            config = AgendaEngineConfig(
                default_period_hours=24,
                max_items_per_agenda=50,
                include_obstacle_resolution=True,
            )

            # Create engine with app_state reference for goal access
            self.agenda_engine = AutonomousAgendaEngine(
                app_state=self,
                config=config,
            )

            # Connect to Nexus
            await self.coo.connect_agenda_engine(self.agenda_engine)

            logger.info(
                "Autonomous Agenda Engine initialized and connected to Nexus",
                component="agenda_engine",
                hitl_enabled=config.hitl_config.enabled,
                max_items=config.max_items_per_agenda,
            )

        except ImportError as e:
            logger.warning(
                "Agenda engine module not available",
                component="agenda_engine",
                error=str(e),
            )
            self.agenda_engine = None

        except Exception as e:
            logger.warning(
                "Could not initialize agenda engine",
                component="agenda_engine",
                error=str(e),
                error_type=type(e).__name__,
            )
            self.agenda_engine = None

    async def _init_workbench(self):
        """Initialize the Workbench development environment service.

        The Workbench provides:
        - Workspace management for development environments
        - Docker-based runtime containers
        - IDE integration (code-server)
        - File and port management
        - Persistence across restarts
        """
        # First check if Docker is available
        docker_available = await self._check_docker()

        try:
            from ag3ntwerk.modules.workbench.service import get_workbench_service
            from ag3ntwerk.modules.workbench.settings import get_workbench_settings

            # Configure runner type based on Docker availability
            settings = get_workbench_settings()
            if not docker_available:
                logger.info(
                    "Docker not available - using fake runner for Workbench",
                    component="workbench",
                )
                settings.runner_type = "fake"

            self.workbench_service = get_workbench_service()
            await self.workbench_service.initialize()

            # Connect to Nexus if workbench pipeline is available
            if self.coo:
                try:
                    from ag3ntwerk.modules.workbench.pipeline import WorkbenchPipeline

                    pipeline = WorkbenchPipeline(self.workbench_service)
                    await self.coo.connect_workbench_pipeline(pipeline)
                    logger.info(
                        "Workbench pipeline connected to Nexus",
                        component="workbench",
                    )
                except ImportError:
                    logger.debug(
                        "Workbench pipeline not available",
                        component="workbench",
                    )
                except Exception as e:
                    logger.warning(
                        "Could not connect Workbench pipeline to Nexus",
                        component="workbench",
                        error=str(e),
                    )

            # Log recovery stats
            stats = self.workbench_service.get_stats()
            logger.info(
                "Workbench service initialized",
                component="workbench",
                runner_type=self.workbench_service._settings.runner_type,
                recovered_workspaces=stats.total_workspaces,
                running_workspaces=stats.running_workspaces,
            )

        except ImportError as e:
            logger.info(
                "Workbench module not available",
                component="workbench",
                reason=str(e),
            )
            self.workbench_service = None

        except Exception as e:
            logger.warning(
                "Could not initialize Workbench",
                component="workbench",
                error=str(e),
            )
            self.workbench_service = None

    async def _check_docker(self) -> bool:
        """Check if Docker is available and running."""
        import subprocess

        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug("Docker availability check failed: %s", e)
            return False

    def _init_orchestrator(self):
        self.orchestrator = Orchestrator(self.registry)
        for wf in _ALL_WORKFLOWS:
            self.orchestrator.register_workflow(wf)
        logger.info(
            "Orchestrator initialized",
            component="orchestrator",
            workflow_count=len(_ALL_WORKFLOWS),
        )

    def _seed_initial_goals(self):
        """Seed initial strategic goals from development plan if none exist."""
        if self._goals:
            return  # Don't overwrite existing goals

        strategic_goals = [
            {
                "title": "Phase 1: Foundation Hardening",
                "description": "Stabilize core platform with comprehensive test suite, error handling, state persistence, and CLI enhancements.",
                "milestones": [
                    "Comprehensive pytest test suite with >80% coverage",
                    "Custom exception hierarchy with retry logic",
                    "SQLite-backed state persistence",
                    "Enhanced CLI with status, run, and agents commands",
                ],
            },
            {
                "title": "Phase 2: Ollama Migration",
                "description": "Replace GPT4All with Ollama for cost-effective, reliable local LLM inference.",
                "milestones": [
                    "OllamaProvider implementation with full feature parity",
                    "Provider abstraction with auto-detection",
                    "Model management scripts",
                    "Performance benchmarks",
                ],
            },
            {
                "title": "Phase 3: Operations Stack Completion",
                "description": "Complete the Operations Stack agents: Index (Index), Aegis (Aegis), Accord (Accord).",
                "milestones": [
                    "Index (Index) with data governance, analytics, and knowledge managers",
                    "Aegis (Aegis) with risk assessment and scenario planning",
                    "Accord (Accord) with compliance framework support",
                    "Vector store integration for knowledge management",
                ],
            },
            {
                "title": "Phase 4: Technology Stack Enhancement",
                "description": "Complete Technology Stack and integrate with Sentinel: Foundry (Foundry), Citadel (Citadel).",
                "milestones": [
                    "Foundry (Foundry) with delivery, quality, and DevOps managers",
                    "Citadel (Citadel) as Sentinel bridge",
                    "CI/CD pipeline integration",
                    "Security posture reporting",
                ],
            },
            {
                "title": "Phase 5: Product Lifecycle Management",
                "description": "Enable ag3ntwerk to build, deploy, and operate software products (GozerAI portfolio).",
                "milestones": [
                    "Blueprint (Blueprint) for product direction",
                    "Beacon (Beacon) for customer relationships",
                    "Vector (Vector) for revenue operations",
                    "Repository abstraction and release management",
                ],
            },
            {
                "title": "Eliminate Claude API Costs",
                "description": "Q1 2026 priority: Fully migrate to local Ollama inference to eliminate external API costs.",
                "milestones": [
                    "Verify Ollama connection stability",
                    "Optimize model selection for tasks",
                    "Remove GPT4All dependencies",
                    "Document local-only deployment",
                ],
            },
        ]

        for goal_data in strategic_goals:
            goal = self.create_goal(
                title=goal_data["title"],
                description=goal_data["description"],
            )
            for milestone_title in goal_data["milestones"]:
                self.add_milestone(goal["id"], milestone_title)

        logger.info(
            "Seeded initial strategic goals",
            component="app_state",
            goal_count=len(strategic_goals),
        )

    # ------------------------------------------------------------------
    # Health Checks
    # ------------------------------------------------------------------

    def _register_health_checks(self):
        """Register health checks for all subsystems."""
        aggregator = get_health_aggregator()

        async def check_llm_provider():
            if not self.llm_provider:
                return {"status": "failing", "message": "LLM provider not configured"}
            try:
                is_healthy = await self.llm_provider.health_check()
                return {
                    "status": "passing" if is_healthy else "failing",
                    "message": (
                        "LLM provider is responsive"
                        if is_healthy
                        else "LLM provider not responding"
                    ),
                    "details": {
                        "provider": self.llm_provider.name,
                        "default_model": getattr(self.llm_provider, "default_model", None),
                    },
                }
            except Exception as e:
                return {
                    "status": "failing",
                    "message": str(e),
                    "details": {"error_type": type(e).__name__},
                }

        aggregator.register(
            "llm_provider",
            check_llm_provider,
            critical=False,
            timeout=10.0,
            description="LLM provider connectivity",
        )

        async def check_cos():
            if not self.coo:
                return {"status": "warning", "message": "Overwatch not initialized (LLM required)"}
            return {
                "status": "passing",
                "message": "Overwatch (Overwatch) is ready",
                "details": {
                    "codename": self.coo.codename,
                    "capabilities": len(self.coo.capabilities),
                },
            }

        aggregator.register(
            "cos",
            check_cos,
            critical=False,
            timeout=5.0,
            description="Overwatch (Overwatch) coordinator agent",
        )

        async def check_registry():
            if not self.registry:
                return {"status": "failing", "message": "Agent registry not initialized"}
            return {
                "status": "passing",
                "message": "Agent registry is operational",
                "details": {"registered_executives": len(self.registry.STANDARD_AGENTS)},
            }

        aggregator.register(
            "agent_registry",
            check_registry,
            critical=True,
            timeout=5.0,
            description="Agent agent registry",
        )

        async def check_orchestrator():
            if not self.orchestrator:
                return {"status": "failing", "message": "Orchestrator not initialized"}
            return {
                "status": "passing",
                "message": "Orchestrator is operational",
                "details": {"registered_workflows": len(self.orchestrator._workflows)},
            }

        aggregator.register(
            "orchestrator",
            check_orchestrator,
            critical=True,
            timeout=5.0,
            description="Workflow orchestrator",
        )

        async def check_http_pool():
            try:
                pool = await get_http_client_pool()
                return {
                    "status": "passing" if pool.is_healthy() else "warning",
                    "message": (
                        "HTTP client pool is healthy"
                        if pool.is_healthy()
                        else "HTTP client pool degraded"
                    ),
                    "details": pool.get_all_stats(),
                }
            except Exception as e:
                return {"status": "failing", "message": str(e)}

        aggregator.register(
            "http_client_pool",
            check_http_pool,
            critical=False,
            timeout=5.0,
            description="HTTP connection pool",
        )

        async def check_integrations():
            from ag3ntwerk.core.config import get_config as _get_config

            integ = _get_config().integrations
            summary = integ.summary()
            active = [k for k, v in summary.items() if v]
            if not active:
                return {
                    "status": "warning",
                    "message": "No Revenue Stack integrations configured",
                    "details": summary,
                }
            return {
                "status": "passing",
                "message": f"{len(active)} integration(s) configured: {', '.join(active)}",
                "details": summary,
            }

        aggregator.register(
            "integrations",
            check_integrations,
            critical=False,
            timeout=5.0,
            description="Revenue Stack integrations (social, payments, voice)",
        )

        async def check_database():
            if not self.database:
                return {
                    "status": "warning",
                    "message": "Database not initialized (running in memory-only mode)",
                }
            try:
                # Simple query to test connectivity
                await self.database.fetch_one("SELECT 1")
                return {
                    "status": "passing",
                    "message": "Database is operational",
                    "details": {"backend": self.database.config.backend.value},
                }
            except Exception as e:
                return {"status": "failing", "message": f"Database error: {e}"}

        aggregator.register(
            "database",
            check_database,
            critical=False,
            timeout=5.0,
            description="SQLite/PostgreSQL persistence",
        )

        async def check_task_queue():
            if not self.task_queue:
                return {"status": "warning", "message": "Task queue not initialized"}
            try:
                stats = await self.task_queue.get_stats()
                return {
                    "status": "passing",
                    "message": "Task queue is operational",
                    "details": {
                        "pending": stats.pending,
                        "processing": stats.processing,
                        "completed": stats.completed,
                        "failed": stats.failed,
                    },
                }
            except Exception as e:
                return {"status": "failing", "message": f"Task queue error: {e}"}

        aggregator.register(
            "task_queue",
            check_task_queue,
            critical=False,
            timeout=5.0,
            description="SQLite-backed task queue",
        )

        async def check_workbench():
            if not self.workbench_service:
                return {"status": "warning", "message": "Workbench not initialized"}
            try:
                is_healthy = await self.workbench_service.is_healthy()
                stats = self.workbench_service.get_stats()
                return {
                    "status": "passing" if is_healthy else "warning",
                    "message": "Workbench is operational" if is_healthy else "Workbench degraded",
                    "details": {
                        "total_workspaces": stats.total_workspaces,
                        "running_workspaces": stats.running_workspaces,
                        "runner_type": self.workbench_service._settings.runner_type,
                    },
                }
            except Exception as e:
                return {"status": "failing", "message": f"Workbench error: {e}"}

        aggregator.register(
            "workbench",
            check_workbench,
            critical=False,
            timeout=5.0,
            description="Development environment workbench",
        )

        async def check_metacognition():
            if not self.coo:
                return {
                    "status": "warning",
                    "message": "Overwatch not initialized, metacognition unavailable",
                }
            metacog_svc = getattr(self.coo, "_metacognition_service", None)
            if metacog_svc is None:
                return {"status": "warning", "message": "Metacognition service not connected"}
            try:
                stats = metacog_svc.get_stats()
                registered = stats.get("registered_agents", [])
                agent_health = stats.get("agent_health", {})
                unhealthy = [
                    code
                    for code, health in agent_health.items()
                    if health in ("critical", "unhealthy")
                ]
                status = "passing"
                message = f"Metacognition service active with {len(registered)} agent(s)"
                if unhealthy:
                    status = "warning"
                    message = f"Metacognition active but {len(unhealthy)} agent(s) unhealthy: {', '.join(unhealthy)}"
                return {
                    "status": status,
                    "message": message,
                    "details": {
                        "registered_agents": len(registered),
                        "total_reflections": stats.get("total_reflections", 0),
                        "total_outcomes_tracked": stats.get("total_outcomes_tracked", 0),
                        "unhealthy_agents": unhealthy,
                    },
                }
            except Exception as e:
                return {"status": "failing", "message": f"Metacognition error: {e}"}

        aggregator.register(
            "metacognition",
            check_metacognition,
            critical=False,
            timeout=5.0,
            description="Metacognition service (personality, reflection, heuristics)",
        )

        async def check_learning_pipeline():
            if not self.coo:
                return {
                    "status": "warning",
                    "message": "Overwatch not initialized, learning pipeline unavailable",
                }
            # The pipeline is typically attached to the Overwatch or accessible via learning routes
            pipeline = getattr(self.coo, "_learning_pipeline", None) or getattr(
                self.coo, "_continuous_pipeline", None
            )
            if pipeline is None:
                # Try to find it through the learning orchestrator
                orch = getattr(self.coo, "_learning_orchestrator", None)
                pipeline = getattr(orch, "_pipeline", None) if orch else None
            if pipeline is None:
                return {"status": "warning", "message": "Learning pipeline not initialized"}
            try:
                from ag3ntwerk.learning.continuous_pipeline import PipelineState

                state_value = pipeline.state
                if state_value == PipelineState.ERROR:
                    return {
                        "status": "failing",
                        "message": f"Learning pipeline in ERROR state ({pipeline._consecutive_errors} consecutive errors)",
                        "details": {
                            "state": state_value.value,
                            "total_cycles": pipeline._total_cycles,
                            "failed_cycles": pipeline._failed_cycles,
                            "consecutive_errors": pipeline._consecutive_errors,
                        },
                    }
                elif state_value == PipelineState.RUNNING:
                    success_rate = (
                        pipeline._successful_cycles / pipeline._total_cycles
                        if pipeline._total_cycles > 0
                        else 1.0
                    )
                    status = "passing" if success_rate >= 0.7 else "warning"
                    return {
                        "status": status,
                        "message": f"Learning pipeline running ({pipeline._total_cycles} cycles, {success_rate:.0%} success)",
                        "details": {
                            "state": state_value.value,
                            "total_cycles": pipeline._total_cycles,
                            "successful_cycles": pipeline._successful_cycles,
                            "failed_cycles": pipeline._failed_cycles,
                            "success_rate": round(success_rate, 3),
                        },
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Learning pipeline is {state_value.value}",
                        "details": {"state": state_value.value},
                    }
            except Exception as e:
                return {"status": "failing", "message": f"Learning pipeline error: {e}"}

        aggregator.register(
            "learning_pipeline",
            check_learning_pipeline,
            critical=False,
            timeout=5.0,
            description="Continuous learning pipeline cycle health",
        )

        async def check_ollama():
            if not self.ollama_manager:
                return {
                    "status": "warning",
                    "message": "Ollama not initialized (using external LLM)",
                }
            try:
                is_healthy = await self.ollama_manager.check_health()
                models = await self.ollama_manager.get_models() if is_healthy else []
                return {
                    "status": "passing" if is_healthy else "failing",
                    "message": "Ollama is running" if is_healthy else "Ollama not responding",
                    "details": {
                        "host": self.ollama_manager.host,
                        "models_available": len(models),
                        "started_by_us": self.ollama_manager._started_by_us,
                    },
                }
            except Exception as e:
                return {"status": "failing", "message": f"Ollama error: {e}"}

        aggregator.register(
            "ollama",
            check_ollama,
            critical=False,
            timeout=10.0,
            description="Local LLM inference (Ollama)",
        )

        logger.info("Health checks registered", check_count=12, component="health")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self):
        """Shutdown the ag3ntwerk system with graceful task draining."""
        logger.info("Shutting down ag3ntwerk system", component="app_state")

        shutdown_manager = await get_shutdown_manager()

        async def close_llm():
            if self.llm_provider:
                try:
                    await self.llm_provider.disconnect()
                    logger.info("LLM provider disconnected")
                except Exception as e:
                    logger.warning("Error during LLM provider shutdown", error=str(e))

        async def close_http_pool():
            try:
                await shutdown_http_clients()
                logger.info("HTTP client pool shutdown complete", component="http_client")
            except Exception as e:
                logger.warning(
                    "Error during HTTP client pool shutdown", component="http_client", error=str(e)
                )

        async def close_websockets():
            for ws in list(self.websocket_clients):
                try:
                    await ws.close(code=1001, reason="Server shutdown")
                except Exception as e:
                    logger.debug("Error closing WebSocket connection during shutdown: %s", e)
            self.websocket_clients.clear()
            logger.info("WebSocket connections closed", component="websocket")

        async def close_task_queue():
            try:
                await shutdown_queue()
                logger.info("Task queue shutdown complete", component="task_queue")
            except Exception as e:
                logger.warning(
                    "Error during task queue shutdown", component="task_queue", error=str(e)
                )

        async def close_database():
            if self.database:
                try:
                    from ag3ntwerk.persistence.database import close_database as _close_db

                    await _close_db()
                    logger.info("Database shutdown complete", component="database")
                except Exception as e:
                    logger.warning(
                        "Error during database shutdown", component="database", error=str(e)
                    )

        async def close_workbench():
            if self.workbench_service:
                try:
                    await self.workbench_service.shutdown()
                    logger.info("Workbench service shutdown complete", component="workbench")
                except Exception as e:
                    logger.warning(
                        "Error during Workbench shutdown", component="workbench", error=str(e)
                    )

        async def close_ollama():
            if self.ollama_manager:
                try:
                    await self.ollama_manager.stop_health_monitoring()
                    # Note: We don't stop Ollama itself - it can keep running
                    logger.info("Ollama health monitoring stopped", component="ollama")
                except Exception as e:
                    logger.warning("Error during Ollama shutdown", component="ollama", error=str(e))

        shutdown_manager.register_hook("close_websockets", close_websockets, priority=10)
        shutdown_manager.register_hook("close_workbench", close_workbench, priority=15)
        shutdown_manager.register_hook("close_ollama", close_ollama, priority=18)
        shutdown_manager.register_hook("close_llm", close_llm, priority=20)
        shutdown_manager.register_hook("close_http_pool", close_http_pool, priority=30)
        shutdown_manager.register_hook("close_task_queue", close_task_queue, priority=40)
        shutdown_manager.register_hook("close_database", close_database, priority=50)

        graceful = await shutdown_manager.shutdown(drain_timeout=30.0, force_timeout=60.0)

        self.initialized = False
        logger.info("ag3ntwerk system shutdown complete", component="app_state", graceful=graceful)

    # ------------------------------------------------------------------
    # Task helpers
    # ------------------------------------------------------------------

    def create_task(
        self, description: str, task_type: str, priority: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new task."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter:04d}"
        task = {
            "id": task_id,
            "description": description,
            "task_type": task_type,
            "priority": priority,
            "status": "pending",
            "context": context,
            "result": None,
            "routed_to": None,
            "created_at": datetime.now().isoformat(),
        }
        self._tasks[task_id] = task
        return task

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks."""
        return list(self._tasks.values())

    # ------------------------------------------------------------------
    # Goal helpers
    # ------------------------------------------------------------------

    def create_goal(
        self,
        title: str,
        description: Optional[str] = None,
        milestones: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create a new goal."""
        self._goal_counter += 1
        goal_id = f"goal_{self._goal_counter:04d}"
        milestone_list = []
        if milestones:
            for i, m in enumerate(milestones):
                milestone_list.append(
                    {
                        "id": f"{goal_id}_m{i + 1}",
                        "title": m.get("title", ""),
                        "status": "pending",
                    }
                )
        goal = {
            "id": goal_id,
            "title": title,
            "description": description,
            "status": "active",
            "progress": 0.0,
            "milestones": milestone_list,
            "created_at": datetime.now().isoformat(),
        }
        self._goals[goal_id] = goal
        return goal

    def list_goals(self) -> List[Dict[str, Any]]:
        """List all goals."""
        return list(self._goals.values())

    def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def update_goal(self, goal_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        for key in ("title", "description", "status", "progress"):
            if key in updates and updates[key] is not None:
                goal[key] = updates[key]
        return goal

    def add_milestone(self, goal_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Add a milestone to a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        milestone_num = len(goal["milestones"]) + 1
        milestone = {
            "id": f"{goal_id}_m{milestone_num}",
            "title": title,
            "status": "pending",
        }
        goal["milestones"].append(milestone)
        return milestone

    def update_milestone(
        self, goal_id: str, milestone_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        """Update a milestone status."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        for m in goal["milestones"]:
            if m["id"] == milestone_id:
                m["status"] = status
                # Recalculate progress
                completed = sum(1 for ms in goal["milestones"] if ms["status"] == "completed")
                total = len(goal["milestones"])
                goal["progress"] = (completed / total * 100) if total > 0 else 0.0
                return m
        return None

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcast event to all connected WebSocket clients."""
        message = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        disconnected = []

        for ws in self.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.debug(f"WebSocket client disconnected during broadcast: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            self.websocket_clients.remove(ws)


# Module-level singleton
state = AppState()
