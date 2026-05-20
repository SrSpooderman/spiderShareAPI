from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.steam.domain.ports import SteamGameRepository
from app.modules.steam.domain.steam_game import SteamGame, SteamGameCreate
from app.modules.steam.infrastructure.mappers import (
    steam_game_create_to_model,
    steam_game_model_to_domain,
)
from app.modules.steam.infrastructure.models import SteamGameModel


class SqlAlchemySteamGameRepository(SteamGameRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_appid(self, appid: int) -> SteamGame | None:
        statement = select(SteamGameModel).where(SteamGameModel.appid == appid)
        model = self.session.scalar(statement)

        if model is None:
            return None

        return steam_game_model_to_domain(model)

    def create(self, steam_game: SteamGameCreate) -> SteamGame:
        model = steam_game_create_to_model(steam_game)

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)

        return steam_game_model_to_domain(model)

    def upsert_by_appid(self, appid: int, name: str) -> SteamGame:
        statement = select(SteamGameModel).where(SteamGameModel.appid == appid)
        model = self.session.scalar(statement)

        if model is None:
            return self.create(SteamGameCreate(appid=appid, name=name))

        model.name = name
        self.session.commit()
        self.session.refresh(model)

        return steam_game_model_to_domain(model)
