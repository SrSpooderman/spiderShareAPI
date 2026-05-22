from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate
from app.modules.users.domain.user import User, UserCreate, UserRole
from app.modules.videos.domain.ports import VideoListFilters, VideoListResult
from app.modules.videos.domain.video import Video, VideoCreate, VideoReaction
from app.shared.infrastructure.providers.steam.steam_client import SteamApiError
from tests.factories import make_steam_game, make_user, make_video, utc_now


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

    def list(self) -> list[User]:
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
        self.favorites: set[tuple[UUID, UUID]] = set()
        self.reactions: dict[tuple[UUID, UUID], VideoReaction] = {}

        for video in videos or []:
            self.add(video)

    def add(self, video: Video) -> Video:
        self.videos[video.id] = video
        return video

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
        if filters.tags:
            tag_names = {tag.strip() for tag in filters.tags if tag.strip()}
            videos = [
                video
                for video in videos
                if tag_names & {tag.name for tag in video.tags}
            ]

        videos = sorted(
            videos,
            key=lambda video: (video.favorite_count, video.created_at),
            reverse=True,
        )

        return VideoListResult(items=videos[offset : offset + limit], total=len(videos))

    def create(self, video: VideoCreate) -> Video:
        self.created.append(video)
        return self.add(
            make_video(
                owner_id=video.owner_id,
                title=video.title,
                description=video.description,
                original_filename=video.original_filename,
                is_registered_only=video.is_registered_only,
            )
        )

    def update_metadata(
        self,
        video_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        is_registered_only: bool | None = None,
        category_ids: list[UUID] | None = None,
        tags: list[str] | None = None,
    ) -> Video | None:
        video = self.videos.get(video_id)
        if video is None:
            return None

        changes = {
            "title": title,
            "description": description,
            "is_registered_only": is_registered_only,
            "category_ids": category_ids,
            "tags": tags,
        }
        self.updated.append((video_id, changes))

        edited_at = utc_now()
        updated_video = replace(
            video,
            title=title if title is not None else video.title,
            description=description if description is not None else video.description,
            is_registered_only=(
                is_registered_only
                if is_registered_only is not None
                else video.is_registered_only
            ),
            edited=True,
            edited_at=edited_at,
            updated_at=edited_at,
        )
        self.videos[video_id] = updated_video

        return updated_video

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
        reaction = self.reactions.get((video_id, user_id))
        if reaction is None:
            reaction = VideoReaction(
                id=make_user().id,
                video_id=video_id,
                user_id=user_id,
                reaction_type=reaction_type,
                created_at=now,
                updated_at=now,
            )
        else:
            reaction = replace(reaction, reaction_type=reaction_type, updated_at=now)

        self.reactions[(video_id, user_id)] = reaction
        return reaction

    def remove_reaction(self, video_id: UUID, user_id: UUID) -> None:
        self.reactions.pop((video_id, user_id), None)

    def get_reaction_counts(self, video_id: UUID) -> dict[str, int]:
        counts: dict[str, int] = {}
        for (reaction_video_id, _user_id), reaction in self.reactions.items():
            if reaction_video_id != video_id:
                continue
            counts[reaction.reaction_type] = counts.get(reaction.reaction_type, 0) + 1

        return counts


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
