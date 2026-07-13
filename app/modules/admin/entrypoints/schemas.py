from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.domain.user import AuthProvider, UserRole
from app.modules.videos.domain.video import VideoProcessingStatus


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class AdminServiceStatusResponse(CamelModel):
    name: str
    status: str
    detail: str


class AdminProcessingErrorResponse(CamelModel):
    id: UUID
    video_id: UUID = Field(alias="videoId")
    attempt: int
    error_type: str = Field(alias="errorType")
    error_message: str = Field(alias="errorMessage")
    job_id: str | None = Field(alias="jobId")
    duration_ms: float | None = Field(alias="durationMs")
    created_at: datetime = Field(alias="createdAt")


class AdminVideoSummaryResponse(CamelModel):
    id: UUID
    title: str
    owner_username: str = Field(alias="ownerUsername")
    owner_id: UUID = Field(alias="ownerId")
    processing_status: VideoProcessingStatus = Field(alias="processingStatus")
    visibility: str
    duration_seconds: float | None = Field(alias="durationSeconds")
    source_created_at: datetime | None = Field(alias="sourceCreatedAt")
    created_at: datetime = Field(alias="createdAt")
    latest_processing_error: AdminProcessingErrorResponse | None = Field(
        alias="latestProcessingError",
    )


class AdminVideoVariantResponse(CamelModel):
    type: str
    codec: str
    width: int
    height: int
    size_bytes: int = Field(alias="sizeBytes")


class AdminVideoDetailResponse(AdminVideoSummaryResponse):
    original_filename: str = Field(alias="originalFilename")
    width: int | None
    height: int | None
    thumbnail_path: str | None = Field(alias="thumbnailPath")
    variants: list[AdminVideoVariantResponse]


class AdminDashboardTotalsResponse(CamelModel):
    videos: int
    pending: int
    processing: int
    ready: int
    failed: int
    queued_jobs: int = Field(alias="queuedJobs")
    active_jobs: int = Field(alias="activeJobs")
    failed_jobs: int = Field(alias="failedJobs")


class AdminDashboardResponse(CamelModel):
    totals: AdminDashboardTotalsResponse
    services: list[AdminServiceStatusResponse]
    recent_failures: list[AdminVideoSummaryResponse] = Field(alias="recentFailures")
    recent_uploads: list[AdminVideoSummaryResponse] = Field(alias="recentUploads")


class AdminWorkerEventResponse(CamelModel):
    id: str
    event_type: str = Field(alias="eventType")
    level: str
    message: str
    video_id: UUID | None = Field(alias="videoId")
    job_id: str | None = Field(alias="jobId")
    worker_name: str = Field(alias="workerName")
    metadata: dict | None = None
    created_at: datetime = Field(alias="createdAt")


class AdminQueueJobResponse(CamelModel):
    id: str
    video_id: str = Field(alias="videoId")
    status: str
    attempts: int
    enqueued_at: datetime | None = Field(alias="enqueuedAt")


class AdminUserResponse(CamelModel):
    id: UUID
    username: str
    display_name: str | None = Field(alias="displayName")
    auth_provider: AuthProvider = Field(default=AuthProvider.LOCAL, alias="authProvider")
    oidc_email: str | None = Field(default=None, alias="oidcEmail")
    oidc_name: str | None = Field(default=None, alias="oidcName")
    role: UserRole
    is_active: bool = Field(alias="isActive")
    video_count: int = Field(alias="videoCount")


class AdminUserDetailResponse(AdminUserResponse):
    oidc_subject: str | None = Field(default=None, alias="oidcSubject")
    oidc_groups: list[str] = Field(default_factory=list, alias="oidcGroups")
    last_login_at: datetime | None = Field(alias="lastLoginAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    recent_videos: list[AdminVideoSummaryResponse] = Field(alias="recentVideos")


class AdminUserUpdateRequest(CamelModel):
    role: UserRole | None = None
    is_active: bool | None = Field(default=None, alias="isActive")


class AdminAuditEntryResponse(CamelModel):
    id: str
    actor_username: str = Field(alias="actorUsername")
    action: str
    entity: str
    result: str
    created_at: datetime = Field(alias="createdAt")


class AdminRawLogLineResponse(CamelModel):
    line: str
    source: str
    created_at: datetime | None = Field(alias="createdAt")
