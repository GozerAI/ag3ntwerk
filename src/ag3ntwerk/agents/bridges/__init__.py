"""Service bridges for external ag3ntwerk services.

These bridges enable communication between the Overwatch (Overwatch) coordination
layer and external peer services: Nexus (Nexus), Forge (Forge), and Sentinel (Sentinel/Citadel).

Communication is handled via Redis pub/sub for loose coupling and
scalability in a federated architecture.
"""

from ag3ntwerk.agents.bridges.nexus_bridge import NexusBridge, NexusBridgeConfig
from ag3ntwerk.agents.bridges.forge_bridge import ForgeBridge, ForgeBridgeConfig
from ag3ntwerk.agents.bridges.sentinel_bridge import SentinelBridge, SentinelBridgeConfig

__all__ = [
    "NexusBridge",
    "NexusBridgeConfig",
    "ForgeBridge",
    "ForgeBridgeConfig",
    "SentinelBridge",
    "SentinelBridgeConfig",
]
