"""
Swarm Panel — Live view of Claude Swarm backends, tasks, and models.

Shows:
- Backend health with traffic-light indicators
- Active/recent tasks with status
- Model capabilities overview
"""

import logging
from typing import Any, Dict, List

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout

from .styles import COLORS

logger = logging.getLogger(__name__)


class SwarmPanel(QFrame):
    """Dashboard panel showing Swarm backend health, tasks, and models."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(4)

        # Title
        title = QLabel("Swarm Cluster")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        # Status line
        self._status_label = QLabel("  Checking...")
        self._status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        self._layout.addWidget(self._status_label)

        self._content_widgets: list = []
        self._layout.addStretch()

    def update_swarm(self, data: Dict[str, Any]) -> None:
        """Update panel from swarm status data.

        Expected shape::

            {
                "available": True,
                "backends": [ { name, health, url, active_requests, max_concurrent, ... } ],
                "tasks": { "completed": N, "failed": N, "queued": N },
                "workers": N,
            }
        """
        if not isinstance(data, dict):
            logger.warning("Invalid swarm data type: %s", type(data).__name__)
            return

        # Clear old widgets
        for w in self._content_widgets:
            w.deleteLater()
        self._content_widgets.clear()

        available = data.get("available", False)
        if not available:
            self._status_label.setText("  Swarm offline")
            self._status_label.setStyleSheet(f"color: {COLORS['accent_error']}; font-size: 10px;")
            return

        workers = data.get("workers", 0)
        tasks = data.get("tasks", {})
        completed = tasks.get("completed", 0)
        failed = tasks.get("failed", 0)
        queued = tasks.get("queued", 0)

        self._status_label.setText(
            f"  {workers} worker(s) | {completed} done | {failed} failed | {queued} queued"
        )
        self._status_label.setStyleSheet(f"color: {COLORS['accent_success']}; font-size: 10px;")

        # Backends section
        backends = data.get("backends", [])
        if backends:
            header = QLabel("Backends")
            header.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, header)
            self._content_widgets.append(header)

            for b in backends:
                row = self._make_backend_row(b)
                self._layout.insertWidget(self._layout.count() - 1, row)
                self._content_widgets.append(row)

        # Models section (from top-level or nested)
        models = data.get("models", [])
        if models:
            mheader = QLabel("Models")
            mheader.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600; margin-top: 6px;"
            )
            self._layout.insertWidget(self._layout.count() - 1, mheader)
            self._content_widgets.append(mheader)

            for m in models[:6]:
                row = self._make_model_row(m)
                self._layout.insertWidget(self._layout.count() - 1, row)
                self._content_widgets.append(row)

    # ── Helpers ──────────────────────────────────────────────

    def _make_backend_row(self, b: Dict) -> QFrame:
        """Create a row widget for one backend."""
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none; padding: 0;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(8, 2, 8, 2)
        hl.setSpacing(6)

        # Health dot
        health = b.get("health", "unknown")
        color_map = {
            "healthy": COLORS["accent_success"],
            "degraded": COLORS["accent_warning"],
            "unhealthy": COLORS["accent_error"],
        }
        dot_color = color_map.get(health, COLORS["text_muted"])
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
        dot.setFixedWidth(14)
        hl.addWidget(dot)

        # Name
        name = QLabel(b.get("name", "?"))
        name.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 10px; font-weight: 600;")
        name.setFixedWidth(80)
        hl.addWidget(name)

        # Slots
        active = b.get("active_requests", 0)
        total = b.get("max_concurrent", 1)
        slots = QLabel(f"{active}/{total}")
        slots.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        slots.setFixedWidth(30)
        hl.addWidget(slots)

        # Latency
        lat = b.get("avg_latency_ms", 0)
        lat_color = (
            COLORS["accent_success"]
            if lat < 5000
            else COLORS["accent_warning"] if lat < 15000 else COLORS["accent_error"]
        )
        latency = QLabel(f"{lat:.0f}ms" if lat > 0 else "—")
        latency.setStyleSheet(f"color: {lat_color}; font-size: 10px;")
        hl.addWidget(latency)

        hl.addStretch()
        return row

    def _make_model_row(self, m: Dict) -> QLabel:
        """Create a label for one model."""
        name = m.get("name", "?")
        quality = m.get("quality_rating", "?")
        tools = m.get("supports_tool_calling", False)
        tc = m.get("tool_calling_quality", "none")
        icon = "🔧" if tools else ""
        color = COLORS["accent_info"] if tools else COLORS["text_muted"]

        label = QLabel(f"  {name}  q={quality}/10  {tc} {icon}")
        label.setStyleSheet(f"color: {color}; font-size: 10px;")
        return label
