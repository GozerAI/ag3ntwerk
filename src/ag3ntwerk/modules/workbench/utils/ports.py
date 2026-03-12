"""
Workbench Port Utilities - Port allocation and management.

Provides functions for allocating and checking ports for preview URLs.
"""

import logging
import socket
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a port is in use.

    Args:
        port: The port number to check.
        host: The host to check on.

    Returns:
        True if the port is in use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.bind((host, port))
            return False
        except socket.error:
            return True


def find_free_port(
    start: int = 8100,
    end: int = 8200,
    host: str = "127.0.0.1",
) -> Optional[int]:
    """
    Find a free port in a range.

    Args:
        start: Start of port range.
        end: End of port range.
        host: Host to check on.

    Returns:
        A free port number, or None if no free port found.
    """
    for port in range(start, end):
        if not is_port_in_use(port, host):
            return port
    return None


class PortAllocator:
    """
    Manages port allocation for workspace previews.

    Tracks which ports are allocated to which workspaces
    and provides thread-safe allocation/deallocation.
    """

    def __init__(
        self,
        start_port: int = 8100,
        end_port: int = 8200,
        host: str = "127.0.0.1",
    ):
        """
        Initialize the port allocator.

        Args:
            start_port: Start of port range.
            end_port: End of port range.
            host: Host to bind to.
        """
        self._start_port = start_port
        self._end_port = end_port
        self._host = host

        # workspace_id -> set of allocated ports
        self._allocations: Dict[str, Set[int]] = {}

        # port -> workspace_id
        self._port_to_workspace: Dict[int, str] = {}

    def allocate(self, workspace_id: str) -> Optional[int]:
        """
        Allocate a free port for a workspace.

        Args:
            workspace_id: The workspace to allocate for.

        Returns:
            Allocated port number, or None if no ports available.
        """
        for port in range(self._start_port, self._end_port):
            # Skip if already allocated
            if port in self._port_to_workspace:
                continue

            # Check if actually free
            if is_port_in_use(port, self._host):
                continue

            # Allocate
            self._port_to_workspace[port] = workspace_id

            if workspace_id not in self._allocations:
                self._allocations[workspace_id] = set()
            self._allocations[workspace_id].add(port)

            logger.debug(f"Allocated port {port} for workspace {workspace_id}")
            return port

        logger.warning(f"No free ports available for workspace {workspace_id}")
        return None

    def release(self, workspace_id: str, port: int) -> bool:
        """
        Release a port allocation.

        Args:
            workspace_id: The workspace that owns the port.
            port: The port to release.

        Returns:
            True if released successfully.
        """
        if port not in self._port_to_workspace:
            return False

        if self._port_to_workspace[port] != workspace_id:
            logger.warning(
                f"Port {port} is allocated to {self._port_to_workspace[port]}, "
                f"not {workspace_id}"
            )
            return False

        del self._port_to_workspace[port]

        if workspace_id in self._allocations:
            self._allocations[workspace_id].discard(port)
            if not self._allocations[workspace_id]:
                del self._allocations[workspace_id]

        logger.debug(f"Released port {port} from workspace {workspace_id}")
        return True

    def release_all(self, workspace_id: str) -> int:
        """
        Release all ports for a workspace.

        Args:
            workspace_id: The workspace to release ports for.

        Returns:
            Number of ports released.
        """
        if workspace_id not in self._allocations:
            return 0

        ports = list(self._allocations[workspace_id])
        for port in ports:
            self._port_to_workspace.pop(port, None)

        del self._allocations[workspace_id]

        logger.debug(f"Released {len(ports)} ports for workspace {workspace_id}")
        return len(ports)

    def get_ports(self, workspace_id: str) -> Set[int]:
        """
        Get all ports allocated to a workspace.

        Args:
            workspace_id: The workspace to get ports for.

        Returns:
            Set of allocated port numbers.
        """
        return self._allocations.get(workspace_id, set()).copy()

    def get_workspace(self, port: int) -> Optional[str]:
        """
        Get the workspace that owns a port.

        Args:
            port: The port to look up.

        Returns:
            Workspace ID or None.
        """
        return self._port_to_workspace.get(port)

    def is_allocated(self, port: int) -> bool:
        """
        Check if a port is allocated.

        Args:
            port: The port to check.

        Returns:
            True if allocated.
        """
        return port in self._port_to_workspace

    def get_stats(self) -> Dict:
        """
        Get allocation statistics.

        Returns:
            Dictionary with stats.
        """
        total_range = self._end_port - self._start_port
        allocated = len(self._port_to_workspace)

        return {
            "start_port": self._start_port,
            "end_port": self._end_port,
            "total_ports": total_range,
            "allocated_ports": allocated,
            "available_ports": total_range - allocated,
            "workspaces_with_ports": len(self._allocations),
        }
