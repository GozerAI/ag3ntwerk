"""ag3ntwerk Command Center API."""

from ag3ntwerk.api.app import app
from ag3ntwerk.api.models import TaskCreate, ChatMessage, WorkflowExecute
from ag3ntwerk.api.state import AppState, state
from ag3ntwerk.api.services import TaskService, ChatService, WorkflowService
from ag3ntwerk.api.dashboard import DashboardService, ExecutiveDashboard, DashboardWidget
from ag3ntwerk.api.module_routes import (
    modules_router,
    trends_router,
    commerce_router,
    brand_router,
    scheduler_router,
)
from ag3ntwerk.api.swarm_routes import swarm_router

__all__ = [
    "app",
    # Models
    "TaskCreate",
    "ChatMessage",
    "WorkflowExecute",
    # State
    "AppState",
    "state",
    # Services
    "TaskService",
    "ChatService",
    "WorkflowService",
    # Dashboard
    "DashboardService",
    "ExecutiveDashboard",
    "DashboardWidget",
    # Module routers
    "modules_router",
    "trends_router",
    "commerce_router",
    "brand_router",
    "scheduler_router",
    "swarm_router",
]
