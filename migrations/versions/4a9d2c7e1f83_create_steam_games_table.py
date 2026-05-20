"""create steam games table

Revision ID: 4a9d2c7e1f83
Revises: 7f4e2a1c9b30
Create Date: 2026-05-01 23:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a9d2c7e1f83"
down_revision: Union[str, None] = "7f4e2a1c9b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "steam_games",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("appid", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appid", name="uq_steam_games_appid"),
    )


def downgrade() -> None:
    op.drop_table("steam_games")
