from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.wiring import get_current_user, get_optional_current_user
from app.modules.users.domain.user import User
from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.get_video import GetVideo
from app.modules.videos.application.list_videos import ListVideos, ListVideosQuery
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.update_video import UpdateVideo, UpdateVideoCommand
from app.modules.videos.domain.ports import VideoRepository
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
    get_update_video,
    get_video_repository,
)


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

    raise error


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
    except (VideoNotFoundError, VideoPermissionError) as error:
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
    except (VideoNotFoundError, VideoPermissionError) as error:
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
    except (VideoNotFoundError, VideoPermissionError) as error:
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
