import hashlib
import json
import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse

from app.modules.auth.wiring import (
    get_current_user,
    get_optional_current_user,
    require_admin,
    require_super_admin,
)
from app.modules.users.domain.user import User
from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.errors import (
    VideoDurationTooLongError,
    VideoFileEmptyError,
    VideoFileTooLargeError,
    VideoNotFoundError,
    VideoPermissionError,
    VideoReactionLimitError,
    VideoUnsupportedMimeTypeError,
    VideoUploadError,
)
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.get_video import GetVideo
from app.modules.videos.application.list_videos import ListVideos, ListVideosQuery
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.upload_video import UploadVideo, UploadVideoCommand
from app.modules.videos.application.update_video import UpdateVideo, UpdateVideoCommand
from app.modules.videos.domain.ports import (
    VideoCategoryRepository,
    VideoProcessingQueue,
    VideoRepository,
    VideoStorage,
)
from app.modules.videos.domain.video import (
    VideoCategoryCreate,
    VideoCategorySource,
    VideoOwner,
    VideoProcessingStatus,
    VideoVariantType,
)
from app.modules.videos.entrypoints.schemas import (
    SteamGridDbGameResponse,
    SteamVideoCategoryImportRequest,
    VideoCategoryCreateRequest,
    VideoCategoryResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoReactionCountResponse,
    VideoReactionRequest,
    VideoReactionResponse,
    VideoUpdateRequest,
)
from app.modules.videos.wiring import (
    get_delete_video,
    get_favorite_video,
    get_get_video,
    get_list_videos,
    get_react_to_video,
    get_upload_video,
    get_update_video,
    get_video_category_repository,
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)
from app.modules.steam.wiring import get_steamgriddb_client
from app.shared.infrastructure.idempotency import IdempotencyRepository
from app.shared.infrastructure.providers.steam.steamgriddb_client import (
    SteamGridDbClient,
    SteamGridDbConfigurationError,
    SteamGridDbError,
)
from app.shared.wiring import get_idempotency_repository
from config.settings import settings


router = APIRouter(tags=["videos"])
logger = logging.getLogger(__name__)
VIDEO_UPLOAD_IDEMPOTENCY_SCOPE = "videos.upload"
STEAMGRIDDB_VERTICAL_GRID_DIMENSIONS = "600x900"
STEAMGRIDDB_HORIZONTAL_GRID_DIMENSIONS = "920x430"


def _fields_set(request: VideoUpdateRequest) -> set[str]:
    fields_set = getattr(request, "model_fields_set", None)
    if fields_set is not None:
        return fields_set

    return getattr(request, "__fields_set__", set())


def _map_video_error(error: Exception) -> HTTPException:
    if isinstance(error, VideoNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    if isinstance(error, VideoPermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access that video",
        )
    if isinstance(error, VideoReactionLimitError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A user can only react "
                f"{settings.max_video_reactions_per_user} times to the same video"
            ),
        )

    raise error


def _map_video_upload_error(error: VideoUploadError) -> HTTPException:
    if isinstance(error, VideoFileTooLargeError):
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Video file is too large",
        )
    if isinstance(error, VideoDurationTooLongError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video duration is too long",
        )
    if isinstance(error, VideoUnsupportedMimeTypeError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video must be mp4 or webm",
        )
    if isinstance(error, VideoFileEmptyError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video file cannot be empty",
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Video upload failed",
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized_tags = [tag.strip() for tag in tags if tag.strip()]
    if len(normalized_tags) > settings.max_video_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Too many tags",
        )

    return normalized_tags


def _normalize_required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} cannot be blank",
        )

    return text


def _normalize_optional_text(value: str | None) -> str:
    if value is None:
        return ""

    return value.strip()


def _map_steamgriddb_error(error: Exception) -> HTTPException:
    if isinstance(error, SteamGridDbConfigurationError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )
    if isinstance(error, SteamGridDbError):
        return HTTPException(
            status_code=error.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )

    raise error


def _best_grid_url(grids: list[dict]) -> str | None:
    if not grids:
        return None

    grid = grids[0]
    return grid.get("url") or grid.get("thumb")


def _steamgriddb_game_to_response(game: dict) -> SteamGridDbGameResponse | None:
    game_id = game.get("id")
    name = game.get("name")
    if game_id is None or not name:
        return None

    return SteamGridDbGameResponse(
        id=game_id,
        name=name,
        types=game.get("types") or [],
        verified=game.get("verified"),
    )


