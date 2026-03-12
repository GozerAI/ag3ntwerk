"""
ag3ntwerk Command Center - Unified FastAPI Backend

This is the single API endpoint for managing ag3ntwerk AI agents:
- Nexus (Nexus) - Central control plane and task routing
- Forge (Forge) - Technology and development
- Keystone (Keystone) - Finance and budgeting
- And more...
"""

# Load environment variables from .env file before any other imports
from dotenv import load_dotenv

load_dotenv()

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

from pathlib import Path as FilePath

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Query,
    Path,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Import auth dependencies
from ag3ntwerk.api.auth import (
    require_auth,
    optional_auth,
    AuthenticatedUser,
    Permission,
)

# Import extracted modules
from ag3ntwerk.api.models import (
    TaskCreate,
    ChatMessage,
    WorkflowExecute,
    MAX_WORKFLOW_NAME_LENGTH,
    GoalCreate,
    GoalUpdate,
    MilestoneCreate,
    COOModeUpdate,
)
from ag3ntwerk.api.state import state
from ag3ntwerk.api.services import (
    TaskService,
    ChatService,
    WorkflowService,
    GoalService,
    MemoryService,
    COOService,
)

# Import structured logging
from ag3ntwerk.core.logging import (
    get_logger,
    configure_logging,
    set_log_context,
    clear_log_context,
)

# Import health check system
from ag3ntwerk.core.health import (
    get_aggregated_health,
    check_readiness,
    check_liveness,
    HealthStatus,
)

# Import shutdown manager
from ag3ntwerk.core.shutdown import get_shutdown_manager, setup_signal_handlers

# Import configuration
from ag3ntwerk.core.config import get_config

# Import metrics
from ag3ntwerk.core.metrics import get_metrics_collector

# Import error handling
from ag3ntwerk.core.errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

from ag3ntwerk.api.module_routes import (
    modules_router,
    trends_router,
    commerce_router,
    brand_router,
    scheduler_router,
)
from ag3ntwerk.modules.workbench.module_routes import workbench_router
from ag3ntwerk.api.webhooks import router as webhooks_router
from ag3ntwerk.api.interview_routes import router as interviews_router
from ag3ntwerk.api.content_routes import router as content_router
from ag3ntwerk.api.voice_routes import router as voice_router
from ag3ntwerk.api.workflow_routes import router as workflow_router
from ag3ntwerk.api.automation_routes import (
    research_router,
    harvesting_router,
    security_router as security_automation_router,
)
from ag3ntwerk.api.fleet_routes import fleet_router
from ag3ntwerk.api.swarm_routes import swarm_router
from ag3ntwerk.api.learning_routes import router as learning_router
from ag3ntwerk.api.metacognition_routes import router as metacognition_router


# ============================================================
# Logging Configuration
# ============================================================

_log_format = os.getenv("LOG_FORMAT", "console").lower()
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
configure_logging(
    level=_log_level,
    json_output=(_log_format == "json"),
    include_stack_info=True,
)
logger = get_logger(__name__)


# ============================================================
# Auth Configuration
# ============================================================

# Configurable auth: set AGENTWERK_AUTH_REQUIRED=true in production
_auth_required = os.getenv("AGENTWERK_AUTH_REQUIRED", "false").lower() == "true"


def get_auth_dependency(permissions: Optional[set] = None):
    """Return auth dependency based on configuration."""
    if _auth_required:
        return require_auth(permissions)
    return optional_auth()


# Context variable for request ID - accessible throughout the request lifecycle
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """
    Get the current request ID.

    Returns the request ID from the context variable, or an empty string
    if called outside of a request context.

    Usage:
        from ag3ntwerk.api.app import get_request_id

        def my_function():
            request_id = get_request_id()
            logger.info(f"Processing request {request_id}")
    """
    return request_id_var.get()


# ============================================================
# Rate Limiting
# ============================================================

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    Limiter = None

# Import Environment enum for production-specific checks
from ag3ntwerk.core.config import Environment

# Import built-in rate limiter as mandatory fallback for auth endpoints.
# Auth endpoints must ALWAYS be rate-limited, even when slowapi is missing.
from ag3ntwerk.api.auth import RateLimiter as AuthRateLimiter

