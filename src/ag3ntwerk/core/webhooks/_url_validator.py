"""
URL validation and SSRF protection for webhooks.

Provides comprehensive protection against Server-Side Request Forgery
(SSRF) attacks by validating webhook URLs against:

- Private/reserved IP ranges (IPv4 and IPv6)
- Internal hostnames (localhost, *.local, *.internal)
- Cloud metadata endpoints (AWS, GCP, Azure)
- DNS rebinding (resolves hostname before IP check)
- Scheme enforcement (HTTPS required in production)
"""

import asyncio
import ipaddress
import logging
import re
import socket
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private/reserved IPv4 networks that MUST be blocked to prevent SSRF.
_BLOCKED_IPV4_NETWORKS: List[ipaddress.IPv4Network] = [
    ipaddress.IPv4Network("127.0.0.0/8"),  # Loopback
    ipaddress.IPv4Network("10.0.0.0/8"),  # Private (RFC 1918)
    ipaddress.IPv4Network("172.16.0.0/12"),  # Private (RFC 1918)
    ipaddress.IPv4Network("192.168.0.0/16"),  # Private (RFC 1918)
    ipaddress.IPv4Network("169.254.0.0/16"),  # Link-local (APIPA)
    ipaddress.IPv4Network("0.0.0.0/8"),  # "This" network
    ipaddress.IPv4Network("100.64.0.0/10"),  # Shared address space (CGN)
    ipaddress.IPv4Network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1 (documentation)
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2 (documentation)
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3 (documentation)
    ipaddress.IPv4Network("224.0.0.0/4"),  # Multicast
    ipaddress.IPv4Network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.IPv4Network("255.255.255.255/32"),  # Broadcast
]

# Private/reserved IPv6 networks that MUST be blocked to prevent SSRF.
_BLOCKED_IPV6_NETWORKS: List[ipaddress.IPv6Network] = [
    ipaddress.IPv6Network("::1/128"),  # Loopback
    ipaddress.IPv6Network("fe80::/10"),  # Link-local
    ipaddress.IPv6Network("fc00::/7"),  # Unique local (RFC 4193)
    ipaddress.IPv6Network("::ffff:0:0/96"),  # IPv4-mapped IPv6
    ipaddress.IPv6Network("::/128"),  # Unspecified
    ipaddress.IPv6Network("ff00::/8"),  # Multicast
    ipaddress.IPv6Network("100::/64"),  # Discard-only (RFC 6666)
    ipaddress.IPv6Network("2001:db8::/32"),  # Documentation
    ipaddress.IPv6Network("::ffff:127.0.0.0/104"),  # IPv4-mapped loopback
    ipaddress.IPv6Network("::ffff:10.0.0.0/104"),  # IPv4-mapped private
    ipaddress.IPv6Network("::ffff:172.16.0.0/108"),  # IPv4-mapped private
    ipaddress.IPv6Network("::ffff:192.168.0.0/112"),  # IPv4-mapped private
    ipaddress.IPv6Network("::ffff:169.254.0.0/112"),  # IPv4-mapped link-local
]

# Hostnames that are always blocked (case-insensitive match).
_BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "169.254.169.254",  # AWS EC2 metadata
    "metadata.google.internal",  # GCP metadata
    "metadata.internal",  # Generic cloud metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}

# Hostname suffix patterns that are blocked (e.g. *.local, *.internal).
_BLOCKED_HOSTNAME_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".localdomain",
    ".home.arpa",
    ".corp",
    ".lan",
)

