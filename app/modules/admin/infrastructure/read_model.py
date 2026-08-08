import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.admin.entrypoints.schemas import (
    AdminAuditEntryResponse,
    AdminDashboardResponse,
    AdminDashboardTotalsResponse,
    AdminProcessingErrorResponse,
    AdminRawLogLineResponse,
    AdminUserDetailResponse,
    AdminServiceStatusResponse,
    AdminUserResponse,
    AdminVideoDetailResponse,
    AdminVideoSummaryResponse,
    AdminVideoVariantResponse,
    AdminWorkerEventResponse,
)
from app.modules.admin.infrastructure.models import (
    AdminAuditEntryModel,
    WorkerEventModel,
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
        owner: str | None = None,
        visibility: str | None = None,
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
        event_type: str | None = None,
        worker_name: str | None = None,
        search: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminWorkerEventResponse]:
        raise NotImplementedError

    def users(
        self,
        *,
        username: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[AdminUserResponse]:
        raise NotImplementedError

    def get_user(self, user_id: UUID) -> AdminUserDetailResponse | None:
        raise NotImplementedError

    def audit_entries(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminAuditEntryResponse]:
        raise NotImplementedError

    def raw_logs(
        self,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AdminRawLogLineResponse]:
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
        owner: str | None = None,
        visibility: str | None = None,
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
        if owner:
            conditions.append(VideoModel.owner.has(UserModel.username.ilike(f"%{owner}%")))
        if visibility == "public":
            conditions.append(VideoModel.is_registered_only.is_(False))
        if visibility == "registered":
            conditions.append(VideoModel.is_registered_only.is_(True))
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
        event_type: str | None = None,
        worker_name: str | None = None,
        search: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminWorkerEventResponse]:
        statement = (
            select(WorkerEventModel)
            .order_by(WorkerEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conditions = []
        if video_id is not None:
            conditions.append(WorkerEventModel.video_id == str(video_id))
        if job_id:
            conditions.append(WorkerEventModel.job_id == job_id)
        if level:
            conditions.append(WorkerEventModel.level == level)
        if event_type:
            conditions.append(WorkerEventModel.event_type == event_type)
        if worker_name:
            conditions.append(WorkerEventModel.worker_name == worker_name)
        if search:
            pattern = f"%{search}%"
            conditions.append(
                WorkerEventModel.event_type.ilike(pattern)
                | WorkerEventModel.message.ilike(pattern)
            )
        if created_from is not None:
            conditions.append(WorkerEventModel.created_at >= created_from)
        if created_to is not None:
            conditions.append(WorkerEventModel.created_at <= created_to)
        if conditions:
            statement = statement.where(*conditions)

        return [
            AdminWorkerEventResponse(
                id=model.id,
                event_type=model.event_type,
                level=model.level,
                message=model.message,
                video_id=UUID(model.video_id) if model.video_id is not None else None,
                job_id=model.job_id,
                worker_name=model.worker_name,
                metadata=model.metadata_json,
                created_at=model.created_at,
            )
            for model in self.session.scalars(statement).all()
        ]

    def users(
        self,
        *,
        username: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[AdminUserResponse]:
        video_counts = {
            owner_id: count
            for owner_id, count in self.session.execute(
                select(VideoModel.owner_id, func.count(VideoModel.id)).group_by(
                    VideoModel.owner_id,
                )
            )
        }
        statement = select(UserModel).order_by(UserModel.created_at.desc())
        conditions = []
        if username:
            conditions.append(UserModel.username.ilike(f"%{username}%"))
        if role:
            conditions.append(UserModel.role == role)
        if is_active is not None:
            conditions.append(UserModel.is_active.is_(is_active))
        if conditions:
            statement = statement.where(*conditions)
        return [
            self._user_summary(model, video_counts.get(model.id, 0))
            for model in self.session.scalars(statement).all()
        ]

    def get_user(self, user_id: UUID) -> AdminUserDetailResponse | None:
        model = self.session.scalar(select(UserModel).where(UserModel.id == str(user_id)))
        if model is None:
            return None

        video_count = self.session.scalar(
            select(func.count(VideoModel.id)).where(VideoModel.owner_id == model.id),
        )
        recent_videos = self.list_videos(owner_id=user_id, limit=5)
        summary = self._user_summary(model, int(video_count or 0))
        return AdminUserDetailResponse(
            **summary.model_dump(),
            oidc_subject=model.oidc_subject,
            oidc_groups=self._oidc_groups(model),
            last_login_at=model.last_login_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            recent_videos=recent_videos,
        )

    def audit_entries(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AdminAuditEntryResponse]:
        statement = (
            select(AdminAuditEntryModel)
            .order_by(AdminAuditEntryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            AdminAuditEntryResponse(
                id=model.id,
                actor_username=model.actor_username,
                action=model.action,
                entity=f"{model.entity_type}:{model.entity_id}",
                result=model.result,
                created_at=model.created_at,
            )
            for model in self.session.scalars(statement).all()
        ]

    def raw_logs(
        self,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AdminRawLogLineResponse]:
        statement = (
            select(WorkerEventModel)
            .order_by(WorkerEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            AdminRawLogLineResponse(
                line=(
                    f"event={model.event_type} level={model.level} "
                    f"worker={model.worker_name} video_id={model.video_id or '-'} "
                    f"job_id={model.job_id or '-'} message=\"{model.message}\""
                ),
                source="worker_events",
                created_at=model.created_at,
            )
            for model in self.session.scalars(statement).all()
        ]

    def _user_summary(self, model: UserModel, video_count: int) -> AdminUserResponse:
        return AdminUserResponse(
            id=UUID(model.id),
            username=model.username,
            display_name=model.display_name,
            auth_provider=model.auth_provider,
            oidc_email=model.oidc_email,
            oidc_name=model.oidc_name,
            role=model.role,
            is_active=model.is_active,
            video_count=video_count,
        )

    def _oidc_groups(self, model: UserModel) -> list[str]:
        if not model.oidc_groups:
            return []
        try:
            decoded = json.loads(model.oidc_groups)
        except json.JSONDecodeError:
            return []
        if not isinstance(decoded, list):
            return []
        return [str(group) for group in decoded if str(group).strip()]

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
            source_created_at=model.source_created_at,
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
