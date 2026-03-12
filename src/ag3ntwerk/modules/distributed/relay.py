"""
Relay Agent & Bridge - Hybrid cloud/local fleet orchestration.

Solves the fundamental problem: a cloud-hosted ag3ntwerk cannot reach
devices on the operator's local network. This module provides:

1. RelayAgent   — lightweight daemon running on one trusted local machine.
                  Opens an outbound WebSocket tunnel to cloud ag3ntwerk.
                  Executes discovery, provisioning, and commands locally.

2. RelayBridge  — cloud-side connection manager. Receives relay tunnels,
                  routes fleet operations through them, tracks relay health.

3. RelayRouter  — transparent routing layer. Fleet modules call
                  `router.execute(target_ip, ...)` and it decides whether
                  to go direct (same-LAN) or relay (cross-network).

Architecture:
    Cloud ag3ntwerk  <───── outbound WS tunnel ──────  Local Relay Agent
        │                                                │
        ├─ RelayBridge (accepts tunnels)                 ├─ Network discovery
        ├─ RelayRouter (routes operations)               ├─ SSH/TCP to local nodes
        ├─ Fleet UI / approval gates                     ├─ Resource profiling
        └─ Workload scheduling                           └─ Command execution

Primary owners: Forge, Sentinel
"""

import asyncio
import hashlib
import hmac
import json
import logging
import platform
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class RelayStatus(str, Enum):
    """Connection status of a relay agent."""

    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    HEARTBEAT_MISSED = "heartbeat_missed"
    DISCONNECTED = "disconnected"
    REJECTED = "rejected"


class RelayCapability(str, Enum):
    """Operations a relay can perform on behalf of the controller."""

    NETWORK_SCAN = "network_scan"
    TCP_PROBE = "tcp_probe"
    SSH_EXECUTE = "ssh_execute"
    HTTP_FORWARD = "http_forward"
    FILE_TRANSFER = "file_transfer"
    RESOURCE_PROFILE = "resource_profile"
    AGENT_DEPLOY = "agent_deploy"


class CommandStatus(str, Enum):
    """Status of a relayed command."""

    QUEUED = "queued"
    SENT = "sent"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RelayIdentity:
    """Identity and metadata for a relay agent."""

    relay_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    hostname: str = field(default_factory=socket.gethostname)
    platform: str = field(default_factory=platform.system)
    version: str = "0.1.0"
    capabilities: List[RelayCapability] = field(default_factory=lambda: list(RelayCapability))
    networks: List[str] = field(default_factory=list)  # CIDRs this relay can reach
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relay_id": self.relay_id,
            "name": self.name,
            "hostname": self.hostname,
            "platform": self.platform,
            "version": self.version,
            "capabilities": [c.value for c in self.capabilities],
            "networks": self.networks,
            "registered_at": self.registered_at,
        }


@dataclass
class RelayConnection:
    """Cloud-side representation of a connected relay."""

    identity: RelayIdentity
    status: RelayStatus = RelayStatus.CONNECTING
    connected_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    latency_ms: float = 0.0
    commands_executed: int = 0
    commands_failed: int = 0
    websocket: Any = None  # WebSocket connection object
    pending_commands: Dict[str, asyncio.Future] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "status": self.status.value,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "latency_ms": round(self.latency_ms, 2),
            "commands_executed": self.commands_executed,
            "commands_failed": self.commands_failed,
            "uptime_seconds": self._uptime(),
        }

    def _uptime(self) -> float:
        if not self.connected_at:
            return 0.0
        connected = datetime.fromisoformat(self.connected_at)
        return (datetime.now(timezone.utc) - connected).total_seconds()


@dataclass
class RelayCommand:
    """A command sent through the relay tunnel."""

    command_id: str = field(default_factory=lambda: str(uuid4()))
    operation: str = ""  # scan, probe, execute, profile, deploy
    target_ip: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: CommandStatus = CommandStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout_seconds: float = 120.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "operation": self.operation,
            "target_ip": self.target_ip,
            "status": self.status.value,
            "created_at": self.created_at,
            "sent_at": self.sent_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


# =============================================================================
# Relay Bridge (Cloud Side)
# =============================================================================


