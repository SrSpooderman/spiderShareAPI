from uuid import uuid4

import pytest

from app.modules.steam.domain.steam_game import SteamGameCreate
from app.modules.steam.infrastructure.mappers import (
    steam_game_create_to_model,
    steam_game_model_to_domain,
)
from app.modules.steam.infrastructure.models import SteamGameModel
from tests.factories import utc_now


@pytest.mark.unit
def test_steam_game_create_to_model_preserves_game_fields() -> None:
    steam_game_create = SteamGameCreate(appid=10, name="Counter-Strike")

    model = steam_game_create_to_model(steam_game_create)

    assert model.appid == 10
    assert model.name == "Counter-Strike"


@pytest.mark.unit
def test_steam_game_model_to_domain_preserves_game_fields() -> None:
    game_id = uuid4()
    created_at = utc_now()
    updated_at = utc_now()
    model = SteamGameModel(
        id=str(game_id),
        appid=10,
        name="Counter-Strike",
        created_at=created_at,
        updated_at=updated_at,
    )

    steam_game = steam_game_model_to_domain(model)

    assert steam_game.id == game_id
    assert steam_game.appid == 10
    assert steam_game.name == "Counter-Strike"
    assert steam_game.created_at == created_at
    assert steam_game.updated_at == updated_at
