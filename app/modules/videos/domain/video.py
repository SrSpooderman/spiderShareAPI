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


@dataclass
class VideoCategory:
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass
class VideoTag:
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


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
class VideoCreate:
    owner_id: UUID
    title: str
    description: str
    original_filename: str
    is_registered_only: bool = False
    category_ids: list[UUID] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Video:
    id: UUID
    owner_id: UUID
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
