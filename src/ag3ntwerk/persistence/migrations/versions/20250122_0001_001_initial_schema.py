"""Initial schema - captures existing ag3ntwerk tables.

Revision ID: 001
Revises: None
Create Date: 2025-01-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Analytics table - stores metrics and telemetry data
    op.create_table(
        "analytics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("dimensions", sa.Text(), server_default="{}"),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), server_default="system"),
    )
    op.create_index("idx_analytics_metric", "analytics", ["metric_name"])
    op.create_index("idx_analytics_timestamp", "analytics", ["timestamp"])

    # Audit trail table - tracks all system actions
    op.create_table(
        "audit_trail",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), server_default="{}"),
        sa.Column("outcome", sa.Text()),
        sa.Column("timestamp", sa.Text(), nullable=False),
    )
    op.create_index("idx_audit_entity", "audit_trail", ["entity_type", "entity_id"])
    op.create_index("idx_audit_timestamp", "audit_trail", ["timestamp"])

    # Plugin configuration table
    op.create_table(
        "plugin_config",
        sa.Column("plugin_id", sa.Text(), primary_key=True),
        sa.Column("config_data", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Integer(), server_default="1"),
        sa.Column("version", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    # Decision history table - tracks agent decisions
    op.create_table(
        "decision_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.Text(), unique=True, nullable=False),
        sa.Column("agent_code", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text()),
        sa.Column("decision_type", sa.Text(), nullable=False),
        sa.Column("input_summary", sa.Text()),
        sa.Column("output_summary", sa.Text()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("alternatives", sa.Text(), server_default="[]"),
        sa.Column("selected_option", sa.Text()),
        sa.Column("timestamp", sa.Text(), nullable=False),
    )
    op.create_index("idx_decision_agent", "decision_history", ["agent_code"])
    op.create_index("idx_decision_timestamp", "decision_history", ["timestamp"])

    # Workflow executions table
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.Text(), unique=True, nullable=False),
        sa.Column("workflow_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_data", sa.Text()),
        sa.Column("output_data", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text()),
    )
    op.create_index("idx_workflow_status", "workflow_executions", ["status"])


def downgrade() -> None:
    op.drop_index("idx_workflow_status", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("idx_decision_timestamp", table_name="decision_history")
    op.drop_index("idx_decision_agent", table_name="decision_history")
    op.drop_table("decision_history")

    op.drop_table("plugin_config")

    op.drop_index("idx_audit_timestamp", table_name="audit_trail")
    op.drop_index("idx_audit_entity", table_name="audit_trail")
    op.drop_table("audit_trail")

    op.drop_index("idx_analytics_timestamp", table_name="analytics")
    op.drop_index("idx_analytics_metric", table_name="analytics")
    op.drop_table("analytics")
