"""add video category external metadata

Revision ID: 9d2f4a7c1b8e
Revises: b7e1c9a2d4f6
Create Date: 2026-06-18 21:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d2f4a7c1b8e"
down_revision: Union[str, None] = "b7e1c9a2d4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_categories",
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="custom",
            nullable=False,
        ),
    )
    op.add_column(
        "video_categories",
        sa.Column("steam_appid", sa.Integer(), nullable=True),
    )
    op.add_column(
        "video_categories",
        sa.Column("steamgriddb_game_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "video_categories",
        sa.Column("thumbnail_vertical_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "video_categories",
        sa.Column("thumbnail_horizontal_url", sa.String(length=1000), nullable=True),
    )
    op.create_index(
        "ix_video_categories_steam_appid",
        "video_categories",
        ["steam_appid"],
    )
    op.create_index(
        "ix_video_categories_steamgriddb_game_id",
        "video_categories",
        ["steamgriddb_game_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_video_categories_steamgriddb_game_id", table_name="video_categories")
    op.drop_index("ix_video_categories_steam_appid", table_name="video_categories")
    op.drop_column("video_categories", "thumbnail_horizontal_url")
    op.drop_column("video_categories", "thumbnail_vertical_url")
    op.drop_column("video_categories", "steamgriddb_game_id")
    op.drop_column("video_categories", "steam_appid")
    op.drop_column("video_categories", "source")
