from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.admin.entrypoints.schemas import (
    AdminAuditEntryResponse,
    AdminDashboardResponse,
    AdminQueueJobResponse,
    AdminRawLogLineResponse,
    AdminUserDetailResponse,
    AdminUserUpdateRequest,
    AdminUserResponse,
    AdminVideoDetailResponse,
    AdminVideoSummaryResponse,
    AdminWorkerEventResponse,
)
from app.modules.admin.infrastructure.events import AdminEventRecorder
from app.modules.admin.infrastructure.queue import AdminQueueInspector
from app.modules.admin.infrastructure.read_model import AdminReadModel
from app.modules.admin.wiring import (
    get_admin_event_recorder,
    get_admin_queue_inspector,
    get_admin_read_model,
)
from app.modules.auth.wiring import require_admin, require_super_admin
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.user import User, UserRole, can_create_user_with_role, can_manage_user
from app.modules.users.wiring import get_user_repository
from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.errors import VideoNotFoundError, VideoPermissionError
from app.modules.videos.domain.ports import VideoProcessingQueue, VideoRepository, VideoStorage
from app.modules.videos.domain.video import VideoProcessingStatus
from app.modules.videos.wiring import (
    get_delete_video,
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)


router = APIRouter(prefix="/admin", tags=["admin"])


def _fields_set(request) -> set[str]:
    fields_set = getattr(request, "model_fields_set", None)
    if fields_set is not None:
        return fields_set
    return getattr(request, "__fields_set__", set())


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> AdminDashboardResponse:
    return read_model.dashboard()


