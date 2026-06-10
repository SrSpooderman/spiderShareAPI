from uuid import UUID

from app.modules.videos.domain.video import (
    Video,
    VideoAspectRatio,
    VideoCategory,
    VideoCreate,
    VideoFavorite,
    VideoOwner,
    VideoProcessingStatus,
    VideoReaction,
    VideoTag,
    VideoVariant,
    VideoVariantType,
)
from app.modules.videos.infrastructure.models import (
    VideoCategoryModel,
    VideoFavoriteModel,
    VideoModel,
    VideoReactionModel,
    VideoTagModel,
    VideoVariantModel,
)


def video_model_to_domain(model: VideoModel) -> Video:
    categories = [
        video_category_model_to_domain(assignment.category)
        for assignment in model.category_assignments
    ]
    tags = [video_tag_model_to_domain(assignment.tag) for assignment in model.tag_assignments]
    variants = [video_variant_model_to_domain(variant) for variant in model.variants]

    return Video(
        id=UUID(model.id),
        owner_id=UUID(model.owner_id),
        owner=(
            VideoOwner(
                id=UUID(model.owner.id),
                username=model.owner.username,
                display_name=model.owner.display_name,
            )
            if model.owner is not None
            else None
        ),
        title=model.title,
        description=model.description,
        original_filename=model.original_filename,
        is_registered_only=model.is_registered_only,
        edited=model.edited,
        edited_at=model.edited_at,
        processing_status=VideoProcessingStatus(model.processing_status),
        width=model.width,
        height=model.height,
        aspect_ratio=(
            VideoAspectRatio(model.aspect_ratio)
            if model.aspect_ratio is not None
            else None
        ),
        duration_seconds=model.duration_seconds,
        thumbnail_path=model.thumbnail_path,
        variants=variants,
        favorite_count=model.favorite_count,
        categories=categories,
        tags=tags,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def video_create_to_model(video: VideoCreate) -> VideoModel:
    model = VideoModel(
        owner_id=str(video.owner_id),
        title=video.title,
        description=video.description,
        original_filename=video.original_filename,
        is_registered_only=video.is_registered_only,
    )
    if video.id is not None:
        model.id = str(video.id)

    return model


def video_category_model_to_domain(model: VideoCategoryModel) -> VideoCategory:
    return VideoCategory(
        id=UUID(model.id),
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def video_tag_model_to_domain(model: VideoTagModel) -> VideoTag:
    return VideoTag(
        id=UUID(model.id),
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def video_favorite_model_to_domain(model: VideoFavoriteModel) -> VideoFavorite:
    return VideoFavorite(
        id=UUID(model.id),
        video_id=UUID(model.video_id),
        user_id=UUID(model.user_id),
        created_at=model.created_at,
    )


def video_reaction_model_to_domain(model: VideoReactionModel) -> VideoReaction:
    return VideoReaction(
        id=UUID(model.id),
        video_id=UUID(model.video_id),
        user_id=UUID(model.user_id),
        reaction_type=model.reaction_type,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def video_variant_model_to_domain(model: VideoVariantModel) -> VideoVariant:
    return VideoVariant(
        id=UUID(model.id),
        video_id=UUID(model.video_id),
        variant_type=VideoVariantType(model.variant_type),
        codec=model.codec,
        container=model.container,
        width=model.width,
        height=model.height,
        bitrate_kbps=model.bitrate_kbps,
        size_bytes=model.size_bytes,
        path=model.path,
        created_at=model.created_at,
    )
