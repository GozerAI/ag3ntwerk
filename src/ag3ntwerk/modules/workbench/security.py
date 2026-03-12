"""
Workbench Module Security - Authentication and authorization.

Provides security middleware and utilities for the workbench module.
"""

import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ag3ntwerk.modules.workbench.settings import get_workbench_settings

logger = logging.getLogger(__name__)

# Security scheme for bearer token auth
bearer_scheme = HTTPBearer(auto_error=False)


def verify_workbench_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> bool:
    """
    Verify the workbench auth token.

    This is a FastAPI dependency that checks the bearer token against
    the configured auth token.

    Args:
        credentials: The bearer token credentials from the request.

    Returns:
        True if authenticated.

    Raises:
        HTTPException: If authentication fails.
    """
    settings = get_workbench_settings()

    # If no token configured, authentication is disabled (dev mode)
    if not settings.security.auth_token:
        logger.warning("Workbench authentication disabled - no auth_token configured")
        return True

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(
        credentials.credentials,
        settings.security.auth_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def verify_localhost_only(request: Request) -> bool:
    """
    Verify that the request comes from localhost.

    This is a FastAPI dependency that checks the request origin
    when localhost_only is enabled.

    Args:
        request: The incoming request.

    Returns:
        True if request is allowed.

    Raises:
        HTTPException: If request is not from localhost.
    """
    settings = get_workbench_settings()

    if not settings.security.localhost_only:
        return True

    # Check client host
    client_host = request.client.host if request.client else None
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}

    if client_host not in allowed_hosts:
        logger.warning(f"Rejected request from non-localhost host: {client_host}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to localhost only",
        )

    return True


async def workbench_auth(
    token_valid: bool = Depends(verify_workbench_token),
    localhost_valid: bool = Depends(verify_localhost_only),
) -> bool:
    """
    Combined authentication dependency for workbench routes.

    Verifies both the bearer token (if configured) and localhost
    restriction (if enabled).

    Usage:
        @router.get("/workspaces")
        async def list_workspaces(auth: bool = Depends(workbench_auth)):
            ...
    """
    return token_valid and localhost_valid


def generate_auth_token(length: int = 32) -> str:
    """
    Generate a secure random auth token.

    Args:
        length: Token length in bytes (actual string will be longer).

    Returns:
        URL-safe random token string.
    """
    return secrets.token_urlsafe(length)


def validate_workspace_name(name: str) -> bool:
    """
    Validate a workspace name for security.

    Checks that the name is safe for:
    - Filesystem paths
    - Docker container names
    - Network hostnames

    Args:
        name: The workspace name to validate.

    Returns:
        True if name is valid.
    """
    import re

    # Must start with alphanumeric
    if not name or not name[0].isalnum():
        return False

    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
        return False

    # Maximum length
    if len(name) > 64:
        return False

    # No reserved names
    reserved = {"con", "prn", "aux", "nul", "com1", "lpt1"}
    if name.lower() in reserved:
        return False

    return True


def sanitize_command(cmd: list) -> list:
    """
    Sanitize a command for safe execution.

    Removes or escapes potentially dangerous elements.

    Args:
        cmd: Command as list of arguments.

    Returns:
        Sanitized command list.

    Raises:
        ValueError: If command contains dangerous patterns.
    """
    # Dangerous patterns that should never be executed
    dangerous_patterns = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        ":(){:|:&};:",  # Fork bomb
        "> /dev/sd",
        "dd if=/dev/zero",
        "chmod 777 /",
        "chown -R",
        "curl | bash",
        "wget | sh",
    ]

    cmd_str = " ".join(cmd)

    for pattern in dangerous_patterns:
        if pattern in cmd_str:
            raise ValueError(f"Command contains dangerous pattern: {pattern}")

    # Check for shell escapes
    shell_escapes = [";", "&&", "||", "|", "`", "$(", "${"]
    for escape in shell_escapes:
        if any(escape in arg for arg in cmd):
            logger.warning(f"Command contains shell escape: {escape}")

    return cmd


def sanitize_file_path(path: str) -> str:
    """
    Sanitize a file path to prevent directory traversal.

    Args:
        path: The file path to sanitize.

    Returns:
        Sanitized path.

    Raises:
        ValueError: If path contains traversal attempts.
    """
    import os

    # Remove null bytes
    path = path.replace("\x00", "")

    # Check for directory traversal
    if ".." in path:
        raise ValueError("Path traversal not allowed")

    # Check for absolute paths
    if os.path.isabs(path):
        raise ValueError("Absolute paths not allowed")

    # Normalize path
    normalized = os.path.normpath(path)

    # After normalization, check again for traversal
    if normalized.startswith(".."):
        raise ValueError("Path traversal not allowed")

    return normalized


def check_environment_vars(env: dict) -> dict:
    """
    Check environment variables for security issues.

    Removes or warns about potentially dangerous variables.

    Args:
        env: Dictionary of environment variables.

    Returns:
        Sanitized environment dictionary.
    """
    # Variables that should never be overridden
    dangerous_vars = {
        "PATH",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "HOME",
        "USER",
        "SHELL",
    }

    sanitized = {}

    for key, value in env.items():
        # Check for dangerous variable names
        if key.upper() in dangerous_vars:
            logger.warning(f"Blocked dangerous environment variable: {key}")
            continue

        # Check for null bytes
        if "\x00" in key or "\x00" in value:
            logger.warning(f"Blocked environment variable with null byte: {key}")
            continue

        sanitized[key] = value

    return sanitized
