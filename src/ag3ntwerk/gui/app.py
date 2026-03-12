"""
ag3ntwerk Dashboard - Overwatch-centric task monitoring and communication.

Simple dashboard showing:
- Task status across all agents
- Single chat interface routed through Overwatch (Overwatch)
- Agent workload overview
"""

import logging
import sys
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QScrollArea,
    QLineEdit,
    QPushButton,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from .styles import COLORS, get_agent_color
from .backend import CSuiteBackend
from .swarm_panel import SwarmPanel

logger = logging.getLogger(__name__)


class TaskCard(QFrame):
    """A single task card showing status."""

    def __init__(self, task_id: str, description: str, assigned_to: str, status: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)

        color = get_agent_color(assigned_to)
        status_color = {
            "pending": COLORS["text_muted"],
            "in_progress": COLORS["accent_warning"],
            "completed": COLORS["accent_success"],
            "failed": COLORS["accent_error"],
        }.get(status, COLORS["text_muted"])

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border-left: 3px solid {color};
                border-radius: 6px;
                padding: 8px;
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Task info
        info = QVBoxLayout()
        info.setSpacing(2)

        desc = QLabel(description[:50] + "..." if len(description) > 50 else description)
        desc.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        info.addWidget(desc)

        meta = QLabel(f"{assigned_to}")
        meta.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
        info.addWidget(meta)

        layout.addLayout(info)
        layout.addStretch()

        # Status
        status_label = QLabel(f"● {status.replace('_', ' ').title()}")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        layout.addWidget(status_label)


class ExecutiveStatus(QFrame):
    """Shows an agent's current workload."""

    def __init__(self, code: str, codename: str, task_count: int = 0, parent=None):
        super().__init__(parent)
        self.code = code
        color = get_agent_color(code)

        self.setFixedSize(140, 80)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Code
        code_label = QLabel(code)
        code_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 700;")
        layout.addWidget(code_label)

        # Codename
        name_label = QLabel(codename)
        name_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        layout.addWidget(name_label)

        layout.addStretch()

        # Task count
        self.count_label = QLabel(f"{task_count} tasks")
        self.count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        layout.addWidget(self.count_label)

        # Health indicator
        self.health_indicator = QLabel("●")
        self.health_indicator.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 8px;")
        layout.addWidget(self.health_indicator)

    def set_task_count(self, count: int):
        self.count_label.setText(f"{count} task{'s' if count != 1 else ''}")

    def set_health(self, is_healthy: bool, health_score: float = 1.0):
        if is_healthy and health_score >= 0.7:
            color = COLORS["accent_success"]
        elif is_healthy and health_score >= 0.4:
            color = COLORS["accent_warning"]
        else:
            color = COLORS["accent_error"]
        self.health_indicator.setStyleSheet(f"color: {color}; font-size: 8px;")


