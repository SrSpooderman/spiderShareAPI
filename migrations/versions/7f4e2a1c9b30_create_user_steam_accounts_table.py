"""create user steam accounts table

Revision ID: 7f4e2a1c9b30
Revises: 2b0c6f8a4d1e
Create Date: 2026-05-01 19:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f4e2a1c9b30"
down_revision: Union[str, None] = "2b0c6f8a4d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table("user_steam_accounts")
