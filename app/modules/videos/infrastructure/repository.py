from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.videos.domain.ports import (
    VideoCategoryRepository,
    VideoListFilters,
    VideoListResult,
    VideoRepository,
)
from app.modules.videos.domain.video import (
    Video,
    VideoCategory,
    VideoCategoryCreate,
    VideoCreate,
    VideoProcessingResult,
    VideoProcessingStatus,
    VideoReaction,
)
from app.modules.videos.infrastructure.mappers import (
    video_category_model_to_domain,
    video_reaction_model_to_domain,
    video_create_to_model,
    video_model_to_domain,
)
from app.modules.videos.infrastructure.models import (
    VideoCategoryAssignmentModel,
    VideoCategoryModel,
    VideoFavoriteModel,
    VideoModel,
    VideoProcessingErrorModel,
    VideoReactionModel,
    VideoTagAssignmentModel,
    VideoTagModel,
    VideoVariantModel,
)


class SqlAlchemyVideoCategoryRepository(VideoCategoryRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[VideoCategory]:
        models = self.session.scalars(
            select(VideoCategoryModel).order_by(VideoCategoryModel.name.asc())
        ).all()

        return [video_category_model_to_domain(model) for model in models]

    def get_by_id(self, category_id: UUID) -> VideoCategory | None:
        model = self.session.get(VideoCategoryModel, str(category_id))
        if model is None:
            return None

        return video_category_model_to_domain(model)

    def create(self, category: VideoCategoryCreate) -> VideoCategory:
        model = VideoCategoryModel(
            name=category.name,
            source=category.source.value,
            steam_appid=category.steam_appid,
            steamgriddb_game_id=category.steamgriddb_game_id,
            thumbnail_vertical_url=category.thumbnail_vertical_url,
            thumbnail_horizontal_url=category.thumbnail_horizontal_url,
            thumbnail_vertical_image=category.thumbnail_vertical_image,
            thumbnail_vertical_content_type=category.thumbnail_vertical_content_type,
            thumbnail_horizontal_image=category.thumbnail_horizontal_image,
            thumbnail_horizontal_content_type=category.thumbnail_horizontal_content_type,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)

        return video_category_model_to_domain(model)

    def update(self, category_id: UUID, category: VideoCategoryCreate) -> VideoCategory | None:
        model = self.session.get(VideoCategoryModel, str(category_id))
        if model is None:
            return None
        model.name = category.name
        model.thumbnail_vertical_url = category.thumbnail_vertical_url
        model.thumbnail_horizontal_url = category.thumbnail_horizontal_url
        model.thumbnail_vertical_image = category.thumbnail_vertical_image
        model.thumbnail_vertical_content_type = category.thumbnail_vertical_content_type
        model.thumbnail_horizontal_image = category.thumbnail_horizontal_image
        model.thumbnail_horizontal_content_type = category.thumbnail_horizontal_content_type
        self.session.commit()
        self.session.refresh(model)
        return video_category_model_to_domain(model)

    def delete(self, category_id: UUID) -> bool:
        model = self.session.get(VideoCategoryModel, str(category_id))
        if model is None:
            return False
        self.session.delete(model)
        self.session.commit()
        return True

    def upsert_steam_category(self, category: VideoCategoryCreate) -> VideoCategory:
        model = None
        if category.steam_appid is not None:
            model = self.session.scalar(
                select(VideoCategoryModel).where(
                    VideoCategoryModel.steam_appid == category.steam_appid
                )
            )
        if model is None and category.steamgriddb_game_id is not None:
            model = self.session.scalar(
                select(VideoCategoryModel).where(
                    VideoCategoryModel.steamgriddb_game_id
                    == category.steamgriddb_game_id
                )
            )
        if model is None:
            model = self.session.scalar(
                select(VideoCategoryModel).where(VideoCategoryModel.name == category.name)
            )

        if model is None:
            return self.create(category)

        model.name = category.name
        model.source = category.source.value
        model.steam_appid = category.steam_appid
        model.steamgriddb_game_id = category.steamgriddb_game_id
        model.thumbnail_vertical_url = category.thumbnail_vertical_url
        model.thumbnail_horizontal_url = category.thumbnail_horizontal_url
        self.session.commit()
        self.session.refresh(model)

        return video_category_model_to_domain(model)


class SqlAlchemyVideoRepository(VideoRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, video_id: UUID) -> Video | None:
        model = self._get_model(video_id)

        if model is None:
            return None

        return video_model_to_domain(model)

    def list_visible(
        self,
        *,
        current_user_id: UUID | None,
        filters: VideoListFilters,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        conditions = self._list_conditions(current_user_id, filters)
        statement = (
            select(VideoModel)
            .where(*conditions)
            .options(
                selectinload(VideoModel.category_assignments).selectinload(
                    VideoCategoryAssignmentModel.category,
                ),
                selectinload(VideoModel.tag_assignments).selectinload(
                    VideoTagAssignmentModel.tag,
                ),
                selectinload(VideoModel.variants),
                selectinload(VideoModel.processing_errors),
                selectinload(VideoModel.owner),
            )
            .order_by(
                self._popularity_score_expression().desc(),
                VideoModel.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        count_statement = select(func.count(VideoModel.id)).where(*conditions)
        models = self.session.scalars(statement).all()
        total = self.session.scalar(count_statement) or 0

        return VideoListResult(
            items=[video_model_to_domain(model) for model in models],
            total=total,
        )

    def create(self, video: VideoCreate) -> Video:
        model = video_create_to_model(video)
        self.session.add(model)
        self.session.flush()

        self._replace_category_assignments(model, video.category_ids)
        self._replace_tag_assignments(model, video.tags)

        video_id = UUID(model.id)
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

    def mark_processing(self, video_id: UUID) -> Video | None:
        model = self._get_model(video_id)
        if model is None:
            return None

        model.processing_status = VideoProcessingStatus.PROCESSING.value
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

    def mark_processed(
        self,
        video_id: UUID,
        result: VideoProcessingResult,
    ) -> Video | None:
        model = self._get_model(video_id)
        if model is None:
            return None

        model.processing_status = VideoProcessingStatus.READY.value
        model.width = result.width
        model.height = result.height
        model.aspect_ratio = result.aspect_ratio.value
        model.duration_seconds = result.duration_seconds
        model.thumbnail_path = result.thumbnail_path
        model.variants.clear()
        self.session.flush()
        model.variants.extend(
            [
                VideoVariantModel(
                    video_id=model.id,
                    variant_type=variant.variant_type.value,
                    codec=variant.codec,
                    container=variant.container,
                    width=variant.width,
                    height=variant.height,
                    bitrate_kbps=variant.bitrate_kbps,
                    size_bytes=variant.size_bytes,
                    path=variant.path,
                )
                for variant in result.variants
            ]
        )
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

    def mark_failed(
        self,
        video_id: UUID,
        *,
        error_type: str,
        error_message: str,
        job_id: str | None,
        duration_ms: float | None,
    ) -> Video | None:
        model = self._get_model(video_id)
        if model is None:
            return None

        model.processing_status = VideoProcessingStatus.FAILED.value
        model.processing_errors.append(
            VideoProcessingErrorModel(
                video_id=model.id,
                attempt=len(model.processing_errors) + 1,
                error_type=error_type,
                error_message=error_message,
                job_id=job_id,
                duration_ms=duration_ms,
            )
        )
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

    def reset_processing(self, video_id: UUID) -> Video | None:
        model = self._get_model(video_id)
        if model is None:
            return None

        model.processing_status = VideoProcessingStatus.PENDING.value
        model.width = None
        model.height = None
        model.aspect_ratio = None
        model.duration_seconds = None
        model.thumbnail_path = None
        model.variants.clear()
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

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
        model = self._get_model(video_id)

        if model is None:
            return None

        if title is not None:
            model.title = title
        if description is not None:
            model.description = description
        if is_registered_only is not None:
            model.is_registered_only = is_registered_only
        if category_ids is not None:
            self._replace_category_assignments(model, category_ids)
        if tags is not None:
            self._replace_tag_assignments(model, tags)

        model.edited = True
        model.edited_at = datetime.now(timezone.utc)
        self.session.commit()
        model = self._get_model(video_id)

        return video_model_to_domain(model)

    def delete(self, video_id: UUID) -> bool:
        model = self._get_model(video_id)

        if model is None:
            return False

        self.session.delete(model)
        self.session.commit()

        return True

    def add_favorite(self, video_id: UUID, user_id: UUID) -> None:
        model = VideoFavoriteModel(video_id=str(video_id), user_id=str(user_id))
        video_model = self.session.scalar(
            select(VideoModel).where(VideoModel.id == str(video_id))
        )
        if video_model is None:
            return

        self.session.add(model)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            return

        video_model.favorite_count += 1
        self.session.commit()

    def remove_favorite(self, video_id: UUID, user_id: UUID) -> None:
        model = self.session.scalar(
            select(VideoFavoriteModel).where(
                VideoFavoriteModel.video_id == str(video_id),
                VideoFavoriteModel.user_id == str(user_id),
            )
        )
        if model is None:
            return

        video_model = self.session.scalar(
            select(VideoModel).where(VideoModel.id == str(video_id))
        )
        self.session.delete(model)
        if video_model is not None:
            video_model.favorite_count = max(video_model.favorite_count - 1, 0)
        self.session.commit()

    def list_favorites(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> VideoListResult:
        statement = (
            select(VideoModel)
            .join(VideoFavoriteModel, VideoFavoriteModel.video_id == VideoModel.id)
            .where(VideoFavoriteModel.user_id == str(user_id))
            .options(
                selectinload(VideoModel.category_assignments).selectinload(
                    VideoCategoryAssignmentModel.category,
                ),
                selectinload(VideoModel.tag_assignments).selectinload(
                    VideoTagAssignmentModel.tag,
                ),
                selectinload(VideoModel.variants),
                selectinload(VideoModel.processing_errors),
                selectinload(VideoModel.owner),
            )
            .order_by(VideoFavoriteModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_statement = select(func.count(VideoFavoriteModel.id)).where(
            VideoFavoriteModel.user_id == str(user_id)
        )
        models = self.session.scalars(statement).all()
        total = self.session.scalar(count_statement) or 0

        return VideoListResult(
            items=[video_model_to_domain(model) for model in models],
            total=total,
        )

    def is_favorite(self, video_id: UUID, user_id: UUID) -> bool:
        statement = select(VideoFavoriteModel.id).where(
            VideoFavoriteModel.video_id == str(video_id),
            VideoFavoriteModel.user_id == str(user_id),
        )

        return self.session.scalar(statement) is not None

    def set_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> VideoReaction:
        model = self.session.scalar(
            select(VideoReactionModel).where(
                VideoReactionModel.video_id == str(video_id),
                VideoReactionModel.user_id == str(user_id),
                VideoReactionModel.reaction_type == reaction_type,
            )
        )
        if model is None:
            model = VideoReactionModel(
                video_id=str(video_id),
                user_id=str(user_id),
                reaction_type=reaction_type,
            )
            self.session.add(model)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            model = self.session.scalar(
                select(VideoReactionModel).where(
                    VideoReactionModel.video_id == str(video_id),
                    VideoReactionModel.user_id == str(user_id),
                    VideoReactionModel.reaction_type == reaction_type,
                )
            )
            if model is None:
                raise
        self.session.refresh(model)

        return video_reaction_model_to_domain(model)

    def remove_reaction(self, video_id: UUID, user_id: UUID) -> None:
        models = self.session.scalars(
            select(VideoReactionModel).where(
                VideoReactionModel.video_id == str(video_id),
                VideoReactionModel.user_id == str(user_id),
            )
        ).all()
        if not models:
            return

        for model in models:
            self.session.delete(model)
        self.session.commit()

    def count_user_reactions(self, video_id: UUID, user_id: UUID) -> int:
        statement = select(func.count(VideoReactionModel.id)).where(
            VideoReactionModel.video_id == str(video_id),
            VideoReactionModel.user_id == str(user_id),
        )

        return self.session.scalar(statement) or 0

    def has_user_reaction(
        self,
        video_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> bool:
        statement = select(VideoReactionModel.id).where(
            VideoReactionModel.video_id == str(video_id),
            VideoReactionModel.user_id == str(user_id),
            VideoReactionModel.reaction_type == reaction_type,
        )

        return self.session.scalar(statement) is not None

    def get_reaction_counts(self, video_id: UUID) -> dict[str, int]:
        statement = (
            select(VideoReactionModel.reaction_type, func.count(VideoReactionModel.id))
            .where(VideoReactionModel.video_id == str(video_id))
            .group_by(VideoReactionModel.reaction_type)
        )

        return {reaction_type: count for reaction_type, count in self.session.execute(statement)}

    def _get_model(self, video_id: UUID) -> VideoModel | None:
        statement = (
            select(VideoModel)
            .where(VideoModel.id == str(video_id))
            .options(
                selectinload(VideoModel.category_assignments).selectinload(
                    VideoCategoryAssignmentModel.category,
                ),
                selectinload(VideoModel.tag_assignments).selectinload(
                    VideoTagAssignmentModel.tag,
                ),
                selectinload(VideoModel.variants),
                selectinload(VideoModel.processing_errors),
                selectinload(VideoModel.owner),
            )
        )

        return self.session.scalar(statement)

    def _list_conditions(
        self,
        current_user_id: UUID | None,
        filters: VideoListFilters,
    ) -> list:
        conditions = []
        if current_user_id is None:
            conditions.append(VideoModel.is_registered_only.is_(False))
        if filters.title:
            conditions.append(VideoModel.title.ilike(f"%{filters.title}%"))
        if filters.owner_id is not None:
            conditions.append(VideoModel.owner_id == str(filters.owner_id))
        if filters.category_ids:
            conditions.append(
                VideoModel.category_assignments.any(
                    VideoCategoryAssignmentModel.category_id.in_(
                        [str(category_id) for category_id in filters.category_ids]
                    )
                )
            )
        if filters.tags:
            tag_names = [tag.strip() for tag in filters.tags if tag.strip()]
            if tag_names:
                conditions.append(
                    VideoModel.tag_assignments.any(
                        VideoTagAssignmentModel.tag.has(VideoTagModel.name.in_(tag_names))
                    )
                )

        return conditions

    def _popularity_score_expression(self):
        total_favorites = VideoModel.favorite_count
        return VideoModel.favorite_count * 3 + total_favorites

    def _replace_category_assignments(
        self,
        model: VideoModel,
        category_ids: list[UUID],
    ) -> None:
        model.category_assignments.clear()
        self.session.flush()
        model.category_assignments.extend(
            [
                VideoCategoryAssignmentModel(
                    video_id=model.id,
                    category_id=str(category_id),
                )
                for category_id in category_ids
            ]
        )

    def _replace_tag_assignments(self, model: VideoModel, tags: list[str]) -> None:
        model.tag_assignments.clear()
        self.session.flush()
        model.tag_assignments.extend(
            [
                VideoTagAssignmentModel(
                    video_id=model.id,
                    tag_id=self._get_or_create_tag(tag).id,
                )
                for tag in dict.fromkeys(
                    normalized for normalized in map(str.strip, tags) if normalized
                )
            ]
        )

    def _get_or_create_tag(self, name: str) -> VideoTagModel:
        statement = select(VideoTagModel).where(VideoTagModel.name == name)
        model = self.session.scalar(statement)

        if model is not None:
            return model

        model = VideoTagModel(name=name)
        self.session.add(model)
        self.session.flush()

        return model