class PersonalityPanel(QFrame):
    """Shows personality trait bars per agent, color-coded by drift from baseline."""

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
        self._layout.setSpacing(8)

        title = QLabel("Personality Profiles")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        self._trait_widgets: Dict[str, QLabel] = {}
        self._layout.addStretch()

    def update_profiles(self, profiles: Dict[str, Dict]) -> None:
        """Update displayed profiles from metacognition data.

        Args:
            profiles: Dict of {agent_code: {traits: {name: {value, baseline, drift}}}}
        """
        if not isinstance(profiles, dict):
            logger.warning("Invalid profiles data type: %s", type(profiles).__name__)
            return
        logger.debug("Updating profiles for %d agents", len(profiles))

        # Clear existing trait widgets
        for widget in self._trait_widgets.values():
            widget.deleteLater()
        self._trait_widgets.clear()

        for code, data in profiles.items():
            if not isinstance(data, dict):
                logger.warning("Invalid profile entry for %s: %s", code, type(data).__name__)
                continue
            traits = data.get("traits", {})
            if not traits:
                continue

            # Agent label
            label = QLabel(f"{code}")
            label.setStyleSheet(
                f"color: {get_agent_color(code)}; font-size: 12px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, label)
            self._trait_widgets[f"{code}_label"] = label

            # Trait bars
            for trait_name, trait_info in traits.items():
                if not isinstance(trait_info, dict):
                    logger.warning("Invalid trait info for %s.%s", code, trait_name)
                    continue
                value = trait_info.get("value", 0.5)
                baseline = trait_info.get("baseline", 0.5)
                drift = abs(value - baseline)

                # Color based on drift
                if drift > 0.2:
                    bar_color = COLORS["accent_error"]
                elif drift > 0.1:
                    bar_color = COLORS["accent_warning"]
                else:
                    bar_color = COLORS["accent_success"]

                bar_text = f"  {trait_name}: {value:.2f}"
                bar_label = QLabel(bar_text)
                bar_label.setStyleSheet(f"color: {bar_color}; font-size: 10px;")
                self._layout.insertWidget(self._layout.count() - 1, bar_label)
                self._trait_widgets[f"{code}_{trait_name}"] = bar_label


class DriftAlertBanner(QFrame):
    """Banner showing critical drift alerts. Hidden when no critical alerts exist."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['accent_error']}20;
                border: 1px solid {COLORS['accent_error']};
                border-radius: 8px;
                padding: 8px 16px;
            }}
        """
        )
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)

        self._icon = QLabel("!")
        self._icon.setStyleSheet(
            f"color: {COLORS['accent_error']}; font-size: 14px; font-weight: 700;"
        )
        self._layout.addWidget(self._icon)

        self._label = QLabel("")
        self._label.setStyleSheet(f"color: {COLORS['accent_error']}; font-size: 12px;")
        self._label.setWordWrap(True)
        self._layout.addWidget(self._label, 1)

        self.setVisible(False)

    def update_alerts(self, alerts: List[Dict]) -> None:
        """Update banner with drift alerts. Shows only critical alerts."""
        if not isinstance(alerts, list):
            logger.warning("Invalid alerts data type: %s", type(alerts).__name__)
            self.setVisible(False)
            return

        critical = [a for a in alerts if isinstance(a, dict) and a.get("severity") == "critical"]
        if not critical:
            self.setVisible(False)
            return

        logger.info("Showing %d critical drift alerts", len(critical))
        parts = []
        for alert in critical[:3]:  # Show max 3
            try:
                parts.append(
                    f"{alert['agent_code']}.{alert['trait_name']} " f"(drift: {alert['drift']:.2f})"
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Malformed drift alert entry: %s", e)
                continue
        if not parts:
            self.setVisible(False)
            return
        text = "Critical drift: " + ", ".join(parts)
        if len(critical) > 3:
            text += f" (+{len(critical) - 3} more)"

        self._label.setText(text)
        self.setVisible(True)


class TrendPanel(QFrame):
    """Shows trait trend classifications per agent."""

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

        title = QLabel("Personality Trends")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        self._content_widgets: list = []
        self._layout.addStretch()

    def update_trends(self, trend_data: Dict) -> None:
        """Update from get_trend_summary() output."""
        if not isinstance(trend_data, dict):
            logger.warning("Invalid trend_data type: %s", type(trend_data).__name__)
            return

        for w in self._content_widgets:
            w.deleteLater()
        self._content_widgets.clear()

        agents = trend_data.get("agents", {})
        if not isinstance(agents, dict):
            logger.warning("Invalid agents data in trends: %s", type(agents).__name__)
            return
        logger.debug("Updating trends for %d agents", len(agents))

        for code, agent_data in agents.items():
            if not isinstance(agent_data, dict):
                logger.warning("Invalid trend entry for %s", code)
                continue
            traits = agent_data.get("traits", {})
            if not traits:
                continue

            label = QLabel(code)
            label.setStyleSheet(
                f"color: {get_agent_color(code)}; font-size: 12px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, label)
            self._content_widgets.append(label)

            for trait_name, info in traits.items():
                if not isinstance(info, dict):
                    continue
                classification = info.get("classification", "stable")
                velocity = info.get("velocity", 0.0)
                color = {
                    "improving": COLORS["accent_success"],
                    "stable": COLORS["text_muted"],
                    "declining": COLORS["accent_error"],
                    "oscillating": COLORS["accent_warning"],
                }.get(classification, COLORS["text_muted"])

                text = f"  {trait_name}: {classification} ({velocity:+.3f})"
                trait_label = QLabel(text)
                trait_label.setStyleSheet(f"color: {color}; font-size: 10px;")
                self._layout.insertWidget(self._layout.count() - 1, trait_label)
                self._content_widgets.append(trait_label)


class CoherencePanel(QFrame):
    """Shows coherence scores and agent health status."""

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

        title = QLabel("Agent Health & Coherence")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        self._content_widgets: list = []
        self._layout.addStretch()

    def update_coherence(self, reports: List[Dict]) -> None:
        """Update from list of compute_coherence().to_dict() dicts."""
        if not isinstance(reports, list):
            logger.warning("Invalid coherence reports type: %s", type(reports).__name__)
            return
        logger.debug("Updating coherence for %d reports", len(reports))

        for w in self._content_widgets:
            w.deleteLater()
        self._content_widgets.clear()

        for report in reports:
            if not isinstance(report, dict):
                logger.warning("Invalid coherence report entry: %s", type(report).__name__)
                continue
            code = report.get("agent_code", "?")
            score = report.get("coherence_score", 1.0)
            health = report.get("health_classification", "healthy")
            tensions = report.get("tensions", [])

            health_color = {
                "healthy": COLORS["accent_success"],
                "drifting": COLORS["accent_warning"],
                "oscillating": COLORS["accent_warning"],
                "degrading": COLORS["accent_error"],
            }.get(health, COLORS["text_muted"])

            text = f"{code}: {health} (coherence: {score:.2f})"
            label = QLabel(text)
            label.setStyleSheet(f"color: {health_color}; font-size: 11px; font-weight: 500;")
            self._layout.insertWidget(self._layout.count() - 1, label)
            self._content_widgets.append(label)

            if score < 0.8 and isinstance(tensions, list):
                for t in tensions[:3]:
                    if not isinstance(t, dict):
                        continue
                    desc = t.get(
                        "description", f"{t.get('trait_a', '?')} vs {t.get('trait_b', '?')}"
                    )
                    t_label = QLabel(f"    {desc}")
                    t_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
                    self._layout.insertWidget(self._layout.count() - 1, t_label)
                    self._content_widgets.append(t_label)


class TeamLearningPanel(QFrame):
    """Shows learned team compositions and best pairs."""

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

        title = QLabel("Team Learning")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        self._content_widgets: list = []
        self._layout.addStretch()

    def update_teams(self, stats: Dict, pairs: List[Dict]) -> None:
        """Update from get_team_stats() and get_best_pairs() output."""
        if not isinstance(stats, dict):
            logger.warning("Invalid team stats type: %s", type(stats).__name__)
            stats = {}
        if not isinstance(pairs, list):
            logger.warning("Invalid team pairs type: %s", type(pairs).__name__)
            pairs = []
        logger.debug(
            "Updating teams: %d compositions, %d pairs",
            len(stats.get("compositions", [])),
            len(pairs),
        )

        for w in self._content_widgets:
            w.deleteLater()
        self._content_widgets.clear()

        compositions = stats.get("compositions", [])
        if not isinstance(compositions, list):
            compositions = []
        if compositions:
            header = QLabel("Top Compositions")
            header.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, header)
            self._content_widgets.append(header)

            for comp in compositions[:5]:
                if not isinstance(comp, dict):
                    continue
                team = ", ".join(comp.get("team", []))
                rate = comp.get("success_rate", 0)
                task = comp.get("task_type", "?")
                color = COLORS["accent_success"] if rate >= 0.7 else COLORS["accent_warning"]
                text = f"  {team} ({task}): {rate:.0%}"
                label = QLabel(text)
                label.setStyleSheet(f"color: {color}; font-size: 10px;")
                self._layout.insertWidget(self._layout.count() - 1, label)
                self._content_widgets.append(label)

        if pairs:
            header = QLabel("Best Pairs")
            header.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, header)
            self._content_widgets.append(header)

            for pair in pairs[:5]:
                if not isinstance(pair, dict):
                    continue
                names = ", ".join(pair.get("pair", []))
                rate = pair.get("success_rate", 0)
                color = COLORS["accent_success"] if rate >= 0.7 else COLORS["accent_warning"]
                text = f"  {names}: {rate:.0%}"
                label = QLabel(text)
                label.setStyleSheet(f"color: {color}; font-size: 10px;")
                self._layout.insertWidget(self._layout.count() - 1, label)
                self._content_widgets.append(label)

        if not compositions and not pairs:
            empty = QLabel("  No team data yet")
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            self._layout.insertWidget(self._layout.count() - 1, empty)
            self._content_widgets.append(empty)


