"""
Autonomous Agenda Engine for ag3ntwerk.

This module provides self-directed planning capabilities that enable the system to:
1. Ingest goals and decompose them into actionable workstreams
2. Detect obstacles - capability gaps, resource constraints, dependencies
3. Generate strategies to overcome obstacles
4. Create prioritized agendas with human-in-the-loop checkpoints
5. Continuously adapt based on execution outcomes

Components:
- models: Data classes for obstacles, strategies, workstreams, agenda items
- goal_analyzer: Goal decomposition into workstreams
- constraint_detector: Obstacle and constraint detection
- strategy_generator: Strategy generation for obstacle resolution
- security: Risk assessment, HITL checkpoints, audit logging
- engine: Main orchestrator (AutonomousAgendaEngine)
- persistence: Database storage for agenda state

Usage:
    from ag3ntwerk.agenda import AutonomousAgendaEngine, AgendaEngineConfig

    engine = AutonomousAgendaEngine(
        app_state=state,
        config=AgendaEngineConfig(),
    )
    agenda = await engine.generate_agenda(period_hours=24)
"""

from ag3ntwerk.agenda.models import (
    # Enums
    ObstacleType,
    StrategyType,
    ConfidenceLevel,
    WorkstreamStatus,
    RiskLevel,
    RiskCategory,
    CheckpointType,
    # Data classes
    CapabilityRequirement,
    Obstacle,
    Strategy,
    Workstream,
    AgendaItem,
    Agenda,
    RiskAssessment,
    Checkpoint,
    HITLConfig,
    AuditEntry,
)

from ag3ntwerk.agenda.goal_analyzer import GoalAnalyzer
from ag3ntwerk.agenda.constraint_detector import ConstraintDetector, ResourceThresholds
from ag3ntwerk.agenda.strategy_generator import StrategyGenerator
from ag3ntwerk.agenda.security import RiskAssessor, CheckpointManager, AuditLogger
from ag3ntwerk.agenda.engine import AutonomousAgendaEngine, AgendaEngineConfig
from ag3ntwerk.agenda.persistence import AgendaPersistence

__all__ = [
    # Main Engine
    "AutonomousAgendaEngine",
    "AgendaEngineConfig",
    # Component Classes
    "GoalAnalyzer",
    "ConstraintDetector",
    "ResourceThresholds",
    "StrategyGenerator",
    "RiskAssessor",
    "CheckpointManager",
    "AuditLogger",
    "AgendaPersistence",
    # Enums
    "ObstacleType",
    "StrategyType",
    "ConfidenceLevel",
    "WorkstreamStatus",
    "RiskLevel",
    "RiskCategory",
    "CheckpointType",
    # Data classes
    "CapabilityRequirement",
    "Obstacle",
    "Strategy",
    "Workstream",
    "AgendaItem",
    "Agenda",
    "RiskAssessment",
    "Checkpoint",
    "HITLConfig",
    "AuditEntry",
]
