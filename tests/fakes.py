from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate
from app.modules.users.domain.user import User, UserCreate, UserRole
from app.modules.videos.domain.ports import VideoListFilters, VideoListResult
from app.modules.videos.domain.video import (
    Video,
    VideoCategory,
    VideoCategoryCreate,
    VideoCreate,
    VideoProcessingError,
    VideoProcessingResult,
    VideoProcessingStatus,
    VideoReaction,
    VideoTag,
    VideoTagCreate,
    video_popularity_score,
)
from app.shared.infrastructure.providers.steam.steam_client import SteamApiError
from tests.factories import (
    make_steam_game,
    make_user,
    make_video,
    make_video_category,
    make_video_tag,
    make_video_variant,
    utc_now,
)


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users: dict[UUID, User] = {}
        self.created: list[UserCreate] = []
        self.updated: list[tuple[UUID, dict]] = []
        self.deleted: list[UUID] = []

        for user in users or []:
            self.add(user)

    def add(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def get_by_id(self, user_uuid: UUID) -> User | None:
        return self.users.get(user_uuid)

    def get_by_username(self, username: str) -> User | None:
        return next(
            (user for user in self.users.values() if user.username == username),
            None,
        )

    def get_by_oidc_subject(self, subject: str) -> User | None:
        return next(
            (user for user in self.users.values() if user.oidc_subject == subject),
            None,
        )

    def list_users(self) -> list[User]:
        return list(self.users.values())

    def create(self, user: UserCreate) -> User:
        self.created.append(user)
        created_user = make_user(
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            avatar_image=user.avatar_image,
            password_hash=user.password_hash,
            ldap=user.ldap,
            auth_provider=user.auth_provider,
            oidc_subject=user.oidc_subject,
            oidc_email=user.oidc_email,
            oidc_name=user.oidc_name,
            oidc_groups=user.oidc_groups or [],
            role=user.role,
        )
        return self.add(created_user)

    def update(
        self,
        user_uuid: UUID,
        *,
        username: str | None = None,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_image: bytes | None = None,
        password_hash: str | None = None,
        oidc_email: str | None = None,
        oidc_name: str | None = None,
        oidc_groups: list[str] | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        last_login_at: datetime | None = None,
        clear_display_name: bool = False,
        clear_bio: bool = False,
        clear_avatar_image: bool = False,
    ) -> User | None:
        user = self.users.get(user_uuid)
        if user is None:
            return None

        changes = {
            "username": username,
            "display_name": display_name,
            "bio": bio,
            "avatar_image": avatar_image,
            "password_hash": password_hash,
            "oidc_email": oidc_email,
            "oidc_name": oidc_name,
            "oidc_groups": oidc_groups,
            "role": role,
            "is_active": is_active,
            "last_login_at": last_login_at,
            "clear_display_name": clear_display_name,
            "clear_bio": clear_bio,
            "clear_avatar_image": clear_avatar_image,
        }
        self.updated.append((user_uuid, changes))

        if username is not None:
            user.username = username
        if display_name is not None or clear_display_name:
            user.display_name = display_name
        if bio is not None or clear_bio:
            user.bio = bio
        if avatar_image is not None or clear_avatar_image:
            user.avatar_image = avatar_image
        if password_hash is not None:
            user.password_hash = password_hash
        if oidc_email is not None:
            user.oidc_email = oidc_email
        if oidc_name is not None:
            user.oidc_name = oidc_name
        if oidc_groups is not None:
            user.oidc_groups = oidc_groups
        if role is not None:
            user.role = UserRole(role)
        if is_active is not None:
            user.is_active = is_active
        if last_login_at is not None:
            user.last_login_at = last_login_at

        return user

    def delete(self, user_uuid: UUID) -> bool:
        self.deleted.append(user_uuid)
        return self.users.pop(user_uuid, None) is not None


class FakeSteamGameRepository:
    def __init__(self, games: list[SteamGame] | None = None) -> None:
        self.games: dict[int, SteamGame] = {}
        self.created: list[SteamGameCreate] = []
        self.upserted: list[tuple[int, str]] = []

        for game in games or []:
            self.add(game)

    def add(self, game: SteamGame) -> SteamGame:
        self.games[game.appid] = game
        return game

    def get_by_appid(self, appid: int) -> SteamGame | None:
        return self.games.get(appid)

    def create(self, steam_game: SteamGameCreate) -> SteamGame:
        self.created.append(steam_game)
        return self.add(make_steam_game(appid=steam_game.appid, name=steam_game.name))

    def upsert_by_appid(self, appid: int, name: str) -> SteamGame:
        self.upserted.append((appid, name))
        game = self.games.get(appid)
        if game is None:
            return self.create(SteamGameCreate(appid=appid, name=name))

        game.name = name
        return game


class FakeVideoRepository:
    def __init__(self, videos: list[Video] | None = None) -> None:
        self.videos: dict[UUID, Video] = {}
        self.created: list[VideoCreate] = []
        self.updated: list[tuple[UUID, dict]] = []
        self.deleted: list[UUID] = []
        self.reset: list[UUID] = []
        self.processing_errors: dict[UUID, list[VideoProcessingError]] = {}
        self.favorites: set[tuple[UUID, UUID]] = set()
        self.reactions: dict[tuple[UUID, UUID, str], VideoReaction] = {}
        self.tags: dict[UUID, VideoTag] = {}

        for video in videos or []:
            self.add(video)

    def add(self, video: Video) -> Video:
        self.videos[video.id] = video
        for tag in video.tags:
            self.tags[tag.id] = tag
        return video

    def add_tag(self, tag: VideoTag) -> VideoTag:
        self.tags[tag.id] = tag
        return tag

    def get_by_id(self, video_id: UUID) -> Video | None:
        return self.videos.get(video_id)

    def list_visible(
        self,
        *,
        current_user_id: UUID | None,
        filters: VideoListFilters,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        videos = [
            video
            for video in self.videos.values()
            if current_user_id is not None or not video.is_registered_only
        ]
        if filters.title:
            videos = [
                video
                for video in videos
                if filters.title.lower() in video.title.lower()
            ]
        if filters.owner_id is not None:
            videos = [video for video in videos if video.owner_id == filters.owner_id]
        if filters.category_ids:
            category_ids = set(filters.category_ids)
            videos = [
                video
                for video in videos
                if category_ids & {category.id for category in video.categories}
            ]
        if filters.tag_ids:
            tag_ids = set(filters.tag_ids)
            videos = [
                video
                for video in videos
                if tag_ids & {tag.id for tag in video.tags}
            ]

        videos = sorted(
            videos,
            key=lambda video: (video_popularity_score(video), video.created_at),
            reverse=True,
        )

        return VideoListResult(items=videos[offset : offset + limit], total=len(videos))

    def create(self, video: VideoCreate) -> Video:
        self.created.append(video)
        return self.add(
            make_video(
                id=video.id,
                owner_id=video.owner_id,
                owner_username="test-user",
                title=video.title,
                description=video.description,
                original_filename=video.original_filename,
                is_registered_only=video.is_registered_only,
                edited=video.edited,
                tags=self._tags_for_ids(video.tag_ids),
            )
        )

    def mark_processing(self, video_id: UUID) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        updated_video = replace(
            video,
            processing_status=VideoProcessingStatus.PROCESSING,
        )
        self.videos[video_id] = updated_video
        return updated_video

    def mark_processed(
        self,
        video_id: UUID,
        result: VideoProcessingResult,
    ) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        now = utc_now()
        variants = [
            make_video_variant(
                video_id=video_id,
                variant_type=variant.variant_type,
                codec=variant.codec,
                container=variant.container,
                width=variant.width,
                height=variant.height,
                bitrate_kbps=variant.bitrate_kbps,
                size_bytes=variant.size_bytes,
                path=variant.path,
            )
            for variant in result.variants
        ]
        updated_video = replace(
            video,
            processing_status=VideoProcessingStatus.READY,
            width=result.width,
            height=result.height,
            aspect_ratio=result.aspect_ratio,
            duration_seconds=result.duration_seconds,
            source_created_at=result.source_created_at or video.created_at,
            thumbnail_path=result.thumbnail_path,
            variants=variants,
            updated_at=now,
        )
        self.videos[video_id] = updated_video
        return updated_video

    def mark_failed(
        self,
        video_id: UUID,
        *,
        error_type: str,
        error_message: str,
        job_id: str | None,
        duration_ms: float | None,
    ) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        errors = self.processing_errors.setdefault(video_id, [])
        processing_error = VideoProcessingError(
            id=uuid4(),
            video_id=video_id,
            attempt=len(errors) + 1,
            error_type=error_type,
            error_message=error_message,
            job_id=job_id,
            duration_ms=duration_ms,
            created_at=utc_now(),
        )
        errors.append(processing_error)
        updated_video = replace(
            video,
            processing_status=VideoProcessingStatus.FAILED,
            latest_processing_error=processing_error,
        )
        self.videos[video_id] = updated_video
        return updated_video

    def reset_processing(self, video_id: UUID) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        self.reset.append(video_id)
        updated_video = replace(
            video,
            processing_status=VideoProcessingStatus.PENDING,
            width=None,
            height=None,
            aspect_ratio=None,
            duration_seconds=None,
            source_created_at=None,
            thumbnail_path=None,
            variants=[],
        )
        self.videos[video_id] = updated_video
        return updated_video

    def update_metadata(
        self,
        video_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        is_registered_only: bool | None = None,
        edited: bool | None = None,
        category_ids: list[UUID] | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        changes = {
            "title": title,
            "description": description,
            "is_registered_only": is_registered_only,
            "edited": edited,
            "category_ids": category_ids,
            "tag_ids": tag_ids,
        }
        self.updated.append((video_id, changes))

        now = utc_now()
        updated_video = replace(
            video,
            title=title if title is not None else video.title,
            description=description if description is not None else video.description,
            is_registered_only=(
                is_registered_only
                if is_registered_only is not None
                else video.is_registered_only
            ),
            edited=edited if edited is not None else video.edited,
            tags=self._tags_for_ids(tag_ids) if tag_ids is not None else video.tags,
            updated_at=now,
        )
        self.videos[video_id] = updated_video

        return updated_video

    def _tags_for_ids(self, tag_ids: list[UUID]) -> list[VideoTag]:
        tags = []
        for tag_id in dict.fromkeys(tag_ids):
            tag = self.tags.get(tag_id)
            if tag is None:
                tag = make_video_tag(id=tag_id, name=str(tag_id))
                self.tags[tag_id] = tag
            tags.append(tag)
        return tags

    def delete(self, video_id: UUID) -> bool:
        self.deleted.append(video_id)
        return self.videos.pop(video_id, None) is not None

    def add_favorite(self, video_id: UUID, user_id: UUID) -> None:
        key = (video_id, user_id)
        if key in self.favorites:
            return

        self.favorites.add(key)
        video = self.videos.get(video_id)
        if video is not None:
            self.videos[video_id] = replace(
                video,
                favorite_count=video.favorite_count + 1,
            )

    def remove_favorite(self, video_id: UUID, user_id: UUID) -> None:
        key = (video_id, user_id)
        if key not in self.favorites:
            return

        self.favorites.remove(key)
        video = self.videos.get(video_id)
        if video is not None:
            self.videos[video_id] = replace(
                video,
                favorite_count=max(video.favorite_count - 1, 0),
            )

    def list_favorites(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        videos = [
            self.videos[video_id]
            for video_id, favorite_user_id in self.favorites
            if favorite_user_id == user_id and video_id in self.videos
        ]
        videos = sorted(videos, key=lambda video: video.created_at, reverse=True)

        return VideoListResult(items=videos[offset : offset + limit], total=len(videos))

    def is_favorite(self, video_id: UUID, user_id: UUID) -> bool:
        return (video_id, user_id) in self.favorites

    def set_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> VideoReaction:
        now = utc_now()
        reaction = self.reactions.get((video_id, user_id, reaction_type))
        if reaction is None:
            reaction = VideoReaction(
                id=make_user().id,
                video_id=video_id,
                user_id=user_id,
                reaction_type=reaction_type,
                created_at=now,
                updated_at=now,
            )
        self.reactions[(video_id, user_id, reaction_type)] = reaction
        return reaction

    def remove_reaction(self, video_id: UUID, user_id: UUID) -> None:
        for key in list(self.reactions):
            reaction_video_id, reaction_user_id, _reaction_type = key
            if reaction_video_id == video_id and reaction_user_id == user_id:
                self.reactions.pop(key, None)

    def count_user_reactions(self, video_id: UUID, user_id: UUID) -> int:
        return sum(
            1
            for reaction_video_id, reaction_user_id, _reaction_type in self.reactions
            if reaction_video_id == video_id and reaction_user_id == user_id
        )

    def has_user_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> bool:
        return (video_id, user_id, reaction_type) in self.reactions

    def get_reaction_counts(self, video_id: UUID) -> dict[str, int]:
        counts: dict[str, int] = {}
        for (reaction_video_id, _user_id, _reaction_type), reaction in self.reactions.items():
            if reaction_video_id != video_id:
                continue
            counts[reaction.reaction_type] = counts.get(reaction.reaction_type, 0) + 1

        return counts


class FakeVideoCategoryRepository:
    def __init__(self, categories: list[VideoCategory] | None = None) -> None:
        self.categories: dict[UUID, VideoCategory] = {}
        self.created: list[VideoCategoryCreate] = []
        self.upserted: list[VideoCategoryCreate] = []

        for category in categories or []:
            self.add(category)

    def add(self, category: VideoCategory) -> VideoCategory:
        self.categories[category.id] = category
        return category

    def list(self) -> list[VideoCategory]:
        return sorted(self.categories.values(), key=lambda category: category.name)

    def get_by_id(self, category_id: UUID) -> VideoCategory | None:
        return self.categories.get(category_id)

    def create(self, category: VideoCategoryCreate) -> VideoCategory:
        self.created.append(category)
        return self.add(
            make_video_category(
                name=category.name,
                source=category.source,
                steam_appid=category.steam_appid,
                steamgriddb_game_id=category.steamgriddb_game_id,
                thumbnail_vertical_url=category.thumbnail_vertical_url,
                thumbnail_horizontal_url=category.thumbnail_horizontal_url,
                thumbnail_vertical_image=category.thumbnail_vertical_image,
                thumbnail_vertical_content_type=category.thumbnail_vertical_content_type,
                thumbnail_horizontal_image=category.thumbnail_horizontal_image,
                thumbnail_horizontal_content_type=category.thumbnail_horizontal_content_type,
            )
        )

    def upsert_steam_category(self, category: VideoCategoryCreate) -> VideoCategory:
        self.upserted.append(category)
        existing = next(
            (
                stored_category
                for stored_category in self.categories.values()
                if (
                    category.steam_appid is not None
                    and stored_category.steam_appid == category.steam_appid
                )
                or (
                    category.steamgriddb_game_id is not None
                    and stored_category.steamgriddb_game_id == category.steamgriddb_game_id
                )
            ),
            None,
        )
        if existing is not None:
            updated = make_video_category(
                id=existing.id,
                name=category.name,
                source=category.source,
                steam_appid=category.steam_appid,
                steamgriddb_game_id=category.steamgriddb_game_id,
                thumbnail_vertical_url=category.thumbnail_vertical_url,
                thumbnail_horizontal_url=category.thumbnail_horizontal_url,
                thumbnail_vertical_image=category.thumbnail_vertical_image,
                thumbnail_vertical_content_type=category.thumbnail_vertical_content_type,
                thumbnail_horizontal_image=category.thumbnail_horizontal_image,
                thumbnail_horizontal_content_type=category.thumbnail_horizontal_content_type,
            )
            self.categories[existing.id] = updated
            return updated

        return self.create(category)

    def update(self, category_id: UUID, category: VideoCategoryCreate) -> VideoCategory | None:
        existing = self.categories.get(category_id)
        if existing is None:
            return None
        updated = make_video_category(
            id=category_id,
            name=category.name,
            source=existing.source,
            steam_appid=existing.steam_appid,
            steamgriddb_game_id=existing.steamgriddb_game_id,
            thumbnail_vertical_url=category.thumbnail_vertical_url,
            thumbnail_horizontal_url=category.thumbnail_horizontal_url,
            thumbnail_vertical_image=category.thumbnail_vertical_image,
            thumbnail_vertical_content_type=category.thumbnail_vertical_content_type,
            thumbnail_horizontal_image=category.thumbnail_horizontal_image,
            thumbnail_horizontal_content_type=category.thumbnail_horizontal_content_type,
        )
        self.categories[category_id] = updated
        return updated

    def delete(self, category_id: UUID) -> bool:
        return self.categories.pop(category_id, None) is not None


class FakeVideoTagRepository:
    def __init__(self, tags: list[VideoTag] | None = None) -> None:
        self.tags: dict[UUID, VideoTag] = {}
        self.created: list[VideoTagCreate] = []

        for tag in tags or []:
            self.add(tag)

    def add(self, tag: VideoTag) -> VideoTag:
        self.tags[tag.id] = tag
        return tag

    def list(self) -> list[VideoTag]:
        return sorted(self.tags.values(), key=lambda tag: tag.name)

    def create(self, tag: VideoTagCreate) -> VideoTag:
        self.created.append(tag)
        existing = next(
            (stored_tag for stored_tag in self.tags.values() if stored_tag.name == tag.name),
            None,
        )
        if existing is not None:
            return existing

        return self.add(make_video_tag(name=tag.name))


class FakeVideoStorage:
    def __init__(
        self,
        error: Exception | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self.error = error
        self.delete_error = delete_error
        self.saved: list[dict] = []
        self.deleted: list[UUID] = []
        self.deleted_all: list[UUID] = []
        self.deleted_processing_outputs: list[UUID] = []
        self.original_paths: dict[UUID, Path] = {}
        self.variant_paths: dict[tuple[UUID, str], Path] = {}
        self.thumbnail_paths: dict[UUID, Path] = {}

    def save_original(
        self,
        *,
        video_id: UUID,
        original_filename: str,
        content_type: str | None,
        file,
    ) -> None:
        if self.error is not None:
            raise self.error

        self.saved.append(
            {
                "video_id": video_id,
                "original_filename": original_filename,
                "content_type": content_type,
                "content": file.read(),
            }
        )

    def delete_original(self, video_id: UUID) -> None:
        self.deleted.append(video_id)

    def delete_video_files(self, video_id: UUID) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_all.append(video_id)

    def delete_processing_outputs(self, video_id: UUID) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_processing_outputs.append(video_id)

    def get_original_path(self, video_id: UUID) -> Path | None:
        return self.original_paths.get(video_id)

    def get_variant_path(self, video_id: UUID, variant_type) -> Path | None:
        return self.variant_paths.get((video_id, variant_type.value))

    def get_thumbnail_path(self, video_id: UUID) -> Path | None:
        return self.thumbnail_paths.get(video_id)


class FakeVideoTranscoder:
    def __init__(self, result: VideoProcessingResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.transcoded: list[UUID] = []

    def transcode(self, video_id: UUID) -> VideoProcessingResult:
        self.transcoded.append(video_id)
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result

        from app.modules.videos.domain.video import (
            VideoAspectRatio,
            VideoVariantCreate,
            VideoVariantType,
        )

        return VideoProcessingResult(
            width=1920,
            height=1080,
            aspect_ratio=VideoAspectRatio.RATIO_16_9,
            duration_seconds=12.5,
            source_created_at=None,
            thumbnail_path=f"thumbnails/{video_id}/thumbnail.jpg",
            variants=[
                VideoVariantCreate(
                    variant_type=VideoVariantType.LOW_H264,
                    codec="h264",
                    container="mp4",
                    width=1280,
                    height=720,
                    bitrate_kbps=None,
                    size_bytes=1024,
                    path=f"variants/{video_id}/low_h264.mp4",
                ),
            ],
        )


class FakeVideoProcessingQueue:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.enqueued: list[UUID] = []
        self.force_flags: list[bool] = []

    def enqueue(self, video_id: UUID, *, force: bool = False) -> None:
        if self.error is not None:
            raise self.error
        self.force_flags.append(force)
        self.enqueued.append(video_id)


@dataclass
class FakeIdempotencyRecord:
    scope: str
    user_id: str
    key: str
    request_hash: str
    status: str
    response_status_code: int | None = None
    response_body: dict | None = None
    error_message: str | None = None


class FakeIdempotencyRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], FakeIdempotencyRecord] = {}

    def get(
        self,
        *,
        scope: str,
        user_id: str,
        key: str,
    ) -> FakeIdempotencyRecord | None:
        return self.records.get((scope, user_id, key))

    def start(
        self,
        *,
        scope: str,
        user_id: str,
        key: str,
        request_hash: str,
    ) -> tuple[FakeIdempotencyRecord, bool]:
        existing_record = self.get(scope=scope, user_id=user_id, key=key)
        if existing_record is not None:
            return existing_record, False

        record = FakeIdempotencyRecord(
            scope=scope,
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            status="processing",
        )
        self.records[(scope, user_id, key)] = record
        return record, True

    def complete(
        self,
        record: FakeIdempotencyRecord,
        *,
        response_status_code: int,
        response_body: dict,
    ) -> None:
        record.status = "completed"
        record.response_status_code = response_status_code
        record.response_body = response_body
        record.error_message = None

    def fail(self, record: FakeIdempotencyRecord, error_message: str) -> None:
        record.status = "failed"
        record.error_message = error_message

    def delete(self, record: FakeIdempotencyRecord) -> None:
        self.records.pop((record.scope, record.user_id, record.key), None)


class FakePasswordHasher:
    def __init__(self) -> None:
        self.hashed_passwords: list[str] = []
        self.verified_passwords: list[tuple[str, str]] = []

    def hash_password(self, plain_password: str) -> str:
        self.hashed_passwords.append(plain_password)
        return f"hashed:{plain_password}"

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        self.verified_passwords.append((plain_password, password_hash))
        return password_hash == f"hashed:{plain_password}"


class FakeAccessTokenService:
    def __init__(self, token: str = "fake-access-token") -> None:
        self.token = token
        self.users: list[User] = []

    def create_access_token(self, user: User) -> str:
        self.users.append(user)
        return self.token


class FakeSteamClient:
    def __init__(
        self,
        *,
        profiles: dict[str, dict] | None = None,
        owned_games: dict[str, dict] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.profiles = profiles or {}
        self.owned_games = owned_games or {}
        self.errors = errors or {}
        self.player_summary_requests: list[str] = []
        self.owned_games_requests: list[tuple[str, bool, str]] = []

    def get_player_summary(self, steam_id_or_vanity: str) -> dict:
        self.player_summary_requests.append(steam_id_or_vanity)
        error = self.errors.get(steam_id_or_vanity)
        if error is not None:
            raise error

        profile = self.profiles.get(steam_id_or_vanity)
        if profile is None:
            raise SteamApiError("Steam user not found", status_code=404)

        return profile

    def get_owned_games(
        self,
        steam_id_or_vanity: str,
        include_played_free_games: bool = True,
        language: str = "english",
    ) -> dict:
        self.owned_games_requests.append(
            (steam_id_or_vanity, include_played_free_games, language)
        )
        error = self.errors.get(steam_id_or_vanity)
        if error is not None:
            raise error

        return self.owned_games.get(
            steam_id_or_vanity,
            {"steamid": steam_id_or_vanity, "game_count": 0, "games": []},
        )


class FakeSteamGridDbClient:
    def __init__(
        self,
        *,
        games_by_search: dict[str, list[dict]] | None = None,
        games_by_appid: dict[int, dict] | None = None,
        games_by_id: dict[int, dict] | None = None,
        grids_by_game_dimensions: dict[tuple[int, str], list[dict]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.games_by_search = games_by_search or {}
        self.games_by_appid = games_by_appid or {}
        self.games_by_id = games_by_id or {}
        self.grids_by_game_dimensions = grids_by_game_dimensions or {}
        self.error = error
        self.search_requests: list[str] = []
        self.appid_requests: list[int] = []
        self.game_id_requests: list[int] = []
        self.grid_requests: list[tuple[int, str, int]] = []

    def search_games(self, term: str) -> list[dict]:
        if self.error is not None:
            raise self.error
        self.search_requests.append(term)
        return self.games_by_search.get(term, [])

    def get_game_by_steam_appid(self, appid: int) -> dict:
        if self.error is not None:
            raise self.error
        self.appid_requests.append(appid)
        return self.games_by_appid.get(appid, {})

    def get_game_by_id(self, game_id: int) -> dict:
        if self.error is not None:
            raise self.error
        self.game_id_requests.append(game_id)
        return self.games_by_id.get(game_id, {})

    def get_grids(
        self,
        game_id: int,
        *,
        dimensions: str,
        limit: int = 1,
        page: int | None = None,
    ) -> list[dict]:
        if self.error is not None:
            raise self.error
        self.grid_requests.append((game_id, dimensions, limit, page))
        return self.grids_by_game_dimensions.get((game_id, dimensions), [])
