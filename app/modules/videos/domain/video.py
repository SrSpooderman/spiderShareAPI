from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.modules.users.domain.user import User, UserRole


class VideoAspectRatio(str, Enum):
    RATIO_4_3 = "4:3"
    RATIO_16_9 = "16:9"
    RATIO_21_9 = "21:9"


class VideoProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoVariantType(str, Enum):
    ORIGINAL = "original"
    ORIGINAL_AV1 = "original_av1"
    ORIGINAL_H264 = "original_h264"
    LOW_H264 = "low_h264"


class VideoCategorySource(str, Enum):
    CUSTOM = "custom"
    STEAM = "steam"


@dataclass
class VideoOwner:
    id: UUID
    username: str
    display_name: str | None


@dataclass
class VideoCategory:
    id: UUID
    name: str
    source: VideoCategorySource
    steam_appid: int | None
    steamgriddb_game_id: int | None
    thumbnail_vertical_url: str | None
    thumbnail_horizontal_url: str | None
    thumbnail_vertical_image: bytes | None
    thumbnail_vertical_content_type: str | None
    thumbnail_horizontal_image: bytes | None
    thumbnail_horizontal_content_type: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VideoCategoryCreate:
    name: str
    source: VideoCategorySource = VideoCategorySource.CUSTOM
    steam_appid: int | None = None
    steamgriddb_game_id: int | None = None
    thumbnail_vertical_url: str | None = None
    thumbnail_horizontal_url: str | None = None
    thumbnail_vertical_image: bytes | None = None
    thumbnail_vertical_content_type: str | None = None
    thumbnail_horizontal_image: bytes | None = None
    thumbnail_horizontal_content_type: str | None = None


@dataclass
class VideoTag:
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VideoTagCreate:
    name: str


@dataclass
class VideoFavorite:
    id: UUID
    video_id: UUID
    user_id: UUID
    created_at: datetime


@dataclass
class VideoReaction:
    id: UUID
    video_id: UUID
    user_id: UUID
    reaction_type: str
    created_at: datetime
    updated_at: datetime


@dataclass
class VideoVariant:
    id: UUID
    video_id: UUID
    variant_type: VideoVariantType
    codec: str
    container: str
    width: int
    height: int
    bitrate_kbps: int | None
    size_bytes: int
    path: str
    created_at: datetime


@dataclass
class VideoProcessingError:
    id: UUID
    video_id: UUID
    attempt: int
    error_type: str
    error_message: str
    job_id: str | None
    duration_ms: float | None
    created_at: datetime


@dataclass(frozen=True)
class VideoVariantCreate:
    variant_type: VideoVariantType
    codec: str
    container: str
    width: int
    height: int
    bitrate_kbps: int | None
    size_bytes: int
    path: str


@dataclass(frozen=True)
class VideoProcessingResult:
    width: int
    height: int
    aspect_ratio: VideoAspectRatio
    duration_seconds: float
    source_created_at: datetime | None
    thumbnail_path: str
    variants: list[VideoVariantCreate]


@dataclass
class VideoCreate:
    owner_id: UUID
    title: str
    description: str
    original_filename: str
    id: UUID | None = None
    is_registered_only: bool = False
    edited: bool = False
    category_ids: list[UUID] = field(default_factory=list)
    tag_ids: list[UUID] = field(default_factory=list)


@dataclass
class Video:
    id: UUID
    owner_id: UUID
    owner: VideoOwner | None
    title: str
    description: str
    original_filename: str
    is_registered_only: bool
    edited: bool
    edited_at: datetime | None
    processing_status: VideoProcessingStatus
    width: int | None
    height: int | None
    aspect_ratio: VideoAspectRatio | None
    duration_seconds: float | None
    source_created_at: datetime | None
    thumbnail_path: str | None
    variants: list[VideoVariant]
    latest_processing_error: VideoProcessingError | None
    favorite_count: int
    categories: list[VideoCategory]
    tags: list[VideoTag]
    created_at: datetime
    updated_at: datetime


def can_view_video(video: Video, current_user: User | None) -> bool:
    if not video.is_registered_only:
        return True

    return current_user is not None


def can_edit_video(video: Video, current_user: User | None) -> bool:
    if current_user is None:
        return False

    return current_user.id == video.owner_id or current_user.role in {
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    }


def can_delete_video(video: Video, current_user: User | None) -> bool:
    if current_user is None:
        return False

    return current_user.id == video.owner_id or current_user.role == UserRole.SUPER_ADMIN


def can_favorite_or_react_to_video(video: Video, current_user: User | None) -> bool:
    return current_user is not None and can_view_video(video, current_user)


def video_popularity_score(video: Video) -> int:
    total_favorites = video.favorite_count
    return video.favorite_count * 3 + total_favorites