class TraitMapPanel(QFrame):
    """Shows learned trait map overlay and validation status."""

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

        title = QLabel("Learned Trait Map")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(title)

        self._content_widgets: list = []
        self._layout.addStretch()

    def update_trait_map(self, learned: Dict, updates: List[Dict]) -> None:
        """Update from get_learned_trait_map() and trait_map_updates."""
        if not isinstance(learned, dict):
            logger.warning("Invalid learned trait map type: %s", type(learned).__name__)
            learned = {}
        if not isinstance(updates, list):
            logger.warning("Invalid trait map updates type: %s", type(updates).__name__)
            updates = []
        logger.debug("Updating trait map: %d task types, %d updates", len(learned), len(updates))

        for w in self._content_widgets:
            w.deleteLater()
        self._content_widgets.clear()

        if not learned:
            empty = QLabel("  No learned overrides yet")
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            self._layout.insertWidget(self._layout.count() - 1, empty)
            self._content_widgets.append(empty)
            return

        # Build validation status lookup
        validation_map: Dict[str, str] = {}
        for u in updates:
            if not isinstance(u, dict):
                continue
            key = f"{u.get('task_type')}:{u.get('trait_name')}"
            validation_map[key] = u.get("validation_status", "pending")

        for task_type, traits in learned.items():
            if not isinstance(traits, dict):
                logger.warning("Invalid traits for task type %s", task_type)
                continue

            header = QLabel(task_type)
            header.setStyleSheet(
                f"color: {COLORS['accent_info']}; font-size: 11px; font-weight: 600;"
            )
            self._layout.insertWidget(self._layout.count() - 1, header)
            self._content_widgets.append(header)

            for trait_name, value in traits.items():
                key = f"{task_type}:{trait_name}"
                status = validation_map.get(key, "unknown")
                status_color = {
                    "validated": COLORS["accent_success"],
                    "pending": COLORS["accent_warning"],
                    "rolled_back": COLORS["accent_error"],
                }.get(status, COLORS["text_muted"])

                try:
                    text = f"  {trait_name}: {value:.2f} [{status}]"
                except (TypeError, ValueError):
                    text = f"  {trait_name}: {value} [{status}]"
                label = QLabel(text)
                label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
                self._layout.insertWidget(self._layout.count() - 1, label)
                self._content_widgets.append(label)


