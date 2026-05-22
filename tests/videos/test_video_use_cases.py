import pytest

from app.modules.users.domain.user import UserRole
from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.errors import VideoPermissionError
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.list_videos import ListVideos, ListVideosQuery
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.update_video import UpdateVideo, UpdateVideoCommand


@pytest.mark.unit
def test_list_videos_applies_visibility_filters_and_popularity_order(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    public_low = video_repository.add(
        video_factory(owner_id=owner.id, title="Alpha", favorite_count=1)
    )
    public_high = video_repository.add(
        video_factory(owner_id=owner.id, title="Alpha boss", favorite_count=5)
    )
    video_repository.add(
        video_factory(owner_id=owner.id, title="Alpha private", is_registered_only=True)
    )
    list_videos = ListVideos(video_repository)

    result = list_videos.execute(
        ListVideosQuery(title="alpha", limit=10, offset=0),
        current_user=None,
    )

    assert result.total == 2
    assert result.items == [public_high, public_low]


@pytest.mark.unit
def test_update_video_marks_video_as_edited_for_owner(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    video = video_repository.add(video_factory(owner_id=owner.id, edited=False))
    update_video = UpdateVideo(video_repository)

    updated = update_video.execute(
        UpdateVideoCommand(video_id=video.id, title="New title"),
        owner,
    )

    assert updated.title == "New title"
    assert updated.edited is True
    assert updated.edited_at is not None


@pytest.mark.unit
def test_delete_video_allows_owner_and_super_admin_but_blocks_admin(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory(role=UserRole.USER)
    admin = user_factory(role=UserRole.ADMIN)
    super_admin = user_factory(role=UserRole.SUPER_ADMIN)
    admin_blocked_video = video_repository.add(video_factory(owner_id=owner.id))
    owner_video = video_repository.add(video_factory(owner_id=owner.id))
    super_admin_video = video_repository.add(video_factory(owner_id=owner.id))
    delete_video = DeleteVideo(video_repository)

    with pytest.raises(VideoPermissionError):
        delete_video.execute(admin_blocked_video.id, admin)

    delete_video.execute(owner_video.id, owner)
    delete_video.execute(super_admin_video.id, super_admin)

    assert video_repository.get_by_id(admin_blocked_video.id) is not None
    assert video_repository.get_by_id(owner_video.id) is None
    assert video_repository.get_by_id(super_admin_video.id) is None


@pytest.mark.unit
def test_favorite_video_adds_and_removes_favorite(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    user = user_factory()
    video = video_repository.add(video_factory())
    favorite_video = FavoriteVideo(video_repository)

    favorite_video.add(video.id, user)
    assert video_repository.is_favorite(video.id, user.id) is True
    assert video_repository.get_by_id(video.id).favorite_count == 1

    favorite_video.remove(video.id, user)
    assert video_repository.is_favorite(video.id, user.id) is False
    assert video_repository.get_by_id(video.id).favorite_count == 0


@pytest.mark.unit
def test_react_to_video_sets_changes_counts_and_removes_reaction(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    user = user_factory()
    other_user = user_factory()
    video = video_repository.add(video_factory())
    react_to_video = ReactToVideo(video_repository)

    react_to_video.set(video.id, "like", user)
    react_to_video.set(video.id, "like", other_user)
    react_to_video.set(video.id, "wow", user)

    assert react_to_video.get_counts(video.id, None) == {"like": 1, "wow": 1}

    react_to_video.remove(video.id, user)
    assert react_to_video.get_counts(video.id, None) == {"like": 1}
