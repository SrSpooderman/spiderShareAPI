from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.wiring import get_current_user, get_optional_current_user
from app.modules.users.domain.user import User
from app.modules.videos.application.errors import (
    VideoNotFoundError,
    VideoPermissionError,
    VideoReactionLimitError,
)
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.entrypoints.schemas import (
    VideoListResponse,
    VideoReactionCountResponse,
    VideoReactionRequest,
    VideoReactionResponse,
)
from app.modules.videos.wiring import (
    get_favorite_video,
    get_react_to_video,
    get_video_repository,
)
from app.modules.videos.domain.ports import VideoRepository
from config.settings import settings


router = APIRouter(prefix="/interactions", tags=["interactions"])


def _map_video_error(error: Exception) -> HTTPException:
    if isinstance(error, VideoNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if isinstance(error, VideoPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access that video")
    if isinstance(error, VideoReactionLimitError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user can only react {settings.max_video_reactions_per_user} times to the same video",
        )
    raise error


@router.post("/videos/{video_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def favorite_video(video_id: UUID, current_user: User = Depends(get_current_user), favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video)) -> Response:
    try:
        favorite_video_use_case.add(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/videos/{video_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_video(video_id: UUID, current_user: User = Depends(get_current_user), favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video)) -> Response:
    try:
        favorite_video_use_case.remove(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/video-favorites", response_model=VideoListResponse)
def list_my_video_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    favorite_video_use_case: FavoriteVideo = Depends(get_favorite_video),
    react_to_video: ReactToVideo = Depends(get_react_to_video),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> VideoListResponse:
    result = favorite_video_use_case.list_user_favorites(current_user, limit=limit, offset=offset)
    favorites_by_video_id = {
        video.id: video_repository.is_favorite(video.id, current_user.id)
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


@router.get("/videos/{video_id}/reactions", response_model=list[VideoReactionCountResponse])
def get_video_reactions(video_id: UUID, current_user: User | None = Depends(get_optional_current_user), react_to_video: ReactToVideo = Depends(get_react_to_video)) -> list[VideoReactionCountResponse]:
    try:
        reaction_counts = react_to_video.get_counts(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)
    return [VideoReactionCountResponse(type=reaction_type, count=count) for reaction_type, count in sorted(reaction_counts.items())]


@router.post("/videos/{video_id}/reactions", response_model=VideoReactionResponse)
def react_to_video_route(video_id: UUID, request: VideoReactionRequest, current_user: User = Depends(get_current_user), react_to_video: ReactToVideo = Depends(get_react_to_video)) -> VideoReactionResponse:
    try:
        reaction = react_to_video.set(video_id, request.reaction_type, current_user)
    except (VideoNotFoundError, VideoPermissionError, VideoReactionLimitError) as error:
        raise _map_video_error(error)
    return VideoReactionResponse.from_domain(reaction)


@router.delete("/videos/{video_id}/reactions", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_reaction(video_id: UUID, current_user: User = Depends(get_current_user), react_to_video: ReactToVideo = Depends(get_react_to_video)) -> Response:
    try:
        react_to_video.remove(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError) as error:
        raise _map_video_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