# Strict rate limiters for auth-sensitive endpoints (always active).
# These use the built-in token-bucket implementation from auth.py so
# auth endpoints are *never* unprotected, even when slowapi is absent.
_auth_rate_limiter = AuthRateLimiter(requests_per_minute=5, burst_size=5)
_api_key_rate_limiter = AuthRateLimiter(requests_per_minute=10, burst_size=10)


def _get_client_ip(request: Request) -> str:
    """Extract client IP for rate-limiting keying."""
    if request.client:
        return request.client.host
    return "unknown"


async def enforce_auth_rate_limit(request: Request) -> None:
    """
    Enforce strict rate limiting on authentication endpoints.

    Raises HTTP 429 if the caller exceeds the allowed rate (5 req/min).
    Always active regardless of slowapi availability.
    """
    client_ip = _get_client_ip(request)
    if not _auth_rate_limiter.is_allowed(client_ip):
        remaining = _auth_rate_limiter.get_remaining(client_ip)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for authentication endpoint. Try again later.",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": str(remaining)},
        )


async def enforce_api_key_rate_limit(request: Request) -> None:
    """
    Enforce rate limiting on API key validation endpoints.

    Slightly higher limit (10 req/min) than login/token endpoints (5 req/min).
    Always active regardless of slowapi availability.
    """
    client_ip = _get_client_ip(request)
    if not _api_key_rate_limiter.is_allowed(client_ip):
        remaining = _api_key_rate_limiter.get_remaining(client_ip)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for API key endpoint. Try again later.",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": str(remaining)},
        )


# ============================================================
# Shutdown Flag - shared across middleware and lifespan
# ============================================================

_shutting_down = False
_in_flight_requests = 0
_in_flight_lock = asyncio.Lock()
_drain_complete = asyncio.Event()

# Default drain timeout in seconds; override via AGENTWERK_DRAIN_TIMEOUT env var
_drain_timeout = float(os.getenv("AGENTWERK_DRAIN_TIMEOUT", "30"))


def is_shutting_down() -> bool:
    """Check whether the application is shutting down.

    Route handlers or background tasks can call this to bail out
    early when a graceful shutdown is in progress.
    """
    return _shutting_down


# ============================================================
# Lifespan Management
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful shutdown."""
    global _shutting_down, _in_flight_requests

    logger.info("Starting ag3ntwerk Command Center", component="lifespan", phase="startup")

    # Initialise the shutdown manager and wire signal handlers
    shutdown_manager = await get_shutdown_manager()
    setup_signal_handlers(shutdown_manager)

    # Check rate-limiting availability at startup
    config = get_config()
    if not RATE_LIMITING_AVAILABLE:
        if config.environment == Environment.PRODUCTION:
            logger.error(
                "SECURITY WARNING: slowapi is not installed -- external rate limiting "
                "is disabled in PRODUCTION. Auth endpoints use built-in fallback "
                "rate limiting, but slowapi is strongly recommended. "
                "Install with: pip install slowapi",
                component="security",
                phase="startup",
            )
        else:
            logger.warning(
                "slowapi not installed -- external rate limiting disabled. "
                "Auth endpoints are protected by built-in fallback rate limiter. "
                "Install slowapi for full rate limiting: pip install slowapi",
                component="security",
                phase="startup",
            )
    else:
        logger.info(
            "Rate limiting enabled via slowapi",
            component="security",
            phase="startup",
        )

    await state.initialize()
    logger.info(
        "ag3ntwerk Command Center is ready to accept requests",
        component="lifespan",
        phase="startup",
    )

    yield  # ---- application is running ----

    # -- Graceful shutdown begins --
    logger.info(
        "Shutdown signal received -- beginning graceful shutdown",
        component="lifespan",
        phase="shutdown",
    )

    # 1. Set the flag so the middleware rejects NEW requests with 503.
    _shutting_down = True

    # 2. Wait for in-flight requests to drain (up to _drain_timeout).
    drain_deadline = asyncio.get_event_loop().time() + _drain_timeout
    while True:
        async with _in_flight_lock:
            count = _in_flight_requests
        if count == 0:
            logger.info(
                "All in-flight requests drained",
                component="lifespan",
                phase="shutdown",
            )
            break
        remaining = drain_deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            logger.warning(
                "Drain timeout exceeded with requests still in flight",
                component="lifespan",
                phase="shutdown",
                in_flight=count,
                drain_timeout=_drain_timeout,
            )
            break
        logger.info(
            "Waiting for in-flight requests to complete",
            component="lifespan",
            phase="shutdown",
            in_flight=count,
            remaining_seconds=round(remaining, 1),
        )
        await asyncio.sleep(min(0.5, remaining))

    # 3. Shut down background tasks, connections, database via state
    logger.info(
        "Shutting down subsystems (learning pipeline, metacognition, DB, etc.)",
        component="lifespan",
        phase="shutdown",
    )
    await state.shutdown()

    logger.info(
        "ag3ntwerk Command Center shutdown complete",
        component="lifespan",
        phase="shutdown",
    )


# ============================================================
# FastAPI Application
# ============================================================

if RATE_LIMITING_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None

app = FastAPI(
    title="ag3ntwerk Command Center",
    description="Unified API for ag3ntwerk AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiting error handler if available
if RATE_LIMITING_AVAILABLE and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================
# Exception Handlers
# ============================================================


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    """Handle HTTPException with standardized format."""
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception):
    """Handle all other exceptions with standardized format."""
    config = get_config()
    return await generic_exception_handler(request, exc, include_debug=config.debug)


try:
    from pydantic import ValidationError

    @app.exception_handler(ValidationError)
    async def handle_validation_exception(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors with standardized format."""
        return await validation_exception_handler(request, exc)

