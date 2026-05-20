from abc import ABC, abstractmethod

from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate


class SteamGameRepository(ABC):
    @abstractmethod
    def get_by_appid(self, appid: int) -> SteamGame | None:
        pass

    @abstractmethod
    def create(self, steam_game: SteamGameCreate) -> SteamGame:
        pass

    @abstractmethod
    def upsert_by_appid(self, appid: int, name: str) -> SteamGame:
        pass
