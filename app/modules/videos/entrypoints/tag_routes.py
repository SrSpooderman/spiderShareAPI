from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.modules.auth.wiring import get_current_user, require_admin
from app.modules.users.domain.user import User
from app.modules.videos.domain.ports import VideoTagRepository
from app.modules.videos.domain.video import VideoTagCreate
from app.modules.videos.entrypoints.schemas import (
    VideoTagCreateRequest,
    VideoTagResponse,
)
from app.modules.videos.wiring import get_video_tag_repository
from app.shared.infrastructure.logging import get_logger


router = APIRouter(prefix="/tags", tags=["tags"])
logger = get_logger(__name__)


@router.get("", response_model=list[VideoTagResponse])
def list_video_tags(
    repository: VideoTagRepository = Depends(get_video_tag_repository),
) -> list[VideoTagResponse]:
    return [VideoTagResponse.from_domain(tag) for tag in repository.list()]


@router.post("", response_model=VideoTagResponse, status_code=status.HTTP_201_CREATED)
def create_video_tag(
    request: VideoTagCreateRequest,
    current_user: User = Depends(get_current_user),
    repository: VideoTagRepository = Depends(get_video_tag_repository),
) -> VideoTagResponse:
    tag = repository.create(VideoTagCreate(name=request.name))
    logger.info("Video tag created tag_id=%s requested_by=%s", tag.id, current_user.id)
    return VideoTagResponse.from_domain(tag)


@router.patch("/{tag_id}", response_model=VideoTagResponse)
def update_video_tag(
    tag_id: UUID,
    request: VideoTagCreateRequest,
    current_user: User = Depends(get_current_user),
    repository: VideoTagRepository = Depends(get_video_tag_repository),
) -> VideoTagResponse:
    tag = repository.update(tag_id, VideoTagCreate(name=request.name))
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video tag not found",
        )

    logger.info("Video tag updated tag_id=%s requested_by=%s", tag.id, current_user.id)
    return VideoTagResponse.from_domain(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_tag(
    tag_id: UUID,
    current_user: User = Depends(require_admin),
    repository: VideoTagRepository = Depends(get_video_tag_repository),
) -> Response:
    deleted = repository.delete(tag_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video tag not found",
        )

    logger.info("Video tag deleted tag_id=%s requested_by=%s", tag_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
