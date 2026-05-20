import pytest

from app.modules.steam.application.store_steam_game import (
    InvalidSteamGameError,
    StoreSteamGame,
    StoreSteamGameCommand,
)


@pytest.mark.unit
def test_store_steam_game_converts_appid_and_strips_name(
    steam_game_repository,
) -> None:
    store_steam_game = StoreSteamGame(steam_game_repository)

    result = store_steam_game.execute(
        StoreSteamGameCommand(appid="10", name="  Counter-Strike  ")
    )

    assert result.appid == 10
    assert result.name == "Counter-Strike"
    assert steam_game_repository.upserted == [(10, "Counter-Strike")]


@pytest.mark.unit
@pytest.mark.parametrize("invalid_appid", ["abc", None])
def test_store_steam_game_rejects_non_integer_appid(
    invalid_appid,
    steam_game_repository,
) -> None:
    store_steam_game = StoreSteamGame(steam_game_repository)

    with pytest.raises(InvalidSteamGameError):
        store_steam_game.execute(
            StoreSteamGameCommand(appid=invalid_appid, name="Counter-Strike")
        )

    assert steam_game_repository.upserted == []


@pytest.mark.unit
@pytest.mark.parametrize("invalid_appid", [0, -1])
def test_store_steam_game_rejects_non_positive_appid(
    invalid_appid: int,
    steam_game_repository,
) -> None:
    store_steam_game = StoreSteamGame(steam_game_repository)

    with pytest.raises(InvalidSteamGameError):
        store_steam_game.execute(
            StoreSteamGameCommand(appid=invalid_appid, name="Counter-Strike")
        )

    assert steam_game_repository.upserted == []


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   "])
def test_store_steam_game_rejects_blank_name(
    invalid_name: str,
    steam_game_repository,
) -> None:
    store_steam_game = StoreSteamGame(steam_game_repository)

    with pytest.raises(InvalidSteamGameError):
        store_steam_game.execute(StoreSteamGameCommand(appid=10, name=invalid_name))

    assert steam_game_repository.upserted == []
