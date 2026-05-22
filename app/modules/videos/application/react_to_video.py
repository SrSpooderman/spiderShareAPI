from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.application.errors import (
    VideoNotFoundError,
    VideoPermissionError,
    VideoReactionLimitError,
)
from app.modules.videos.domain.ports import VideoRepository
from app.modules.videos.domain.video import VideoReaction, can_favorite_or_react_to_video
from config.settings import settings


class ReactToVideo:
    def __init__(self, video_repository: VideoRepository) -> None:
        self.video_repository = video_repository

    def get_counts(self, video_id: UUID, current_user: User | None) -> dict[str, int]:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_favorite_or_react_to_video(video, current_user):
            if current_user is None and not video.is_registered_only:
                return self.video_repository.get_reaction_counts(video_id)
            raise VideoPermissionError

        return self.video_repository.get_reaction_counts(video_id)

    def set(
        self,
        video_id: UUID,
        reaction_type: str,
        current_user: User,
    ) -> VideoReaction:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_favorite_or_react_to_video(video, current_user):
            raise VideoPermissionError

        reaction_count = self.video_repository.count_user_reactions(
            video_id,
            current_user.id,
        )
        has_reaction = self.video_repository.has_user_reaction(
            video_id,
            current_user.id,
            reaction_type,
        )
        if reaction_count >= settings.max_video_reactions_per_user and not has_reaction:
            raise VideoReactionLimitError

        if has_reaction:
            return self.video_repository.set_reaction(
                video_id,
                current_user.id,
                reaction_type,
            )

        return self.video_repository.set_reaction(
            video_id,
            current_user.id,
            reaction_type,
        )

    def remove(self, video_id: UUID, current_user: User) -> None:
        video = self.video_repository.get_by_id(video_id)

        if video is None:
            raise VideoNotFoundError

        if not can_favorite_or_react_to_video(video, current_user):
            raise VideoPermissionError

        self.video_repository.remove_reaction(video_id, current_user.id)
