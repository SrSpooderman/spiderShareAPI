from dataclasses import replace
from uuid import uuid4

import pytest

from app.modules.users.domain.user import UserRole
from app.modules.videos.domain.video import (
    Video,
    VideoProcessingStatus,
    can_delete_video,
    can_edit_video,
    can_favorite_or_react_to_video,
    can_view_video,
)
from tests.factories import utc_now


def make_video(*, owner_id=None, is_registered_only: bool = False) -> Video:
    now = utc_now()
    return Video(
        id=uuid4(),
        owner_id=owner_id or uuid4(),
        title="Clip",
        description="Context",
        original_filename="clip.mp4",
        is_registered_only=is_registered_only,
        edited=False,
        edited_at=None,
        processing_status=VideoProcessingStatus.PENDING,
        width=None,
        height=None,
        aspect_ratio=None,
        favorite_count=0,
        categories=[],
        tags=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
def test_public_video_is_visible_to_anonymous_user() -> None:
    video = make_video()

    assert can_view_video(video, current_user=None) is True


@pytest.mark.unit
def test_registered_only_video_requires_user(user_factory) -> None:
    video = make_video(is_registered_only=True)
    user = user_factory()

    assert can_view_video(video, current_user=None) is False
    assert can_view_video(video, current_user=user) is True


@pytest.mark.unit
def test_owner_admin_and_super_admin_can_edit_video(user_factory) -> None:
    owner = user_factory(role=UserRole.USER)
    admin = user_factory(role=UserRole.ADMIN)
    super_admin = user_factory(role=UserRole.SUPER_ADMIN)
    stranger = user_factory(role=UserRole.USER)
    video = make_video(owner_id=owner.id)

    assert can_edit_video(video, owner) is True
    assert can_edit_video(video, admin) is True
    assert can_edit_video(video, super_admin) is True
    assert can_edit_video(video, stranger) is False
    assert can_edit_video(video, None) is False


@pytest.mark.unit
def test_owner_and_super_admin_can_delete_video(user_factory) -> None:
    owner = user_factory(role=UserRole.USER)
    admin = user_factory(role=UserRole.ADMIN)
    super_admin = user_factory(role=UserRole.SUPER_ADMIN)
    video = make_video(owner_id=owner.id)

    assert can_delete_video(video, owner) is True
    assert can_delete_video(video, super_admin) is True
    assert can_delete_video(video, admin) is False
    assert can_delete_video(video, None) is False


@pytest.mark.unit
def test_only_logged_users_can_favorite_or_react_to_visible_video(user_factory) -> None:
    user = user_factory()
    public_video = make_video()
    registered_only_video = replace(public_video, is_registered_only=True)

    assert can_favorite_or_react_to_video(public_video, None) is False
    assert can_favorite_or_react_to_video(public_video, user) is True
    assert can_favorite_or_react_to_video(registered_only_video, user) is True
