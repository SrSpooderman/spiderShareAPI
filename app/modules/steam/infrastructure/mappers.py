from uuid import UUID

from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate
from app.modules.steam.infrastructure.models import SteamGameModel


def steam_game_model_to_domain(model: SteamGameModel) -> SteamGame:
    return SteamGame(
        id=UUID(model.id),
        appid=model.appid,
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def steam_game_create_to_model(steam_game: SteamGameCreate) -> SteamGameModel:
    return SteamGameModel(
        appid=steam_game.appid,
        name=steam_game.name,
    )
