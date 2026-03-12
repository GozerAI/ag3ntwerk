"""Add learning system tables for closed learning loops.

Revision ID: 002
Revises: 001
Create Date: 2025-01-23

Tables added:
- learning_outcomes: Central storage for all task outcomes
- learned_patterns: Patterns that influence behavior
- agent_performance: Rolling performance metrics per agent
- learning_issues: Detected issues needing attention
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # learning_outcomes - Central outcome storage
    op.create_table(
        "learning_outcomes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        # Hierarchy tracking
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("manager_code", sa.Text()),
        sa.Column("specialist_code", sa.Text()),
        # Outcome data
        sa.Column("outcome_type", sa.Text(), nullable=False),  # success, failure, partial, timeout
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("effectiveness", sa.Float(), server_default="0.0"),
        sa.Column("duration_ms", sa.Float()),
        # Confidence tracking
        sa.Column("initial_confidence", sa.Float()),
        sa.Column("actual_accuracy", sa.Float()),
        # Error tracking
        sa.Column("error_category", sa.Text()),  # timeout, capability, resource, logic, external
        sa.Column("error_message", sa.Text()),
        sa.Column("is_recoverable", sa.Boolean(), server_default="1"),
        # Context
        sa.Column("input_hash", sa.Text()),
        sa.Column("output_summary", sa.Text()),
        sa.Column("context_snapshot", sa.Text()),  # JSON
        # Timestamps
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_outcomes_executive", "learning_outcomes", ["agent_code"])
    op.create_index("idx_outcomes_manager", "learning_outcomes", ["manager_code"])
    op.create_index("idx_outcomes_specialist", "learning_outcomes", ["specialist_code"])
    op.create_index("idx_outcomes_task_type", "learning_outcomes", ["task_type"])
    op.create_index("idx_outcomes_success", "learning_outcomes", ["success"])
    op.create_index("idx_outcomes_created", "learning_outcomes", ["created_at"])

    # learned_patterns - Patterns that influence behavior
    op.create_table(
        "learned_patterns",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "pattern_type", sa.Text(), nullable=False
        ),  # routing, confidence, capability, error
        sa.Column("scope_level", sa.Text(), nullable=False),  # agent, manager, specialist
        sa.Column("scope_code", sa.Text(), nullable=False),  # Forge, AM, SD, etc.
        # Pattern definition
        sa.Column("condition_json", sa.Text(), nullable=False),  # JSON conditions
        sa.Column("recommendation", sa.Text(), nullable=False),
        # Metrics
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("success_rate", sa.Float()),
        sa.Column("avg_improvement", sa.Float()),
        # Adjustments to apply
        sa.Column("confidence_adjustment", sa.Float(), server_default="0.0"),
        sa.Column("priority_adjustment", sa.Integer(), server_default="0"),
        sa.Column("routing_preference", sa.Text()),  # Preferred agent code
        # Lifecycle
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("last_applied_at", sa.Text()),
        sa.Column("application_count", sa.Integer(), server_default="0"),
        sa.Column("expires_at", sa.Text()),
        # Validation
        sa.Column("validated_by", sa.Text()),  # human, automated, none
        sa.Column("validation_score", sa.Float()),
        # Timestamps
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_patterns_scope", "learned_patterns", ["scope_level", "scope_code"])
    op.create_index("idx_patterns_type", "learned_patterns", ["pattern_type"])
    op.create_index("idx_patterns_active", "learned_patterns", ["is_active"])

    # agent_performance - Rolling performance metrics per agent
    op.create_table(
        "agent_performance",
        sa.Column("agent_code", sa.Text(), primary_key=True),
        sa.Column("agent_level", sa.Text(), nullable=False),  # agent, manager, specialist
        sa.Column("parent_code", sa.Text()),  # Parent agent in hierarchy
        # Performance metrics (rolling window)
        sa.Column("total_tasks", sa.Integer(), server_default="0"),
        sa.Column("successful_tasks", sa.Integer(), server_default="0"),
        sa.Column("failed_tasks", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_ms", sa.Float(), server_default="0.0"),
        # Success rates by task type (JSON: {task_type: rate})
        sa.Column("task_type_success_rates", sa.Text(), server_default="{}"),
        # Confidence calibration
        sa.Column("avg_confidence", sa.Float(), server_default="0.5"),
        sa.Column("avg_actual_accuracy", sa.Float(), server_default="0.5"),
        sa.Column("confidence_calibration_score", sa.Float(), server_default="0.0"),
        # Trend data
        sa.Column(
            "performance_trend", sa.Text(), server_default="stable"
        ),  # improving, declining, stable
        sa.Column("trend_magnitude", sa.Float(), server_default="0.0"),
        # Health
        sa.Column("health_score", sa.Float(), server_default="1.0"),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0"),
        sa.Column("last_failure_at", sa.Text()),
        sa.Column("circuit_breaker_open", sa.Boolean(), server_default="0"),
        # Timestamps
        sa.Column("last_updated", sa.Text(), nullable=False),
        sa.Column("window_start", sa.Text(), nullable=False),
    )
    op.create_index("idx_perf_level", "agent_performance", ["agent_level"])
    op.create_index("idx_perf_parent", "agent_performance", ["parent_code"])

    # learning_issues - Detected issues needing attention
    op.create_table(
        "learning_issues",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "issue_type", sa.Text(), nullable=False
        ),  # anomaly, pattern_decline, error_spike, etc.
        sa.Column("severity", sa.Text(), nullable=False),  # critical, high, medium, low
        sa.Column("priority", sa.Integer(), nullable=False),  # 1-10, for task queue
        # Source
        sa.Column("source_agent_code", sa.Text(), nullable=False),
        sa.Column("source_level", sa.Text(), nullable=False),
        sa.Column("detected_pattern_id", sa.Text()),
        # Issue details
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.Text()),  # JSON array of evidence
        sa.Column("suggested_action", sa.Text()),
        # Task queue integration
        sa.Column("task_id", sa.Text()),  # Created task ID (if any)
        sa.Column("task_created_at", sa.Text()),
        # Lifecycle
        sa.Column(
            "status", sa.Text(), server_default="open"
        ),  # open, investigating, resolved, dismissed
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_at", sa.Text()),
        sa.Column("resolved_by", sa.Text()),
        # Timestamps
        sa.Column("created_at", sa.Text(), nullable=False),
        # Foreign key
        sa.ForeignKeyConstraint(["detected_pattern_id"], ["learned_patterns.id"]),
    )
    op.create_index("idx_issues_status", "learning_issues", ["status"])
    op.create_index("idx_issues_severity", "learning_issues", ["severity"])
    op.create_index("idx_issues_agent", "learning_issues", ["source_agent_code"])
    op.create_index("idx_issues_created", "learning_issues", ["created_at"])


def downgrade() -> None:
    # Drop learning_issues
    op.drop_index("idx_issues_created", table_name="learning_issues")
    op.drop_index("idx_issues_agent", table_name="learning_issues")
    op.drop_index("idx_issues_severity", table_name="learning_issues")
    op.drop_index("idx_issues_status", table_name="learning_issues")
    op.drop_table("learning_issues")

    # Drop agent_performance
    op.drop_index("idx_perf_parent", table_name="agent_performance")
    op.drop_index("idx_perf_level", table_name="agent_performance")
    op.drop_table("agent_performance")

    # Drop learned_patterns
    op.drop_index("idx_patterns_active", table_name="learned_patterns")
    op.drop_index("idx_patterns_type", table_name="learned_patterns")
    op.drop_index("idx_patterns_scope", table_name="learned_patterns")
    op.drop_table("learned_patterns")

    # Drop learning_outcomes
    op.drop_index("idx_outcomes_created", table_name="learning_outcomes")
    op.drop_index("idx_outcomes_success", table_name="learning_outcomes")
    op.drop_index("idx_outcomes_task_type", table_name="learning_outcomes")
    op.drop_index("idx_outcomes_specialist", table_name="learning_outcomes")
    op.drop_index("idx_outcomes_manager", table_name="learning_outcomes")
    op.drop_index("idx_outcomes_executive", table_name="learning_outcomes")
    op.drop_table("learning_outcomes")