except ImportError:
    pass


# ============================================================
# Middleware
# ============================================================

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def shutdown_guard(request: Request, call_next):
    """Return 503 for new requests when the application is shutting down.

    Health endpoints are exempted so that orchestrators (e.g. Kubernetes)
    can still query liveness/readiness during the drain period.
    """
    global _in_flight_requests

    # Allow health probes through even during shutdown
    _exempt_paths = ("/health", "/health/live", "/health/ready", "/health/detailed")
    if _shutting_down and request.url.path not in _exempt_paths:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Service is shutting down",
                "retry_after": 5,
            },
            headers={"Retry-After": "5"},
        )

    # Track in-flight requests for drain logic
    async with _in_flight_lock:
        _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        async with _in_flight_lock:
            _in_flight_requests -= 1


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing and observability."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_var.set(request_id)
    request.state.request_id = request_id

    set_log_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )

    logger.debug(
        "Request started",
        query_params=str(request.query_params) if request.query_params else None,
    )

    try:
        response = await call_next(request)
        logger.debug("Request completed", status_code=response.status_code)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
    finally:
        clear_log_context()


_is_production_env = (
    os.getenv("AGENTWERK_ENV", os.getenv("ENVIRONMENT", "development")).lower() == "production"
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if _is_production_env:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Auth-sensitive path prefixes that receive strict rate limiting (5 req/min).
# These are endpoints where credential submission or token generation occurs.
_AUTH_RATE_LIMITED_PATHS = {
    "/api/v1/fleet/relays/token",  # relay token generation
}

# Auth-sensitive path prefixes that receive moderate rate limiting (10 req/min).
# These are endpoints that accept API keys or bearer tokens for validation.
_API_KEY_RATE_LIMITED_PREFIXES = (
    "/api/v1/tasks",  # accepts auth credentials
    "/api/v1/chat",  # accepts auth credentials
    "/api/v1/workflows/execute",  # accepts auth credentials
    "/api/v1/coo/start",  # admin auth endpoint
    "/api/v1/coo/stop",  # admin auth endpoint
    "/api/v1/coo/mode",  # admin auth endpoint
)


@app.middleware("http")
async def auth_endpoint_rate_limit(request: Request, call_next):
    """Enforce mandatory rate limiting on auth-sensitive endpoints.

    This middleware runs regardless of whether slowapi is installed.
    Auth endpoints are always rate-limited to prevent brute-force attacks.
    """
    path = request.url.path

    # Strict limit for token-generation / login-equivalent endpoints
    if path in _AUTH_RATE_LIMITED_PATHS:
        await enforce_auth_rate_limit(request)

    # Moderate limit for endpoints that accept credentials
    elif any(path.startswith(prefix) for prefix in _API_KEY_RATE_LIMITED_PREFIXES):
        await enforce_api_key_rate_limit(request)

    return await call_next(request)


# ============================================================
# Module Routers
# ============================================================

app.include_router(modules_router)
app.include_router(trends_router)
app.include_router(commerce_router)
app.include_router(brand_router)
app.include_router(scheduler_router)
app.include_router(workbench_router)
app.include_router(webhooks_router)
app.include_router(interviews_router)
app.include_router(content_router)
app.include_router(voice_router)
app.include_router(workflow_router)
app.include_router(research_router)
app.include_router(harvesting_router)
app.include_router(security_automation_router)
app.include_router(fleet_router)
app.include_router(learning_router)
app.include_router(metacognition_router)
app.include_router(swarm_router)


# ============================================================
# Service Instances
# ============================================================

_task_service = TaskService(state)
_chat_service = ChatService(state)
_workflow_service = WorkflowService(state, is_production=_is_production_env)
_goal_service = GoalService(state)
_memory_service = MemoryService(state)
_coo_service = COOService(state)


# ============================================================
# Health & Status Endpoints
# ============================================================


@app.get("/api")
async def api_root():
    """API root info."""
    return {
        "name": "ag3ntwerk Command Center",
        "version": "1.0.0",
        "status": "running" if state.initialized else "initializing",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Basic health check endpoint (Kubernetes liveness probe compatible)."""
    return {
        "status": "healthy" if state.initialized else "initializing",
        "llm_connected": state.llm_provider is not None,
        "coo_ready": state.coo is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/live")
async def liveness():
    """Kubernetes liveness probe endpoint."""
    is_alive = await check_liveness()
    if is_alive:
        return {"status": "alive"}
    return JSONResponse(status_code=503, content={"status": "dead"})


@app.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe endpoint."""
    is_ready = await check_readiness()
    if is_ready:
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not_ready"})


@app.get("/health/detailed")
async def detailed_health(force_refresh: bool = Query(default=False)):
    """Detailed health check endpoint with aggregated status from all subsystems."""
    health_result = await get_aggregated_health(
        force_refresh=force_refresh,
        include_details=True,
    )

    status_code = 200
    if health_result.status == HealthStatus.UNHEALTHY:
        status_code = 503
    elif health_result.status == HealthStatus.DEGRADED:
        status_code = 200

    return JSONResponse(status_code=status_code, content=health_result.to_dict())


@app.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint for monitoring."""
    collector = get_metrics_collector()
    return collector.get_summary()


@app.get("/api/v1/status")
async def get_status():
    """Get comprehensive system status."""
    agents = []
    if state.registry:
        for code, (module, class_name) in state.registry.STANDARD_AGENTS.items():
            agents.append(
                {
                    "code": code,
                    "codename": code,
                    "available": state.llm_provider is not None,
                }
            )

    return {
        "initialized": state.initialized,
        "llm_connected": state.llm_provider is not None,
        "coo_ready": state.coo is not None,
        "agents": agents,
        "tasks": {
            "total": len(state._tasks),
            "pending": len([t for t in state._tasks.values() if t["status"] == "pending"]),
            "completed": len([t for t in state._tasks.values() if t["status"] == "completed"]),
        },
        "websocket_clients": len(state.websocket_clients),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Agent Endpoints
# ============================================================


@app.get("/api/v1/agents")
async def list_agents():
    """List all available ag3ntwerk agents."""
    from ag3ntwerk.modules import get_modules_for_executive, get_module_info

    agents = []
    if state.registry:
        for code, (module, class_name) in state.registry.STANDARD_AGENTS.items():
            entry = {
                "code": code,
                "codename": code,
                "available": state.llm_provider is not None,
            }

            # Include capabilities, domain, and modules if agent is instantiated
            agent = state.registry.get(code)
            if agent:
                entry["domain"] = agent.domain
                entry["capabilities"] = getattr(agent, "capabilities", [])

                module_ids = get_modules_for_executive(code)
                entry["modules"] = [
                    {
                        "id": mid,
                        "name": get_module_info(mid).get("name", mid),
                        "description": get_module_info(mid).get("description", ""),
                        "ownership": (
                            "primary"
                            if code in get_module_info(mid).get("primary_owners", [])
                            else "secondary"
                        ),
                    }
                    for mid in module_ids
                    if get_module_info(mid)
                ]

            agents.append(entry)

    return {"agents": agents, "count": len(agents)}


# ============================================================
# Task Endpoints
# ============================================================


@app.get("/api/v1/tasks")
async def list_tasks():
    """List all tasks."""
    tasks = state.list_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.post("/api/v1/tasks")
async def create_task(
    request: Request,
    task: TaskCreate,
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Create a new task."""
    if limiter:
        pass  # Rate limiting handled by slowapi decorator, not .check()

    return await _task_service.create_and_execute(
        description=task.description,
        task_type=task.task_type,
        priority=task.priority,
        context=task.context,
    )


# ============================================================
# Dashboard Stats Endpoint
# ============================================================


@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    tasks = state.list_tasks()
    goals = state.list_goals()
    executives_count = len(state.registry.STANDARD_AGENTS) if state.registry else 0

    return {
        "tasks": {
            "total": len(tasks),
            "active": len([t for t in tasks if t["status"] in ("pending", "running")]),
            "completed": len([t for t in tasks if t["status"] == "completed"]),
        },
        "goals": {
            "total": len(goals),
            "active": len([g for g in goals if g["status"] == "active"]),
        },
        "memory": {"total_chunks": 0},
        "knowledge": {"total_entities": 0, "total_facts": 0},
        "decisions": {"total": 0},
        "coo": {
            "state": "running" if state.coo else "not_available",
            "mode": state._coo_mode,
        },
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# Nexus Endpoints
# ============================================================


@app.get("/api/v1/coo/status")
async def get_coo_status():
    """Get Nexus status."""
    return await _coo_service.get_status()


@app.post("/api/v1/coo/start")
async def start_coo(
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.ADMIN})),
):
    """Start the Nexus."""
    if state.coo:
        return {"success": True, "message": "Nexus already running"}

    if state.llm_provider is None:
        raise HTTPException(status_code=500, detail="LLM provider not initialized")

    try:
        if state.registry:
            state.coo = state.registry.get("Nexus")
        else:
            from ag3ntwerk.agents.overwatch import Overwatch

            state.coo = Overwatch(llm_provider=state.llm_provider)

        state._coo_start_time = datetime.now()
        await state.broadcast("coo_started", {"timestamp": datetime.now().isoformat()})
        return {"success": True, "message": "Nexus started"}

    except Exception as e:  # Intentional catch-all: API route handler
        logger.error("Failed to start Nexus: %s", e, exc_info=True)
        return {"success": False, "message": f"Failed to start Nexus: {e}"}


