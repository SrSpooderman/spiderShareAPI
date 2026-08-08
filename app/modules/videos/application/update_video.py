from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.domain.ports import VideoRepository
from app.modules.videos.domain.video import Video, can_edit_video


@dataclass(frozen=True)
class UpdateVideoCommand:
    video_id: UUID
    title: str | None = None
    description: str | None = None
    is_registered_only: bool | None = None
    edited: bool | None = None
    category_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None
    source_created_at: datetime | None = None
    source_created_at_set: bool = False


class UpdateVideo:
    def __init__(self, video_repository: VideoRepository) -> None:
        self.video_repository = video_repository

    def execute(self, command: UpdateVideoCommand, current_user: User) -> Video:
        video = self.video_repository.get_by_id(command.video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_edit_video(video, current_user):
            raise VideoPermissionError

        updated_video = self.video_repository.update_metadata(
            command.video_id,
            title=command.title,
            description=command.description,
            is_registered_only=command.is_registered_only,
            edited=command.edited,
            category_ids=command.category_ids,
            tag_ids=command.tag_ids,
            source_created_at=command.source_created_at,
            source_created_at_set=command.source_created_at_set,
        )

        if updated_video is None:
            raise VideoNotFoundError

        return updated_video
