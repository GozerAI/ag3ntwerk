"""
Add Phase 4 tables for proactive behavior capabilities.

Tables:
- opportunities: Detected improvement opportunities
- proactive_tasks: Auto-generated maintenance tasks

Revision ID: 006
Revises: 005
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 4 tables."""

    # Opportunities table for detected improvements
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("opportunity_type", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("affected_agent", sa.Text()),
        sa.Column("affected_task_type", sa.Text()),
        sa.Column("impact_score", sa.Float(), server_default="0.0"),
        sa.Column("estimated_improvement", sa.Float(), server_default="0.0"),
        sa.Column("task_volume_affected", sa.Integer(), server_default="0"),
        sa.Column("evidence_json", sa.Text()),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("auto_actionable", sa.Integer(), server_default="0"),
        sa.Column("status", sa.Text(), server_default="'open'"),
        sa.Column("detected_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text()),
        sa.Column("acknowledged_at", sa.Text()),
        sa.Column("addressed_at", sa.Text()),
        sa.Column("dismissed_at", sa.Text()),
        sa.Column("resolution", sa.Text()),
    )
    op.create_index("idx_opportunities_type", "opportunities", ["opportunity_type"])
    op.create_index("idx_opportunities_status", "opportunities", ["status"])
    op.create_index("idx_opportunities_priority", "opportunities", ["priority"])
    op.create_index("idx_opportunities_agent", "opportunities", ["affected_agent"])
    op.create_index("idx_opportunities_detected", "opportunities", ["detected_at"])

    # Proactive tasks table for auto-generated tasks
    op.create_table(
        "proactive_tasks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_agent", sa.Text()),
        sa.Column("target_task_type", sa.Text()),
        sa.Column("parameters_json", sa.Text()),
        sa.Column("expected_duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("source_opportunity_id", sa.Text()),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.Text(), server_default="'pending'"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("queued_at", sa.Text()),
        sa.Column("started_at", sa.Text()),
        sa.Column("completed_at", sa.Text()),
        sa.Column("result_json", sa.Text()),
    )
    op.create_index("idx_proactive_tasks_type", "proactive_tasks", ["task_type"])
    op.create_index("idx_proactive_tasks_status", "proactive_tasks", ["status"])
    op.create_index("idx_proactive_tasks_priority", "proactive_tasks", ["priority"])
    op.create_index("idx_proactive_tasks_created", "proactive_tasks", ["created_at"])
    op.create_index("idx_proactive_tasks_opportunity", "proactive_tasks", ["source_opportunity_id"])

    # Opportunity history table for tracking actions
    op.create_table(
        "opportunity_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), server_default="'system'"),
        sa.Column("details", sa.Text()),
    )
    op.create_index(
        "idx_opportunity_history_opportunity", "opportunity_history", ["opportunity_id"]
    )
    op.create_index("idx_opportunity_history_timestamp", "opportunity_history", ["timestamp"])


def downgrade() -> None:
    """Drop Phase 4 tables."""
    op.drop_index("idx_opportunity_history_timestamp", table_name="opportunity_history")
    op.drop_index("idx_opportunity_history_opportunity", table_name="opportunity_history")
    op.drop_table("opportunity_history")

    op.drop_index("idx_proactive_tasks_opportunity", table_name="proactive_tasks")
    op.drop_index("idx_proactive_tasks_created", table_name="proactive_tasks")
    op.drop_index("idx_proactive_tasks_priority", table_name="proactive_tasks")
    op.drop_index("idx_proactive_tasks_status", table_name="proactive_tasks")
    op.drop_index("idx_proactive_tasks_type", table_name="proactive_tasks")
    op.drop_table("proactive_tasks")

    op.drop_index("idx_opportunities_detected", table_name="opportunities")
    op.drop_index("idx_opportunities_agent", table_name="opportunities")
    op.drop_index("idx_opportunities_priority", table_name="opportunities")
    op.drop_index("idx_opportunities_status", table_name="opportunities")
    op.drop_index("idx_opportunities_type", table_name="opportunities")
    op.drop_table("opportunities")