@app.post("/api/v1/coo/stop")
async def stop_coo(
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.ADMIN})),
):
    """Stop the Nexus."""
    state.coo = None
    state._coo_start_time = None
    await state.broadcast("coo_stopped", {"timestamp": datetime.now().isoformat()})
    return {"success": True, "message": "Nexus stopped"}


@app.post("/api/v1/coo/mode")
async def set_coo_mode(
    mode_update: COOModeUpdate,
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.ADMIN})),
):
    """Set the Nexus operating mode."""
    return await _coo_service.set_mode(mode_update.mode)


@app.get("/api/v1/coo/suggestions")
async def get_coo_suggestions():
    """Get the next suggested action from Nexus."""
    return await _coo_service.get_suggestions()


@app.post("/api/v1/coo/suggestions/{suggestion_id}/approve")
async def approve_coo_suggestion(
    suggestion_id: str = Path(..., min_length=1, max_length=100),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Approve and execute a Nexus suggestion."""
    return await _coo_service.approve_suggestion(suggestion_id)


@app.post("/api/v1/coo/suggestions/{suggestion_id}/reject")
async def reject_coo_suggestion(
    suggestion_id: str = Path(..., min_length=1, max_length=100),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Reject a Nexus suggestion."""
    return await _coo_service.reject_suggestion(suggestion_id)


# ============================================================
# Autonomous Agenda Engine Endpoints
# ============================================================


@app.get("/api/v1/coo/agenda")
async def get_agenda_status():
    """Get the current agenda status."""
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")
    return state.coo.get_agenda_status()


@app.post("/api/v1/coo/agenda/generate")
async def generate_agenda(
    period_hours: int = Query(24, ge=1, le=168),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Generate a new autonomous agenda.

    Args:
        period_hours: Duration of agenda period (1-168 hours, default 24)
    """
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")
    if not state.coo.is_agenda_enabled():
        raise HTTPException(status_code=503, detail="Agenda engine not connected")

    goals = state.list_goals()
    return await state.coo.generate_agenda(period_hours=period_hours, goals=goals)


@app.get("/api/v1/coo/agenda/items")
async def get_agenda_items(
    count: int = Query(10, ge=1, le=50),
    include_awaiting_approval: bool = Query(True),
):
    """Get agenda items.

    Args:
        count: Maximum number of items to return (1-50, default 10)
        include_awaiting_approval: Include items awaiting approval (default True)
    """
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    return await state.coo.get_agenda_items(
        count=count,
        include_awaiting_approval=include_awaiting_approval,
    )


@app.post("/api/v1/coo/agenda/items/{item_id}/execute")
async def execute_agenda_item(
    item_id: str = Path(..., min_length=1, max_length=100),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Execute a specific agenda item."""
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    result = await state.coo.execute_agenda_item(item_id)
    return {
        "success": result.success,
        "item_id": item_id,
        "output": result.output,
        "error": result.error,
    }


@app.post("/api/v1/coo/agenda/items/{item_id}/approve")
async def approve_agenda_item(
    item_id: str = Path(..., min_length=1, max_length=100),
    notes: str = Query("", max_length=500),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Approve an agenda item for execution."""
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    approver = user.metadata.get("email", user.user_id) if user else "anonymous"
    success = await state.coo.approve_agenda_item(item_id, approver, notes)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Agenda item not found or already processed: {item_id}"
        )

    return {"success": True, "item_id": item_id, "status": "approved"}


@app.post("/api/v1/coo/agenda/items/{item_id}/reject")
async def reject_agenda_item(
    item_id: str = Path(..., min_length=1, max_length=100),
    reason: str = Query(..., min_length=1, max_length=500),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Reject an agenda item."""
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    approver = user.metadata.get("email", user.user_id) if user else "anonymous"
    success = await state.coo.reject_agenda_item(item_id, approver, reason)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Agenda item not found or already processed: {item_id}"
        )

    return {"success": True, "item_id": item_id, "status": "rejected", "reason": reason}


@app.get("/api/v1/coo/agenda/obstacles")
async def get_agenda_obstacles(
    goal_id: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, max_length=20),
):
    """Get obstacles identified by the agenda engine.

    Args:
        goal_id: Filter by goal ID
        status: Filter by status (active, resolved)
    """
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    return state.coo.get_agenda_obstacles(goal_id=goal_id, status=status)


@app.get("/api/v1/coo/agenda/strategies")
async def get_agenda_strategies(
    obstacle_id: Optional[str] = Query(None, max_length=100),
):
    """Get strategies generated by the agenda engine.

    Args:
        obstacle_id: Filter by obstacle ID
    """
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    return state.coo.get_agenda_strategies(obstacle_id=obstacle_id)


@app.get("/api/v1/coo/agenda/workstreams")
async def get_agenda_workstreams(
    goal_id: Optional[str] = Query(None, max_length=100),
):
    """Get workstreams from the agenda engine.

    Args:
        goal_id: Filter by goal ID
    """
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    if not state.coo.is_agenda_enabled():
        return []

    workstreams = state.coo._agenda_engine.list_workstreams(goal_id=goal_id)
    return [ws.to_dict() for ws in workstreams]


@app.post("/api/v1/coo/agenda/batch-approve")
async def batch_approve_agenda_items(
    item_ids: list[str] = Query(..., min_length=1, max_length=50),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_TASK})),
):
    """Batch approve multiple agenda items."""
    if not state.coo:
        raise HTTPException(status_code=503, detail="Nexus not running")

    approver = user.email if user else "anonymous"
    count = (
        state.coo._agenda_engine.batch_approve(item_ids, approver)
        if state.coo.is_agenda_enabled()
        else 0
    )

    return {"success": True, "approved_count": count, "total_requested": len(item_ids)}


