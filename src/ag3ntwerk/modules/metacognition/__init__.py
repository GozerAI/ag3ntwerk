"""
Metacognition Module for ag3ntwerk.

Provides self-differentiation, agent-level and system-level reflection,
adaptive heuristics, and personality evolution for all agent agents.

This module plugs into the existing learning pipeline as Phase 5.5
(between PARAMETER_TUNING and OPPORTUNITY_DETECTION).
"""

from ag3ntwerk.modules.metacognition.service import MetacognitionService

__all__ = ["MetacognitionService"]
