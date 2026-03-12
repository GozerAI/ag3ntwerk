"""
Add Phase 9 tables for predictive intelligence.

Tables:
- demand_forecasts: Demand forecast records
- cascade_predictions: Cascade effect predictions
- cascade_outcomes: Recorded cascade outcomes for learning
- context_optimizations: Context optimization records
- optimization_outcomes: Optimization outcome tracking

Revision ID: 011
Revises: 010
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 9 tables."""

    # Demand forecasts table
    op.create_table(
        "demand_forecasts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("horizon_hours", sa.Integer(), nullable=False),
        sa.Column("expected_volume", sa.Float(), nullable=False),
        sa.Column("distribution_json", sa.Text()),
        sa.Column("confidence_lower", sa.Float()),
        sa.Column("confidence_upper", sa.Float()),
        sa.Column("scaling_action", sa.Text()),
        sa.Column("scaling_urgency", sa.Float()),
        sa.Column("seasonality_type", sa.Text()),
        sa.Column("trend_direction", sa.Text()),
    )
    op.create_index("idx_demand_forecasts_created", "demand_forecasts", ["created_at"])
    op.create_index("idx_demand_forecasts_scaling", "demand_forecasts", ["scaling_action"])

    # Cascade predictions table
    op.create_table(
        "cascade_predictions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("selected_agent", sa.Text(), nullable=False),
        sa.Column("expected_duration", sa.Float()),
        sa.Column("risk_level", sa.Text()),
        sa.Column("risk_score", sa.Float()),
        sa.Column("downstream_agents_json", sa.Text()),
    )
    op.create_index("idx_cascade_predictions_created", "cascade_predictions", ["created_at"])
    op.create_index("idx_cascade_predictions_task", "cascade_predictions", ["task_type"])
    op.create_index("idx_cascade_predictions_risk", "cascade_predictions", ["risk_level"])

    # Cascade outcomes table (for learning)
    op.create_table(
        "cascade_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prediction_id", sa.Text(), nullable=False),
        sa.Column("actual_duration_ms", sa.Float()),
        sa.Column("predicted_duration_ms", sa.Float()),
        sa.Column("had_failures", sa.Integer(), server_default="0"),
        sa.Column("predicted_failures", sa.Integer(), server_default="0"),
        sa.Column("downstream_agents", sa.Text()),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_cascade_outcomes_prediction", "cascade_outcomes", ["prediction_id"])
    op.create_index("idx_cascade_outcomes_recorded", "cascade_outcomes", ["recorded_at"])

    # Context optimizations table
    op.create_table(
        "context_optimizations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("original_priority", sa.Integer()),
        sa.Column("recommended_priority", sa.Integer()),
        sa.Column("original_timeout", sa.Float()),
        sa.Column("recommended_timeout", sa.Float()),
        sa.Column("recommended_agent", sa.Text()),
        sa.Column("should_defer", sa.Integer(), server_default="0"),
        sa.Column("confidence", sa.Float()),
        sa.Column("optimizations_json", sa.Text()),
        sa.Column("outcome_success", sa.Integer()),
        sa.Column("actual_duration_ms", sa.Float()),
        sa.Column("completed_at", sa.Text()),
    )
    op.create_index("idx_context_optimizations_created", "context_optimizations", ["created_at"])
    op.create_index("idx_context_optimizations_task", "context_optimizations", ["task_type"])
    op.create_index(
        "idx_context_optimizations_agent", "context_optimizations", ["recommended_agent"]
    )

    # Optimization outcomes table (aggregated stats)
    op.create_table(
        "optimization_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optimization_id", sa.Text(), nullable=False),
        sa.Column("optimization_type", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("outcome_success", sa.Integer()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_optimization_outcomes_type", "optimization_outcomes", ["optimization_type"]
    )
    op.create_index("idx_optimization_outcomes_created", "optimization_outcomes", ["created_at"])

    # Time series data table (for forecasting)
    op.create_table(
        "demand_time_series",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hour_bucket", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text()),
        sa.Column("agent_code", sa.Text()),
        sa.Column("task_count", sa.Integer(), server_default="0"),
        sa.Column("success_count", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_ms", sa.Float()),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_demand_time_series_bucket", "demand_time_series", ["hour_bucket"])
    op.create_index("idx_demand_time_series_task", "demand_time_series", ["task_type"])


def downgrade() -> None:
    """Drop Phase 9 tables."""
    op.drop_index("idx_demand_time_series_task", table_name="demand_time_series")
    op.drop_index("idx_demand_time_series_bucket", table_name="demand_time_series")
    op.drop_table("demand_time_series")

    op.drop_index("idx_optimization_outcomes_created", table_name="optimization_outcomes")
    op.drop_index("idx_optimization_outcomes_type", table_name="optimization_outcomes")
    op.drop_table("optimization_outcomes")

    op.drop_index("idx_context_optimizations_agent", table_name="context_optimizations")
    op.drop_index("idx_context_optimizations_task", table_name="context_optimizations")
    op.drop_index("idx_context_optimizations_created", table_name="context_optimizations")
    op.drop_table("context_optimizations")

    op.drop_index("idx_cascade_outcomes_recorded", table_name="cascade_outcomes")
    op.drop_index("idx_cascade_outcomes_prediction", table_name="cascade_outcomes")
    op.drop_table("cascade_outcomes")

    op.drop_index("idx_cascade_predictions_risk", table_name="cascade_predictions")
    op.drop_index("idx_cascade_predictions_task", table_name="cascade_predictions")
    op.drop_index("idx_cascade_predictions_created", table_name="cascade_predictions")
    op.drop_table("cascade_predictions")

    op.drop_index("idx_demand_forecasts_scaling", table_name="demand_forecasts")
    op.drop_index("idx_demand_forecasts_created", table_name="demand_forecasts")
    op.drop_table("demand_forecasts")
