from io import BytesIO

import pytest

from app.modules.users.domain.user import UserRole
from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.errors import (
    VideoPermissionError,
    VideoReactionLimitError,
)
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.list_videos import ListVideos, ListVideosQuery
from app.modules.videos.application.process_video import ProcessVideo
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.upload_video import UploadVideo, UploadVideoCommand
from app.modules.videos.application.update_video import UpdateVideo, UpdateVideoCommand
from tests.fakes import FakeVideoRepository


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
    video_storage,
) -> None:
    owner = user_factory(role=UserRole.USER)
    admin = user_factory(role=UserRole.ADMIN)
    super_admin = user_factory(role=UserRole.SUPER_ADMIN)
    admin_blocked_video = video_repository.add(video_factory(owner_id=owner.id))
    owner_video = video_repository.add(video_factory(owner_id=owner.id))
    super_admin_video = video_repository.add(video_factory(owner_id=owner.id))
    delete_video = DeleteVideo(video_repository, video_storage)

    with pytest.raises(VideoPermissionError):
        delete_video.execute(admin_blocked_video.id, admin)

    delete_video.execute(owner_video.id, owner)
    delete_video.execute(super_admin_video.id, super_admin)

    assert video_repository.get_by_id(admin_blocked_video.id) is not None
    assert video_repository.get_by_id(owner_video.id) is None
    assert video_repository.get_by_id(super_admin_video.id) is None
    assert video_storage.deleted_all == [owner_video.id, super_admin_video.id]


@pytest.mark.unit
def test_delete_video_logs_physical_delete_errors_but_keeps_record_deleted(
    caplog,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    from tests.fakes import FakeVideoStorage

    owner = user_factory(role=UserRole.USER)
    video = video_repository.add(video_factory(owner_id=owner.id))
    delete_video = DeleteVideo(
        video_repository,
        FakeVideoStorage(delete_error=OSError("disk failed")),
    )

    delete_video.execute(video.id, owner)

    assert video_repository.get_by_id(video.id) is None
    assert "Failed to delete video files" in caplog.text


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

    assert react_to_video.get_counts(video.id, None) == {"like": 2, "wow": 1}

    react_to_video.remove(video.id, user)
    assert react_to_video.get_counts(video.id, None) == {"like": 1}


@pytest.mark.unit
def test_react_to_video_allows_two_user_reactions_but_blocks_third(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    user = user_factory()
    video = video_repository.add(video_factory())
    react_to_video = ReactToVideo(video_repository)

    react_to_video.set(video.id, "🔥", user)
    react_to_video.set(video.id, "😂", user)
    react_to_video.set(video.id, "🔥", user)

    with pytest.raises(VideoReactionLimitError):
        react_to_video.set(video.id, "😮", user)

    assert react_to_video.get_counts(video.id, None) == {"🔥": 1, "😂": 1}


@pytest.mark.unit
def test_upload_video_saves_file_and_creates_video(user_factory, video_storage) -> None:
    user = user_factory()
    video_repository = FakeVideoRepository()
    upload_video = UploadVideo(video_repository, video_storage)

    video = upload_video.execute(
        UploadVideoCommand(
            owner_id=user.id,
            title="Clip",
            description="Context",
            original_filename="clip.mp4",
            content_type="video/mp4",
            file=BytesIO(b"video-bytes"),
            tags=["boss"],
        )
    )

    assert video.owner_id == user.id
    assert video.original_filename == "clip.mp4"
    assert video_repository.created[0].id == video.id
    assert video_storage.saved[0]["video_id"] == video.id
    assert video_storage.saved[0]["content"] == b"video-bytes"


@pytest.mark.unit
def test_process_video_marks_video_ready_with_variants(
    video_factory,
    video_transcoder,
) -> None:
    video_repository = FakeVideoRepository()
    video = video_repository.add(video_factory())
    process_video = ProcessVideo(video_repository, video_transcoder)

    processed = process_video.execute(video.id)

    assert processed.processing_status.value == "ready"
    assert processed.width == 1920
    assert processed.height == 1080
    assert processed.duration_seconds == 12.5
    assert [variant.codec for variant in processed.variants] == ["av1", "h264"]
    assert video_transcoder.transcoded == [video.id]


@pytest.mark.unit
def test_process_video_marks_video_failed_when_transcoding_errors(video_factory) -> None:
    from tests.fakes import FakeVideoTranscoder

    video_repository = FakeVideoRepository()
    video = video_repository.add(video_factory())
    process_video = ProcessVideo(
        video_repository,
        FakeVideoTranscoder(error=RuntimeError("boom")),
    )

    processed = process_video.execute(video.id, job_id="job-1")

    assert processed.processing_status.value == "failed"
    assert processed.latest_processing_error is not None
    assert processed.latest_processing_error.attempt == 1
    assert processed.latest_processing_error.error_type == "RuntimeError"
    assert processed.latest_processing_error.error_message == "boom"
    assert processed.latest_processing_error.job_id == "job-1"