class COODashboard(QMainWindow):
    """Main ag3ntwerk Dashboard - Overwatch-centric view."""

    def __init__(self):
        super().__init__()
        logger.info("Initializing ag3ntwerk Dashboard")
        self.setWindowTitle("ag3ntwerk Dashboard")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self._tasks: List[Dict] = []
        self._exec_widgets: Dict[str, ExecutiveStatus] = {}

        # Backend
        self._backend = CSuiteBackend(self)
        self._connect_signals()

        self._setup_ui()
        logger.info("UI setup complete")

        # Connect to backend after UI is ready
        QTimer.singleShot(100, self._init_backend)

    def _connect_signals(self):
        """Connect backend signals to UI handlers."""
        logger.debug("Connecting backend signals")
        self._backend.connected.connect(self._on_connected)
        self._backend.task_created.connect(self._on_task_created)
        self._backend.task_updated.connect(self._on_task_updated)
        self._backend.tasks_refreshed.connect(self._on_tasks_refreshed)
        self._backend.coo_response.connect(self._on_coo_response)
        self._backend.agent_status.connect(self._on_agent_status)
        self._backend.metacognition_status.connect(self._on_metacognition_status)
        self._backend.drift_alerts.connect(self._on_drift_alerts)
        self._backend.coherence_data.connect(self._on_coherence_data)
        self._backend.trend_data.connect(self._on_trend_data)
        self._backend.team_data.connect(self._on_team_data)
        self._backend.trait_map_data.connect(self._on_trait_map_data)
        self._backend.swarm_data.connect(self._on_swarm_data)

    def _init_backend(self):
        """Initialize backend connection."""
        logger.info("Initiating backend connection")
        self._add_message("Connecting to ag3ntwerk backend...", is_coo=True)
        self._backend.connect_backend()

    def _on_connected(self, success: bool, message: str):
        """Handle backend connection result."""
        logger.info("Backend connection result: success=%s message=%s", success, message)
        if success:
            self._add_message(f"Connected: {message}", is_coo=True)
            self._add_message("Ready to coordinate. What would you like me to handle?", is_coo=True)
            self.coo_status_label.setText("● Nexus Online")
            self.coo_status_label.setStyleSheet(
                f"color: {COLORS['accent_success']}; font-size: 12px;"
            )
        else:
            self._add_message(f"Connection failed: {message}", is_coo=True)
            self._add_message("Running in offline mode with limited functionality.", is_coo=True)
            self.coo_status_label.setText("● Nexus Offline")
            self.coo_status_label.setStyleSheet(
                f"color: {COLORS['accent_error']}; font-size: 12px;"
            )

    def _on_task_created(self, task: Dict):
        """Handle new task creation."""
        logger.debug("Task created: %s", task.get("id", "?") if isinstance(task, dict) else "?")
        self._tasks.append(task)
        self._refresh_task_list()

    def _on_task_updated(self, task: Dict):
        """Handle task update."""
        logger.debug(
            "Task updated: %s -> %s",
            task.get("id", "?") if isinstance(task, dict) else "?",
            task.get("status", "?") if isinstance(task, dict) else "?",
        )
        for i, t in enumerate(self._tasks):
            if t["id"] == task["id"]:
                self._tasks[i] = task
                break
        self._refresh_task_list()

    def _on_tasks_refreshed(self, tasks: List[Dict]):
        """Handle full task list refresh."""
        logger.debug("Tasks refreshed: %d tasks", len(tasks) if isinstance(tasks, list) else 0)
        self._tasks = tasks
        self._refresh_task_list()

    def _on_coo_response(self, response: str):
        """Handle Nexus response message."""
        self._add_message(response, is_coo=True)

    def _on_agent_status(self, status: Dict):
        """Handle agent status update."""
        # Update health indicators
        health_data = status.get("health", {})
        if health_data.get("health_routing_enabled"):
            agents_health = health_data.get("agents", {})
            for code, widget in self._exec_widgets.items():
                if code in agents_health:
                    h = agents_health[code]
                    widget.set_health(h.get("is_healthy", True), h.get("health_score", 1.0))

        # Update task counts from Nexus metrics
        coo_status = status.get("coo_status", {})
        if coo_status:
            metrics = coo_status.get("metrics", {})
            # Display metrics could be added here

    def _on_metacognition_status(self, data: Dict):
        """Handle metacognition status update — refresh personality panel."""
        logger.debug("Metacognition status received")
        if not isinstance(data, dict):
            logger.warning("Invalid metacognition data type: %s", type(data).__name__)
            return
        profiles = data.get("profiles", {})
        self._personality_panel.update_profiles(profiles)

    def _on_drift_alerts(self, alerts: List[Dict]):
        """Handle drift alerts — update banner."""
        logger.debug(
            "Drift alerts received: %d alerts", len(alerts) if isinstance(alerts, list) else 0
        )
        self._drift_banner.update_alerts(alerts)

    def _on_coherence_data(self, reports: list):
        """Handle coherence data update."""
        logger.debug(
            "Coherence data received: %d reports", len(reports) if isinstance(reports, list) else 0
        )
        self._coherence_panel.update_coherence(reports)

    def _on_trend_data(self, data: Dict):
        """Handle trend data update."""
        logger.debug("Trend data received")
        self._trend_panel.update_trends(data)

    def _on_team_data(self, data: Dict):
        """Handle team learning data update."""
        logger.debug("Team data received")
        if not isinstance(data, dict):
            logger.warning("Invalid team data type: %s", type(data).__name__)
            return
        self._team_learning_panel.update_teams(data.get("stats", {}), data.get("pairs", []))

    def _on_trait_map_data(self, data: Dict):
        """Handle trait map data update."""
        logger.debug("Trait map data received")
        if not isinstance(data, dict):
            logger.warning("Invalid trait map data type: %s", type(data).__name__)
            return
        self._trait_map_panel.update_trait_map(data.get("learned", {}), data.get("updates", []))

    def _on_swarm_data(self, data: Dict):
        """Handle swarm status data update."""
        logger.debug("Swarm data received")
        if not isinstance(data, dict):
            logger.warning("Invalid swarm data type: %s", type(data).__name__)
            return
        self._swarm_panel.update_swarm(data)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Drift alert banner (hidden by default)
        self._drift_banner = DriftAlertBanner()
        layout.addWidget(self._drift_banner)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(24)

        # Left: Agent grid + Tasks
        left = QVBoxLayout()
        left.setSpacing(16)

        # Agent status grid
        exec_section = self._create_executive_grid()
        left.addWidget(exec_section)

        # Active tasks
        tasks_section = self._create_tasks_section()
        left.addWidget(tasks_section, 1)

        # Metacognition panels (scrollable)
        meta_scroll = QScrollArea()
        meta_scroll.setWidgetResizable(True)
        meta_scroll.setStyleSheet(
            f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """
        )
        meta_container = QWidget()
        meta_layout = QVBoxLayout(meta_container)
        meta_layout.setSpacing(12)
        meta_layout.setContentsMargins(0, 0, 0, 0)

        self._trend_panel = TrendPanel()
        meta_layout.addWidget(self._trend_panel)
        self._coherence_panel = CoherencePanel()
        meta_layout.addWidget(self._coherence_panel)
        self._team_learning_panel = TeamLearningPanel()
        meta_layout.addWidget(self._team_learning_panel)
        self._trait_map_panel = TraitMapPanel()
        meta_layout.addWidget(self._trait_map_panel)
        self._swarm_panel = SwarmPanel()
        meta_layout.addWidget(self._swarm_panel)
        meta_layout.addStretch()

        meta_scroll.setWidget(meta_container)
        left.addWidget(meta_scroll, 1)

        content.addLayout(left, 2)

        # Right: Chat + Personality Panel
        right = QVBoxLayout()
        right.setSpacing(16)
        chat_section = self._create_chat_section()
        right.addWidget(chat_section, 2)
        self._personality_panel = PersonalityPanel()
        right.addWidget(self._personality_panel, 1)
        content.addLayout(right, 1)

        layout.addLayout(content)

    def _create_header(self) -> QFrame:
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("ag3ntwerk Dashboard")
        title.setStyleSheet(
            f"""
            color: {COLORS['text_primary']};
            font-size: 24px;
            font-weight: 700;
        """
        )
        layout.addWidget(title)

        layout.addStretch()

        # Nexus Status
        self.coo_status_label = QLabel("● Connecting...")
        self.coo_status_label.setStyleSheet(f"color: {COLORS['accent_warning']}; font-size: 12px;")
        layout.addWidget(self.coo_status_label)

        return header

    def _create_executive_grid(self) -> QFrame:
        section = QFrame()
        section.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Agent Status")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        # Grid of agents
        grid = QGridLayout()
        grid.setSpacing(8)

        agents = [
            ("Overwatch", "Overwatch"),
            ("Sentinel", "Sentinel"),
            ("Forge", "Forge"),
            ("Keystone", "Keystone"),
            ("Compass", "Compass"),
            ("Axiom", "Axiom"),
            ("Index", "Index"),
            ("Blueprint", "Blueprint"),
            ("Echo", "Echo"),
            ("Beacon", "Beacon"),
            ("Foundry", "Foundry"),
            ("Citadel", "Citadel"),
            ("Aegis", "Aegis"),
            ("Accord", "Accord"),
            ("Vector", "Vector"),
        ]

        for i, (code, codename) in enumerate(agents):
            widget = ExecutiveStatus(code, codename)
            self._exec_widgets[code] = widget
            grid.addWidget(widget, i // 5, i % 5)

        layout.addLayout(grid)
        return section

    def _create_tasks_section(self) -> QFrame:
        section = QFrame()
        section.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 12px;
            }}
        """
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Active Tasks")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        self.task_count_label = QLabel("0 tasks")
        self.task_count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header.addWidget(self.task_count_label)

        layout.addLayout(header)

        # Scrollable task list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.addStretch()

        scroll.setWidget(self.tasks_container)
        layout.addWidget(scroll)

        return section

    def _create_chat_section(self) -> QFrame:
        section = QFrame()
        section.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-radius: 12px;
            }}
        """
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        title = QLabel("Overwatch - Overwatch")
        title.setStyleSheet(
            f"""
            color: {get_agent_color('Overwatch')};
            font-size: 14px;
            font-weight: 600;
        """
        )
        layout.addWidget(title)

        subtitle = QLabel("All requests routed through Overwatch")
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(subtitle)

        # Messages area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 8, 0, 8)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        scroll.setWidget(self.messages_container)
        self.messages_scroll = scroll
        layout.addWidget(scroll, 1)

        # Input
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Send a task to Overwatch...")
        self.message_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {get_agent_color('Overwatch')};
            }}
        """
        )
        self.message_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.message_input)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(70)
        send_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {get_agent_color('Overwatch')};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #7c3aed;
            }}
        """
        )
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

        return section

    def _add_message(self, text: str, is_coo: bool = False):
        msg = QFrame()
        msg_layout = QVBoxLayout(msg)
        msg_layout.setContentsMargins(10, 8, 10, 8)

        if is_coo:
            msg.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLORS['bg_tertiary']};
                    border-left: 2px solid {get_agent_color('Overwatch')};
                    border-radius: 6px;
                }}
            """
            )
            sender = QLabel("Overwatch")
            sender.setStyleSheet(
                f"color: {get_agent_color('Overwatch')}; font-size: 10px; font-weight: 600;"
            )
        else:
            msg.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLORS['accent_primary']};
                    border-radius: 6px;
                    margin-left: 40px;
                }}
            """
            )
            sender = QLabel("You")
            sender.setStyleSheet(f"color: rgba(255,255,255,0.7); font-size: 10px;")

        msg_layout.addWidget(sender)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        msg_layout.addWidget(content)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg)

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Scroll chat to bottom."""
        scrollbar = self.messages_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return

        logger.info("Sending message to backend (%d chars)", len(text))
        self._add_message(text, is_coo=False)
        self.message_input.clear()

        # Send to backend
        self._backend.send_message(text)

    def _refresh_task_list(self):
        """Refresh the task list display."""
        # Clear existing
        while self.tasks_layout.count() > 1:
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add task cards
        for task in self._tasks:
            card = TaskCard(
                task_id=task["id"],
                description=task["description"],
                assigned_to=task["assigned_to"],
                status=task["status"],
            )
            self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, card)

        self.task_count_label.setText(
            f"{len(self._tasks)} task{'s' if len(self._tasks) != 1 else ''}"
        )

        # Update agent counts
        counts = {}
        for task in self._tasks:
            agent_code = task["assigned_to"]
            counts[agent_code] = counts.get(agent_code, 0) + 1

        for code, widget in self._exec_widgets.items():
            widget.set_task_count(counts.get(code, 0))

    def closeEvent(self, event):
        """Handle window close."""
        logger.info("Dashboard closing, cleaning up backend")
        self._backend.cleanup()
        super().closeEvent(event)


def run():
    """Run the ag3ntwerk Dashboard."""
    import os

    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RENDER_LOOP", "basic")

    logger.info("Starting ag3ntwerk Dashboard application")
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = COODashboard()
    window.show()
    logger.info("Dashboard window shown, entering event loop")

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
