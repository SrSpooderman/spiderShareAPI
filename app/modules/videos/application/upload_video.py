from dataclasses import dataclass, field
from typing import BinaryIO
from uuid import UUID, uuid4

from app.modules.videos.domain.ports import VideoRepository, VideoStorage
from app.modules.videos.domain.video import Video, VideoCreate


@dataclass(frozen=True)
class UploadVideoCommand:
    owner_id: UUID
    title: str
    description: str
    original_filename: str
    content_type: str | None
    file: BinaryIO
    is_registered_only: bool = False
    edited: bool = False
    category_ids: list[UUID] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class UploadVideo:
    def __init__(
        self,
        video_repository: VideoRepository,
        video_storage: VideoStorage,
    ) -> None:
        self.video_repository = video_repository
        self.video_storage = video_storage

    def execute(self, command: UploadVideoCommand) -> Video:
        video_id = uuid4()
        self.video_storage.save_original(
            video_id=video_id,
            original_filename=command.original_filename,
            content_type=command.content_type,
            file=command.file,
        )

        try:
            return self.video_repository.create(
                VideoCreate(
                    id=video_id,
                    owner_id=command.owner_id,
                    title=command.title,
                    description=command.description,
                    original_filename=command.original_filename,
                    is_registered_only=command.is_registered_only,
                    edited=command.edited,
                    category_ids=command.category_ids,
                    tags=command.tags,
                )
            )
        except Exception:
            self.video_storage.delete_original(video_id)
            raise
