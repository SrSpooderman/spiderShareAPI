from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.admin.entrypoints.schemas import (
    AdminDashboardResponse,
    AdminDashboardTotalsResponse,
    AdminServiceStatusResponse,
    AdminUserDetailResponse,
    AdminUserResponse,
    AdminVideoDetailResponse,
    AdminVideoSummaryResponse,
    AdminWorkerEventResponse,
)
from app.modules.admin.wiring import (
    get_admin_event_recorder,
    get_admin_queue_inspector,
    get_admin_read_model,
)
from app.modules.auth.wiring import get_current_user, require_admin, require_super_admin
from app.modules.videos.domain.video import VideoProcessingStatus
from app.modules.videos.wiring import (
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)
from tests.fakes import FakeVideoProcessingQueue, FakeVideoRepository, FakeVideoStorage


class FakeAdminReadModel:
    def __init__(self) -> None:
        self.video_id = uuid4()
        self.owner_id = uuid4()
        self.video = AdminVideoSummaryResponse(
            id=self.video_id,
            title="Boss clip",
            owner_username="alice",
            owner_id=self.owner_id,
            processing_status=VideoProcessingStatus.FAILED,
            visibility="public",
            duration_seconds=None,
            created_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
            latest_processing_error=None,
        )
        self.detail = AdminVideoDetailResponse(
            **self.video.model_dump(),
            original_filename="clip.mp4",
            width=None,
            height=None,
            thumbnail_path=None,
            variants=[],
        )

    def dashboard(self):
        return AdminDashboardResponse(
            totals=AdminDashboardTotalsResponse(
                videos=1,
                pending=0,
                processing=0,
                ready=0,
                failed=1,
                queued_jobs=1,
                active_jobs=0,
                failed_jobs=0,
            ),
            services=[
                AdminServiceStatusResponse(name="API", status="ok", detail="Responding")
            ],
            recent_failures=[self.video],
            recent_uploads=[self.video],
        )

    def list_videos(self, **_kwargs):
        return [self.video]

    def get_video(self, _video_id):
        return self.detail

    def worker_events(self, **_kwargs):
        return [
            AdminWorkerEventResponse(
                id="evt-1",
                event_type="video.processing.failed",
                level="error",
                message="boom",
                video_id=self.video_id,
                job_id="job-1",
                worker_name="jaimito_worker",
                created_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
            )
        ]

    def users(self, **_kwargs):
        return [
            AdminUserResponse(
                id=self.owner_id,
                username="alice",
                display_name="Alice",
                role="user",
                is_active=True,
                video_count=1,
            )
        ]

    def get_user(self, _user_id):
        return AdminUserDetailResponse(
            **self.users()[0].model_dump(),
            last_login_at=None,
            created_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
            updated_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
            recent_videos=[self.video],
        )

    def audit_entries(self, **_kwargs):
        return []

    def raw_logs(self, **_kwargs):
        return []


class FakeAdminQueueInspector:
    def summary(self):
        return {
            "redis_status": "ok",
            "redis_detail": "Healthy",
            "worker_status": "ok",
            "worker_detail": "1 queued",
            "queued_jobs": 1,
            "active_jobs": 0,
            "failed_jobs": 0,
        }

    def jobs(self):
        return []


class FakeAdminEventRecorder:
    def __init__(self) -> None:
        self.worker_events = []
        self.audit_entries = []

    def worker_event(self, **kwargs) -> None:
        self.worker_events.append(kwargs)

    def audit(self, **kwargs) -> None:
        self.audit_entries.append(kwargs)


@pytest.mark.http
def test_admin_routes_require_admin_role(app, client, user_factory) -> None:
    user = user_factory(role="user")
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/admin/dashboard")

    assert response.status_code == 403


@pytest.mark.http
def test_admin_dashboard_and_videos_return_backoffice_contract(
    app,
    client,
    user_factory,
) -> None:
    admin = user_factory(role="admin")
    read_model = FakeAdminReadModel()
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_admin_read_model] = lambda: read_model

    dashboard_response = client.get("/admin/dashboard")
    videos_response = client.get("/admin/videos")
    detail_response = client.get(f"/admin/videos/{read_model.video_id}")
    events_response = client.get("/admin/worker/events")
    users_response = client.get("/admin/users", params={"username": "ali"})
    user_detail_response = client.get(f"/admin/users/{read_model.owner_id}")

    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["totals"]["queuedJobs"] == 1
    assert dashboard_response.json()["recentFailures"][0]["ownerUsername"] == "alice"
    assert videos_response.status_code == 200
    assert videos_response.json()[0]["processingStatus"] == "failed"
    assert detail_response.status_code == 200
    assert detail_response.json()["originalFilename"] == "clip.mp4"
    assert events_response.status_code == 200
    assert events_response.json()[0]["workerName"] == "jaimito_worker"
    assert users_response.status_code == 200
    assert users_response.json()[0]["videoCount"] == 1
    assert user_detail_response.status_code == 200
    assert user_detail_response.json()["recentVideos"][0]["title"] == "Boss clip"


@pytest.mark.http
def test_admin_queue_and_audit_endpoints(
    app,
    client,
    user_factory,
) -> None:
    admin = user_factory(role="admin")
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_admin_read_model] = lambda: FakeAdminReadModel()
    app.dependency_overrides[get_admin_queue_inspector] = lambda: FakeAdminQueueInspector()

    queue_response = client.get("/admin/queue/jobs")
    audit_response = client.get("/admin/audit")

    assert queue_response.status_code == 200
    assert queue_response.json() == []
    assert audit_response.status_code == 200
    assert audit_response.json() == []


@pytest.mark.http
def test_admin_retry_requires_super_admin_and_requeues_video(
    app,
    client,
    user_factory,
    video_factory,
) -> None:
    super_admin = user_factory(role="super_admin")
    video_repository = FakeVideoRepository()
    video_storage = FakeVideoStorage()
    queue = FakeVideoProcessingQueue()
    event_recorder = FakeAdminEventRecorder()
    video = video_repository.add(
        video_factory(processing_status=VideoProcessingStatus.FAILED)
    )
    read_model = FakeAdminReadModel()
    read_model.video_id = video.id
    app.dependency_overrides[require_super_admin] = lambda: super_admin
    app.dependency_overrides[get_admin_read_model] = lambda: read_model
    app.dependency_overrides[get_admin_event_recorder] = lambda: event_recorder
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_video_processing_queue] = lambda: queue

    response = client.post(f"/admin/videos/{video.id}/processing/retry")

    assert response.status_code == 200
    assert video_storage.deleted_processing_outputs == [video.id]
    assert video_repository.reset == [video.id]
    assert queue.enqueued == [video.id]
    assert queue.force_flags == [True]
    assert event_recorder.audit_entries[0]["action"] == "processing.retry.requested"
    assert event_recorder.audit_entries[0]["result"] == "success"
    assert event_recorder.worker_events[0]["event_type"] == "processing.retry.requested"
