"""
Add Phase 8 tables for advanced feedback loops.

Tables:
- evolved_capabilities: Agent capability evolution tracking
- pattern_propagations: Pattern propagation records
- failure_investigations: Failure root cause analysis

Revision ID: 010
Revises: 009
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 8 tables."""

    # Evolved capabilities table
    op.create_table(
        "evolved_capabilities",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("capability_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("task_types", sa.Text()),
        sa.Column("configuration", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_gap_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.Text()),
        sa.Column("test_results", sa.Text()),
        sa.Column("success_rate", sa.Float(), server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
    )
    op.create_index("idx_evolved_capabilities_agent", "evolved_capabilities", ["agent_code"])
    op.create_index("idx_evolved_capabilities_status", "evolved_capabilities", ["status"])
    op.create_index("idx_evolved_capabilities_type", "evolved_capabilities", ["capability_type"])

    # Pattern propagations table
    op.create_table(
        "pattern_propagations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source_pattern_id", sa.Text(), nullable=False),
        sa.Column("source_agent", sa.Text(), nullable=False),
        sa.Column("target_agent", sa.Text(), nullable=False),
        sa.Column("propagated_pattern_id", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text()),
        sa.Column("test_outcomes", sa.Integer(), server_default="0"),
        sa.Column("test_successes", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.Text()),
    )
    op.create_index(
        "idx_pattern_propagations_source", "pattern_propagations", ["source_pattern_id"]
    )
    op.create_index("idx_pattern_propagations_target", "pattern_propagations", ["target_agent"])
    op.create_index("idx_pattern_propagations_status", "pattern_propagations", ["status"])

    # Failure investigations table
    op.create_table(
        "failure_investigations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("outcome_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("root_causes", sa.Text()),
        sa.Column("correlations", sa.Text()),
        sa.Column("recommended_fixes", sa.Text()),
        sa.Column("similar_failures_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text()),
        sa.Column("summary", sa.Text()),
    )
    op.create_index("idx_failure_investigations_task", "failure_investigations", ["task_type"])
    op.create_index("idx_failure_investigations_agent", "failure_investigations", ["agent_code"])
    op.create_index("idx_failure_investigations_status", "failure_investigations", ["status"])
    op.create_index("idx_failure_investigations_created", "failure_investigations", ["created_at"])

    # Demand gaps table (for capability evolver)
    op.create_table(
        "demand_gaps",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("volume", sa.Integer(), server_default="0"),
        sa.Column("failure_rate", sa.Float(), server_default="0.0"),
        sa.Column("avg_duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("error_patterns", sa.Text()),
        sa.Column("detected_at", sa.Text(), nullable=False),
        sa.Column("severity", sa.Float(), server_default="0.0"),
        sa.Column("addressed", sa.Integer(), server_default="0"),
        sa.Column("addressed_by", sa.Text()),
    )
    op.create_index("idx_demand_gaps_agent", "demand_gaps", ["agent_code"])
    op.create_index("idx_demand_gaps_severity", "demand_gaps", ["severity"])


def downgrade() -> None:
    """Drop Phase 8 tables."""
    op.drop_index("idx_demand_gaps_severity", table_name="demand_gaps")
    op.drop_index("idx_demand_gaps_agent", table_name="demand_gaps")
    op.drop_table("demand_gaps")

    op.drop_index("idx_failure_investigations_created", table_name="failure_investigations")
    op.drop_index("idx_failure_investigations_status", table_name="failure_investigations")
    op.drop_index("idx_failure_investigations_agent", table_name="failure_investigations")
    op.drop_index("idx_failure_investigations_task", table_name="failure_investigations")
    op.drop_table("failure_investigations")

    op.drop_index("idx_pattern_propagations_status", table_name="pattern_propagations")
    op.drop_index("idx_pattern_propagations_target", table_name="pattern_propagations")
    op.drop_index("idx_pattern_propagations_source", table_name="pattern_propagations")
    op.drop_table("pattern_propagations")

    op.drop_index("idx_evolved_capabilities_type", table_name="evolved_capabilities")
    op.drop_index("idx_evolved_capabilities_status", table_name="evolved_capabilities")
    op.drop_index("idx_evolved_capabilities_agent", table_name="evolved_capabilities")
    op.drop_table("evolved_capabilities")
