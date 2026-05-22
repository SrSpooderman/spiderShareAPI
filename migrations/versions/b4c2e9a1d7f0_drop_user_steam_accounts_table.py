"""drop user steam accounts table

Revision ID: b4c2e9a1d7f0
Revises: 4a9d2c7e1f83
Create Date: 2026-05-20 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c2e9a1d7f0"
down_revision: Union[str, None] = "4a9d2c7e1f83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Destructive by design: back up this table before applying in production.
    op.drop_table("user_steam_accounts")


def downgrade() -> None:
    op.create_table(
        "user_steam_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("steam_id_64", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "steam_id_64",
            name="uq_user_steam_accounts_steam_id_64",
        ),
        sa.UniqueConstraint("user_id", name="uq_user_steam_accounts_user_id"),
    )
