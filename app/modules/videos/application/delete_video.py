from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.domain.ports import VideoRepository, VideoStorage
from app.modules.videos.domain.video import can_delete_video
from app.shared.infrastructure.logging import get_logger


logger = get_logger(__name__)


class DeleteVideo:
    def __init__(
        self,
        video_repository: VideoRepository,
        video_storage: VideoStorage,
    ) -> None:
        self.video_repository = video_repository
        self.video_storage = video_storage

    def execute(self, video_id: UUID, current_user: User) -> None:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_delete_video(video, current_user):
            raise VideoPermissionError

        self.video_repository.delete(video_id)
        try:
            self.video_storage.delete_video_files(video_id)
        except Exception:
            logger.exception("Failed to delete video files video_id=%s", video_id)
