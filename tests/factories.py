from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.steam.domain.steam_game import SteamGame
from app.modules.users.domain.user import User, UserRole
from app.modules.videos.domain.video import (
    Video,
    VideoCategory,
    VideoCategorySource,
    VideoOwner,
    VideoProcessingError,
    VideoProcessingStatus,
    VideoVariant,
    VideoVariantType,
    VideoTag,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def make_user(
    *,
    id: UUID | None = None,
    username: str = "test-user",
    display_name: str | None = None,
    bio: str | None = None,
    avatar_image: bytes | None = None,
    password_hash: str = "hashed:password",
    ldap: bool = False,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    last_seen_version: str | None = None,
    last_login_at: datetime | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> User:
    now = utc_now()
    return User(
        id=id or uuid4(),
        username=username,
        display_name=display_name,
        bio=bio,
        avatar_image=avatar_image,
        password_hash=password_hash,
        ldap=ldap,
        role=role,
        is_active=is_active,
        last_seen_version=last_seen_version,
        last_login_at=last_login_at,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_steam_game(
    *,
    id: UUID | None = None,
    appid: int = 10,
    name: str = "Counter-Strike",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> SteamGame:
    now = utc_now()
    return SteamGame(
        id=id or uuid4(),
        appid=appid,
        name=name,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_video_category(
    *,
    id: UUID | None = None,
    name: str = "Highlights",
    source: VideoCategorySource = VideoCategorySource.CUSTOM,
    steam_appid: int | None = None,
    steamgriddb_game_id: int | None = None,
    thumbnail_vertical_url: str | None = None,
    thumbnail_horizontal_url: str | None = None,
    thumbnail_vertical_image: bytes | None = None,
    thumbnail_vertical_content_type: str | None = None,
    thumbnail_horizontal_image: bytes | None = None,
    thumbnail_horizontal_content_type: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> VideoCategory:
    now = utc_now()
    return VideoCategory(
        id=id or uuid4(),
        name=name,
        source=source,
        steam_appid=steam_appid,
        steamgriddb_game_id=steamgriddb_game_id,
        thumbnail_vertical_url=thumbnail_vertical_url,
        thumbnail_horizontal_url=thumbnail_horizontal_url,
        thumbnail_vertical_image=thumbnail_vertical_image,
        thumbnail_vertical_content_type=thumbnail_vertical_content_type,
        thumbnail_horizontal_image=thumbnail_horizontal_image,
        thumbnail_horizontal_content_type=thumbnail_horizontal_content_type,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_video_tag(
    *,
    id: UUID | None = None,
    name: str = "clip",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> VideoTag:
    now = utc_now()
    return VideoTag(
        id=id or uuid4(),
        name=name,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_video(
    *,
    id: UUID | None = None,
    owner_id: UUID | None = None,
    owner_username: str = "test-user",
    owner_display_name: str | None = None,
    title: str = "Clip",
    description: str = "Context",
    original_filename: str = "clip.mp4",
    is_registered_only: bool = False,
    edited: bool = False,
    edited_at: datetime | None = None,
    processing_status: VideoProcessingStatus = VideoProcessingStatus.PENDING,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: float | None = None,
    thumbnail_path: str | None = None,
    variants: list[VideoVariant] | None = None,
    latest_processing_error: VideoProcessingError | None = None,
    favorite_count: int = 0,
    categories: list[VideoCategory] | None = None,
    tags: list[VideoTag] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Video:
    now = utc_now()
    resolved_owner_id = owner_id or uuid4()
    return Video(
        id=id or uuid4(),
        owner_id=resolved_owner_id,
        owner=VideoOwner(
            id=resolved_owner_id,
            username=owner_username,
            display_name=owner_display_name,
        ),
        title=title,
        description=description,
        original_filename=original_filename,
        is_registered_only=is_registered_only,
        edited=edited,
        edited_at=edited_at,
        processing_status=processing_status,
        width=width,
        height=height,
        aspect_ratio=None,
        duration_seconds=duration_seconds,
        thumbnail_path=thumbnail_path,
        variants=variants or [],
        latest_processing_error=latest_processing_error,
        favorite_count=favorite_count,
        categories=categories or [],
        tags=tags or [],
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_video_variant(
    *,
    id: UUID | None = None,
    video_id: UUID | None = None,
    variant_type: VideoVariantType = VideoVariantType.LOW_H264,
    codec: str = "h264",
    container: str = "mp4",
    width: int = 1280,
    height: int = 720,
    bitrate_kbps: int | None = None,
    size_bytes: int = 1024,
    path: str = "variants/video/low_h264.mp4",
    created_at: datetime | None = None,
) -> VideoVariant:
    now = utc_now()
    return VideoVariant(
        id=id or uuid4(),
        video_id=video_id or uuid4(),
        variant_type=variant_type,
        codec=codec,
        container=container,
        width=width,
        height=height,
        bitrate_kbps=bitrate_kbps,
        size_bytes=size_bytes,
        path=path,
        created_at=created_at or now,
    )
