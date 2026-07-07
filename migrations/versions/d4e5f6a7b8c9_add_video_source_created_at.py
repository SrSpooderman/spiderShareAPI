"""add video source created at

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("source_created_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE videos SET source_created_at = created_at "
        "WHERE source_created_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("videos", "source_created_at")
