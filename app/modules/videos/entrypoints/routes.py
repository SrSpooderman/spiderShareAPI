import hashlib
import json
from datetime import datetime
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
from app.modules.videos.application.get_video import GetVideo
from app.modules.videos.application.list_videos import ListVideos, ListVideosQuery
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.upload_video import UploadVideo, UploadVideoCommand
from app.modules.videos.application.update_video import UpdateVideo, UpdateVideoCommand
from app.modules.videos.domain.ports import (
    VideoProcessingQueue,
    VideoRepository,
    VideoStorage,
)
from app.modules.videos.domain.video import (
    VideoOwner,
    VideoProcessingStatus,
    VideoVariantType,
)
from app.modules.videos.entrypoints.schemas import (
    VideoDetailResponse,
    VideoListResponse,
    VideoUpdateRequest,
)
from app.modules.videos.wiring import (
    get_delete_video,
    get_get_video,
    get_list_videos,
    get_react_to_video,
    get_upload_video,
    get_update_video,
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)
from app.shared.infrastructure.idempotency import IdempotencyRepository
from app.shared.infrastructure.logging import get_logger
from app.shared.wiring import get_idempotency_repository
from config.settings import settings


router = APIRouter(tags=["videos"])
logger = get_logger(__name__)
VIDEO_UPLOAD_IDEMPOTENCY_SCOPE = "videos.upload"
VIDEO_FILTER_DATE_FORMAT = "%d/%m/%Y"


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
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "message": "Video file is too large",
                "size_bytes": error.size_bytes,
                "limit_bytes": error.limit_bytes,
            },
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


def _normalize_tag_ids(tag_ids: list[UUID]) -> list[UUID]:
    normalized_tag_ids = list(dict.fromkeys(tag_ids))
    if len(normalized_tag_ids) > settings.max_video_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Too many tags",
        )

    return normalized_tag_ids


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


def _parse_video_filter_date(value: str | None, field_name: str):
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    try:
        return datetime.strptime(text, VIDEO_FILTER_DATE_FORMAT).date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must use DD/MM/YYYY format",
        )


def _resolve_video_date_filters(
    *,
    created_date: str | None,
    created_from: str | None,
    created_to: str | None,
):
    exact_date = _parse_video_filter_date(created_date, "created_date")
    from_date = _parse_video_filter_date(created_from, "created_from")
    to_date = _parse_video_filter_date(created_to, "created_to")

    if exact_date is not None and (from_date is not None or to_date is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="created_date cannot be combined with created_from or created_to",
        )

    if exact_date is not None:
        return exact_date, exact_date

    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="created_from cannot be after created_to",
        )

    return from_date, to_date


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
    edited: bool,
    source_created_at: datetime | None,
    source_updated_at: datetime | None,
    category_ids: list[UUID],
    tag_ids: list[UUID],
) -> str:
    digest = hashlib.sha256()
    metadata = {
        "title": title,
        "description": description,
        "is_registered_only": is_registered_only,
        "edited": edited,
        "source_created_at": (
            source_created_at.isoformat() if source_created_at is not None else None
        ),
        "source_updated_at": (
            source_updated_at.isoformat() if source_updated_at is not None else None
        ),
        "category_ids": sorted(str(category_id) for category_id in category_ids),
        "tag_ids": sorted(str(tag_id) for tag_id in tag_ids),
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
    edited: bool = Form(default=False),
    source_created_at: datetime | None = Form(default=None),
    source_updated_at: datetime | None = Form(default=None),
    category_ids: list[UUID] = Form(default=[]),
    tag_ids: list[UUID] = Form(default=[]),
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
    normalized_tag_ids = _normalize_tag_ids(tag_ids)

    request_hash = await _video_upload_request_hash(
        file=file,
        title=normalized_title,
        description=normalized_description,
        is_registered_only=is_registered_only,
        edited=edited,
        source_created_at=source_created_at,
        source_updated_at=source_updated_at,
        category_ids=category_ids,
        tag_ids=normalized_tag_ids,
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
                edited=edited,
                source_created_at=source_created_at,
                source_updated_at=source_updated_at,
                category_ids=category_ids,
                tag_ids=normalized_tag_ids,
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
    category_ids: list[UUID] | None = Query(default=None),
    tag_ids: list[UUID] | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    created_date: str | None = Query(default=None, min_length=10, max_length=10),
    created_from: str | None = Query(default=None, min_length=10, max_length=10),
    created_to: str | None = Query(default=None, min_length=10, max_length=10),
    edited: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User | None = Depends(get_optional_current_user),
    list_videos_use_case: ListVideos = Depends(get_list_videos),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> VideoListResponse:
    resolved_created_from, resolved_created_to = _resolve_video_date_filters(
        created_date=created_date,
        created_from=created_from,
        created_to=created_to,
    )
    result = list_videos_use_case.execute(
        ListVideosQuery(
            title=title,
            category_ids=category_ids,
            tag_ids=tag_ids,
            owner_id=owner_id,
            created_from=resolved_created_from,
            created_to=resolved_created_to,
            edited=edited,
            limit=limit,
            offset=offset,
        ),
        current_user,
    )

    favorites_by_video_id = {
        video.id: (
            current_user is not None
            and video_repository.is_favorite(video.id, current_user.id)
        )
        for video in result.items
    }
    reaction_counts_by_video_id = {
        video.id: react_to_video.get_counts(video.id, current_user)
        for video in result.items
    }

    return VideoListResponse.from_result(
        result,
        limit=limit,
        offset=offset,
        current_user=current_user,
        favorites_by_video_id=favorites_by_video_id,
        reaction_counts_by_video_id=reaction_counts_by_video_id,
    )


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


def _clip_video_response(
    video_id: UUID,
    current_user: User | None,
    get_video_use_case: GetVideo,
    video_storage: VideoStorage,
    *,
    prefer_original_h264: bool = True,
) -> FileResponse:
    video = _get_accessible_video(video_id, current_user, get_video_use_case)
    if video.processing_status != VideoProcessingStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video is not ready",
        )

    variant_path = (
        video_storage.get_variant_path(video_id, VideoVariantType.ORIGINAL_H264)
        if prefer_original_h264
        else None
    )
    if variant_path is None:
        variant_path = video_storage.get_variant_path(video_id, VideoVariantType.LOW_H264)
    _ensure_file_exists(variant_path)

    return FileResponse(
        variant_path,
        media_type="video/mp4",
        filename=f"{video_id}.mp4",
        content_disposition_type="inline",
    )


@router.get("/clip/{video_id}")
def clip_video(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> FileResponse:
    return _clip_video_response(video_id, current_user, get_video_use_case, video_storage)


@router.get("/clip/{video_id}/h264")
def clip_video_h264(
    video_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    get_video_use_case: GetVideo = Depends(get_get_video),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> FileResponse:
    return _clip_video_response(
        video_id,
        current_user,
        get_video_use_case,
        video_storage,
        prefer_original_h264=False,
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
                edited=request.edited if "edited" in fields_set else None,
                category_ids=(
                    request.category_ids if "category_ids" in fields_set else None
                ),
                tag_ids=request.tag_ids if "tag_ids" in fields_set else None,
                source_created_at=(
                    request.source_created_at
                    if "source_created_at" in fields_set
                    else None
                ),
                source_created_at_set="source_created_at" in fields_set,
                source_updated_at=(
                    request.source_updated_at
                    if "source_updated_at" in fields_set
                    else None
                ),
                source_updated_at_set="source_updated_at" in fields_set,
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
