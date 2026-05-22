from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.steam.domain.steam_game import SteamGame
from app.modules.users.domain.user import User, UserRole
from app.modules.videos.domain.video import (
    Video,
    VideoCategory,
    VideoProcessingStatus,
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
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> VideoCategory:
    now = utc_now()
    return VideoCategory(
        id=id or uuid4(),
        name=name,
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
    title: str = "Clip",
    description: str = "Context",
    original_filename: str = "clip.mp4",
    is_registered_only: bool = False,
    edited: bool = False,
    edited_at: datetime | None = None,
    processing_status: VideoProcessingStatus = VideoProcessingStatus.PENDING,
    width: int | None = None,
    height: int | None = None,
    favorite_count: int = 0,
    categories: list[VideoCategory] | None = None,
    tags: list[VideoTag] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Video:
    now = utc_now()
    return Video(
        id=id or uuid4(),
        owner_id=owner_id or uuid4(),
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
        favorite_count=favorite_count,
        categories=categories or [],
        tags=tags or [],
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