# Regex for detecting numeric IPv6 in brackets (e.g. [::1], [fe80::1])
_IPV6_BRACKET_RE = re.compile(r"^\[(.+)\]$")


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check whether an IP address falls within any blocked network."""
    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in net for net in _BLOCKED_IPV4_NETWORKS)
    elif isinstance(ip, ipaddress.IPv6Address):
        # Also check if it's an IPv4-mapped IPv6 address
        if ip.ipv4_mapped:
            return _is_blocked_ip(ip.ipv4_mapped)
        return any(ip in net for net in _BLOCKED_IPV6_NETWORKS)
    return False


def _is_blocked_hostname(hostname: str) -> str | None:
    """
    Check whether a hostname matches any blocked pattern.

    Returns:
        Error message if blocked, None if allowed.
    """
    lower = hostname.lower().strip(".")

    # Exact match
    if lower in _BLOCKED_HOSTNAMES:
        return f"Host '{hostname}' is a blocked internal address."

    # Suffix match (*.local, *.internal, etc.)
    for suffix in _BLOCKED_HOSTNAME_SUFFIXES:
        if lower.endswith(suffix):
            return f"Host '{hostname}' matches blocked internal pattern " f"'*{suffix}'."

    # Bracketed IPv6 (e.g. [::1])
    m = _IPV6_BRACKET_RE.match(lower)
    if m:
        inner = m.group(1)
        try:
            ip = ipaddress.ip_address(inner)
            if _is_blocked_ip(ip):
                return f"Host '{hostname}' resolves to blocked IP {ip}."
        except ValueError:
            pass

    # Bare IP address
    try:
        ip = ipaddress.ip_address(lower)
        if _is_blocked_ip(ip):
            return f"Host '{hostname}' is a blocked IP address."
    except ValueError:
        pass  # Not a bare IP — that's fine, it's a hostname

    return None


class URLValidator:
    """Validates webhook URLs against SSRF and security policies."""

    ALLOWED_SCHEMES = {"http", "https"}

    def __init__(self, allow_localhost: bool = False, allow_http: bool = True):
        """
        Args:
            allow_localhost: If True, skip hostname and IP blocking
                             (development only).
            allow_http: If True, allow both http and https schemes.
                        Set to False in production to require HTTPS.
        """
        self._allow_localhost = allow_localhost
        self._allow_http = allow_http

    async def validate(self, url: str) -> tuple[bool, str]:
        """
        Validate a webhook URL for SSRF safety.

        Performs the following checks in order:
        1. Scheme validation (https required unless allow_http=True)
        2. Host presence check
        3. Hostname blocklist (localhost, *.local, *.internal, etc.)
        4. DNS resolution to IP addresses
        5. IP address blocklist (private, reserved, link-local, loopback)

        Returns:
            (is_valid, error_message) — error_message is empty when valid.
        """
        try:
            parsed = urlparse(url)

            # ----------------------------------------------------------
            # 1. Scheme check
            # ----------------------------------------------------------
            allowed_schemes = self.ALLOWED_SCHEMES if self._allow_http else {"https"}
            if parsed.scheme not in allowed_schemes:
                if not self._allow_http:
                    return False, "Only HTTPS webhook URLs are allowed."
                return False, f"Invalid scheme: {parsed.scheme}. Must be http or https."

            # ----------------------------------------------------------
            # 2. Host presence
            # ----------------------------------------------------------
            if not parsed.netloc:
                return False, "URL must have a host."

            host = parsed.hostname or ""
            if not host:
                return False, "URL must have a valid hostname."

            # ----------------------------------------------------------
            # 3. Hostname blocklist (skip in dev when allow_localhost=True)
            # ----------------------------------------------------------
            if not self._allow_localhost:
                block_reason = _is_blocked_hostname(host)
                if block_reason:
                    logger.warning(
                        "Webhook URL blocked by hostname check",
                        url=url,
                        host=host,
                        reason=block_reason,
                    )
                    return False, block_reason

                # -------------------------------------------------------
                # 4. DNS resolution — resolve hostname to IPs BEFORE the
                #    IP-range check to prevent DNS rebinding attacks.
                # -------------------------------------------------------
                try:
                    loop = asyncio.get_running_loop()
                    addrinfo = await loop.getaddrinfo(
                        host,
                        None,
                        family=socket.AF_UNSPEC,
                        type=socket.SOCK_STREAM,
                    )
                except socket.gaierror:
                    return False, f"Could not resolve hostname: {host}"

                if not addrinfo:
                    return False, f"Hostname resolved to no addresses: {host}"

                # -------------------------------------------------------
                # 5. IP address blocklist — every resolved address must
                #    pass; if ANY address is blocked, reject the URL.
                # -------------------------------------------------------
                for family, _, _, _, sockaddr in addrinfo:
                    ip_str = sockaddr[0]
                    try:
                        ip = ipaddress.ip_address(ip_str)
                    except ValueError:
                        continue

                    if _is_blocked_ip(ip):
                        logger.warning(
                            "Webhook URL blocked: resolved to private/reserved IP",
                            url=url,
                            host=host,
                            resolved_ip=str(ip),
                        )
                        return False, (
                            f"Resolved IP {ip_str} is not allowed " f"(private/reserved range)."
                        )

            return True, ""

        except Exception as e:
            logger.error("URL validation error", url=url, error=str(e))
            return False, f"Invalid URL: {e}"
