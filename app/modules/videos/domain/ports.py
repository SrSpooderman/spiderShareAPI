from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.modules.videos.domain.video import (
    Video,
    VideoCategory,
    VideoCategoryCreate,
    VideoCreate,
    VideoProcessingResult,
    VideoReaction,
    VideoTag,
    VideoTagCreate,
    VideoVariantType,
)


@dataclass(frozen=True)
class VideoListFilters:
    title: str | None = None
    category_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None
    owner_id: UUID | None = None
    created_from: date | None = None
    created_to: date | None = None
    edited: bool | None = None


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
    def mark_processing(self, video_id: UUID) -> Video | None:
        pass

    @abstractmethod
    def mark_processed(
        self,
        video_id: UUID,
        result: VideoProcessingResult,
    ) -> Video | None:
        pass

    @abstractmethod
    def mark_failed(
        self,
        video_id: UUID,
        *,
        error_type: str,
        error_message: str,
        job_id: str | None,
        duration_ms: float | None,
    ) -> Video | None:
        pass

    @abstractmethod
    def reset_processing(self, video_id: UUID) -> Video | None:
        pass

    @abstractmethod
    def update_metadata(
        self,
        video_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        is_registered_only: bool | None = None,
        edited: bool | None = None,
        category_ids: list[UUID] | None = None,
        tag_ids: list[UUID] | None = None,
        source_created_at: datetime | None = None,
        source_created_at_set: bool = False,
        source_updated_at: datetime | None = None,
        source_updated_at_set: bool = False,
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
    def count_user_reactions(self, video_id: UUID, user_id: UUID) -> int:
        pass

    @abstractmethod
    def has_user_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> bool:
        pass

    @abstractmethod
    def get_reaction_counts(self, video_id: UUID) -> dict[str, int]:
        pass


class VideoCategoryRepository(ABC):
    @abstractmethod
    def list(self) -> list[VideoCategory]:
        pass

    @abstractmethod
    def search(self, *, name: str | None = None) -> list[VideoCategory]:
        pass

    @abstractmethod
    def get_by_id(self, category_id: UUID) -> VideoCategory | None:
        pass

    @abstractmethod
    def create(self, category: VideoCategoryCreate) -> VideoCategory:
        pass

    @abstractmethod
    def update(self, category_id: UUID, category: VideoCategoryCreate) -> VideoCategory | None:
        pass

    @abstractmethod
    def delete(self, category_id: UUID) -> bool:
        pass

    @abstractmethod
    def upsert_steam_category(self, category: VideoCategoryCreate) -> VideoCategory:
        pass


class VideoTagRepository(ABC):
    @abstractmethod
    def list(self) -> list[VideoTag]:
        pass

    @abstractmethod
    def get_by_id(self, tag_id: UUID) -> VideoTag | None:
        pass

    @abstractmethod
    def search(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> list[VideoTag]:
        pass

    @abstractmethod
    def create(self, tag: VideoTagCreate) -> VideoTag:
        pass

    @abstractmethod
    def update(self, tag_id: UUID, tag: VideoTagCreate) -> VideoTag | None:
        pass

    @abstractmethod
    def delete(self, tag_id: UUID) -> bool:
        pass


class VideoStorage(ABC):
    @abstractmethod
    def save_original(
        self,
        *,
        video_id: UUID,
        original_filename: str,
        content_type: str | None,
        file: BinaryIO,
    ) -> None:
        pass

    @abstractmethod
    def delete_original(self, video_id: UUID) -> None:
        pass

    @abstractmethod
    def delete_video_files(self, video_id: UUID) -> None:
        pass

    @abstractmethod
    def delete_processing_outputs(self, video_id: UUID) -> None:
        pass

    @abstractmethod
    def get_original_path(self, video_id: UUID) -> Path | None:
        pass

    @abstractmethod
    def get_variant_path(self, video_id: UUID, variant_type: VideoVariantType) -> Path | None:
        pass

    @abstractmethod
    def get_thumbnail_path(self, video_id: UUID) -> Path | None:
        pass


class VideoTranscoder(ABC):
    @abstractmethod
    def transcode(self, video_id: UUID) -> VideoProcessingResult:
        pass


class VideoProcessingQueue(ABC):
    @abstractmethod
    def enqueue(self, video_id: UUID, *, force: bool = False) -> None:
        pass
