"""
Agent Registry.

Central registry for managing and accessing all ag3ntwerk agents.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from ag3ntwerk.core.base import Agent, Manager
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all ag3ntwerk agents.

    The registry provides:
    - Lazy initialization of agents
    - Centralized LLM provider management
    - Agent lookup by code or role
    - Cross-agent coordination support

    Example:
        ```python
        registry = AgentRegistry(llm_provider=provider)

        # Auto-registers standard agents
        cpo = registry.get("Blueprint")
        cfo = registry.get("Keystone")

        # Get by codename
        blueprint = registry.get_by_codename("Blueprint")

        # List all agents
        agents = registry.list_agents()
        ```
    """

    # Standard agent mappings: codename -> (module_path, class_name)
    STANDARD_AGENTS = {
        "Overwatch": ("ag3ntwerk.agents.overwatch", "Overwatch"),
        "Forge": ("ag3ntwerk.agents.forge", "Forge"),
        "Keystone": ("ag3ntwerk.agents.keystone", "Keystone"),
        "Echo": ("ag3ntwerk.agents.echo", "Echo"),
        "Sentinel": ("ag3ntwerk.agents.sentinel", "Sentinel"),
        "Blueprint": ("ag3ntwerk.agents.blueprint", "Blueprint"),
        "Axiom": ("ag3ntwerk.agents.axiom", "Axiom"),
        "Index": ("ag3ntwerk.agents.index_agent", "Index"),
        "Foundry": ("ag3ntwerk.agents.foundry", "Foundry"),
        "Citadel": ("ag3ntwerk.agents.citadel", "Citadel"),
        "Beacon": ("ag3ntwerk.agents.beacon", "Beacon"),
        "Vector": ("ag3ntwerk.agents.vector", "Vector"),
        "Aegis": ("ag3ntwerk.agents.aegis", "Aegis"),
        "Accord": ("ag3ntwerk.agents.accord", "Accord"),
        "Compass": ("ag3ntwerk.agents.compass", "Compass"),
        "Nexus": ("ag3ntwerk.agents.nexus", "Nexus"),
    }

    # Backward-compatibility aliases: old agent code -> codename
    AGENT_ALIASES = {
        "CoS": "Overwatch",
        "CTO": "Forge",
        "CFO": "Keystone",
        "CMO": "Echo",
        "CIO": "Sentinel",
        "CPO": "Blueprint",
        "CDO": "Axiom",
        "CDaO": "Index",
        "CEngO": "Foundry",
        "CSecO": "Citadel",
        "CCO": "Beacon",
        "CRevO": "Vector",
        "CRiO": "Aegis",
        "CCoMO": "Accord",
        "CSO": "Compass",
        "COO": "Nexus",
    }

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        auto_register: bool = True,
    ):
        """
        Initialize the agent registry.

        Args:
            llm_provider: LLM provider for all agents
            auto_register: Whether to auto-register standard agents
        """
        self.llm_provider = llm_provider
        self._executives: Dict[str, Agent] = {}
        self._codename_map: Dict[str, str] = {}  # codename -> code
        self._classes: Dict[str, Type[Agent]] = {}

        if auto_register:
            self._setup_standard_executives()

    def _setup_standard_executives(self) -> None:
        """Setup mappings for standard agents (lazy load)."""
        # Keys are already codenames; map lowercase codename -> key
        for codename in self.STANDARD_AGENTS:
            self._codename_map[codename.lower()] = codename
        # Also register old agent aliases so get() works with legacy codes
        for alias, codename in self.AGENT_ALIASES.items():
            self._codename_map[alias.lower()] = codename

    def _load_executive_class(self, code: str) -> Optional[Type[Agent]]:
        """Dynamically load an agent class."""
        if not code:
            return None

        if code in self._classes:
            return self._classes[code]

        if code not in self.STANDARD_AGENTS:
            return None

        module_path, class_name = self.STANDARD_AGENTS[code]

        try:
            import importlib

            module = importlib.import_module(module_path)
            cls = getattr(module, class_name, None)
            if cls is None:
                return None
            self._classes[code] = cls
            return cls
        except ImportError:
            # Module not found - may not be implemented yet
            return None

    def register(
        self,
        code: str,
        agent: Agent,
        codename: Optional[str] = None,
    ) -> None:
        """
        Register an agent instance.

        Args:
            code: Agent code (e.g., "Blueprint")
            agent: Agent instance
            codename: Optional codename for the agent
        """
        self._executives[code] = agent

        if codename:
            self._codename_map[codename.lower()] = code
        elif hasattr(agent, "codename"):
            self._codename_map[agent.codename.lower()] = code

    def register_class(
        self,
        code: str,
        executive_class: Type[Agent],
        codename: Optional[str] = None,
    ) -> None:
        """
        Register an agent class for lazy instantiation.

        Args:
            code: Agent code
            executive_class: Agent class
            codename: Optional codename
        """
        self._classes[code] = executive_class

        if codename:
            self._codename_map[codename.lower()] = code

    def get(self, code: str) -> Optional[Agent]:
        """
        Get an agent by codename or legacy code.

        Lazily instantiates if not already created.
        Accepts codenames ("Blueprint", "Keystone") or legacy agent codes
        ("CPO", "CFO") via AGENT_ALIASES.

        Args:
            code: Agent codename or legacy code

        Returns:
            Agent instance or None if not found
        """
        # Validate input
        if not code or not isinstance(code, str):
            return None

        # Resolve legacy aliases to codename
        code = self.AGENT_ALIASES.get(code, code)

        # Return cached instance
        if code in self._executives:
            return self._executives[code]

        # Try to load and instantiate
        cls = self._load_executive_class(code)
        if cls:
            try:
                agent = cls(llm_provider=self.llm_provider)
                self._executives[code] = agent
                return agent
            except Exception as e:
                # Failed to instantiate - log and return None
                logger.warning(f"Failed to instantiate agent {code}: {e}")
                return None

        return None

    def get_by_codename(self, codename: str) -> Optional[Agent]:
        """
        Get an agent by codename.

        Args:
            codename: Agent codename (e.g., "Blueprint", "Keystone")

        Returns:
            Agent instance or None if not found
        """
        code = self._codename_map.get(codename.lower())
        if code:
            return self.get(code)
        return None

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents.

        Returns:
            List of agent info dictionaries
        """
        result = []

        for codename, (module, class_name) in self.STANDARD_AGENTS.items():
            # Check if already instantiated
            instantiated = codename in self._executives

            # Try to get class info
            cls = self._load_executive_class(codename)
            available = cls is not None

            info = {
                "code": codename,
                "codename": codename,
                "class_name": class_name,
                "module": module,
                "available": available,
                "instantiated": instantiated,
            }

            if instantiated:
                exec_instance = self._executives[codename]
                info["name"] = exec_instance.name
                info["domain"] = getattr(exec_instance, "domain", "")

            result.append(info)

        return result

    def get_available_codes(self) -> List[str]:
        """Get list of available agent codes."""
        return [
            code
            for code in self.STANDARD_AGENTS
            if self._load_executive_class(code) is not None
        ]

    def get_by_capability(self, capability: str) -> List[Agent]:
        """
        Find agents that can handle a capability.

        Args:
            capability: Task type or capability to find

        Returns:
            List of agents that can handle this capability
        """
        result = []

        for code in self.get_available_codes():
            agent = self.get(code)
            if agent and hasattr(agent, "capabilities"):
                if capability in agent.capabilities:
                    result.append(agent)

        return result

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """
        Set LLM provider for all agents.

        Updates existing instances and sets default for new ones.

        Args:
            provider: LLM provider to use
        """
        self.llm_provider = provider

        # Update existing instances
        for agent in self._executives.values():
            agent.llm_provider = provider

    def clear(self) -> None:
        """Clear all instantiated agents."""
        self._executives.clear()

    def __contains__(self, code: str) -> bool:
        """Check if an agent codename (or legacy alias) is available."""
        resolved = self.AGENT_ALIASES.get(code, code)
        return resolved in self.STANDARD_AGENTS

    def __getitem__(self, code: str) -> Agent:
        """Get agent by code, raising if not found."""
        agent = self.get(code)
        if agent is None:
            raise KeyError(f"Agent not found: {code}")
        return agent


# Module-level export so callers can do:
#   from ag3ntwerk.orchestration.registry import STANDARD_AGENTS, AGENT_ALIASES
STANDARD_AGENTS = AgentRegistry.STANDARD_AGENTS
AGENT_ALIASES = AgentRegistry.AGENT_ALIASES
