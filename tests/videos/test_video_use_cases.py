from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

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
from app.modules.videos.domain.video import VideoProcessingResult
from tests.fakes import FakeVideoRepository


@pytest.mark.unit
def test_list_videos_applies_visibility_filters_and_created_at_desc_order(
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    older = video_repository.add(
        video_factory(
            owner_id=owner.id,
            title="Alpha older",
            favorite_count=5,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    newer = video_repository.add(
        video_factory(
            owner_id=owner.id,
            title="Alpha newer",
            favorite_count=1,
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
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
    assert result.items == [newer, older]


@pytest.mark.unit
def test_list_videos_orders_by_source_created_at_in_requested_direction(
    video_factory,
    video_repository,
) -> None:
    oldest_source = video_repository.add(
        video_factory(
            title="Oldest source",
            created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
            source_created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    )
    newest_source = video_repository.add(
        video_factory(
            title="Newest source",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
    )
    missing_source = video_repository.add(
        video_factory(
            title="Missing source",
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            source_created_at=None,
        )
    )
    list_videos = ListVideos(video_repository)

    descending_result = list_videos.execute(
        ListVideosQuery(
            sort_by="source_created_at",
            sort_direction="desc",
        ),
        current_user=None,
    )
    ascending_result = list_videos.execute(
        ListVideosQuery(
            sort_by="source_created_at",
            sort_direction="asc",
        ),
        current_user=None,
    )

    assert descending_result.items == [newest_source, oldest_source, missing_source]
    assert ascending_result.items == [oldest_source, newest_source, missing_source]


@pytest.mark.unit
def test_update_video_only_sets_edited_when_requested_by_owner(
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
    assert updated.edited is False
    assert updated.edited_at is None

    updated = update_video.execute(
        UpdateVideoCommand(video_id=video.id, edited=True),
        owner,
    )

    assert updated.edited is True
    assert updated.edited_at is None


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
    source_created_at = datetime(2026, 7, 7, 18, 22, 10, tzinfo=timezone.utc)

    video = upload_video.execute(
        UploadVideoCommand(
            owner_id=user.id,
            title="Clip",
            description="Context",
            original_filename="clip.mp4",
            content_type="video/mp4",
            file=BytesIO(b"video-bytes"),
            edited=True,
            source_created_at=source_created_at,
            tag_ids=[uuid4()],
        )
    )

    assert video.owner_id == user.id
    assert video.original_filename == "clip.mp4"
    assert video.edited is True
    assert video.source_created_at == source_created_at
    assert video_repository.created[0].id == video.id
    assert video_repository.created[0].source_created_at == source_created_at
    assert video_storage.saved[0]["video_id"] == video.id
    assert video_storage.saved[0]["content"] == b"video-bytes"


@pytest.mark.unit
def test_process_video_marks_video_ready_with_low_variant(
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
    assert processed.source_created_at is None
    assert [variant.codec for variant in processed.variants] == ["h264"]
    assert video_transcoder.transcoded == [video.id]


@pytest.mark.unit
def test_process_video_preserves_existing_source_created_at(
    video_factory,
    video_transcoder,
) -> None:
    source_created_at = datetime(2026, 7, 7, 18, 22, 10, tzinfo=timezone.utc)
    video_repository = FakeVideoRepository()
    video = video_repository.add(
        video_factory(
            source_created_at=source_created_at,
        )
    )
    process_video = ProcessVideo(video_repository, video_transcoder)

    processed = process_video.execute(video.id)

    assert processed.source_created_at == source_created_at


@pytest.mark.unit
def test_process_video_prefers_metadata_source_created_at(
    video_factory,
    video_transcoder,
) -> None:
    user_source_created_at = datetime(2026, 7, 7, 18, 22, 10, tzinfo=timezone.utc)
    metadata_source_created_at = datetime(2026, 8, 8, 10, 12, 30, tzinfo=timezone.utc)
    video_repository = FakeVideoRepository()
    video = video_repository.add(
        video_factory(
            source_created_at=user_source_created_at,
        )
    )
    default_result = video_transcoder.transcode(video.id)
    video_transcoder.transcoded.clear()
    video_transcoder.result = VideoProcessingResult(
        width=default_result.width,
        height=default_result.height,
        aspect_ratio=default_result.aspect_ratio,
        duration_seconds=default_result.duration_seconds,
        source_created_at=metadata_source_created_at,
        thumbnail_path=default_result.thumbnail_path,
        variants=default_result.variants,
    )
    process_video = ProcessVideo(video_repository, video_transcoder)

    processed = process_video.execute(video.id)

    assert processed.source_created_at == metadata_source_created_at


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
