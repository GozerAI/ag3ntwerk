"""
Add meeting intelligence tables.

Tables:
- meetings: Meeting recordings with transcripts and analysis
- action_items: Action items extracted from meetings

Revision ID: 013
Revises: 012
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create meeting intelligence tables."""

    op.create_table(
        "meetings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("audio_file", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("transcript_text", sa.Text()),
        sa.Column("transcript_segments", sa.Text(), server_default="[]"),
        sa.Column("analysis", sa.Text()),
        sa.Column("source", sa.Text(), server_default="hidock"),
        sa.Column("tags", sa.Text(), server_default="[]"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_index("idx_meetings_status", "meetings", ["status"])
    op.create_index("idx_meetings_created", "meetings", ["created_at"])

    op.create_table(
        "action_items",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Text(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assignee", sa.Text()),
        sa.Column("assignee_email", sa.Text()),
        sa.Column("deadline", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("calendar_event_id", sa.Text()),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_index("idx_action_items_meeting", "action_items", ["meeting_id"])
    op.create_index("idx_action_items_status", "action_items", ["status"])
    op.create_index("idx_action_items_assignee", "action_items", ["assignee"])
    op.create_index("idx_action_items_deadline", "action_items", ["deadline"])


def downgrade() -> None:
    """Drop meeting intelligence tables."""
    op.drop_table("action_items")
    op.drop_table("meetings")
