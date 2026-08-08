"""drop video source updated at

Revision ID: a8b6c4d2e0f1
Revises: f9a1b2c3d4e5
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b6c4d2e0f1"
down_revision: Union[str, None] = "f9a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("videos", "source_updated_at")


def downgrade() -> None:
    op.add_column("videos", sa.Column("source_updated_at", sa.DateTime(), nullable=True))
