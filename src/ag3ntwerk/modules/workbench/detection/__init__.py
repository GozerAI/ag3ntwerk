"""
Framework Detection Package.

Auto-detects project frameworks and generates deployment configurations.
"""

from ag3ntwerk.modules.workbench.detection.framework_detector import (
    FrameworkDetector,
    FrameworkInfo,
    FrameworkType,
    detect_framework,
)
from ag3ntwerk.modules.workbench.detection.config_generator import (
    ConfigGenerator,
    GeneratedConfigs,
)

__all__ = [
    "FrameworkDetector",
    "FrameworkInfo",
    "FrameworkType",
    "detect_framework",
    "ConfigGenerator",
    "GeneratedConfigs",
]
