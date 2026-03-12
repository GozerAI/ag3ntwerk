"""
Add Phase 10 tables for true autonomy.

Tables:
- architecture_proposals: Self-architecture proposals
- alignment_goals: Goal definitions for alignment verification
- alignment_results: Alignment verification results
- approval_history: Human approval history
- trust_changes: Trust level change history
- handoff_strategies: Handoff optimization strategies

Revision ID: 012
Revises: 011
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 10 tables."""

    # Architecture proposals table
    op.create_table(
        "architecture_proposals",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("proposal_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("agents_to_add_json", sa.Text()),
        sa.Column("agents_to_merge_json", sa.Text()),
        sa.Column("agents_to_split_json", sa.Text()),
        sa.Column("agents_to_remove_json", sa.Text()),
        sa.Column("estimated_improvement", sa.Float(), server_default="0.0"),
        sa.Column("risk_assessment", sa.Text()),
        sa.Column("implementation_steps_json", sa.Text()),
        sa.Column("approved_by", sa.Text()),
        sa.Column("approved_at", sa.Text()),
        sa.Column("implemented_at", sa.Text()),
        sa.Column("rejection_reason", sa.Text()),
    )
    op.create_index("idx_architecture_proposals_status", "architecture_proposals", ["status"])
    op.create_index("idx_architecture_proposals_created", "architecture_proposals", ["created_at"])

    # Alignment goals table
    op.create_table(
        "alignment_goals",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("goal_type", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.Text()),
        sa.Column("weight", sa.Float(), server_default="1.0"),
        sa.Column("is_active", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_alignment_goals_type", "alignment_goals", ["goal_type"])
    op.create_index("idx_alignment_goals_active", "alignment_goals", ["is_active"])

    # Alignment results table
    op.create_table(
        "alignment_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.Text(), nullable=False),
        sa.Column("user_alignment", sa.Float()),
        sa.Column("system_alignment", sa.Float()),
        sa.Column("safety_alignment", sa.Float()),
        sa.Column("overall_alignment", sa.Float()),
        sa.Column("alignment_level", sa.Text()),
        sa.Column("recommendation", sa.Text()),
        sa.Column("conflicts_json", sa.Text()),
        sa.Column("explanation", sa.Text()),
        sa.Column("verified_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_alignment_results_decision", "alignment_results", ["decision_id"])
    op.create_index("idx_alignment_results_verified", "alignment_results", ["verified_at"])
    op.create_index("idx_alignment_results_level", "alignment_results", ["alignment_level"])

    # Approval history table
    op.create_table(
        "approval_history",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("approved", sa.Integer(), nullable=False),
        sa.Column("time_to_decision_ms", sa.Float(), server_default="0.0"),
        sa.Column("approver", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_approval_history_action", "approval_history", ["action"])
    op.create_index("idx_approval_history_category", "approval_history", ["category"])
    op.create_index("idx_approval_history_created", "approval_history", ["created_at"])
    op.create_index("idx_approval_history_approved", "approval_history", ["approved"])

    # Trust changes table
    op.create_table(
        "trust_changes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("old_trust", sa.Text()),
        sa.Column("new_trust", sa.Text(), nullable=False),
        sa.Column("changed_by", sa.Text()),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_trust_changes_action", "trust_changes", ["action"])
    op.create_index("idx_trust_changes_created", "trust_changes", ["created_at"])

    # Handoff strategies table
    op.create_table(
        "handoff_strategies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("actions_to_promote_json", sa.Text()),
        sa.Column("actions_to_demote_json", sa.Text()),
        sa.Column("estimated_savings_hours", sa.Float(), server_default="0.0"),
        sa.Column("estimated_risk", sa.Float(), server_default="0.0"),
        sa.Column("current_handoff_rate", sa.Float(), server_default="0.0"),
        sa.Column("projected_handoff_rate", sa.Float(), server_default="0.0"),
        sa.Column("recommendations_json", sa.Text()),
    )
    op.create_index("idx_handoff_strategies_created", "handoff_strategies", ["created_at"])


def downgrade() -> None:
    """Drop Phase 10 tables."""
    op.drop_index("idx_handoff_strategies_created", table_name="handoff_strategies")
    op.drop_table("handoff_strategies")

    op.drop_index("idx_trust_changes_created", table_name="trust_changes")
    op.drop_index("idx_trust_changes_action", table_name="trust_changes")
    op.drop_table("trust_changes")

    op.drop_index("idx_approval_history_approved", table_name="approval_history")
    op.drop_index("idx_approval_history_created", table_name="approval_history")
    op.drop_index("idx_approval_history_category", table_name="approval_history")
    op.drop_index("idx_approval_history_action", table_name="approval_history")
    op.drop_table("approval_history")

    op.drop_index("idx_alignment_results_level", table_name="alignment_results")
    op.drop_index("idx_alignment_results_verified", table_name="alignment_results")
    op.drop_index("idx_alignment_results_decision", table_name="alignment_results")
    op.drop_table("alignment_results")

    op.drop_index("idx_alignment_goals_active", table_name="alignment_goals")
    op.drop_index("idx_alignment_goals_type", table_name="alignment_goals")
    op.drop_table("alignment_goals")

    op.drop_index("idx_architecture_proposals_created", table_name="architecture_proposals")
    op.drop_index("idx_architecture_proposals_status", table_name="architecture_proposals")
    op.drop_table("architecture_proposals")
