"""
Add Phase 5 tables for full autonomy capabilities.

Tables:
- autonomy_approvals: Pending and processed approval requests
- autonomy_action_logs: Logged actions for supervised operations
- pipeline_cycles: Learning pipeline cycle history

Revision ID: 007
Revises: 006
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 5 tables."""

    # Autonomy approvals table for pending/processed approvals
    op.create_table(
        "autonomy_approvals",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("context_json", sa.Text()),
        sa.Column("impact_assessment", sa.Text()),
        sa.Column("recommended_decision", sa.Integer(), server_default="1"),
        sa.Column("status", sa.Text(), server_default="'pending'"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text()),
        sa.Column("decided_at", sa.Text()),
        sa.Column("decided_by", sa.Text()),
    )
    op.create_index("idx_autonomy_approvals_status", "autonomy_approvals", ["status"])
    op.create_index("idx_autonomy_approvals_action", "autonomy_approvals", ["action"])
    op.create_index("idx_autonomy_approvals_created", "autonomy_approvals", ["created_at"])
    op.create_index("idx_autonomy_approvals_expires", "autonomy_approvals", ["expires_at"])

    # Autonomy action logs table for supervised operations
    op.create_table(
        "autonomy_action_logs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("autonomy_level", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("context_json", sa.Text()),
        sa.Column("result_json", sa.Text()),
        sa.Column("success", sa.Integer(), server_default="1"),
        sa.Column("timestamp", sa.Text(), nullable=False),
    )
    op.create_index("idx_autonomy_logs_action", "autonomy_action_logs", ["action"])
    op.create_index("idx_autonomy_logs_category", "autonomy_action_logs", ["category"])
    op.create_index("idx_autonomy_logs_timestamp", "autonomy_action_logs", ["timestamp"])
    op.create_index("idx_autonomy_logs_success", "autonomy_action_logs", ["success"])

    # Pipeline cycles table for learning cycle history
    op.create_table(
        "pipeline_cycles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text()),
        sa.Column("duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("success", sa.Integer(), server_default="1"),
        sa.Column("error", sa.Text()),
        sa.Column("outcomes_collected", sa.Integer(), server_default="0"),
        sa.Column("patterns_detected", sa.Integer(), server_default="0"),
        sa.Column("experiments_started", sa.Integer(), server_default="0"),
        sa.Column("experiments_concluded", sa.Integer(), server_default="0"),
        sa.Column("patterns_activated", sa.Integer(), server_default="0"),
        sa.Column("patterns_deactivated", sa.Integer(), server_default="0"),
        sa.Column("parameters_tuned", sa.Integer(), server_default="0"),
        sa.Column("opportunities_detected", sa.Integer(), server_default="0"),
        sa.Column("tasks_generated", sa.Integer(), server_default="0"),
        sa.Column("items_cleaned", sa.Integer(), server_default="0"),
        sa.Column("phase_durations_json", sa.Text()),
    )
    op.create_index("idx_pipeline_cycles_started", "pipeline_cycles", ["started_at"])
    op.create_index("idx_pipeline_cycles_success", "pipeline_cycles", ["success"])

    # Pipeline state table for tracking current state
    op.create_table(
        "pipeline_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="'stopped'"),
        sa.Column("started_at", sa.Text()),
        sa.Column("stopped_at", sa.Text()),
        sa.Column("total_cycles", sa.Integer(), server_default="0"),
        sa.Column("successful_cycles", sa.Integer(), server_default="0"),
        sa.Column("failed_cycles", sa.Integer(), server_default="0"),
        sa.Column("consecutive_errors", sa.Integer(), server_default="0"),
        sa.Column("last_cycle_id", sa.Text()),
        sa.Column("config_json", sa.Text()),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    # Insert default state row
    op.execute(
        """
        INSERT OR IGNORE INTO pipeline_state (
            id, state, total_cycles, successful_cycles, failed_cycles,
            consecutive_errors, updated_at
        ) VALUES (1, 'stopped', 0, 0, 0, 0, datetime('now'))
    """
    )


def downgrade() -> None:
    """Drop Phase 5 tables."""
    op.drop_table("pipeline_state")

    op.drop_index("idx_pipeline_cycles_success", table_name="pipeline_cycles")
    op.drop_index("idx_pipeline_cycles_started", table_name="pipeline_cycles")
    op.drop_table("pipeline_cycles")

    op.drop_index("idx_autonomy_logs_success", table_name="autonomy_action_logs")
    op.drop_index("idx_autonomy_logs_timestamp", table_name="autonomy_action_logs")
    op.drop_index("idx_autonomy_logs_category", table_name="autonomy_action_logs")
    op.drop_index("idx_autonomy_logs_action", table_name="autonomy_action_logs")
    op.drop_table("autonomy_action_logs")

    op.drop_index("idx_autonomy_approvals_expires", table_name="autonomy_approvals")
    op.drop_index("idx_autonomy_approvals_created", table_name="autonomy_approvals")
    op.drop_index("idx_autonomy_approvals_action", table_name="autonomy_approvals")
    op.drop_index("idx_autonomy_approvals_status", table_name="autonomy_approvals")
    op.drop_table("autonomy_approvals")
