from fastapi import APIRouter, Depends, status

from app.modules.auth.wiring import get_current_user
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
