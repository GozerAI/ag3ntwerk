"""
Cross-Agent Capability Registry.

Enables agents to discover and request work from peers via typed
capability contracts instead of ad-hoc routing.

Usage:
    registry = CapabilityRegistry()
    registry.register("Forge", ["code_review", "architecture_design"])
    registry.register("Citadel", ["security_scan", "threat_assessment"])

    providers = registry.find_providers("security_scan")
    result = await registry.request("security_scan", {"target": "auth_module"})
"""

from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class CapabilityRegistry:
    """Registry for cross-agent capability discovery and routing.

    Agents register their capabilities. Other agents can discover
    providers and route requests to the best-fit provider.
    """

    def __init__(self):
        # capability -> list of (agent_code, priority)
        self._capabilities: Dict[str, List[Tuple[str, int]]] = {}
        # agent_code -> handler coroutine
        self._handlers: Dict[str, Callable[..., Coroutine]] = {}
        # agent_code -> list of capabilities
        self._agent_capabilities: Dict[str, List[str]] = {}

    def register(
        self,
        agent_code: str,
        capabilities: List[str],
        handler: Optional[Callable[..., Coroutine]] = None,
        priority: int = 0,
    ) -> None:
        """Register an agent's capabilities.

        Args:
            agent_code: Agent code (e.g. "Forge", "Citadel")
            capabilities: List of capability strings
            handler: Optional async handler for requests
            priority: Higher = preferred (default 0)
        """
        self._agent_capabilities[agent_code] = list(capabilities)
        if handler:
            self._handlers[agent_code] = handler

        for cap in capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            # Avoid duplicates
            existing_codes = [c for c, _ in self._capabilities[cap]]
            if agent_code not in existing_codes:
                self._capabilities[cap].append((agent_code, priority))
            else:
                # Update priority
                self._capabilities[cap] = [
                    (c, priority if c == agent_code else p) for c, p in self._capabilities[cap]
                ]
            # Keep sorted by priority descending
            self._capabilities[cap].sort(key=lambda x: x[1], reverse=True)

    def unregister(self, agent_code: str) -> None:
        """Remove all capabilities for an agent."""
        self._agent_capabilities.pop(agent_code, None)
        self._handlers.pop(agent_code, None)
        for cap in list(self._capabilities):
            self._capabilities[cap] = [
                (c, p) for c, p in self._capabilities[cap] if c != agent_code
            ]
            if not self._capabilities[cap]:
                del self._capabilities[cap]

    def find_providers(self, capability: str) -> List[str]:
        """Find agents that provide a capability, ordered by priority.

        Args:
            capability: Capability string to look up

        Returns:
            List of agent codes, best-fit first
        """
        entries = self._capabilities.get(capability, [])
        return [code for code, _ in entries]

    def get_agent_capabilities(self, agent_code: str) -> List[str]:
        """Get all capabilities registered for an agent."""
        return list(self._agent_capabilities.get(agent_code, []))

    def list_all_capabilities(self) -> Dict[str, List[str]]:
        """List all registered capabilities and their providers."""
        return {
            cap: [code for code, _ in providers] for cap, providers in self._capabilities.items()
        }

    async def request(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request to the best provider for a capability.

        Args:
            capability: Capability to request
            params: Parameters for the request

        Returns:
            Result dict from the provider
        """
        providers = self.find_providers(capability)
        if not providers:
            return {"error": f"No provider for capability: {capability}"}

        for agent_code in providers:
            handler = self._handlers.get(agent_code)
            if handler:
                try:
                    result = await handler(capability, params)
                    return result
                except Exception as e:
                    logger.debug(
                        "Handler for %s/%s failed: %s",
                        agent_code,
                        capability,
                        e,
                    )
                    continue

        return {
            "error": f"No handler available for capability: {capability}",
            "providers": providers,
        }


# Singleton
_registry_instance: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Get the shared capability registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CapabilityRegistry()
    return _registry_instance
