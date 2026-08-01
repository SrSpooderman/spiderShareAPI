from uuid import uuid4

import pytest

from app.modules.videos.domain.video import (
    VideoAspectRatio,
    VideoCreate,
    VideoProcessingStatus,
)
from app.modules.videos.infrastructure.mappers import (
    video_create_to_model,
    video_favorite_model_to_domain,
    video_model_to_domain,
    video_reaction_model_to_domain,
)
from app.modules.videos.infrastructure.models import (
    VideoCategoryAssignmentModel,
    VideoCategoryModel,
    VideoFavoriteModel,
    VideoModel,
    VideoReactionModel,
    VideoTagAssignmentModel,
    VideoTagModel,
)
from tests.factories import utc_now


@pytest.mark.unit
def test_video_create_to_model_preserves_video_fields() -> None:
    video_id = uuid4()
    owner_id = uuid4()
    video_create = VideoCreate(
        id=video_id,
        owner_id=owner_id,
        title="Clip title",
        description="Clip context",
        original_filename="clip.mp4",
        is_registered_only=True,
        edited=True,
    )

    model = video_create_to_model(video_create)

    assert model.id == str(video_id)
    assert model.owner_id == str(owner_id)
    assert model.title == "Clip title"
    assert model.description == "Clip context"
    assert model.original_filename == "clip.mp4"
    assert model.is_registered_only is True
    assert model.edited is True


@pytest.mark.unit
def test_video_model_to_domain_preserves_video_fields() -> None:
    video_id = uuid4()
    owner_id = uuid4()
    category_id = uuid4()
    tag_id = uuid4()
    now = utc_now()
    source_created_at = now
    source_updated_at = now
    model = VideoModel(
        id=str(video_id),
        owner_id=str(owner_id),
        title="Clip title",
        description="Clip context",
        original_filename="clip.mp4",
        is_registered_only=False,
        edited=True,
        edited_at=now,
        processing_status=VideoProcessingStatus.READY.value,
        width=1920,
        height=1080,
        aspect_ratio=VideoAspectRatio.RATIO_16_9.value,
        source_created_at=source_created_at,
        source_updated_at=source_updated_at,
        favorite_count=3,
        created_at=now,
        updated_at=now,
    )
    category = VideoCategoryModel(
        id=str(category_id),
        name="Highlights",
        created_at=now,
        updated_at=now,
    )
    tag = VideoTagModel(
        id=str(tag_id),
        name="boss-fight",
        created_at=now,
        updated_at=now,
    )
    model.category_assignments = [
        VideoCategoryAssignmentModel(
            video_id=str(video_id),
            category_id=str(category_id),
            category=category,
        )
    ]
    model.tag_assignments = [
        VideoTagAssignmentModel(
            video_id=str(video_id),
            tag_id=str(tag_id),
            tag=tag,
        )
    ]

    video = video_model_to_domain(model)

    assert video.id == video_id
    assert video.owner_id == owner_id
    assert video.title == "Clip title"
    assert video.description == "Clip context"
    assert video.original_filename == "clip.mp4"
    assert video.edited is True
    assert video.source_created_at == source_created_at
    assert video.source_updated_at == source_updated_at
    assert video.processing_status == VideoProcessingStatus.READY
    assert video.aspect_ratio == VideoAspectRatio.RATIO_16_9
    assert video.favorite_count == 3
    assert [category.name for category in video.categories] == ["Highlights"]
    assert [tag.name for tag in video.tags] == ["boss-fight"]


@pytest.mark.unit
def test_video_favorite_model_to_domain_preserves_favorite_fields() -> None:
    favorite_id = uuid4()
    video_id = uuid4()
    user_id = uuid4()
    now = utc_now()
    model = VideoFavoriteModel(
        id=str(favorite_id),
        video_id=str(video_id),
        user_id=str(user_id),
        created_at=now,
    )

    favorite = video_favorite_model_to_domain(model)

    assert favorite.id == favorite_id
    assert favorite.video_id == video_id
    assert favorite.user_id == user_id
    assert favorite.created_at == now


@pytest.mark.unit
def test_video_reaction_model_to_domain_preserves_reaction_fields() -> None:
    reaction_id = uuid4()
    video_id = uuid4()
    user_id = uuid4()
    now = utc_now()
    model = VideoReactionModel(
        id=str(reaction_id),
        video_id=str(video_id),
        user_id=str(user_id),
        reaction_type="like",
        created_at=now,
        updated_at=now,
    )

    reaction = video_reaction_model_to_domain(model)

    assert reaction.id == reaction_id
    assert reaction.video_id == video_id
    assert reaction.user_id == user_id
    assert reaction.reaction_type == "like"
    assert reaction.created_at == now
    assert reaction.updated_at == now
