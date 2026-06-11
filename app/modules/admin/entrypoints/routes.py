from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.admin.entrypoints.schemas import (
    AdminAuditEntryResponse,
    AdminDashboardResponse,
    AdminQueueJobResponse,
    AdminRawLogLineResponse,
    AdminUserResponse,
    AdminVideoDetailResponse,
    AdminVideoSummaryResponse,
    AdminWorkerEventResponse,
)
from app.modules.admin.infrastructure.queue import AdminQueueInspector
from app.modules.admin.infrastructure.read_model import AdminReadModel
from app.modules.admin.wiring import get_admin_queue_inspector, get_admin_read_model
from app.modules.auth.wiring import require_admin, require_super_admin
from app.modules.users.domain.user import User
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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminVideoSummaryResponse]:
    return read_model.list_videos(
        status=status_filter,
        title=title,
        owner_id=owner_id,
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
    _current_user: User = Depends(require_super_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
    video_processing_queue: VideoProcessingQueue = Depends(get_video_processing_queue),
) -> AdminVideoDetailResponse:
    video = video_repository.get_by_id(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    if video.processing_status == VideoProcessingStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video processing is already complete",
        )

    try:
        video_storage.delete_processing_outputs(video_id)
        if video_repository.reset_processing(video_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )
        video_processing_queue.enqueue(video_id, force=True)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video processing queue is unavailable",
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
    delete_video_use_case: DeleteVideo = Depends(get_delete_video),
) -> Response:
    try:
        delete_video_use_case.execute(video_id, current_user)
    except (VideoNotFoundError, VideoPermissionError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
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
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminRawLogLineResponse]:
    return read_model.raw_logs()


@router.get("/queue/jobs", response_model=list[AdminQueueJobResponse])
def admin_queue_jobs(
    _current_user: User = Depends(require_admin),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
) -> list[AdminQueueJobResponse]:
    return queue_inspector.jobs()


@router.get("/users", response_model=list[AdminUserResponse])
def admin_users(
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminUserResponse]:
    return read_model.users()


@router.get("/audit", response_model=list[AdminAuditEntryResponse])
def admin_audit(
    _current_user: User = Depends(require_admin),
    read_model: AdminReadModel = Depends(get_admin_read_model),
) -> list[AdminAuditEntryResponse]:
    return read_model.audit_entries()