class RelayBridge:
    """
    Cloud-side relay connection manager.

    Accepts incoming WebSocket tunnels from relay agents, authenticates
    them, and provides an interface for fleet modules to send commands
    through the appropriate relay.
    """

    def __init__(self):
        self._relays: Dict[str, RelayConnection] = {}
        self._tokens: Dict[str, str] = {}  # token_hash -> relay_id
        self._network_map: Dict[str, str] = {}  # CIDR -> relay_id
        self._command_history: List[Dict[str, Any]] = []
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_timeout = 90  # seconds
        self._max_history = 1000
        self._lock = asyncio.Lock()

    # ---- Token Management ----

    def generate_relay_token(self, relay_name: str = "", created_by: str = "") -> Dict[str, str]:
        """
        Generate a pre-shared token for a relay agent.

        The operator generates this in the cloud UI, then provides
        it to the relay agent during setup.
        """
        token = f"ag3ntwerk-relay-{uuid4().hex}"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        relay_id = str(uuid4())

        self._tokens[token_hash] = relay_id

        logger.info(
            f"Generated relay token for '{relay_name}' " f"(relay_id={relay_id}, by={created_by})"
        )

        return {
            "token": token,
            "relay_id": relay_id,
            "relay_name": relay_name,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "instructions": (
                "Provide this token to the relay agent on your local network. "
                "Run: ag3ntwerk-relay --controller-url <your-vps-url> --token <token>"
            ),
        }

    def validate_token(self, token: str) -> Optional[str]:
        """Validate a relay token, return relay_id if valid."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return self._tokens.get(token_hash)

    def revoke_token(self, relay_id: str) -> bool:
        """Revoke a relay's token, disconnecting it."""
        to_remove = [h for h, rid in self._tokens.items() if rid == relay_id]
        for h in to_remove:
            del self._tokens[h]

        if relay_id in self._relays:
            self._relays[relay_id].status = RelayStatus.REJECTED
            logger.info(f"Revoked relay {relay_id}")
            return True
        return False

    # ---- Connection Management ----

    async def register_relay(
        self,
        websocket: Any,
        token: str,
        identity: RelayIdentity,
    ) -> Optional[RelayConnection]:
        """
        Register an incoming relay connection.

        Called when a relay agent connects via WebSocket.
        """
        relay_id = self.validate_token(token)
        if not relay_id:
            logger.warning(f"Relay connection rejected: invalid token")
            return None

        async with self._lock:
            # Update identity with the assigned relay_id
            identity.relay_id = relay_id

            conn = RelayConnection(
                identity=identity,
                status=RelayStatus.CONNECTED,
                connected_at=datetime.now(timezone.utc).isoformat(),
                last_heartbeat=datetime.now(timezone.utc).isoformat(),
                websocket=websocket,
            )
            self._relays[relay_id] = conn

            # Map networks to this relay
            for cidr in identity.networks:
                self._network_map[cidr] = relay_id

            logger.info(
                f"Relay registered: {identity.name} ({relay_id}) " f"networks={identity.networks}"
            )

        return conn

    async def unregister_relay(self, relay_id: str):
        """Handle relay disconnection."""
        async with self._lock:
            if relay_id in self._relays:
                conn = self._relays[relay_id]
                conn.status = RelayStatus.DISCONNECTED
                conn.websocket = None

                # Cancel any pending commands
                for cmd_id, future in conn.pending_commands.items():
                    if not future.done():
                        future.set_exception(ConnectionError(f"Relay {relay_id} disconnected"))
                conn.pending_commands.clear()

                # Remove network mappings
                to_remove = [cidr for cidr, rid in self._network_map.items() if rid == relay_id]
                for cidr in to_remove:
                    del self._network_map[cidr]

                logger.info(f"Relay disconnected: {relay_id}")

    async def handle_heartbeat(self, relay_id: str, latency_ms: float = 0.0):
        """Process a heartbeat from a relay agent."""
        if relay_id in self._relays:
            conn = self._relays[relay_id]
            conn.last_heartbeat = datetime.now(timezone.utc).isoformat()
            conn.latency_ms = latency_ms
            if conn.status == RelayStatus.HEARTBEAT_MISSED:
                conn.status = RelayStatus.CONNECTED
                logger.info(f"Relay {relay_id} heartbeat recovered")

    async def handle_command_response(self, relay_id: str, command_id: str, result: Dict[str, Any]):
        """Process a command response from a relay agent."""
        if relay_id not in self._relays:
            return

        conn = self._relays[relay_id]
        future = conn.pending_commands.pop(command_id, None)
        if future and not future.done():
            future.set_result(result)
            conn.commands_executed += 1

        # Store in history
        self._command_history.append(
            {
                "relay_id": relay_id,
                "command_id": command_id,
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history :]

    # ---- Command Routing ----

    async def send_command(
        self,
        relay_id: str,
        command: RelayCommand,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """
        Send a command through a relay tunnel and wait for the result.

        This is the core method fleet modules use to execute operations
        on remote networks via the relay.
        """
        if relay_id not in self._relays:
            return {"success": False, "error": f"Relay {relay_id} not found"}

        conn = self._relays[relay_id]
        if conn.status != RelayStatus.CONNECTED:
            return {
                "success": False,
                "error": f"Relay {relay_id} is {conn.status.value}",
            }

        if not conn.websocket:
            return {"success": False, "error": "Relay has no active connection"}

        # Create a future to wait for the response
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        conn.pending_commands[command.command_id] = future

        # Send the command through the WebSocket tunnel
        try:
            message = {
                "type": "command",
                "command_id": command.command_id,
                "operation": command.operation,
                "target_ip": command.target_ip,
                "payload": command.payload,
                "timeout": command.timeout_seconds,
            }
            await conn.websocket.send_json(message)
            command.status = CommandStatus.SENT
            command.sent_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            conn.pending_commands.pop(command.command_id, None)
            conn.commands_failed += 1
            return {"success": False, "error": f"Failed to send: {e}"}

        # Wait for the relay to respond
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            command.status = CommandStatus.COMPLETED
            command.completed_at = datetime.now(timezone.utc).isoformat()
            command.result = result
            return result
        except asyncio.TimeoutError:
            conn.pending_commands.pop(command.command_id, None)
            conn.commands_failed += 1
            command.status = CommandStatus.TIMED_OUT
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
            }

    # ---- Query Methods ----

    def find_relay_for_ip(self, target_ip: str) -> Optional[str]:
        """
        Find which relay can reach a given IP address.

        Checks registered network CIDRs to determine routing.
        """
        import ipaddress

        try:
            addr = ipaddress.ip_address(target_ip)
        except ValueError:
            return None

        for cidr, relay_id in self._network_map.items():
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                if addr in network:
                    # Verify relay is actually connected
                    conn = self._relays.get(relay_id)
                    if conn and conn.status == RelayStatus.CONNECTED:
                        return relay_id
            except ValueError:
                continue

        return None

    def get_connected_relays(self) -> List[Dict[str, Any]]:
        """List all connected relays."""
        return [
            conn.to_dict() for conn in self._relays.values() if conn.status == RelayStatus.CONNECTED
        ]

    def get_all_relays(self) -> List[Dict[str, Any]]:
        """List all relays (connected or not)."""
        return [conn.to_dict() for conn in self._relays.values()]

    def get_relay(self, relay_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific relay."""
        conn = self._relays.get(relay_id)
        return conn.to_dict() if conn else None

    def get_network_map(self) -> Dict[str, str]:
        """Get the CIDR -> relay_id mapping."""
        return dict(self._network_map)

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent command history."""
        return self._command_history[-limit:]

    # ---- Health Monitoring ----

    async def check_relay_health(self) -> Dict[str, Any]:
        """Check health of all connected relays."""
        now = datetime.now(timezone.utc)
        results = {}

        for relay_id, conn in self._relays.items():
            if conn.status == RelayStatus.DISCONNECTED:
                results[relay_id] = {"status": "disconnected"}
                continue

            if conn.last_heartbeat:
                last_hb = datetime.fromisoformat(conn.last_heartbeat)
                elapsed = (now - last_hb).total_seconds()

                if elapsed > self._heartbeat_timeout:
                    conn.status = RelayStatus.HEARTBEAT_MISSED
                    results[relay_id] = {
                        "status": "heartbeat_missed",
                        "seconds_since_heartbeat": elapsed,
                    }
                else:
                    results[relay_id] = {
                        "status": "healthy",
                        "latency_ms": conn.latency_ms,
                        "seconds_since_heartbeat": elapsed,
                    }
            else:
                results[relay_id] = {"status": "no_heartbeat"}

        return results


# =============================================================================
# Relay Router (Transparent Routing Layer)
# =============================================================================


class RelayRouter:
    """
    Transparent routing layer for fleet operations.

    Fleet modules call `router.tcp_connect(ip, port)` or
    `router.execute_on_node(ip, command)` and the router decides
    whether to connect directly (same-LAN) or via a relay.

    This replaces all direct `asyncio.open_connection()` calls
    in discovery.py, provisioner.py, and deployment_planner.py.
    """

    def __init__(self, bridge: Optional[RelayBridge] = None):
        self._bridge = bridge
        self._direct_networks: Set[str] = set()  # CIDRs reachable directly
        self._prefer_relay: bool = False  # True = always use relay if available

    def set_bridge(self, bridge: RelayBridge):
        """Attach the relay bridge for routing."""
        self._bridge = bridge

    def add_direct_network(self, cidr: str):
        """Mark a CIDR as directly reachable (no relay needed)."""
        self._direct_networks.add(cidr)

    def set_prefer_relay(self, prefer: bool):
        """If True, always route through relay when one exists."""
        self._prefer_relay = prefer

    def _is_direct(self, target_ip: str) -> bool:
        """Check if an IP is directly reachable (same LAN)."""
        import ipaddress

        if not self._direct_networks:
            # No direct networks configured — check if relay exists
            if self._bridge and self._bridge.find_relay_for_ip(target_ip):
                return False
            # No relay either — fall back to direct (self-hosted mode)
            return True

        try:
            addr = ipaddress.ip_address(target_ip)
        except ValueError:
            return True

        for cidr in self._direct_networks:
            try:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue

        return False

    async def tcp_probe(
        self,
        target_ip: str,
        port: int,
        timeout: float = 5.0,
    ) -> Tuple[bool, float]:
        """
        Probe a TCP port — direct or relayed.

        Returns (is_open, response_ms).
        """
        if not self._prefer_relay and self._is_direct(target_ip):
            return await self._direct_tcp_probe(target_ip, port, timeout)

        # Route through relay
        if self._bridge:
            relay_id = self._bridge.find_relay_for_ip(target_ip)
            if relay_id:
                return await self._relayed_tcp_probe(relay_id, target_ip, port, timeout)

        # No relay available — try direct as fallback
        return await self._direct_tcp_probe(target_ip, port, timeout)

    async def execute_on_node(
        self,
        target_ip: str,
        endpoint: str,
        payload: Dict[str, Any],
        port: int = 8000,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """
        Send an HTTP request to a node agent — direct or relayed.

        This replaces `_send_to_agent()` and `_execute_step()`.
        """
        if not self._prefer_relay and self._is_direct(target_ip):
            return await self._direct_http(target_ip, port, endpoint, payload, timeout)

        # Route through relay
        if self._bridge:
            relay_id = self._bridge.find_relay_for_ip(target_ip)
            if relay_id:
                return await self._relayed_http(
                    relay_id, target_ip, port, endpoint, payload, timeout
                )

        # No relay — try direct as fallback
        return await self._direct_http(target_ip, port, endpoint, payload, timeout)

    async def scan_network(
        self,
        cidr: str,
        ports: List[int],
        timeout_per_host: float = 3.0,
        concurrency: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Scan a network range — direct or relayed.

        For relayed scans, the entire operation is sent to the relay
        to execute locally (much faster than proxying individual probes).
        """
        # Check if a relay covers this network
        if self._bridge:
            import ipaddress

            try:
                network = ipaddress.ip_network(cidr, strict=False)
                sample_ip = str(next(network.hosts()))
                relay_id = self._bridge.find_relay_for_ip(sample_ip)
                if relay_id:
                    return await self._relayed_network_scan(
                        relay_id, cidr, ports, timeout_per_host, concurrency
                    )
            except (ValueError, StopIteration):
                pass

        # Direct scan (self-hosted mode)
        return await self._direct_network_scan(cidr, ports, timeout_per_host, concurrency)

    async def profile_node(self, target_ip: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Get resource profile from a node — direct or relayed.
        """
        return await self.execute_on_node(
            target_ip=target_ip,
            endpoint="/api/v1/node/profile",
            payload={"detailed": True},
            timeout=timeout,
        )

    # ---- Direct Implementations ----

    async def _direct_tcp_probe(self, ip: str, port: int, timeout: float) -> Tuple[bool, float]:
        """Direct TCP connect probe."""
        try:
            start = time.monotonic()
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout,
            )
            elapsed = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return True, elapsed
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False, 0.0

    async def _direct_http(
        self,
        ip: str,
        port: int,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """Direct HTTP request to a node agent."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=10.0,
            )

            body = json.dumps(payload)
            request = (
                f"POST {endpoint} HTTP/1.1\r\n"
                f"Host: {ip}:{port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
                f"{body}"
            )
            writer.write(request.encode())
            await writer.drain()

            response = await asyncio.wait_for(reader.read(65536), timeout=timeout)
            writer.close()
            await writer.wait_closed()

            response_text = response.decode("utf-8", errors="ignore")
            body_start = response_text.find("\r\n\r\n")
            if body_start > 0:
                resp_body = response_text[body_start + 4 :]
                try:
                    return json.loads(resp_body)
                except json.JSONDecodeError:
                    return {"status": "ok", "raw": resp_body[:500]}

            return {"status": "ok", "raw_response": True}

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            return {"status": "error", "error": str(e)}

    async def _direct_network_scan(
        self,
        cidr: str,
        ports: List[int],
        timeout: float,
        concurrency: int,
    ) -> List[Dict[str, Any]]:
        """Direct network scan (same as original discovery logic)."""
        import ipaddress

        network = ipaddress.ip_network(cidr, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def probe_host(ip: str):
            async with semaphore:
                port_results = []
                alive = False
                for port in ports:
                    is_open, latency = await self._direct_tcp_probe(ip, port, timeout)
                    if is_open:
                        alive = True
                    port_results.append(
                        {
                            "port": port,
                            "open": is_open,
                            "latency_ms": round(latency, 2),
                        }
                    )
                if alive:
                    results.append(
                        {
                            "ip": ip,
                            "alive": True,
                            "ports": port_results,
                        }
                    )

        tasks = [probe_host(ip) for ip in hosts]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    # ---- Relayed Implementations ----

    async def _relayed_tcp_probe(
        self,
        relay_id: str,
        ip: str,
        port: int,
        timeout: float,
    ) -> Tuple[bool, float]:
        """Probe a port via relay tunnel."""
        command = RelayCommand(
            operation="tcp_probe",
            target_ip=ip,
            payload={"port": port, "timeout": timeout},
            timeout_seconds=timeout + 5,
        )
        result = await self._bridge.send_command(relay_id, command, timeout=timeout + 5)
        if result.get("success") is False:
            return False, 0.0
        return result.get("open", False), result.get("latency_ms", 0.0)

    async def _relayed_http(
        self,
        relay_id: str,
        ip: str,
        port: int,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """Forward an HTTP request via relay tunnel."""
        command = RelayCommand(
            operation="http_forward",
            target_ip=ip,
            payload={
                "port": port,
                "endpoint": endpoint,
                "body": payload,
                "timeout": timeout,
            },
            timeout_seconds=timeout + 10,
        )
        return await self._bridge.send_command(relay_id, command, timeout=timeout + 10)

    async def _relayed_network_scan(
        self,
        relay_id: str,
        cidr: str,
        ports: List[int],
        timeout: float,
        concurrency: int,
    ) -> List[Dict[str, Any]]:
        """
        Send entire scan operation to relay for local execution.

        The relay performs the scan on its local network and returns
        aggregated results. This is much faster than proxying individual
        probes over the WAN link.
        """
        command = RelayCommand(
            operation="network_scan",
            payload={
                "cidr": cidr,
                "ports": ports,
                "timeout_per_host": timeout,
                "concurrency": concurrency,
            },
            timeout_seconds=300,  # scans can take a while
        )
        result = await self._bridge.send_command(relay_id, command, timeout=300)
        if result.get("success") is False:
            return []
        return result.get("hosts", [])


# =============================================================================
# Relay Agent (Local Side)
# =============================================================================


class RelayAgent:
    """
    Lightweight local agent that runs on one trusted machine
    inside the operator's network.

    Opens an outbound WebSocket tunnel to the cloud-hosted ag3ntwerk
    and executes fleet operations locally on behalf of the controller.

    Usage:
        agent = RelayAgent(
            controller_url="wss://ag3ntwerk.example.com",
            token="ag3ntwerk-relay-...",
            name="office-relay",
            networks=["192.168.1.0/24", "10.0.0.0/24"],
        )
        await agent.run()
    """

    def __init__(
        self,
        controller_url: str,
        token: str,
        name: str = "",
        networks: Optional[List[str]] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_delay: float = 300.0,
    ):
        self.controller_url = controller_url.rstrip("/")
        self.token = token
        self.name = name or socket.gethostname()
        self.networks = networks or []
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_delay = max_reconnect_delay

        self._identity = RelayIdentity(
            name=self.name,
            networks=self.networks,
        )
        self._running = False
        self._ws = None
        self._reconnect_attempts = 0
        self._handlers: Dict[str, Callable] = {
            "command": self._handle_command,
            "heartbeat": self._handle_heartbeat,
        }

    async def run(self):
        """Main event loop — connect, handle messages, reconnect."""
        self._running = True
        logger.info(
            f"Relay agent '{self.name}' starting. "
            f"Controller: {self.controller_url}, "
            f"Networks: {self.networks}"
        )

        while self._running:
            try:
                await self._connect_and_serve()
            except Exception as e:
                logger.error(f"Relay connection error: {e}")

            if self._running:
                delay = min(
                    self.reconnect_interval * (2**self._reconnect_attempts),
                    self.max_reconnect_delay,
                )
                logger.info(f"Reconnecting in {delay:.0f}s...")
                await asyncio.sleep(delay)
                self._reconnect_attempts += 1

    async def stop(self):
        """Gracefully shut down the relay agent."""
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _connect_and_serve(self):
        """Establish WebSocket and handle messages."""
        try:
            # We use aiohttp or websockets for the client side
            # This is a protocol-level implementation
            import websockets

            ws_url = f"{self.controller_url}/ws/relay"
            logger.info(f"Connecting to {ws_url}...")

            async with websockets.connect(ws_url) as ws:
                self._ws = ws
                self._reconnect_attempts = 0

                # Authenticate
                await ws.send(
                    json.dumps(
                        {
                            "type": "auth",
                            "token": self.token,
                            "identity": self._identity.to_dict(),
                        }
                    )
                )

                # Wait for auth response
                resp = json.loads(await ws.recv())
                if resp.get("type") != "auth_ok":
                    logger.error(f"Authentication failed: {resp.get('error', 'unknown')}")
                    return

                logger.info("Authenticated with controller")

                # Start heartbeat task
                heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

                try:
                    async for raw_msg in ws:
                        message = json.loads(raw_msg)
                        msg_type = message.get("type", "")
                        handler = self._handlers.get(msg_type)
                        if handler:
                            # Run handler in background to not block message loop
                            asyncio.create_task(self._safe_handle(handler, ws, message))
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                finally:
                    heartbeat_task.cancel()

        except ImportError:
            logger.error(
                "websockets package required for relay agent. "
                "Install with: pip install websockets"
            )
            self._running = False
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def _safe_handle(self, handler, ws, message):
        """Run a handler with error isolation."""
        try:
            await handler(ws, message)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            command_id = message.get("command_id")
            if command_id:
                await ws.send(
                    json.dumps(
                        {
                            "type": "command_response",
                            "command_id": command_id,
                            "result": {"success": False, "error": str(e)},
                        }
                    )
                )

    async def _heartbeat_loop(self, ws):
        """Send periodic heartbeats to the controller."""
        while True:
            try:
                await asyncio.sleep(self._identity and 30 or 30)
                start = time.monotonic()
                await ws.send(json.dumps({"type": "heartbeat"}))
                # Latency measured on pong response
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Heartbeat loop broken: %s", e)
                break

    async def _handle_heartbeat(self, ws, message):
        """Respond to heartbeat from controller."""
        await ws.send(
            json.dumps(
                {
                    "type": "heartbeat_response",
                    "relay_id": self._identity.relay_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

    async def _handle_command(self, ws, message):
        """
        Execute a command locally and send the result back.

        This is where the relay does the actual work — scanning,
        probing, HTTP forwarding, etc. — all on the local network.
        """
        command_id = message.get("command_id", "")
        operation = message.get("operation", "")
        target_ip = message.get("target_ip", "")
        payload = message.get("payload", {})

        logger.info(f"Executing command {command_id}: " f"{operation} -> {target_ip or 'network'}")

        try:
            if operation == "tcp_probe":
                result = await self._local_tcp_probe(
                    target_ip,
                    payload.get("port", 80),
                    payload.get("timeout", 5.0),
                )
            elif operation == "http_forward":
                result = await self._local_http_forward(
                    target_ip,
                    payload.get("port", 8000),
                    payload.get("endpoint", "/"),
                    payload.get("body", {}),
                    payload.get("timeout", 120.0),
                )
            elif operation == "network_scan":
                result = await self._local_network_scan(
                    payload.get("cidr", ""),
                    payload.get("ports", [22, 80, 443, 8000]),
                    payload.get("timeout_per_host", 3.0),
                    payload.get("concurrency", 50),
                )
            elif operation == "resource_profile":
                result = await self._local_resource_profile()
            else:
                result = {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            result = {"success": False, "error": str(e)}

        # Send result back through the tunnel
        await ws.send(
            json.dumps(
                {
                    "type": "command_response",
                    "command_id": command_id,
                    "result": result,
                }
            )
        )

    # ---- Local Execution Methods ----

    async def _local_tcp_probe(self, ip: str, port: int, timeout: float) -> Dict[str, Any]:
        """Probe a TCP port on the local network."""
        try:
            start = time.monotonic()
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout,
            )
            elapsed = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return {"open": True, "latency_ms": round(elapsed, 2)}
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return {"open": False, "latency_ms": 0.0}

    async def _local_http_forward(
        self,
        ip: str,
        port: int,
        endpoint: str,
        body: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """Forward an HTTP request to a local node."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=10.0,
            )

            payload = json.dumps(body)
            request = (
                f"POST {endpoint} HTTP/1.1\r\n"
                f"Host: {ip}:{port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(payload)}\r\n"
                f"Connection: close\r\n\r\n"
                f"{payload}"
            )
            writer.write(request.encode())
            await writer.drain()

            response = await asyncio.wait_for(reader.read(65536), timeout=timeout)
            writer.close()
            await writer.wait_closed()

            response_text = response.decode("utf-8", errors="ignore")
            body_start = response_text.find("\r\n\r\n")
            if body_start > 0:
                resp_body = response_text[body_start + 4 :]
                try:
                    return json.loads(resp_body)
                except json.JSONDecodeError:
                    return {"status": "ok", "raw": resp_body[:500]}

            return {"status": "ok", "raw_response": True}

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            return {"status": "error", "error": str(e)}

    async def _local_network_scan(
        self,
        cidr: str,
        ports: List[int],
        timeout: float,
        concurrency: int,
    ) -> Dict[str, Any]:
        """Perform a full network scan locally and return results."""
        import ipaddress

        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        hosts_list = [str(ip) for ip in network.hosts()]

        if len(hosts_list) > 65536:
            return {
                "success": False,
                "error": "Network too large (max /16 = 65536 hosts)",
            }

        semaphore = asyncio.Semaphore(concurrency)
        discovered = []

        async def probe(ip):
            async with semaphore:
                port_results = []
                alive = False
                for port in ports:
                    result = await self._local_tcp_probe(ip, port, timeout)
                    port_results.append(
                        {
                            "port": port,
                            "open": result["open"],
                            "latency_ms": result.get("latency_ms", 0),
                        }
                    )
                    if result["open"]:
                        alive = True
                if alive:
                    discovered.append(
                        {
                            "ip": ip,
                            "alive": True,
                            "ports": port_results,
                        }
                    )

        tasks = [probe(ip) for ip in hosts_list]
        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "success": True,
            "hosts_scanned": len(hosts_list),
            "hosts_found": len(discovered),
            "hosts": discovered,
        }

    async def _local_resource_profile(self) -> Dict[str, Any]:
        """Gather resource info about the relay's own machine."""
        import os
        import shutil

        profile = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count() or 0,
        }

        # Memory (Linux)
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        profile["memory_total_gb"] = round(kb / 1048576, 2)
                    elif line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        profile["memory_available_gb"] = round(kb / 1048576, 2)
        except FileNotFoundError:
            pass

        # Disk
        total, used, free = shutil.disk_usage("/")
        profile["disk_total_gb"] = round(total / (1024**3), 2)
        profile["disk_free_gb"] = round(free / (1024**3), 2)

        return {"success": True, "profile": profile}
