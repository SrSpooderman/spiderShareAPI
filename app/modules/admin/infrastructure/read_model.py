from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.admin.entrypoints.schemas import (
    AdminAuditEntryResponse,
    AdminDashboardResponse,
    AdminDashboardTotalsResponse,
    AdminProcessingErrorResponse,
    AdminRawLogLineResponse,
    AdminServiceStatusResponse,
    AdminUserResponse,
    AdminVideoDetailResponse,
    AdminVideoSummaryResponse,
    AdminVideoVariantResponse,
    AdminWorkerEventResponse,
)
from app.modules.users.infrastructure.models import UserModel
from app.modules.videos.domain.video import VideoProcessingStatus
from app.modules.videos.infrastructure.models import (
    VideoCategoryAssignmentModel,
    VideoModel,
    VideoProcessingErrorModel,
    VideoTagAssignmentModel,
)


class AdminReadModel:
    def dashboard(self) -> AdminDashboardResponse:
        raise NotImplementedError

    def list_videos(
        self,
        *,
        status: VideoProcessingStatus | None = None,
        title: str | None = None,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminVideoSummaryResponse]:
        raise NotImplementedError

    def get_video(self, video_id: UUID) -> AdminVideoDetailResponse | None:
        raise NotImplementedError

    def worker_events(
        self,
        *,
        video_id: UUID | None = None,
        job_id: str | None = None,
        level: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminWorkerEventResponse]:
        raise NotImplementedError

    def users(self) -> list[AdminUserResponse]:
        raise NotImplementedError

    def audit_entries(self) -> list[AdminAuditEntryResponse]:
        raise NotImplementedError

    def raw_logs(self) -> list[AdminRawLogLineResponse]:
        raise NotImplementedError


