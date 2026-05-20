import json
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from config.settings import settings


class SteamApiConfigurationError(Exception):
    pass


class SteamApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SteamClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.api_key = api_key or settings.steam_web_api_key
        self.base_url = (base_url or settings.steam_web_api_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_player_summary(self, steam_id_or_vanity: str) -> dict:
        steam_id = self.resolve_steam_id(steam_id_or_vanity)
        players = self.get_player_summaries([steam_id])

        if not players:
            raise SteamApiError("Steam user not found", status_code=404)

        return players[0]

    def get_player_summaries(self, steam_ids: Sequence[str]) -> list[dict]:
        if not steam_ids:
            return []
        if len(steam_ids) > 100:
            raise ValueError("Steam GetPlayerSummaries accepts at most 100 SteamIDs")

        data = self._get(
            "/ISteamUser/GetPlayerSummaries/v2/",
            {"steamids": ",".join(steam_ids)},
        )

        return data.get("response", {}).get("players", [])

    def resolve_steam_id(self, steam_id_or_vanity: str) -> str:
        steam_identifier = self._normalize_steam_identifier(steam_id_or_vanity)
        if steam_identifier.isdigit():
            return steam_identifier

        data = self._get(
            "/ISteamUser/ResolveVanityURL/v1/",
            {"vanityurl": steam_identifier, "url_type": 1},
        )
        response = data.get("response", {})

        if response.get("success") != 1 or "steamid" not in response:
            raise SteamApiError("Steam vanity URL not found", status_code=404)

        return response["steamid"]

    def get_owned_games(
        self,
        steam_id_or_vanity: str,
        include_played_free_games: bool = True,
        language: str = "english",
    ) -> dict:
        steam_id = self.resolve_steam_id(steam_id_or_vanity)
        data = self._get(
            "/IPlayerService/GetOwnedGames/v1/",
            {
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": int(include_played_free_games),
                "language": language,
            },
        )
        response = data.get("response", {})
        games = [self._with_game_image_urls(game) for game in response.get("games", [])]

        return {
            "steamid": steam_id,
            "game_count": response.get("game_count", len(games)),
            "games": games,
        }

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            raise SteamApiConfigurationError("STEAM_WEB_API_KEY is not configured")

        query = urlencode({"key": self.api_key, "format": "json", **params})
        request = Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "SpiderShare Steam Integration",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise SteamApiError(
                f"Steam API returned HTTP {error.code}",
                status_code=error.code,
            ) from error
        except URLError as error:
            raise SteamApiError(f"Could not reach Steam API: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise SteamApiError("Steam API returned invalid JSON") from error

    def _normalize_steam_identifier(self, steam_id_or_vanity: str) -> str:
        value = steam_id_or_vanity.strip()
        parsed_url = urlparse(value)

        if not parsed_url.scheme or not parsed_url.netloc:
            return value.strip("/")

        path_parts = [unquote(part) for part in parsed_url.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"id", "profiles"}:
            return path_parts[1]

        return value.strip("/")

    def _with_game_image_urls(self, game: dict) -> dict:
        appid = game.get("appid")
        icon_hash = game.get("img_icon_url")

        return {
            **game,
            "icon_url": self._community_app_image_url(appid, icon_hash),
            "header_image_url": (
                f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
                if appid is not None
                else None
            ),
            "capsule_image_url": (
                f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/capsule_184x69.jpg"
                if appid is not None
                else None
            ),
        }

    def _community_app_image_url(
        self,
        appid: int | None,
        image_hash: str | None,
    ) -> str | None:
        if appid is None or not image_hash:
            return None

        return (
            "https://media.steampowered.com/steamcommunity/public/images/apps/"
            f"{appid}/{image_hash}.jpg"
        )
