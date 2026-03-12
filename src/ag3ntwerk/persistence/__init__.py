"""
Persistence Layer for ag3ntwerk.

Provides:
- Analytics storage and querying
- Decision audit trails
- Plugin configuration persistence
- Flexible backend support (SQLite, PostgreSQL)
"""

from .database import DatabaseManager, get_database
from .analytics import AnalyticsStore
from .audit import AuditTrail, AuditEntry, AuditAction
from .plugin_config import PluginConfigStore

__all__ = [
    "DatabaseManager",
    "get_database",
    "AnalyticsStore",
    "AuditTrail",
    "AuditEntry",
    "AuditAction",
    "PluginConfigStore",
]