class SqlAlchemyAdminReadModel(AdminReadModel):
    def __init__(self, session: Session, queue_inspector) -> None:
        self.session = session
        self.queue_inspector = queue_inspector

    def dashboard(self) -> AdminDashboardResponse:
        queue_summary = self.queue_inspector.summary()
        counts = self._video_status_counts()
        services = [
            AdminServiceStatusResponse(name="API", status="ok", detail="Responding"),
            AdminServiceStatusResponse(name="MySQL", status="ok", detail="Session ready"),
            AdminServiceStatusResponse(
                name="Redis",
                status=queue_summary["redis_status"],
                detail=queue_summary["redis_detail"],
            ),
            AdminServiceStatusResponse(
                name="Worker",
                status=queue_summary["worker_status"],
                detail=queue_summary["worker_detail"],
            ),
        ]

        return AdminDashboardResponse(
            totals=AdminDashboardTotalsResponse(
                videos=sum(counts.values()),
                pending=counts[VideoProcessingStatus.PENDING.value],
                processing=counts[VideoProcessingStatus.PROCESSING.value],
                ready=counts[VideoProcessingStatus.READY.value],
                failed=counts[VideoProcessingStatus.FAILED.value],
                queued_jobs=queue_summary["queued_jobs"],
                active_jobs=queue_summary["active_jobs"],
                failed_jobs=queue_summary["failed_jobs"],
            ),
            services=services,
            recent_failures=self.list_videos(
                status=VideoProcessingStatus.FAILED,
                limit=5,
            ),
            recent_uploads=self.list_videos(limit=5),
        )

    def list_videos(
        self,
        *,
        status: VideoProcessingStatus | None = None,
        title: str | None = None,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminVideoSummaryResponse]:
        statement = (
            select(VideoModel)
            .options(
                selectinload(VideoModel.owner),
                selectinload(VideoModel.processing_errors),
            )
            .order_by(VideoModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conditions = []
        if status is not None:
            conditions.append(VideoModel.processing_status == status.value)
        if title:
            conditions.append(VideoModel.title.ilike(f"%{title}%"))
        if owner_id is not None:
            conditions.append(VideoModel.owner_id == str(owner_id))
        if conditions:
            statement = statement.where(*conditions)

        return [self._video_summary(model) for model in self.session.scalars(statement).all()]

    def get_video(self, video_id: UUID) -> AdminVideoDetailResponse | None:
        statement = (
            select(VideoModel)
            .where(VideoModel.id == str(video_id))
            .options(
                selectinload(VideoModel.owner),
                selectinload(VideoModel.processing_errors),
                selectinload(VideoModel.variants),
                selectinload(VideoModel.category_assignments).selectinload(
                    VideoCategoryAssignmentModel.category,
                ),
                selectinload(VideoModel.tag_assignments).selectinload(
                    VideoTagAssignmentModel.tag,
                ),
            )
        )
        model = self.session.scalar(statement)
        if model is None:
            return None

        summary = self._video_summary(model)
        return AdminVideoDetailResponse(
            **summary.model_dump(),
            original_filename=model.original_filename,
            width=model.width,
            height=model.height,
            thumbnail_path=model.thumbnail_path,
            variants=[
                AdminVideoVariantResponse(
                    type=variant.variant_type,
                    codec=variant.codec,
                    width=variant.width,
                    height=variant.height,
                    size_bytes=variant.size_bytes,
                )
                for variant in model.variants
            ],
        )

    def worker_events(
        self,
        *,
        video_id: UUID | None = None,
        job_id: str | None = None,
        level: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminWorkerEventResponse]:
        statement = (
            select(VideoProcessingErrorModel)
            .order_by(VideoProcessingErrorModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conditions = []
        if video_id is not None:
            conditions.append(VideoProcessingErrorModel.video_id == str(video_id))
        if job_id:
            conditions.append(VideoProcessingErrorModel.job_id == job_id)
        if conditions:
            statement = statement.where(*conditions)

        events = [
            AdminWorkerEventResponse(
                id=f"processing-error-{model.id}",
                event_type="video.processing.failed",
                level="error",
                message=model.error_message,
                video_id=UUID(model.video_id),
                job_id=model.job_id,
                worker_name="jaimito_worker",
                created_at=model.created_at,
            )
            for model in self.session.scalars(statement).all()
        ]
        if level is not None:
            events = [event for event in events if event.level == level]
        return events

    def users(self) -> list[AdminUserResponse]:
        video_counts = {
            owner_id: count
            for owner_id, count in self.session.execute(
                select(VideoModel.owner_id, func.count(VideoModel.id)).group_by(
                    VideoModel.owner_id,
                )
            )
        }
        statement = select(UserModel).order_by(UserModel.created_at.desc())
        return [
            AdminUserResponse(
                id=UUID(model.id),
                username=model.username,
                display_name=model.display_name,
                role=model.role,
                is_active=model.is_active,
                video_count=video_counts.get(model.id, 0),
            )
            for model in self.session.scalars(statement).all()
        ]

    def audit_entries(self) -> list[AdminAuditEntryResponse]:
        return []

    def raw_logs(self) -> list[AdminRawLogLineResponse]:
        return [
            AdminRawLogLineResponse(
                line="Raw worker logs are not configured yet; use /admin/worker/events.",
                source="system",
                created_at=datetime.now(timezone.utc),
            )
        ]

    def _video_status_counts(self) -> dict[str, int]:
        counts = {
            VideoProcessingStatus.PENDING.value: 0,
            VideoProcessingStatus.PROCESSING.value: 0,
            VideoProcessingStatus.READY.value: 0,
            VideoProcessingStatus.FAILED.value: 0,
        }
        statement = select(VideoModel.processing_status, func.count(VideoModel.id)).group_by(
            VideoModel.processing_status,
        )
        for status, count in self.session.execute(statement):
            counts[status] = count
        return counts

    def _video_summary(self, model: VideoModel) -> AdminVideoSummaryResponse:
        latest_error = model.processing_errors[-1] if model.processing_errors else None
        return AdminVideoSummaryResponse(
            id=UUID(model.id),
            title=model.title,
            owner_username=model.owner.username if model.owner is not None else "-",
            owner_id=UUID(model.owner_id),
            processing_status=VideoProcessingStatus(model.processing_status),
            visibility="registered" if model.is_registered_only else "public",
            duration_seconds=model.duration_seconds,
            created_at=model.created_at,
            latest_processing_error=(
                AdminProcessingErrorResponse(
                    id=UUID(latest_error.id),
                    video_id=UUID(latest_error.video_id),
                    attempt=latest_error.attempt,
                    error_type=latest_error.error_type,
                    error_message=latest_error.error_message,
                    job_id=latest_error.job_id,
                    duration_ms=latest_error.duration_ms,
                    created_at=latest_error.created_at,
                )
                if latest_error is not None
                else None
            ),
        )
