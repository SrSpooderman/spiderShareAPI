from pydantic import BaseModel


class SteamOwnedGameResponse(BaseModel):
    appid: int
    name: str | None = None
    playtime_forever: int | None = None
    playtime_2weeks: int | None = None
    img_icon_url: str | None = None
    icon_url: str | None = None
    header_image_url: str | None = None
    capsule_image_url: str | None = None


class SteamOwnedGamesResponse(BaseModel):
    steamid: str
    game_count: int
    games: list[SteamOwnedGameResponse]
