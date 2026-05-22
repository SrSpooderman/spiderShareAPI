from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.modules.videos.domain.video import Video, VideoCreate, VideoReaction


@dataclass(frozen=True)
class VideoListFilters:
    title: str | None = None
    tags: list[str] | None = None
    category_ids: list[UUID] | None = None
    owner_id: UUID | None = None


@dataclass(frozen=True)
class VideoListResult:
    items: list[Video]
    total: int


class VideoRepository(ABC):
    @abstractmethod
    def get_by_id(self, video_id: UUID) -> Video | None:
        pass

    @abstractmethod
    def list_visible(
        self,
        *,
        current_user_id: UUID | None,
        filters: VideoListFilters,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        pass

    @abstractmethod
    def create(self, video: VideoCreate) -> Video:
        pass

    @abstractmethod
    def update_metadata(
        self,
        video_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        is_registered_only: bool | None = None,
        category_ids: list[UUID] | None = None,
        tags: list[str] | None = None,
    ) -> Video | None:
        pass

    @abstractmethod
    def delete(self, video_id: UUID) -> bool:
        pass

    @abstractmethod
    def add_favorite(self, video_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def remove_favorite(self, video_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def list_favorites(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        pass

    @abstractmethod
    def is_favorite(self, video_id: UUID, user_id: UUID) -> bool:
        pass

    @abstractmethod
    def set_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> VideoReaction:
        pass

    @abstractmethod
    def remove_reaction(self, video_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def get_reaction_counts(self, video_id: UUID) -> dict[str, int]:
        pass
