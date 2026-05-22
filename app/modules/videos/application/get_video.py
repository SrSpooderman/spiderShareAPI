from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.domain.ports import VideoRepository
from app.modules.videos.domain.video import Video, can_view_video


class GetVideo:
    def __init__(self, video_repository: VideoRepository) -> None:
        self.video_repository = video_repository

    def execute(self, video_id: UUID, current_user: User | None) -> Video:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_view_video(video, current_user):
            raise VideoPermissionError

        return video