@router.get("/videos", response_model=list[AdminVideoSummaryResponse])
def admin_list_videos(
    status_filter: VideoProcessingStatus | None = Query(default=None, alias="status"),
    title: str | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    owner: str | None = Query(default=None),
    visibility: str | None = Query(default=None, pattern="^(public|registered)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminVideoSummaryResponse]:
    return read_model.list_videos(
        status=status_filter,
        title=title,
        owner_id=owner_id,
        owner=owner,
        visibility=visibility,
        limit=limit,
        offset=offset,
    )


@router.get("/videos/{video_id}", response_model=AdminVideoDetailResponse)
def admin_get_video(
    video_id: UUID,
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> AdminVideoDetailResponse:
    video = read_model.get_video(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    return video


@router.post("/videos/{video_id}/processing/retry", response_model=AdminVideoDetailResponse)
def admin_retry_video_processing(
    video_id: UUID,
    current_user: User = Depends(require_super_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
    video_processing_queue: VideoProcessingQueue = Depends(get_video_processing_queue),
) -> AdminVideoDetailResponse:
    video = video_repository.get_by_id(video_id)
    if video is None:
        event_recorder.audit(
            actor=current_user,
            action="processing.retry.requested",
            entity_type="video",
            entity_id=video_id,
            result="failed",
            metadata={"reason": "not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    if video.processing_status == VideoProcessingStatus.READY:
        event_recorder.audit(
            actor=current_user,
            action="processing.retry.requested",
            entity_type="video",
            entity_id=video_id,
            result="failed",
            metadata={"reason": "already_ready"},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video processing is already complete",
        )

    try:
        video_storage.delete_processing_outputs(video_id)
        if video_repository.reset_processing(video_id) is None:
            event_recorder.audit(
                actor=current_user,
                action="processing.retry.requested",
                entity_type="video",
                entity_id=video_id,
                result="failed",
                metadata={"reason": "not_found_after_reset"},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )
        video_processing_queue.enqueue(video_id, force=True)
    except HTTPException:
        raise
    except Exception as error:
        event_recorder.audit(
            actor=current_user,
            action="processing.retry.requested",
            entity_type="video",
            entity_id=video_id,
            result="failed",
            metadata={"reason": type(error).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video processing queue is unavailable",
        )

    event_recorder.audit(
        actor=current_user,
        action="processing.retry.requested",
        entity_type="video",
        entity_id=video_id,
        result="success",
        metadata={"previous_status": video.processing_status.value},
    )
    event_recorder.worker_event(
        event_type="processing.retry.requested",
        level="info",
        message=f"Processing retry requested by {current_user.username}",
        video_id=video_id,
        job_id=f"video-processing-{video_id}",
        metadata={
            "actor_user_id": str(current_user.id),
            "previous_status": video.processing_status.value,
        },
    )

    refreshed = read_model.get_video(video_id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    return refreshed


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_video(
    video_id: UUID,
    current_user: User = Depends(require_super_admin),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
    delete_video_use_case: DeleteVideo = Depends(get_delete_video),
) -> Response:
    try:
        delete_video_use_case.execute(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError):
        event_recorder.audit(
            actor=current_user,
            action="video.delete",
            entity_type="video",
            entity_id=video_id,
            result="failed",
            metadata={"reason": "not_found_or_forbidden"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    event_recorder.audit(
        actor=current_user,
        action="video.delete",
        entity_type="video",
        entity_id=video_id,
        result="success",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/worker/events", response_model=list[AdminWorkerEventResponse])
def admin_worker_events(
    video_id: UUID | None = Query(default=None),
    job_id: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminWorkerEventResponse]:
    return read_model.worker_events(
        video_id=video_id,
        job_id=job_id,
        level=level,
        limit=limit,
        offset=offset,
    )


@router.get("/worker/logs", response_model=list[AdminRawLogLineResponse])
def admin_worker_logs(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminRawLogLineResponse]:
    return read_model.raw_logs(limit=limit, offset=offset)


@router.get("/queue/jobs", response_model=list[AdminQueueJobResponse])
def admin_queue_jobs(
    _current_user: User = Depends(require_admin),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
) -> list[AdminQueueJobResponse]:
    return queue_inspector.jobs()


@router.post("/queue/jobs/{job_id}/requeue", response_model=AdminQueueJobResponse)
def admin_requeue_job(
    job_id: str,
    current_user: User = Depends(require_super_admin),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
) -> AdminQueueJobResponse:
    job = queue_inspector.requeue_job(job_id)
    if job is None:
        event_recorder.audit(
            actor=current_user,
            action="queue.job.requeue",
            entity_type="queue_job",
            entity_id=job_id,
            result="failed",
            metadata={"reason": "not_found_or_unqueueable"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or cannot be requeued",
        )

    event_recorder.audit(
        actor=current_user,
        action="queue.job.requeue",
        entity_type="queue_job",
        entity_id=job_id,
        result="success",
        metadata={"video_id": job.video_id},
    )
    event_recorder.worker_event(
        event_type="queue.job.requeued",
        level="info",
        message=f"Queue job requeued by {current_user.username}",
        video_id=UUID(job.video_id) if job.video_id != "-" else None,
        job_id=job_id,
        metadata={"actor_user_id": str(current_user.id)},
    )
    return job


@router.delete("/queue/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_job(
    job_id: str,
    current_user: User = Depends(require_super_admin),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
) -> Response:
    deleted = queue_inspector.delete_job(job_id)
    if not deleted:
        event_recorder.audit(
            actor=current_user,
            action="queue.job.delete",
            entity_type="queue_job",
            entity_id=job_id,
            result="failed",
            metadata={"reason": "not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    event_recorder.audit(
        actor=current_user,
        action="queue.job.delete",
        entity_type="queue_job",
        entity_id=job_id,
        result="success",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/queue/failed-jobs", status_code=status.HTTP_204_NO_CONTENT)
def admin_clear_failed_jobs(
    current_user: User = Depends(require_super_admin),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
) -> Response:
    deleted = queue_inspector.clear_failed_jobs()
    event_recorder.audit(
        actor=current_user,
        action="queue.failed_jobs.clear",
        entity_type="queue",
        entity_id="failed_jobs",
        result="success",
        metadata={"deleted_jobs": deleted},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users", response_model=list[AdminUserResponse])
def admin_users(
    username: str | None = Query(default=None),
    role: str | None = Query(default=None, pattern="^(user|admin|super_admin)$"),
    is_active: bool | None = Query(default=None),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminUserResponse]:
    return read_model.users(username=username, role=role, is_active=is_active)


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def admin_get_user(
    user_id: UUID,
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> AdminUserDetailResponse:
    user = read_model.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch("/users/{user_id}", response_model=AdminUserDetailResponse)
def admin_update_user(
    user_id: UUID,
    request: AdminUserUpdateRequest,
    current_user: User = Depends(require_super_admin),
    event_recorder: AdminEventRecorder = Depends(get_admin_event_recorder),
    read_model: AdminReadModel = Depends(get_admin_read_model),
    user_repository: UserRepository = Depends(get_user_repository),
) -> AdminUserDetailResponse:
    target_user = user_repository.get_by_id(user_id)
    if target_user is None:
        event_recorder.audit(
            actor=current_user,
            action="user.update",
            entity_type="user",
            entity_id=user_id,
            result="failed",
            metadata={"reason": "not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    fields_set = _fields_set(request)
    if current_user.id == target_user.id and ({"role", "is_active"} & fields_set):
        event_recorder.audit(
            actor=current_user,
            action="user.update",
            entity_type="user",
            entity_id=user_id,
            result="failed",
            metadata={"reason": "self_role_or_status_change"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to change your own role or active status",
        )

    if not can_manage_user(current_user.role, target_user.role):
        event_recorder.audit(
            actor=current_user,
            action="user.update",
            entity_type="user",
            entity_id=user_id,
            result="failed",
            metadata={"reason": "target_not_manageable"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to manage that user",
        )

    if "role" in fields_set:
        if request.role == UserRole.SUPER_ADMIN:
            event_recorder.audit(
                actor=current_user,
                action="user.update",
                entity_type="user",
                entity_id=user_id,
                result="failed",
                metadata={"reason": "assign_super_admin"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to assign super admin role",
            )
        if request.role is not None and not can_create_user_with_role(current_user.role, request.role):
            event_recorder.audit(
                actor=current_user,
                action="user.update",
                entity_type="user",
                entity_id=user_id,
                result="failed",
                metadata={"reason": "role_not_assignable", "requested_role": request.role.value},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to assign that role",
            )

    updated_user = user_repository.update(
        user_id,
        role=request.role.value if request.role is not None else None,
        is_active=request.is_active if "is_active" in fields_set else None,
    )
    if updated_user is None:
        event_recorder.audit(
            actor=current_user,
            action="user.update",
            entity_type="user",
            entity_id=user_id,
            result="failed",
            metadata={"reason": "not_found_after_update"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    event_recorder.audit(
        actor=current_user,
        action="user.update",
        entity_type="user",
        entity_id=user_id,
        result="success",
        metadata={
            "previous_role": target_user.role.value,
            "new_role": updated_user.role.value,
            "previous_is_active": target_user.is_active,
            "new_is_active": updated_user.is_active,
        },
    )

    refreshed = read_model.get_user(user_id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return refreshed


@router.get("/audit", response_model=list[AdminAuditEntryResponse])
def admin_audit(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminAuditEntryResponse]:
    return read_model.audit_entries(limit=limit, offset=offset)
