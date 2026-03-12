"""
Swarm Bridge Module.

Connects ag3ntwerk agent agents to the Claude Swarm for
delegating coding tasks to local LLM instances with tool calling.
"""

from .service import SwarmBridgeService
from .facade import SwarmFacade

__all__ = ["SwarmBridgeService", "SwarmFacade"]
