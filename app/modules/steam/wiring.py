from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.steam.application.store_steam_game import StoreSteamGame
from app.modules.steam.domain.ports import SteamGameRepository
from app.modules.steam.infrastructure.repository import SqlAlchemySteamGameRepository
from app.shared.infrastructure.db.session import get_db
from app.shared.infrastructure.providers.steam.steam_client import SteamClient
from app.shared.infrastructure.providers.steam.steamgriddb_client import SteamGridDbClient


def get_steam_client() -> SteamClient:
    return SteamClient()


def get_steamgriddb_client() -> SteamGridDbClient:
    return SteamGridDbClient()


def get_steam_game_repository(
    db: Session = Depends(get_db),
) -> SteamGameRepository:
    return SqlAlchemySteamGameRepository(db)


def get_store_steam_game(
    steam_game_repository: SteamGameRepository = Depends(get_steam_game_repository),
) -> StoreSteamGame:
    return StoreSteamGame(steam_game_repository)
