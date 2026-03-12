"""
Central identity module for agent code normalization and canonicalization.

This module provides a single source of truth for handling agent codes
case-insensitively while maintaining canonical codes internally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


def normalize_key(code: str) -> str:
    """
    Normalize a code to a stable dictionary key.

    Rules:
    - strip whitespace
    - lower-case
    - remove internal spaces

    Args:
        code: The agent code to normalize

    Returns:
        Normalized key for dictionary lookups

    Examples:
        >>> normalize_key("Citadel")
        'cseco'
        >>> normalize_key("  Forge  ")
        'cto'
        >>> normalize_key("C R O")
        'cro'
    """
    if code is None:
        return ""
    return "".join(code.strip().split()).lower()


@dataclass(frozen=True)
class AgentRegistry:
    """
    Stores canonical agent codes and allows case-insensitive resolution.

    This registry maps normalized keys back to their canonical codes,
    enabling case-insensitive lookups while preserving the original
    mixed-case codes used internally.
    """

    canonical_codes: Dict[str, str]  # normalized_key -> canonical_code

    @classmethod
    def from_codes(cls, codes: Iterable[str]) -> "AgentRegistry":
        """
        Create a registry from an iterable of canonical codes.

        Args:
            codes: Iterable of canonical agent codes

        Returns:
            AgentRegistry instance

        Examples:
            >>> reg = AgentRegistry.from_codes(["Citadel", "Vector", "Aegis"])
            >>> reg.resolve("cseco")
            'Citadel'
        """
        mapping: Dict[str, str] = {}
        for c in codes:
            k = normalize_key(c)
            mapping[k] = c
        return cls(canonical_codes=mapping)

    def resolve(self, code: str) -> Optional[str]:
        """
        Return canonical code or None if unknown.

        Args:
            code: Agent code (any case)

        Returns:
            Canonical code string, or None if not found

        Examples:
            >>> reg = AgentRegistry.from_codes(["Citadel"])
            >>> reg.resolve("CSECO")
            'Citadel'
            >>> reg.resolve("cseco")
            'Citadel'
            >>> reg.resolve("unknown") is None
            True
        """
        return self.canonical_codes.get(normalize_key(code))

    def is_known(self, code: str) -> bool:
        """
        Check if a code is known in this registry.

        Args:
            code: Agent code (any case)

        Returns:
            True if the code resolves to a canonical code
        """
        return self.resolve(code) is not None

    def all_codes(self) -> Iterable[str]:
        """
        Return all canonical codes in the registry.

        Returns:
            Iterable of canonical code strings
        """
        return self.canonical_codes.values()
