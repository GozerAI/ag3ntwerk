"""
Audit Facade - Audit trail management and export.

This facade manages:
- Audit entry creation
- Audit log queries
- Audit export (JSON)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ag3ntwerk.core.decisions.models import AuditEntry, AuditAction
from ag3ntwerk.core.decisions._utils import generate_id, utc_now, apply_max_limit

logger = logging.getLogger(__name__)


class AuditFacade:
    """
    Facade for audit-related operations.

    Manages audit trail creation, queries, and export.
    """

    def __init__(self, max_entries: int = 10000):
        """
        Initialize the audit facade.

        Args:
            max_entries: Maximum audit entries to keep
        """
        self._audit_log: List[AuditEntry] = []
        self._max_audit_entries = max_entries

    # --- Entry Creation ---

    def add_audit_entry(
        self,
        decision_id: str,
        action: AuditAction,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEntry:
        """
        Add an entry to the audit log.

        Args:
            decision_id: ID of the decision
            action: Type of action
            actor: Who performed the action
            details: Additional details
            ip_address: IP address of actor
            user_agent: User agent string

        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            id=generate_id(),
            decision_id=decision_id,
            action=action,
            actor=actor,
            timestamp=utc_now(),
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._audit_log.append(entry)
        self._audit_log = apply_max_limit(self._audit_log, self._max_audit_entries)

        return entry

    # --- Queries ---

    def get_audit_log(
        self,
        decision_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Get audit log entries.

        Args:
            decision_id: Filter by decision
            action: Filter by action type
            actor: Filter by actor
            limit: Maximum entries

        Returns:
            List of audit entries
        """
        entries = self._audit_log

        if decision_id:
            entries = [e for e in entries if e.decision_id == decision_id]
        if action:
            entries = [e for e in entries if e.action == action]
        if actor:
            entries = [e for e in entries if e.actor == actor]

        return entries[-limit:]

    # --- Export ---

    def export_audit_log(self, decision_id: Optional[str] = None) -> str:
        """
        Export audit log as JSON.

        Args:
            decision_id: Optional filter by decision

        Returns:
            JSON string of audit entries
        """
        entries = self.get_audit_log(decision_id=decision_id, limit=10000)
        return json.dumps([e.to_dict() for e in entries], indent=2)

    # --- Stats ---

    def get_stats(self) -> Dict[str, Any]:
        """Get audit facade statistics."""
        return {
            "audit_log_size": len(self._audit_log),
        }
