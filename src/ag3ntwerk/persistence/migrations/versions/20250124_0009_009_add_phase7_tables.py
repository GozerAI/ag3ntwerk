"""
Add Phase 7 tables for cross-component integration.

Tables:
- service_config_changes: Configuration change history for service adaptation
- plugin_registrations: Registered plugins for telemetry

Revision ID: 009
Revises: 008
Create Date: 2025-01-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 7 tables."""

    # Service configuration changes table
    op.create_table(
        "service_config_changes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("parameter", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("applied_at", sa.Text(), nullable=False),
        sa.Column("recommendation_id", sa.Text()),
        sa.Column("success", sa.Integer()),
        sa.Column("outcome_measured_at", sa.Text()),
        sa.Column("outcome_metrics", sa.Text()),
    )
    op.create_index("idx_config_changes_service", "service_config_changes", ["service_id"])
    op.create_index("idx_config_changes_applied", "service_config_changes", ["applied_at"])
    op.create_index("idx_config_changes_success", "service_config_changes", ["success"])

    # Plugin registrations table
    op.create_table(
        "plugin_registrations",
        sa.Column("plugin_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("operations", sa.Text()),
        sa.Column("metadata", sa.Text()),
        sa.Column("registered_at", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.Text()),
        sa.Column("is_active", sa.Integer(), server_default="1"),
    )
    op.create_index("idx_plugin_registrations_active", "plugin_registrations", ["is_active"])

    # Plugin operation history (optional - for detailed tracking)
    op.create_table(
        "plugin_operations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text()),
        sa.Column("duration_ms", sa.Float(), server_default="0.0"),
        sa.Column("success", sa.Integer(), server_default="1"),
        sa.Column("error", sa.Text()),
        sa.Column("input_summary", sa.Text()),
        sa.Column("output_summary", sa.Text()),
        sa.Column("context_json", sa.Text()),
    )
    op.create_index("idx_plugin_operations_plugin", "plugin_operations", ["plugin_id"])
    op.create_index("idx_plugin_operations_started", "plugin_operations", ["started_at"])
    op.create_index("idx_plugin_operations_success", "plugin_operations", ["success"])

    # Workbench dashboard cache (for faster dashboard loads)
    op.create_table(
        "dashboard_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dashboard_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.Text(), nullable=False),
        sa.Column("generation_time_ms", sa.Float(), server_default="0.0"),
    )


def downgrade() -> None:
    """Drop Phase 7 tables."""
    op.drop_table("dashboard_cache")

    op.drop_index("idx_plugin_operations_success", table_name="plugin_operations")
    op.drop_index("idx_plugin_operations_started", table_name="plugin_operations")
    op.drop_index("idx_plugin_operations_plugin", table_name="plugin_operations")
    op.drop_table("plugin_operations")

    op.drop_index("idx_plugin_registrations_active", table_name="plugin_registrations")
    op.drop_table("plugin_registrations")

    op.drop_index("idx_config_changes_success", table_name="service_config_changes")
    op.drop_index("idx_config_changes_applied", table_name="service_config_changes")
    op.drop_index("idx_config_changes_service", table_name="service_config_changes")
    op.drop_table("service_config_changes")
