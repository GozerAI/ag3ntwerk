"""Add pattern_applications table for tracking pattern effectiveness.

Revision ID: 003
Revises: 002
Create Date: 2025-01-24

Tables added:
- pattern_applications: Tracks each pattern application and its outcome
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pattern_applications - Tracks pattern applications and outcomes
    op.create_table(
        "pattern_applications",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("pattern_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("agent_code", sa.Text(), nullable=False),
        # Application details
        sa.Column("applied_at", sa.Text(), nullable=False),
        sa.Column("was_routing_pattern", sa.Boolean(), server_default="0"),
        sa.Column("was_confidence_pattern", sa.Boolean(), server_default="0"),
        # Outcome (filled in after task completes)
        sa.Column("outcome_recorded", sa.Boolean(), server_default="0"),
        sa.Column("outcome_success", sa.Boolean(), server_default="0"),
        sa.Column("outcome_duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("outcome_effectiveness", sa.Float(), server_default="0.0"),
        # Comparison baseline
        sa.Column("baseline_agent", sa.Text()),  # What agent would have been used
        sa.Column("baseline_success_rate", sa.Float()),  # Historical success rate
        # Foreign key
        sa.ForeignKeyConstraint(["pattern_id"], ["learned_patterns.id"]),
    )
    op.create_index("idx_app_pattern", "pattern_applications", ["pattern_id"])
    op.create_index("idx_app_task", "pattern_applications", ["task_id"])
    op.create_index("idx_app_applied", "pattern_applications", ["applied_at"])
    op.create_index("idx_app_outcome", "pattern_applications", ["outcome_recorded"])


def downgrade() -> None:
    op.drop_index("idx_app_outcome", table_name="pattern_applications")
    op.drop_index("idx_app_applied", table_name="pattern_applications")
    op.drop_index("idx_app_task", table_name="pattern_applications")
    op.drop_index("idx_app_pattern", table_name="pattern_applications")
    op.drop_table("pattern_applications")
