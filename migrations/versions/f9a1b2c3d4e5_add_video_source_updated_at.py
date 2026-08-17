"""add video source updated at

Revision ID: f9a1b2c3d4e5
Revises: e3f7a9c1d5b2
Create Date: 2026-08-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9a1b2c3d4e5"
down_revision: Union[str, None] = "e3f7a9c1d5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("source_updated_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE videos SET source_updated_at = updated_at "
        "WHERE source_updated_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("videos", "source_updated_at")
