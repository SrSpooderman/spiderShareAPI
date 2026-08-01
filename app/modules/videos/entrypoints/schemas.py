from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.users.domain.user import User
from app.modules.videos.domain.ports import VideoListResult
from app.modules.videos.domain.video import (
    Video,
    VideoAspectRatio,
    VideoCategory,
    VideoOwner,
    VideoProcessingError,
    VideoProcessingStatus,
    VideoReaction,
    VideoTag,
    VideoVariant,
    VideoVariantType,
    can_delete_video,
    can_edit_video,
    video_popularity_score,
)
from config.settings import settings


class VideoCategoryResponse(BaseModel):
    id: UUID
    name: str
    source: str
    steam_appid: int | None
    steamgriddb_game_id: int | None
    thumbnail_vertical_url: str | None
    thumbnail_horizontal_url: str | None

    @classmethod
    def from_domain(cls, category: VideoCategory) -> "VideoCategoryResponse":
        return cls(
            id=category.id,
            name=category.name,
            source=category.source.value,
            steam_appid=category.steam_appid,
            steamgriddb_game_id=category.steamgriddb_game_id,
            thumbnail_vertical_url=category.thumbnail_vertical_url,
            thumbnail_horizontal_url=category.thumbnail_horizontal_url,
        )


class VideoTagResponse(BaseModel):
    id: UUID
    name: str

    @classmethod
    def from_domain(cls, tag: VideoTag) -> "VideoTagResponse":
        return cls(id=tag.id, name=tag.name)


class VideoTagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name cannot be blank")
        return name


class VideoOwnerResponse(BaseModel):
    id: UUID
    username: str
    display_name: str | None

    @classmethod
    def from_domain(cls, owner: VideoOwner) -> "VideoOwnerResponse":
        return cls(
            id=owner.id,
            username=owner.username,
            display_name=owner.display_name,
        )


class VideoReactionCountResponse(BaseModel):
    type: str
    count: int


class VideoReactionResponse(BaseModel):
    id: UUID
    video_id: UUID
    user_id: UUID
    reaction_type: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, reaction: VideoReaction) -> "VideoReactionResponse":
        return cls(
            id=reaction.id,
            video_id=reaction.video_id,
            user_id=reaction.user_id,
            reaction_type=reaction.reaction_type,
            created_at=reaction.created_at,
            updated_at=reaction.updated_at,
        )


class VideoVariantResponse(BaseModel):
    id: UUID
    variant_type: VideoVariantType
    codec: str
    container: str
    width: int
    height: int
    bitrate_kbps: int | None
    size_bytes: int
    path: str

    @classmethod
    def from_domain(cls, variant: VideoVariant) -> "VideoVariantResponse":
        return cls(
            id=variant.id,
            variant_type=variant.variant_type,
            codec=variant.codec,
            container=variant.container,
            width=variant.width,
            height=variant.height,
            bitrate_kbps=variant.bitrate_kbps,
            size_bytes=variant.size_bytes,
            path=variant.path,
        )


class VideoProcessingErrorResponse(BaseModel):
    id: UUID
    video_id: UUID
    attempt: int
    error_type: str
    error_message: str
    job_id: str | None
    duration_ms: float | None
    created_at: datetime

    @classmethod
    def from_domain(cls, error: VideoProcessingError) -> "VideoProcessingErrorResponse":
        return cls(
            id=error.id,
            video_id=error.video_id,
            attempt=error.attempt,
            error_type=error.error_type,
            error_message=error.error_message,
            job_id=error.job_id,
            duration_ms=error.duration_ms,
            created_at=error.created_at,
        )


class VideoSummaryResponse(BaseModel):
    id: UUID
    title: str
    description: str
    owner: VideoOwnerResponse
    is_registered_only: bool
    edited: bool
    edited_at: datetime | None
    processing_status: VideoProcessingStatus
    latest_processing_error: VideoProcessingErrorResponse | None
    favorite_count: int
    popularity_score: int
    categories: list[VideoCategoryResponse]
    tags: list[VideoTagResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, video: Video) -> "VideoSummaryResponse":
        return cls(
            id=video.id,
            title=video.title,
            description=video.description,
            owner=VideoOwnerResponse.from_domain(
                video.owner
                or VideoOwner(
                    id=video.owner_id,
                    username="-",
                    display_name=None,
                )
            ),
            is_registered_only=video.is_registered_only,
            edited=video.edited,
            edited_at=video.edited_at,
            processing_status=video.processing_status,
            latest_processing_error=(
                VideoProcessingErrorResponse.from_domain(video.latest_processing_error)
                if video.latest_processing_error is not None
                else None
            ),
            favorite_count=video.favorite_count,
            popularity_score=video_popularity_score(video),
            categories=[
                VideoCategoryResponse.from_domain(category)
                for category in video.categories
            ],
            tags=[VideoTagResponse.from_domain(tag) for tag in video.tags],
            created_at=video.created_at,
            updated_at=video.updated_at,
        )


