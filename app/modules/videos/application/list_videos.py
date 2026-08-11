from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.users.domain.user import User
from app.modules.videos.domain.ports import (
    VIDEO_LIST_DEFAULT_SORT_BY,
    VIDEO_LIST_DEFAULT_SORT_DIRECTION,
    VideoListFilters,
    VideoListResult,
    VideoRepository,
)


@dataclass(frozen=True)
class ListVideosQuery:
    title: str | None = None
    category_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None
    owner_id: UUID | None = None
    created_from: date | None = None
    created_to: date | None = None
    edited: bool | None = None
    sort_by: str = VIDEO_LIST_DEFAULT_SORT_BY
    sort_direction: str = VIDEO_LIST_DEFAULT_SORT_DIRECTION
    limit: int = 20
    offset: int = 0


class ListVideos:
    def __init__(self, video_repository: VideoRepository) -> None:
        self.video_repository = video_repository

    def execute(
        self,
        query: ListVideosQuery,
        current_user: User | None,
    ) -> VideoListResult:
        return self.video_repository.list_visible(
            current_user_id=current_user.id if current_user is not None else None,
            filters=VideoListFilters(
                title=query.title,
                category_ids=query.category_ids,
                tag_ids=query.tag_ids,
                owner_id=query.owner_id,
                created_from=query.created_from,
                created_to=query.created_to,
                edited=query.edited,
                sort_by=query.sort_by,
                sort_direction=query.sort_direction,
            ),
            limit=query.limit,
            offset=query.offset,
        )
