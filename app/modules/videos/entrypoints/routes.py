from collections.abc import Callable
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.modules.auth.wiring import get_current_user, get_optional_current_user
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
from app.modules.videos.domain.ports import VideoRepository, VideoStorage
from app.modules.videos.domain.video import VideoProcessingStatus, VideoVariantType
from app.modules.videos.entrypoints.schemas import (
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
    get_video_processing_scheduler,
    get_video_repository,
    get_video_storage,
)
from config.settings import settings


router = APIRouter(tags=["videos"])


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


def _ensure_file_exists(path) -> None:
    if path is None or not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found",
        )


def _get_accessible_video(video_id: UUID, current_user: User | None, get_video_use_case: GetVideo):
    try:
        return get_video_use_case.execute(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)


@router.post("/videos", response_model=VideoDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    description: str | None = Form(default=None, max_length=5000),
    is_registered_only: bool = Form(default=False),
    category_ids: list[UUID] = Form(default=[]),
    tags: list[str] = Form(default=[]),
    current_user: User = Depends(get_current_user),
    upload_video_use_case: UploadVideo = Depends(get_upload_video),
    schedule_video_processing: Callable[[UUID], None] = Depends(
        get_video_processing_scheduler,
    ),
) -> VideoDetailResponse:
    original_filename = file.filename or "video"

    try:
        await file.seek(0)
        video = upload_video_use_case.execute(
            UploadVideoCommand(
                owner_id=current_user.id,
                title=_normalize_required_text(title, "title"),
                description=_normalize_optional_text(description),
                original_filename=original_filename,
                content_type=file.content_type,
                file=file.file,
                is_registered_only=is_registered_only,
                category_ids=category_ids,
                tags=_normalize_tags(tags),
            )
        )
        background_tasks.add_task(schedule_video_processing, video.id)
    except VideoUploadError as error:
        raise _map_video_upload_error(error)
    finally:
        await file.close()

    return VideoDetailResponse.from_domain(
        video,
        current_user=current_user,
        is_favorite=False,
        reaction_counts={},
    )


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