def _ensure_file_exists(path) -> None:
    if path is None or not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found",
        )


async def _video_upload_request_hash(
    *,
    file: UploadFile,
    title: str,
    description: str,
    is_registered_only: bool,
    category_ids: list[UUID],
    tags: list[str],
) -> str:
    digest = hashlib.sha256()
    metadata = {
        "title": title,
        "description": description,
        "is_registered_only": is_registered_only,
        "category_ids": sorted(str(category_id) for category_id in category_ids),
        "tags": sorted(tags),
        "filename": file.filename or "video",
        "content_type": file.content_type,
    }
    digest.update(json.dumps(metadata, sort_keys=True).encode("utf-8"))

    await file.seek(0)
    while chunk := await file.read(1024 * 1024):
        digest.update(chunk)
    await file.seek(0)
    return digest.hexdigest()


def _get_or_start_idempotency_record(
    *,
    idempotency_key: str | None,
    request_hash: str,
    current_user: User,
    idempotency_repository: IdempotencyRepository,
):
    if idempotency_key is None:
        return None

    normalized_key = idempotency_key.strip()
    key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()[:12]
    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key cannot be blank",
        )

    record = idempotency_repository.get(
        scope=VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
        user_id=str(current_user.id),
        key=normalized_key,
    )
    if record is None:
        record, created = idempotency_repository.start(
            scope=VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
            user_id=str(current_user.id),
            key=normalized_key,
            request_hash=request_hash,
        )
        if created:
            logger.info(
                "Idempotency record started scope=%s owner_id=%s key_hash=%s",
                VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
                current_user.id,
                key_hash,
            )
            return record

    if record.request_hash != request_hash:
        logger.warning(
            "Idempotency conflict scope=%s owner_id=%s key_hash=%s",
            VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
            current_user.id,
            key_hash,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request",
        )
    if record.status == "completed" and record.response_body is not None:
        logger.info(
            "Idempotency replay scope=%s owner_id=%s key_hash=%s status_code=%s",
            VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
            current_user.id,
            key_hash,
            record.response_status_code or status.HTTP_201_CREATED,
        )
        return JSONResponse(
            status_code=record.response_status_code or status.HTTP_201_CREATED,
            content=record.response_body,
        )
    if record.status == "processing":
        logger.warning(
            "Idempotency request still processing scope=%s owner_id=%s key_hash=%s",
            VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
            current_user.id,
            key_hash,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotent request is still processing",
        )

    return record


def _get_accessible_video(video_id: UUID, current_user: User | None, get_video_use_case: GetVideo):
    try:
        return get_video_use_case.execute(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)


