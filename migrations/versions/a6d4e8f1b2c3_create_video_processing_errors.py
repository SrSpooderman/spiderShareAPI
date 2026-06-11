"""create video processing errors

Revision ID: a6d4e8f1b2c3
Revises: f2a6d9c8e1b3
Create Date: 2026-06-11
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6d4e8f1b2c3"
down_revision: Union[str, None] = "f2a6d9c8e1b3"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "video_processing_errors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=36), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "video_id",
            "attempt",
            name="uq_video_processing_errors_video_attempt",
        ),
    )
    op.create_index(
        "ix_video_processing_errors_video_id",
        "video_processing_errors",
        ["video_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_video_processing_errors_video_id",
        table_name="video_processing_errors",
    )
    op.drop_table("video_processing_errors")
