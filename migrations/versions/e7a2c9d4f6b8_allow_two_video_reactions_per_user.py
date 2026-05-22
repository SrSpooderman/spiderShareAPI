"""allow two video reactions per user

Revision ID: e7a2c9d4f6b8
Revises: c1e5a7b9d2f4
Create Date: 2026-05-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e7a2c9d4f6b8"
down_revision: Union[str, None] = "c1e5a7b9d2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_video_reactions_video_user",
        "video_reactions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_video_reactions_video_user_type",
        "video_reactions",
        ["video_id", "user_id", "reaction_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_video_reactions_video_user_type",
        "video_reactions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_video_reactions_video_user",
        "video_reactions",
        ["video_id", "user_id"],
    )