@router.post("/videos", response_model=VideoDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    description: str | None = Form(default=None, max_length=5000),
    is_registered_only: bool = Form(default=False),
    category_ids: list[UUID] = Form(default=[]),
    tags: list[str] = Form(default=[]),
    current_user: User = Depends(get_current_user),
    upload_video_use_case: UploadVideo = Depends(get_upload_video),
    video_processing_queue: VideoProcessingQueue = Depends(get_video_processing_queue),
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
    idempotency_repository: IdempotencyRepository = Depends(get_idempotency_repository),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> VideoDetailResponse | JSONResponse:
    original_filename = file.filename or "video"
    upload_size = getattr(file, "size", None)
    normalized_title = _normalize_required_text(title, "title")
    normalized_description = _normalize_optional_text(description)
    normalized_tags = _normalize_tags(tags)

    request_hash = await _video_upload_request_hash(
        file=file,
        title=normalized_title,
        description=normalized_description,
        is_registered_only=is_registered_only,
        category_ids=category_ids,
        tags=normalized_tags,
    )
    idempotency_record_or_response = _get_or_start_idempotency_record(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        current_user=current_user,
        idempotency_repository=idempotency_repository,
    )
    if isinstance(idempotency_record_or_response, JSONResponse):
        await file.close()
        return idempotency_record_or_response
    idempotency_record = idempotency_record_or_response

    try:
        await file.seek(0)
        video = upload_video_use_case.execute(
            UploadVideoCommand(
                owner_id=current_user.id,
                title=normalized_title,
                description=normalized_description,
                original_filename=original_filename,
                content_type=file.content_type,
                file=file.file,
                is_registered_only=is_registered_only,
                category_ids=category_ids,
                tags=normalized_tags,
            )
        )
        video.owner = VideoOwner(
            id=current_user.id,
            username=current_user.username,
            display_name=current_user.display_name,
        )
        logger.info(
            "Video uploaded video_id=%s owner_id=%s filename=%s content_type=%s "
            "size_bytes=%s idempotent=%s",
            video.id,
            current_user.id,
            original_filename,
            file.content_type or "-",
            upload_size if upload_size is not None else "-",
            idempotency_record is not None,
        )
        try:
            video_processing_queue.enqueue(video.id)
            logger.info(
                "Video processing job enqueued video_id=%s owner_id=%s queue_backend=%s",
                video.id,
                current_user.id,
                type(video_processing_queue).__name__,
            )
        except Exception as error:
            logger.exception(
                "Failed to enqueue video processing job video_id=%s owner_id=%s "
                "queue_backend=%s error_type=%s",
                video.id,
                current_user.id,
                type(video_processing_queue).__name__,
                type(error).__name__,
            )
            try:
                video_repository.delete(video.id)
                video_storage.delete_video_files(video.id)
            except Exception:
                logger.exception(
                    "Failed to roll back video after queue enqueue failure video_id=%s "
                    "owner_id=%s",
                    video.id,
                    current_user.id,
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Video processing queue is unavailable",
            )
    except HTTPException as error:
        if idempotency_record is not None and error.status_code >= 500:
            idempotency_repository.fail(idempotency_record, str(error.detail))
        raise
    except VideoUploadError as error:
        logger.warning(
            "Video upload rejected owner_id=%s filename=%s content_type=%s "
            "size_bytes=%s error_type=%s",
            current_user.id,
            original_filename,
            file.content_type or "-",
            upload_size if upload_size is not None else "-",
            type(error).__name__,
        )
        if idempotency_record is not None:
            idempotency_repository.delete(idempotency_record)
        raise _map_video_upload_error(error)
    except Exception as error:
        logger.exception(
            "Video upload failed owner_id=%s filename=%s content_type=%s "
            "size_bytes=%s error_type=%s",
            current_user.id,
            original_filename,
            file.content_type or "-",
            upload_size if upload_size is not None else "-",
            type(error).__name__,
        )
        if idempotency_record is not None:
            idempotency_repository.fail(idempotency_record, str(error))
        raise
    finally:
        await file.close()

    response = VideoDetailResponse.from_domain(
        video,
        current_user=current_user,
        is_favorite=False,
        reaction_counts={},
    )
    if idempotency_record is not None:
        idempotency_repository.complete(
            idempotency_record,
            response_status_code=status.HTTP_201_CREATED,
            response_body=jsonable_encoder(response),
        )
        logger.info(
            "Idempotency record completed scope=%s owner_id=%s video_id=%s",
            VIDEO_UPLOAD_IDEMPOTENCY_SCOPE,
            current_user.id,
            video.id,
        )
    return response


@router.get("/videos", response_model=VideoListResponse)
def list_videos(
    title: str | None = Query(default=None),
    tags: list[str] | None = Query(default=None),
    category_ids: list[UUID] | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User | None = Depends(get_optional_current_user),
    list_videos_use_case: ListVideos = Depends(get_list_videos),
) -> VideoListResponse:
    result = list_videos_use_case.execute(
        ListVideosQuery(
            title=title,
            tags=tags,
            category_ids=category_ids,
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        ),
        current_user,
    )

    return VideoListResponse.from_result(result, limit=limit, offset=offset)


@router.get("/video-categories", response_model=list[VideoCategoryResponse])
def list_video_categories(
    video_category_repository: VideoCategoryRepository = Depends(
        get_video_category_repository
    ),
) -> list[VideoCategoryResponse]:
    return [
        VideoCategoryResponse.from_domain(category)
        for category in video_category_repository.list()
    ]


@router.post(
    "/video-categories",
    response_model=VideoCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_video_category(
    request: VideoCategoryCreateRequest,
    current_user: User = Depends(require_admin),
    video_category_repository: VideoCategoryRepository = Depends(
        get_video_category_repository
    ),
) -> VideoCategoryResponse:
    category = video_category_repository.create(
        VideoCategoryCreate(
            name=request.name,
            source=VideoCategorySource.CUSTOM,
            thumbnail_vertical_url=request.thumbnail_vertical_url,
            thumbnail_horizontal_url=request.thumbnail_horizontal_url,
        )
    )
    logger.info(
        "Video category created category_id=%s source=%s requested_by=%s",
        category.id,
        category.source.value,
        current_user.id,
    )

    return VideoCategoryResponse.from_domain(category)


@router.get(
    "/video-categories/steam/search",
    response_model=list[SteamGridDbGameResponse],
)
def search_steam_video_categories(
    term: str = Query(min_length=1, max_length=100),
    current_user: User = Depends(require_admin),
    steamgriddb_client: SteamGridDbClient = Depends(get_steamgriddb_client),
) -> list[SteamGridDbGameResponse]:
    del current_user
    try:
        games = steamgriddb_client.search_games(term)
    except (SteamGridDbConfigurationError, SteamGridDbError) as error:
        raise _map_steamgriddb_error(error)

    return [
        response
        for response in (_steamgriddb_game_to_response(game) for game in games)
        if response is not None
    ]


@router.post(
    "/video-categories/steam/import",
    response_model=VideoCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_steam_video_category(
    request: SteamVideoCategoryImportRequest,
    current_user: User = Depends(require_admin),
    video_category_repository: VideoCategoryRepository = Depends(
        get_video_category_repository
    ),
    steamgriddb_client: SteamGridDbClient = Depends(get_steamgriddb_client),
) -> VideoCategoryResponse:
    try:
        if request.steam_appid is not None:
            game = steamgriddb_client.get_game_by_steam_appid(request.steam_appid)
        else:
            game = steamgriddb_client.get_game_by_id(request.steamgriddb_game_id)

        game_id = game.get("id")
        name = game.get("name")
        if game_id is None or not name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SteamGridDB game not found",
            )

        vertical_url = _best_grid_url(
            steamgriddb_client.get_grids(
                game_id,
                dimensions=STEAMGRIDDB_VERTICAL_GRID_DIMENSIONS,
            )
        )
        horizontal_url = _best_grid_url(
            steamgriddb_client.get_grids(
                game_id,
                dimensions=STEAMGRIDDB_HORIZONTAL_GRID_DIMENSIONS,
            )
        )
    except HTTPException:
        raise
    except (SteamGridDbConfigurationError, SteamGridDbError) as error:
        raise _map_steamgriddb_error(error)

    category = video_category_repository.upsert_steam_category(
        VideoCategoryCreate(
            name=name.strip(),
            source=VideoCategorySource.STEAM,
            steam_appid=request.steam_appid,
            steamgriddb_game_id=game_id,
            thumbnail_vertical_url=vertical_url,
            thumbnail_horizontal_url=horizontal_url,
        )
    )
    logger.info(
        "Steam video category imported category_id=%s steam_appid=%s "
        "steamgriddb_game_id=%s requested_by=%s has_vertical=%s has_horizontal=%s",
        category.id,
        category.steam_appid,
        category.steamgriddb_game_id,
        current_user.id,
        category.thumbnail_vertical_url is not None,
        category.thumbnail_horizontal_url is not None,
    )

    return VideoCategoryResponse.from_domain(category)


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
def get_video(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> VideoDetailResponse:
    try:
        video = get_video_use_case.execute(video_id, current_user)
        reaction_counts = react_to_video.get_counts(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)

    is_favorite = (
        current_user is not None
        and video_repository.is_favorite(video_id, current_user.id)
    )

    return VideoDetailResponse.from_domain(
        video,
        current_user=current_user,
        is_favorite=is_favorite,
        reaction_counts=reaction_counts,
    )


@router.get("/videos/{video_id}/download")
def download_video(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> FileResponse:
    video = _get_accessible_video(video_id, current_user, get_video_use_case)
    original_path = video_storage.get_original_path(video_id)
    _ensure_file_exists(original_path)

    return FileResponse(
        original_path,
        media_type="application/octet-stream",
        filename=video.original_filename,
    )


@router.get("/videos/{video_id}/stream")
def stream_video(
    video_id: UUID,
    variant_type: VideoVariantType = Query(default=VideoVariantType.LOW_H264),
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> FileResponse:
    video = _get_accessible_video(video_id, current_user, get_video_use_case)
    if variant_type == VideoVariantType.ORIGINAL:
        original_path = video_storage.get_original_path(video_id)
        _ensure_file_exists(original_path)
        media_type = (
            "video/webm"
            if original_path.suffix.lower() == ".webm"
            else "video/mp4"
        )

        return FileResponse(
            original_path,
            media_type=media_type,
            filename=video.original_filename,
            content_disposition_type="inline",
        )

    if video.processing_status != VideoProcessingStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video is not ready",
        )

    variant_path = video_storage.get_variant_path(video_id, variant_type)
    _ensure_file_exists(variant_path)

    return FileResponse(
        variant_path,
        media_type="video/mp4",
        filename=f"{video_id}-{variant_type.value}.mp4",
        content_disposition_type="inline",
    )


@router.get("/videos/{video_id}/thumbnail")
def get_video_thumbnail(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> FileResponse:
    _get_accessible_video(video_id, current_user, get_video_use_case)
    thumbnail_path = video_storage.get_thumbnail_path(video_id)
    _ensure_file_exists(thumbnail_path)

    return FileResponse(
        thumbnail_path,
        media_type="image/jpeg",
        filename=f"{video_id}-thumbnail.jpg",
        content_disposition_type="inline",
    )


@router.patch("/videos/{video_id}", response_model=VideoDetailResponse)
def update_video(
    video_id: UUID,
    request: VideoUpdateRequest,
    current_user: User = Depends(get_current_user),
    update_video_use_case: UpdateVideo = Depends(get_update_video),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> VideoDetailResponse:
    fields_set = _fields_set(request)

    try:
        video = update_video_use_case.execute(
            UpdateVideoCommand(
                video_id=video_id,
                title=request.title if "title" in fields_set else None,
                description=(
                    request.description if "description" in fields_set else None
                ),
                is_registered_only=(
                    request.is_registered_only
                    if "is_registered_only" in fields_set
                    else None
                ),
                category_ids=(
                    request.category_ids if "category_ids" in fields_set else None
                ),
                tags=request.tags if "tags" in fields_set else None,
            ),
            current_user,
        )
        reaction_counts = react_to_video.get_counts(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)

    return VideoDetailResponse.from_domain(
        video,
        current_user=current_user,
        is_favorite=video_repository.is_favorite(video_id, current_user.id),
        reaction_counts=reaction_counts,
    )


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    delete_video_use_case: DeleteVideo = Depends(get_delete_video),
) -> Response:
    try:
        delete_video_use_case.execute(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/videos/{video_id}/processing/retry", response_model=VideoDetailResponse)
def retry_video_processing(
    video_id: UUID,
    current_user: User = Depends(require_super_admin),
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
    video_processing_queue: VideoProcessingQueue = Depends(get_video_processing_queue),
) -> VideoDetailResponse:
    video = video_repository.get_by_id(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    if video.processing_status == VideoProcessingStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video processing is already complete",
        )

    try:
        video_storage.delete_processing_outputs(video_id)
        reset_video = video_repository.reset_processing(video_id)
        if reset_video is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )
        video_processing_queue.enqueue(video_id, force=True)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception(
            "Failed to retry video processing video_id=%s requested_by=%s "
            "queue_backend=%s error_type=%s",
            video_id,
            current_user.id,
            type(video_processing_queue).__name__,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video processing queue is unavailable",
        )

    logger.info(
        "Video processing retry enqueued video_id=%s requested_by=%s "
        "previous_status=%s new_status=%s queue_backend=%s",
        video_id,
        current_user.id,
        video.processing_status.value,
        reset_video.processing_status.value,
        type(video_processing_queue).__name__,
    )
    return VideoDetailResponse.from_domain(
        reset_video,
        current_user=current_user,
        is_favorite=False,
        reaction_counts={},
    )


@router.post("/videos/{video_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def favorite_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video),
) -> Response:
    try:
        favorite_video_use_case.add(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/videos/{video_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video),
) -> Response:
    try:
        favorite_video_use_case.remove(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me/video-favorites", response_model=VideoListResponse)
def list_my_video_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video),
) -> VideoListResponse:
    result = favorite_video_use_case.list_user_favorites(
        current_user,
        limit=limit,
        offset=offset,
    )

    return VideoListResponse.from_result(result, limit=limit, offset=offset)


@router.get("/videos/{video_id}/reactions", response_model=list[VideoReactionCountResponse])
def get_video_reactions(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
) -> list[VideoReactionCountResponse]:
    try:
        reaction_counts = react_to_video.get_counts(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)

    return [
        VideoReactionCountResponse(type=reaction_type, count=count)
        for reaction_type, count in sorted(reaction_counts.items())
    ]


@router.post("/videos/{video_id}/reactions", response_model=VideoReactionResponse)
def react_to_video_route(
    video_id: UUID,
    request: VideoReactionRequest,
    current_user: User = Depends(get_current_user),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
) -> VideoReactionResponse:
    try:
        reaction = react_to_video.set(
            video_id,
            request.reaction_type,
            current_user,
        )
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)

    return VideoReactionResponse.from_domain(reaction)


@router.delete("/videos/{video_id}/reactions", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_reaction(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
) -> Response:
    try:
        react_to_video.remove(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
