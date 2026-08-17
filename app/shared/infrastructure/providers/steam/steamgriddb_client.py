import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config.settings import settings


class SteamGridDbConfigurationError(Exception):
    pass


class SteamGridDbError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SteamGridDbClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.api_key = api_key or settings.steamgriddb_api_key
        self.base_url = (base_url or settings.steamgriddb_api_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_games(self, term: str) -> list[dict]:
        data = self._get(f"/search/autocomplete/{quote(term.strip())}", {})
        return data.get("data", [])

    def get_game_by_steam_appid(self, appid: int) -> dict:
        data = self._get(f"/games/steam/{appid}", {})
        return data.get("data", {})

    def get_game_by_id(self, game_id: int) -> dict:
        data = self._get(f"/games/id/{game_id}", {})
        return data.get("data", {})

    def get_grids(
        self,
        game_id: int,
        *,
        dimensions: str,
        limit: int = 1,
        page: int | None = None,
    ) -> list[dict]:
        params = {
            "dimensions": dimensions,
            "types": "static",
            "nsfw": "false",
            "humor": "false",
            "epilepsy": "false",
            "limit": limit,
        }
        if page is not None:
            params["page"] = page

        data = self._get(
            f"/grids/game/{game_id}",
            params,
        )
        return data.get("data", [])

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            raise SteamGridDbConfigurationError("STEAMGRIDDB_API_KEY is not configured")

        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{self.base_url}{path}{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SpiderShare SteamGridDB Integration",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise SteamGridDbError(
                f"SteamGridDB API returned HTTP {error.code}",
                status_code=error.code,
            ) from error
        except URLError as error:
            raise SteamGridDbError(
                f"Could not reach SteamGridDB API: {error.reason}"
            ) from error
        except json.JSONDecodeError as error:
            raise SteamGridDbError("SteamGridDB API returned invalid JSON") from error
