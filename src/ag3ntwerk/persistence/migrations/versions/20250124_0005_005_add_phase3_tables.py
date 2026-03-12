"""
Add Phase 3 tables for self-improvement capabilities.

Tables:
- pattern_experiments: A/B testing for patterns
- meta_learner_state: Meta-learner parameter state
- generated_handlers: Auto-generated task handlers

Revision ID: 005
Revises: 004
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 3 tables."""

    # Pattern experiments table for A/B testing
    op.create_table(
        "pattern_experiments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("pattern_id", sa.Text(), nullable=False),
        sa.Column("pattern_type", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("target_sample_size", sa.Integer(), server_default="100"),
        sa.Column("traffic_percentage", sa.Float(), server_default="0.5"),
        sa.Column("treatment_json", sa.Text()),
        sa.Column("control_json", sa.Text()),
        sa.Column("status", sa.Text(), server_default="'pending'"),
        sa.Column("started_at", sa.Text()),
        sa.Column("completed_at", sa.Text()),
        sa.Column("result_json", sa.Text()),
    )
    op.create_index("idx_pattern_experiments_pattern_id", "pattern_experiments", ["pattern_id"])
    op.create_index("idx_pattern_experiments_status", "pattern_experiments", ["status"])
    op.create_index("idx_pattern_experiments_task_type", "pattern_experiments", ["task_type"])

    # Meta-learner state table
    op.create_table(
        "meta_learner_state",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("parameters_json", sa.Text(), nullable=False),
        sa.Column("baseline_effectiveness", sa.Float()),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    # Generated handlers table
    op.create_table(
        "generated_handlers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("prompt_template", sa.Text()),
        sa.Column("parameters_json", sa.Text()),
        sa.Column("required_context_json", sa.Text()),
        sa.Column("output_format", sa.Text(), server_default="'text'"),
        sa.Column("source_patterns_json", sa.Text()),
        sa.Column("source_outcomes_json", sa.Text()),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("status", sa.Text(), server_default="'draft'"),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("times_used", sa.Integer(), server_default="0"),
        sa.Column("success_count", sa.Integer(), server_default="0"),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), server_default="'auto'"),
    )
    op.create_index("idx_generated_handlers_task_type", "generated_handlers", ["task_type"])
    op.create_index("idx_generated_handlers_status", "generated_handlers", ["status"])
    op.create_index("idx_generated_handlers_confidence", "generated_handlers", ["confidence"])

    # Tuning history table for meta-learner
    op.create_table(
        "meta_learner_tuning_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("parameter_name", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Float(), nullable=False),
        sa.Column("new_value", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("effectiveness_before", sa.Float()),
        sa.Column("effectiveness_after", sa.Float()),
        sa.Column("was_beneficial", sa.Integer()),
    )
    op.create_index("idx_tuning_history_timestamp", "meta_learner_tuning_history", ["timestamp"])
    op.create_index(
        "idx_tuning_history_parameter", "meta_learner_tuning_history", ["parameter_name"]
    )


def downgrade() -> None:
    """Drop Phase 3 tables."""
    op.drop_index("idx_tuning_history_parameter", table_name="meta_learner_tuning_history")
    op.drop_index("idx_tuning_history_timestamp", table_name="meta_learner_tuning_history")
    op.drop_table("meta_learner_tuning_history")

    op.drop_index("idx_generated_handlers_confidence", table_name="generated_handlers")
    op.drop_index("idx_generated_handlers_status", table_name="generated_handlers")
    op.drop_index("idx_generated_handlers_task_type", table_name="generated_handlers")
    op.drop_table("generated_handlers")

    op.drop_table("meta_learner_state")

    op.drop_index("idx_pattern_experiments_task_type", table_name="pattern_experiments")
    op.drop_index("idx_pattern_experiments_status", table_name="pattern_experiments")
    op.drop_index("idx_pattern_experiments_pattern_id", table_name="pattern_experiments")
    op.drop_table("pattern_experiments")
