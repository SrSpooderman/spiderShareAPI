from dataclasses import dataclass

from app.modules.steam.domain.ports import SteamGameRepository
from app.modules.steam.domain.steam_game import SteamGame


class InvalidSteamGameError(Exception):
    pass


@dataclass(frozen=True)
class StoreSteamGameCommand:
    appid: int
    name: str


class StoreSteamGame:
    def __init__(self, steam_game_repository: SteamGameRepository) -> None:
        self.steam_game_repository = steam_game_repository

    def execute(self, command: StoreSteamGameCommand) -> SteamGame:
        try:
            appid = int(command.appid)
        except (TypeError, ValueError):
            raise InvalidSteamGameError

        name = command.name.strip()

        if appid <= 0 or not name:
            raise InvalidSteamGameError

        return self.steam_game_repository.upsert_by_appid(appid, name)
