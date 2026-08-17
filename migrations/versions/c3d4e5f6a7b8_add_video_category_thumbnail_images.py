"""add binary video category thumbnails"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "9d2f4a7c1b8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name, column in (
        ("thumbnail_vertical_image", sa.LargeBinary()),
        ("thumbnail_vertical_content_type", sa.String(length=100)),
        ("thumbnail_horizontal_image", sa.LargeBinary()),
        ("thumbnail_horizontal_content_type", sa.String(length=100)),
    ):
        op.add_column("video_categories", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    for name in ("thumbnail_horizontal_content_type", "thumbnail_horizontal_image", "thumbnail_vertical_content_type", "thumbnail_vertical_image"):
        op.drop_column("video_categories", name)
