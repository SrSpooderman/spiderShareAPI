"""create admin audit and worker events

Revision ID: b7e1c9a2d4f6
Revises: a6d4e8f1b2c3
Create Date: 2026-06-11
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e1c9a2d4f6"
down_revision: Union[str, None] = "a6d4e8f1b2c3"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "worker_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("level", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("video_id", sa.String(length=36), nullable=True),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("worker_name", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_events_event_type", "worker_events", ["event_type"])
    op.create_index("ix_worker_events_video_id", "worker_events", ["video_id"])
    op.create_index("ix_worker_events_job_id", "worker_events", ["job_id"])
    op.create_index("ix_worker_events_created_at", "worker_events", ["created_at"])

    op.create_table(
        "admin_audit_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("actor_username", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_entries_actor_user_id",
        "admin_audit_entries",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_admin_audit_entries_actor_username",
        "admin_audit_entries",
        ["actor_username"],
    )
    op.create_index("ix_admin_audit_entries_action", "admin_audit_entries", ["action"])
    op.create_index("ix_admin_audit_entries_entity_id", "admin_audit_entries", ["entity_id"])
    op.create_index(
        "ix_admin_audit_entries_created_at",
        "admin_audit_entries",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_entries_created_at", table_name="admin_audit_entries")
    op.drop_index("ix_admin_audit_entries_entity_id", table_name="admin_audit_entries")
    op.drop_index("ix_admin_audit_entries_action", table_name="admin_audit_entries")
    op.drop_index(
        "ix_admin_audit_entries_actor_username",
        table_name="admin_audit_entries",
    )
    op.drop_index(
        "ix_admin_audit_entries_actor_user_id",
        table_name="admin_audit_entries",
    )
    op.drop_table("admin_audit_entries")

    op.drop_index("ix_worker_events_created_at", table_name="worker_events")
    op.drop_index("ix_worker_events_job_id", table_name="worker_events")
    op.drop_index("ix_worker_events_video_id", table_name="worker_events")
    op.drop_index("ix_worker_events_event_type", table_name="worker_events")
    op.drop_table("worker_events")
