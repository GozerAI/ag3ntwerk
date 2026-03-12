"""
Styles and theming for ag3ntwerk GUI.
Dark professional theme with agent-appropriate aesthetics.
"""

# Color palette - professional dark theme
COLORS = {
    # Backgrounds
    "bg_primary": "#0f0f0f",
    "bg_secondary": "#1a1a1a",
    "bg_tertiary": "#252525",
    "bg_elevated": "#2a2a2a",
    # Text
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "text_muted": "#666666",
    # Accents
    "accent_primary": "#3b82f6",  # Blue
    "accent_success": "#22c55e",  # Green
    "accent_warning": "#f59e0b",  # Amber
    "accent_error": "#ef4444",  # Red
    "accent_info": "#06b6d4",  # Cyan
    # Agent colors (for visual distinction)
    "exec_coo": "#8b5cf6",  # Purple - Control Plane
    "exec_cio": "#06b6d4",  # Cyan - Security
    "exec_cto": "#22c55e",  # Green - Technology
    "exec_cfo": "#f59e0b",  # Amber - Finance
    "exec_cso": "#ec4899",  # Pink - Strategy
    "exec_cro": "#3b82f6",  # Blue - Research
    "exec_cdo": "#14b8a6",  # Teal - Data
    "exec_cpo": "#f97316",  # Orange - Product
    "exec_cmo": "#a855f7",  # Violet - Marketing
    "exec_default": "#6b7280",  # Gray - Default
    # Borders
    "border": "#333333",
    "border_light": "#444444",
    # Status
    "status_online": "#22c55e",
    "status_busy": "#f59e0b",
    "status_offline": "#6b7280",
    "status_error": "#ef4444",
}

# Agent color mapping
AGENT_COLORS = {
    "Nexus": COLORS["exec_coo"],
    "Sentinel": COLORS["exec_cio"],
    "Forge": COLORS["exec_cto"],
    "Keystone": COLORS["exec_cfo"],
    "Compass": COLORS["exec_cso"],
    "Axiom": COLORS["exec_cro"],
    "Index": COLORS["exec_cdo"],
    "Blueprint": COLORS["exec_cpo"],
    "Echo": COLORS["exec_cmo"],
    "Beacon": COLORS["accent_info"],
    "Foundry": COLORS["exec_cto"],
    "Citadel": COLORS["exec_cio"],
    "Aegis": COLORS["accent_warning"],
    "Accord": COLORS["accent_info"],
    "Vector": COLORS["exec_cfo"],
    "Overwatch": COLORS["exec_coo"],
}


def get_agent_color(code: str) -> str:
    """Get the color for an agent by their code."""
    return AGENT_COLORS.get(code, COLORS["exec_default"])


# Global stylesheet
STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_primary']};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
}}

QLabel {{
    color: {COLORS['text_primary']};
}}

QPushButton {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_elevated']};
    border-color: {COLORS['accent_primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_primary']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_muted']};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {COLORS['accent_primary']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['accent_primary']};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg_secondary']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['border_light']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QListWidget {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {COLORS['accent_primary']};
}}

QListWidget::item:hover {{
    background-color: {COLORS['bg_tertiary']};
}}

QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent_primary']};
}}

QFrame#sidebar {{
    background-color: {COLORS['bg_secondary']};
    border-right: 1px solid {COLORS['border']};
}}

QFrame#chat_area {{
    background-color: {COLORS['bg_primary']};
}}

QFrame#message_user {{
    background-color: {COLORS['accent_primary']};
    border-radius: 12px;
}}

QFrame#message_assistant {{
    background-color: {COLORS['bg_tertiary']};
    border-radius: 12px;
}}
"""