# ============================================================
# Goal Endpoints
# ============================================================


@app.get("/api/v1/goals")
async def list_goals():
    """List all goals."""
    return await _goal_service.list_goals()


@app.post("/api/v1/goals")
async def create_goal(
    goal: GoalCreate,
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Create a new goal."""
    return await _goal_service.create_goal(
        title=goal.title,
        description=goal.description,
        milestones=goal.milestones,
    )


@app.get("/api/v1/goals/{goal_id}")
async def get_goal(
    goal_id: str = Path(..., min_length=1, max_length=50),
):
    """Get a specific goal."""
    goal = state.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")
    return goal


@app.put("/api/v1/goals/{goal_id}")
async def update_goal(
    updates: GoalUpdate,
    goal_id: str = Path(..., min_length=1, max_length=50),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Update a goal."""
    return await _goal_service.update_goal(goal_id, updates.model_dump(exclude_unset=True))


@app.post("/api/v1/goals/{goal_id}/milestones")
async def add_milestone(
    milestone: MilestoneCreate,
    goal_id: str = Path(..., min_length=1, max_length=50),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Add a milestone to a goal."""
    return await _goal_service.add_milestone(goal_id, milestone.title)


@app.put("/api/v1/goals/{goal_id}/milestones/{milestone_id}")
async def update_milestone(
    goal_id: str = Path(..., min_length=1, max_length=50),
    milestone_id: str = Path(..., min_length=1, max_length=50),
    status: str = Query(..., pattern="^(pending|completed)$"),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Update a milestone status."""
    return await _goal_service.update_milestone(goal_id, milestone_id, status)


# ============================================================
# Memory/Knowledge Endpoints
# ============================================================


@app.get("/api/v1/memory/search")
async def search_memory(
    query: str = Query(..., min_length=1, max_length=1000),
    n_results: int = Query(default=10, ge=1, le=100),
):
    """Search the memory/knowledge base."""
    return await _memory_service.search(query, n_results=n_results)


@app.get("/api/v1/memory/stats")
async def get_memory_stats():
    """Get memory/knowledge statistics."""
    return await _memory_service.get_stats()


# ============================================================
# Chat Endpoint
# ============================================================


@app.post("/api/v1/chat")
async def chat(
    request: Request,
    msg: ChatMessage,
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Chat with an agent."""
    if limiter:
        pass  # Rate limiting handled by slowapi decorator, not .check()

    return await _chat_service.chat(
        message=msg.message,
        agent_code=msg.agent,
        conversation_id=msg.conversation_id,
    )


# ============================================================
# Conversation Endpoints
# ============================================================


@app.get("/api/v1/conversations")
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
):
    """List recent conversations."""
    return await _chat_service.list_conversations(limit=limit)


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str = Path(..., min_length=5, max_length=50),
):
    """Get a conversation with its full message history."""
    conv = await _chat_service.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    return conv


@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str = Path(..., min_length=5, max_length=50),
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.WRITE})),
):
    """Delete a conversation."""
    deleted = await _chat_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    return {"success": True, "conversation_id": conversation_id}


# ============================================================
# Workflow Endpoints
# ============================================================


@app.get("/api/v1/workflows")
async def list_workflows():
    """List all available workflows."""
    if not state.orchestrator:
        return {"workflows": [], "count": 0}

    workflows = state.orchestrator.list_workflows()
    return {"workflows": workflows, "count": len(workflows)}


@app.get("/api/v1/workflows/{workflow_name}")
async def get_workflow_details(
    workflow_name: str = Path(
        ...,
        min_length=1,
        max_length=MAX_WORKFLOW_NAME_LENGTH,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Name of the workflow",
        examples=["product_launch", "incident_response"],
    )
):
    """Get details about a specific workflow including its steps."""
    if not state.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if workflow_name not in state.orchestrator._workflows:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")

    workflow_class = state.orchestrator._workflows[workflow_name]
    workflow = workflow_class(state.registry)

    steps = workflow.define_steps()
    step_details = []
    for step in steps:
        step_details.append(
            {
                "name": step.name,
                "agent": step.agent,
                "task_type": step.task_type,
                "description": step.description,
                "required": step.required,
                "depends_on": step.depends_on,
            }
        )

    return {
        "name": workflow.name,
        "description": workflow.description,
        "steps": step_details,
        "step_count": len(steps),
    }


@app.post("/api/v1/workflows/execute")
async def execute_workflow(
    http_request: Request,
    request: WorkflowExecute,
    user: Optional[AuthenticatedUser] = Depends(get_auth_dependency({Permission.EXECUTE_WORKFLOW})),
):
    """Execute a workflow with given parameters."""
    if limiter:
        pass  # Rate limiting handled by slowapi decorator, not .check()

    if not state.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if not state.llm_provider:
        raise HTTPException(
            status_code=503, detail="LLM not connected. Please ensure Ollama is running."
        )

    if request.workflow_name not in state.orchestrator._workflows:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {request.workflow_name}")

    return await _workflow_service.execute(
        workflow_name=request.workflow_name,
        params=request.params,
    )


@app.get("/api/v1/workflows/history")
async def get_workflow_history(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of executions to return",
    )
):
    """Get recent workflow execution history."""
    if not state.orchestrator:
        return {"executions": [], "count": 0}

    history = state.orchestrator.get_history(limit)
    return {
        "executions": [r.to_dict() for r in history],
        "count": len(history),
    }


@app.get("/api/v1/workflows/executions/{workflow_id}")
async def get_workflow_execution(
    workflow_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Workflow execution ID",
        examples=["wf_12345", "execution_abc"],
    )
):
    """Get details of a specific workflow execution."""
    if workflow_id not in state._workflow_executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {workflow_id}")

    return state._workflow_executions[workflow_id]


# ============================================================
# WebSocket
# ============================================================

WEBSOCKET_AUTH_ENABLED = os.getenv("AGENTWERK_WEBSOCKET_AUTH_ENABLED", "false").lower() == "true"
WEBSOCKET_ALLOWED_TOKENS = set()


async def validate_websocket_token(websocket: WebSocket, token: Optional[str]) -> bool:
    """Validate WebSocket connection token."""
    if not WEBSOCKET_AUTH_ENABLED:
        return True

    if not token:
        logger.warning(
            "WebSocket connection rejected: no token provided",
            client=str(websocket.client),
            component="websocket",
        )
        return False

    if token not in WEBSOCKET_ALLOWED_TOKENS:
        logger.warning(
            "WebSocket connection rejected: invalid token",
            client=str(websocket.client),
            component="websocket",
        )
        return False

    return True


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """WebSocket for real-time updates."""
    if not await validate_websocket_token(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    state.websocket_clients.append(websocket)
    logger.debug(
        "WebSocket client connected",
        client=str(websocket.client),
        component="websocket",
        total_clients=len(state.websocket_clients),
    )

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "data": {"message": "Connected to ag3ntwerk Command Center"},
                "timestamp": datetime.now().isoformat(),
            }
        )

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

    except WebSocketDisconnect:
        logger.debug(
            "WebSocket client disconnected",
            client=str(websocket.client),
            component="websocket",
        )
    finally:
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)


# ============================================================
# Static Files - Web Dashboard
# ============================================================

# Serve the React web dashboard from the built dist folder
_web_dist_path = FilePath(__file__).parent.parent / "web" / "dist"

if _web_dist_path.exists():
    # Mount static assets at /assets (matches Vite build output)
    app.mount(
        "/assets", StaticFiles(directory=str(_web_dist_path / "assets")), name="static_assets"
    )

    # Serve vite.svg if it exists
    @app.get("/vite.svg", include_in_schema=False)
    async def serve_vite_svg():
        svg_path = _web_dist_path / "vite.svg"
        if svg_path.exists():
            return FileResponse(str(svg_path))
        return Response(status_code=404)

    # Serve root path - the dashboard
    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serve the React SPA root."""
        return FileResponse(str(_web_dist_path / "index.html"))

    # Catch-all route for SPA - must be defined AFTER all API routes
    # This serves the React app for any unmatched routes
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        """Serve the React SPA for client-side routing."""
        # Don't serve index.html for API routes, docs, or WebSocket
        excluded_prefixes = (
            "api/",
            "api",
            "docs",
            "redoc",
            "openapi.json",
            "health/",
            "health",
            "metrics",
            "ws",
        )
        if path.startswith(excluded_prefixes) or path == "ws":
            raise HTTPException(status_code=404, detail="Not found")

        # Check if it's a request for a static file that exists
        file_path = (_web_dist_path / path).resolve()
        # Prevent path traversal
        if not str(file_path).startswith(str(_web_dist_path.resolve())):
            raise HTTPException(status_code=403, detail="Forbidden")
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # For all other routes, serve index.html (SPA client-side routing)
        return FileResponse(str(_web_dist_path / "index.html"))

    logger.info(
        "Web dashboard mounted at root",
        path=str(_web_dist_path),
        component="static_files",
    )
else:
    logger.info(
        "Web dashboard not found - run 'npm run build' in src/ag3ntwerk/web to build it",
        expected_path=str(_web_dist_path),
        component="static_files",
    )
