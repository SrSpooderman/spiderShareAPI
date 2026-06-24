import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.wiring import require_admin
from app.modules.steam.wiring import get_steamgriddb_client
from app.modules.users.domain.user import User
from app.modules.videos.domain.ports import VideoCategoryRepository
from app.modules.videos.domain.video import VideoCategoryCreate, VideoCategorySource
from app.modules.videos.entrypoints.schemas import (
    SteamGridDbGameResponse,
    SteamVideoCategoryImportRequest,
    VideoCategoryCreateRequest,
    VideoCategoryResponse,
)
from app.modules.videos.wiring import get_video_category_repository
from app.shared.infrastructure.providers.steam.steamgriddb_client import (
    SteamGridDbClient,
    SteamGridDbConfigurationError,
    SteamGridDbError,
)


router = APIRouter(prefix="/category", tags=["category"])
logger = logging.getLogger(__name__)
VERTICAL_GRID_DIMENSIONS = "600x900"
HORIZONTAL_GRID_DIMENSIONS = "920x430"


def _map_steamgriddb_error(error: Exception) -> HTTPException:
    if isinstance(error, SteamGridDbConfigurationError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))
    if isinstance(error, SteamGridDbError):
        return HTTPException(
            status_code=error.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )
    raise error


def _best_grid_url(grids: list[dict]) -> str | None:
    if not grids:
        return None
    return grids[0].get("url") or grids[0].get("thumb")


def _game_response(game: dict) -> SteamGridDbGameResponse | None:
    if game.get("id") is None or not game.get("name"):
        return None
    return SteamGridDbGameResponse(
        id=game["id"],
        name=game["name"],
        types=game.get("types") or [],
        verified=game.get("verified"),
    )


@router.get("", response_model=list[VideoCategoryResponse])
def list_video_categories(
    repository: VideoCategoryRepository = Depends(get_video_category_repository),
) -> list[VideoCategoryResponse]:
    return [VideoCategoryResponse.from_domain(category) for category in repository.list()]


@router.post("", response_model=VideoCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_custom_video_category(
    request: VideoCategoryCreateRequest,
    current_user: User = Depends(require_admin),
    repository: VideoCategoryRepository = Depends(get_video_category_repository),
) -> VideoCategoryResponse:
    category = repository.create(
        VideoCategoryCreate(
            name=request.name,
            source=VideoCategorySource.CUSTOM,
            thumbnail_vertical_url=request.thumbnail_vertical_url,
            thumbnail_horizontal_url=request.thumbnail_horizontal_url,
        )
    )
    logger.info("Video category created category_id=%s source=%s requested_by=%s", category.id, category.source.value, current_user.id)
    return VideoCategoryResponse.from_domain(category)


@router.get("/steam/search", response_model=list[SteamGridDbGameResponse])
def search_steam_video_categories(
    term: str = Query(min_length=1, max_length=100),
    _current_user: User = Depends(require_admin),
    client: SteamGridDbClient = Depends(get_steamgriddb_client),
) -> list[SteamGridDbGameResponse]:
    try:
        games = client.search_games(term)
    except (SteamGridDbConfigurationError, SteamGridDbError) as error:
        raise _map_steamgriddb_error(error)
    return [response for game in games if (response := _game_response(game)) is not None]


@router.post("/steam/import", response_model=VideoCategoryResponse, status_code=status.HTTP_201_CREATED)
def import_steam_video_category(
    request: SteamVideoCategoryImportRequest,
    current_user: User = Depends(require_admin),
    repository: VideoCategoryRepository = Depends(get_video_category_repository),
    client: SteamGridDbClient = Depends(get_steamgriddb_client),
) -> VideoCategoryResponse:
    try:
        game = (
            client.get_game_by_steam_appid(request.steam_appid)
            if request.steam_appid is not None
            else client.get_game_by_id(request.steamgriddb_game_id)
        )
        game_id, name = game.get("id"), game.get("name")
        if game_id is None or not name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SteamGridDB game not found")
        vertical_url = _best_grid_url(client.get_grids(game_id, dimensions=VERTICAL_GRID_DIMENSIONS))
        horizontal_url = _best_grid_url(client.get_grids(game_id, dimensions=HORIZONTAL_GRID_DIMENSIONS))
    except HTTPException:
        raise
    except (SteamGridDbConfigurationError, SteamGridDbError) as error:
        raise _map_steamgriddb_error(error)

    category = repository.upsert_steam_category(
        VideoCategoryCreate(
            name=name.strip(), source=VideoCategorySource.STEAM,
            steam_appid=request.steam_appid, steamgriddb_game_id=game_id,
            thumbnail_vertical_url=vertical_url, thumbnail_horizontal_url=horizontal_url,
        )
    )
    logger.info("Steam video category imported category_id=%s steam_appid=%s steamgriddb_game_id=%s requested_by=%s has_vertical=%s has_horizontal=%s", category.id, category.steam_appid, category.steamgriddb_game_id, current_user.id, category.thumbnail_vertical_url is not None, category.thumbnail_horizontal_url is not None)
    return VideoCategoryResponse.from_domain(category)
