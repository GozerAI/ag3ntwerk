"""Add calibration_curves table for confidence calibration.

Revision ID: 004
Revises: 003
Create Date: 2025-01-24

Tables added:
- calibration_curves: Stores calibration curves per (agent, task_type)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # calibration_curves - Stores calibration data per agent/task_type
    op.create_table(
        "calibration_curves",
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        # Bucket data (JSON: {bucket_idx: {min, max, predictions, successes, accuracy, error}})
        sa.Column("buckets_json", sa.Text(), nullable=False),
        # Overall metrics
        sa.Column("total_predictions", sa.Integer(), server_default="0"),
        sa.Column("mean_calibration_error", sa.Float(), server_default="0.0"),
        sa.Column("calibration_score", sa.Float(), server_default="0.0"),
        # Timestamps
        sa.Column("last_updated", sa.Text(), nullable=False),
        # Composite primary key
        sa.PrimaryKeyConstraint("agent_code", "task_type"),
    )
    op.create_index("idx_calib_agent", "calibration_curves", ["agent_code"])
    op.create_index("idx_calib_updated", "calibration_curves", ["last_updated"])


def downgrade() -> None:
    op.drop_index("idx_calib_updated", table_name="calibration_curves")
    op.drop_index("idx_calib_agent", table_name="calibration_curves")
    op.drop_table("calibration_curves")
