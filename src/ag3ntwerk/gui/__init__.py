"""
ag3ntwerk Dashboard - Nexus-centric task monitoring interface.

Simple dashboard showing:
- Task status across all agents
- Single chat interface routed through Nexus
- Agent workload overview
"""

from .app import COODashboard, run
from .backend import AgentWerkBackend, AsyncBridge

__all__ = ["COODashboard", "run", "AgentWerkBackend", "AsyncBridge"]
