from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.wiring import get_current_user
from app.modules.steam.application.store_steam_game import (
    InvalidSteamGameError,
    StoreSteamGame,
    StoreSteamGameCommand,
)
from app.modules.steam.entrypoints.schemas import (
    SteamOwnedGamesResponse,
)
from app.modules.steam.wiring import (
    get_store_steam_game,
    get_steam_client,
)
from app.modules.users.domain.user import User
from app.shared.infrastructure.providers.steam.steam_client import (
    SteamApiConfigurationError,
    SteamApiError,
    SteamClient,
)


router = APIRouter(prefix="/steam", tags=["steam"])


@router.get(
    "/users/{steam_id_or_vanity}/games",
    response_model=SteamOwnedGamesResponse,
)
def get_public_steam_user_games(
    steam_id_or_vanity: str,
    include_played_free_games: bool = Query(default=True),
    language: str = Query(default="english"),
    _current_user: User = Depends(get_current_user),
    steam_client: SteamClient = Depends(get_steam_client),
    store_steam_game: StoreSteamGame = Depends(get_store_steam_game),
) -> SteamOwnedGamesResponse:
    try:
        owned_games = steam_client.get_owned_games(
            steam_id_or_vanity,
            include_played_free_games=include_played_free_games,
            language=language,
        )
    except SteamApiConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )
    except SteamApiError as error:
        raise HTTPException(
            status_code=error.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )

    valid_games = []
    for game in owned_games["games"]:
        name = game.get("name")
        appid = game.get("appid")

        if appid is None:
            continue

        valid_games.append(game)

        if name is None:
            continue

        try:
            store_steam_game.execute(StoreSteamGameCommand(appid=appid, name=name))
        except InvalidSteamGameError:
            continue

    owned_games = {**owned_games, "games": valid_games}

    return SteamOwnedGamesResponse.model_validate(owned_games)

