"""add video processing outputs

Revision ID: c1e5a7b9d2f4
Revises: d8f3a6b2c4e1
Create Date: 2026-05-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e5a7b9d2f4"
down_revision: Union[str, None] = "d8f3a6b2c4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("videos", sa.Column("thumbnail_path", sa.String(length=500), nullable=True))
    op.create_table(
        "video_variants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=36), nullable=False),
        sa.Column("variant_type", sa.String(length=32), nullable=False),
        sa.Column("codec", sa.String(length=32), nullable=False),
        sa.Column("container", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bitrate_kbps", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "variant_type", name="uq_video_variants_video_type"),
    )
    op.create_index("ix_video_variants_video_id", "video_variants", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_video_variants_video_id", table_name="video_variants")
    op.drop_table("video_variants")
    op.drop_column("videos", "thumbnail_path")
    op.drop_column("videos", "duration_seconds")
