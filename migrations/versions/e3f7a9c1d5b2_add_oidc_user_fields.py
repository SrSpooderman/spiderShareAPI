"""add oidc user fields

Revision ID: e3f7a9c1d5b2
Revises: d4e5f6a7b8c9
Create Date: 2026-07-13
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f7a9c1d5b2"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(length=32), server_default="local", nullable=False),
    )
    op.add_column("users", sa.Column("oidc_subject", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("oidc_email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("oidc_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("oidc_groups", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_users_oidc_subject", "users", ["oidc_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_oidc_subject", "users", type_="unique")
    op.drop_column("users", "oidc_groups")
    op.drop_column("users", "oidc_name")
    op.drop_column("users", "oidc_email")
    op.drop_column("users", "oidc_subject")
    op.drop_column("users", "auth_provider")
