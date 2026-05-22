from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.domain.ports import VideoListResult, VideoRepository
from app.modules.videos.domain.video import can_favorite_or_react_to_video


class FavoriteVideo:
    def __init__(self, video_repository: VideoRepository) -> None:
        self.video_repository = video_repository

    def add(self, video_id: UUID, current_user: User) -> None:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_favorite_or_react_to_video(video, current_user):
            raise VideoPermissionError

        self.video_repository.add_favorite(video_id, current_user.id)

    def remove(self, video_id: UUID, current_user: User) -> None:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_favorite_or_react_to_video(video, current_user):
            raise VideoPermissionError

        self.video_repository.remove_favorite(video_id, current_user.id)

    def list_user_favorites(
        self,
        current_user: User,
        *,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        return self.video_repository.list_favorites(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
