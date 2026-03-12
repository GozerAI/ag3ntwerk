"""
Add pattern attribution columns to learning_outcomes.

Tracks which patterns influenced each task outcome for effectiveness measurement.

Revision ID: 008
Revises: 007
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pattern attribution columns to learning_outcomes."""

    # Add applied_pattern_ids column (JSON array of pattern IDs)
    op.add_column(
        "learning_outcomes", sa.Column("applied_pattern_ids", sa.Text(), server_default="'[]'")
    )

    # Add was_routing_influenced column
    op.add_column(
        "learning_outcomes", sa.Column("was_routing_influenced", sa.Integer(), server_default="0")
    )

    # Add was_confidence_calibrated column
    op.add_column(
        "learning_outcomes",
        sa.Column("was_confidence_calibrated", sa.Integer(), server_default="0"),
    )

    # Create index for pattern-influenced outcomes
    op.create_index(
        "idx_learning_outcomes_routing_influenced", "learning_outcomes", ["was_routing_influenced"]
    )
    op.create_index(
        "idx_learning_outcomes_confidence_calibrated",
        "learning_outcomes",
        ["was_confidence_calibrated"],
    )


def downgrade() -> None:
    """Remove pattern attribution columns."""
    # SQLite doesn't support DROP COLUMN in older versions
    # For now, these columns will be ignored if not used
    op.drop_index("idx_learning_outcomes_confidence_calibrated", table_name="learning_outcomes")
    op.drop_index("idx_learning_outcomes_routing_influenced", table_name="learning_outcomes")
    # Note: SQLite < 3.35 doesn't support DROP COLUMN
    # op.drop_column("learning_outcomes", "was_confidence_calibrated")
    # op.drop_column("learning_outcomes", "was_routing_influenced")
    # op.drop_column("learning_outcomes", "applied_pattern_ids")
