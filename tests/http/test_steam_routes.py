import pytest

from app.modules.auth.wiring import get_current_user
from app.modules.steam.application.store_steam_game import StoreSteamGame
from app.modules.steam.wiring import (
    get_steam_client,
    get_store_steam_game,
)
from app.shared.infrastructure.providers.steam.steam_client import SteamApiError
from tests.fakes import FakeSteamClient


@pytest.mark.http
def test_get_public_steam_user_games_returns_games_and_stores_valid_ones(
    app,
    client,
    user_factory,
    steam_game_repository,
) -> None:
    current_user = user_factory(username="alice")
    steam_client = FakeSteamClient(
        owned_games={
            "alice": {
                "steamid": "76561198000000000",
                "game_count": 3,
                "games": [
                    {"appid": 10, "name": "Counter-Strike"},
                    {"appid": 20},
                    {"name": "Missing appid"},
                ],
            }
        }
    )
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_steam_client] = lambda: steam_client
    app.dependency_overrides[get_store_steam_game] = lambda: StoreSteamGame(
        steam_game_repository
    )

    response = client.get("/steam/users/alice/games?language=spanish")

    assert response.status_code == 200
    assert response.json()["steamid"] == "76561198000000000"
    assert response.json()["game_count"] == 3
    assert steam_client.owned_games_requests == [("alice", True, "spanish")]
    assert steam_game_repository.upserted == [(10, "Counter-Strike")]


@pytest.mark.http
def test_get_public_steam_user_games_maps_steam_api_error_status(
    app,
    client,
    user_factory,
) -> None:
    current_user = user_factory(username="alice")
    steam_client = FakeSteamClient(
        errors={"alice": SteamApiError("Private profile", status_code=403)}
    )
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_steam_client] = lambda: steam_client
    app.dependency_overrides[get_store_steam_game] = lambda: StoreSteamGame(
        steam_game_repository=None
    )

    response = client.get("/steam/users/alice/games")

    assert response.status_code == 403
    assert response.json()["detail"] == "Private profile"
