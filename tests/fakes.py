from uuid import UUID

from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate
from app.modules.users.domain.user import User, UserCreate, UserRole
from app.shared.infrastructure.providers.steam.steam_client import SteamApiError
from tests.factories import make_steam_game, make_user


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