class VideoDetailResponse(VideoSummaryResponse):
    original_filename: str
    playback_url: str | None
    clip_url: str
    download_url: str
    thumbnail_url: str | None
    aspect_ratio: VideoAspectRatio | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    source_created_at: datetime | None
    source_updated_at: datetime | None
    thumbnail_path: str | None
    variants: list[VideoVariantResponse]
    is_owner: bool
    can_edit: bool
    can_delete: bool
    is_favorite: bool
    reactions: list[VideoReactionCountResponse]

    @classmethod
    def from_domain(
        cls,
        video: Video,
        *,
        current_user: User | None,
        is_favorite: bool,
        reaction_counts: dict[str, int],
    ) -> "VideoDetailResponse":
        return cls(
            **VideoSummaryResponse.from_domain(video).model_dump(),
            original_filename=video.original_filename,
            playback_url=(
                f"/videos/{video.id}/stream"
                if video.processing_status == VideoProcessingStatus.READY
                and video.variants
                else None
            ),
            clip_url=f"/clip/{video.id}",
            download_url=f"/videos/{video.id}/download",
            thumbnail_url=(
                f"/videos/{video.id}/thumbnail"
                if video.thumbnail_path is not None
                else None
            ),
            aspect_ratio=video.aspect_ratio,
            width=video.width,
            height=video.height,
            duration_seconds=video.duration_seconds,
            source_created_at=video.source_created_at,
            source_updated_at=video.source_updated_at,
            thumbnail_path=video.thumbnail_path,
            variants=[
                VideoVariantResponse.from_domain(variant)
                for variant in video.variants
            ],
            is_owner=current_user is not None and current_user.id == video.owner_id,
            can_edit=can_edit_video(video, current_user),
            can_delete=can_delete_video(video, current_user),
            is_favorite=is_favorite,
            reactions=[
                VideoReactionCountResponse(type=reaction_type, count=count)
                for reaction_type, count in sorted(reaction_counts.items())
            ],
        )


class VideoListResponse(BaseModel):
    items: list[VideoDetailResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_result(
        cls,
        result: VideoListResult,
        *,
        limit: int,
        offset: int,
        current_user: User | None,
        favorites_by_video_id: dict[UUID, bool] | None = None,
        reaction_counts_by_video_id: dict[UUID, dict[str, int]] | None = None,
    ) -> "VideoListResponse":
        favorites_by_video_id = favorites_by_video_id or {}
        reaction_counts_by_video_id = reaction_counts_by_video_id or {}

        return cls(
            items=[
                VideoDetailResponse.from_domain(
                    video,
                    current_user=current_user,
                    is_favorite=favorites_by_video_id.get(video.id, False),
                    reaction_counts=reaction_counts_by_video_id.get(video.id, {}),
                )
                for video in result.items
            ],
            total=result.total,
            limit=limit,
            offset=offset,
        )


class VideoCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    thumbnail_vertical_url: str | None = Field(default=None, max_length=1000)
    thumbnail_horizontal_url: str | None = Field(default=None, max_length=1000)

    @field_validator("name", mode="before")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name cannot be blank")
        return name


class SteamGridDbGameResponse(BaseModel):
    id: int
    name: str
    types: list[str] = Field(default_factory=list)
    verified: bool | None = None


class SteamGridDbGridResponse(BaseModel):
    id: int | None
    url: str
    thumb: str | None
    width: int | None
    height: int | None
    style: str | None
    nsfw: bool | None
    humor: bool | None
    epilepsy: bool | None


class SteamGridDbGridListResponse(BaseModel):
    items: list[SteamGridDbGridResponse]
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None


class SteamVideoCategoryImportRequest(BaseModel):
    steam_appid: int | None = Field(default=None, gt=0)
    steamgriddb_game_id: int | None = Field(default=None, gt=0)
    thumbnail_vertical_url: str | None = Field(default=None, max_length=1000)
    thumbnail_horizontal_url: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def at_least_one_external_id(self):
        if self.steam_appid is None and self.steamgriddb_game_id is None:
            raise ValueError("steam_appid or steamgriddb_game_id is required")
        return self


class BulkVideoUploadItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    is_registered_only: bool = False
    category_ids: list[UUID] = Field(default_factory=list)
    tag_ids: list[UUID] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value cannot be blank")
        return text

    @field_validator("tag_ids", mode="after")
    @classmethod
    def tag_ids_must_fit_limit(cls, value: list[UUID]) -> list[UUID]:
        tag_ids = list(dict.fromkeys(value))
        if len(tag_ids) > settings.max_video_tags:
            raise ValueError("too many tags")
        return tag_ids


class BulkVideoUploadResponse(BaseModel):
    items: list[VideoDetailResponse]
    total: int


class VideoUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    is_registered_only: bool | None = None
    edited: bool | None = None
    category_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value

        text = value.strip()
        if not text:
            raise ValueError("value cannot be blank")
        return text

    @field_validator("tag_ids", mode="after")
    @classmethod
    def tag_ids_must_fit_limit(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is None:
            return value

        tag_ids = list(dict.fromkeys(value))
        if len(tag_ids) > settings.max_video_tags:
            raise ValueError("too many tags")
        return tag_ids


class VideoReactionRequest(BaseModel):
    reaction_type: str = Field(min_length=1, max_length=32)

    @field_validator("reaction_type", mode="before")
    @classmethod
    def reaction_type_must_not_be_blank(cls, value: str) -> str:
        reaction_type = value.strip()
        if not reaction_type:
            raise ValueError("reaction_type cannot be blank")
        return reaction_type
