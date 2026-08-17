from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.admin.entrypoints.schemas import (
    AdminAuditEntryResponse,
    AdminConfigEntryResponse,
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
from app.modules.videos.domain.ports import (
    VIDEO_LIST_DEFAULT_SORT_BY,
    VIDEO_LIST_DEFAULT_SORT_DIRECTION,
    VIDEO_LIST_SORT_DIRECTIONS,
    VIDEO_LIST_SORT_FIELDS,
    VideoProcessingQueue,
    VideoRepository,
    VideoStorage,
)
from app.modules.videos.domain.video import VideoProcessingStatus
from app.modules.videos.wiring import (
    get_delete_video,
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)
from config.settings import settings


router = APIRouter(prefix="/admin", tags=["admin"])


SAFE_CONFIG_FIELDS: tuple[tuple[str, str], ...] = (
    ("app_name", "Aplicacion"),
    ("app_version", "Aplicacion"),
    ("app_env", "Aplicacion"),
    ("app_debug", "Aplicacion"),
    ("log_level", "Logging"),
    ("log_format", "Logging"),
    ("jwt_algorithm", "Auth"),
    ("access_token_expire_minutes", "Auth"),
    ("oidc_enabled", "Auth"),
    ("oidc_scope", "Auth"),
    ("oidc_frontend_callback_path", "Auth"),
    ("oidc_default_role", "Auth"),
    ("max_video_size_bytes", "Videos"),
    ("max_video_duration_seconds", "Videos"),
    ("max_video_tags", "Videos"),
    ("max_video_reactions_per_user", "Videos"),
    ("video_allowed_mime_types", "Videos"),
    ("video_processing_queue_name", "Procesamiento"),
    ("video_processing_max_attempts", "Procesamiento"),
    ("video_processing_job_timeout_seconds", "Procesamiento"),
    ("discord_webhook_enabled", "Integraciones"),
)


def _resolve_video_sort(sort_by: str, sort_direction: str) -> tuple[str, str]:
    normalized_sort_by = sort_by.strip()
    normalized_sort_direction = sort_direction.strip().lower()
    if normalized_sort_by not in VIDEO_LIST_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"sort_by must be one of: {', '.join(VIDEO_LIST_SORT_FIELDS)}",
        )
    if normalized_sort_direction not in VIDEO_LIST_SORT_DIRECTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="sort_direction must be asc or desc",
        )

    return normalized_sort_by, normalized_sort_direction


def _fields_set(request) -> set[str]:
    fields_set = getattr(request, "model_fields_set", None)
    if fields_set is not None:
        return fields_set
    return getattr(request, "__fields_set__", set())


def _config_value_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "list"
    if value is None:
        return "empty"
    return "string"


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> AdminDashboardResponse:
    return read_model.dashboard()


@router.get("/config", response_model=list[AdminConfigEntryResponse])
def admin_config(
    _current_user: User = Depends(require_admin),
) -> list[AdminConfigEntryResponse]:
    return [
        AdminConfigEntryResponse(
            key=key,
            value=getattr(settings, key),
            value_type=_config_value_type(getattr(settings, key)),
            category=category,
        )
        for key, category in SAFE_CONFIG_FIELDS
    ]


@router.get("/videos", response_model=list[AdminVideoSummaryResponse])
def admin_list_videos(
    status_filter: VideoProcessingStatus | None = Query(default=None, alias="status"),
    title: str | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    owner: str | None = Query(default=None),
    visibility: str | None = Query(default=None, pattern="^(public|registered)$"),
    sort_by: str = Query(default=VIDEO_LIST_DEFAULT_SORT_BY),
    sort_direction: str = Query(default=VIDEO_LIST_DEFAULT_SORT_DIRECTION),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminVideoSummaryResponse]:
    resolved_sort_by, resolved_sort_direction = _resolve_video_sort(
        sort_by,
        sort_direction,
    )
    return read_model.list_videos(
        status=status_filter,
        title=title,
        owner_id=owner_id,
        owner=owner,
        visibility=visibility,
        sort_by=resolved_sort_by,
        sort_direction=resolved_sort_direction,
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
    event_type: str | None = Query(default=None),
    worker_name: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminWorkerEventResponse]:
    return read_model.worker_events(
        video_id=video_id,
        job_id=job_id,
        level=level,
        event_type=event_type,
        worker_name=worker_name,
        search=search,
        created_from=created_from,
        created_to=created_to,
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
