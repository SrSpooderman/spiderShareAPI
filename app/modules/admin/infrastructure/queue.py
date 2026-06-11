from datetime import datetime
from uuid import UUID

from redis import Redis
from rq import Queue

try:
    from rq.job import Job
    from rq.registry import FailedJobRegistry, StartedJobRegistry
except ImportError:  # pragma: no cover - depends on RQ version
    Job = None
    FailedJobRegistry = None
    StartedJobRegistry = None

from app.modules.admin.entrypoints.schemas import AdminQueueJobResponse
from config.settings import settings


class AdminQueueInspector:
    def summary(self) -> dict:
        raise NotImplementedError

    def jobs(self) -> list[AdminQueueJobResponse]:
        raise NotImplementedError

    def delete_job(self, job_id: str) -> bool:
        raise NotImplementedError

    def requeue_job(self, job_id: str) -> AdminQueueJobResponse | None:
        raise NotImplementedError

    def clear_failed_jobs(self) -> int:
        raise NotImplementedError


class RqAdminQueueInspector(AdminQueueInspector):
    def __init__(self, redis_url: str | None = None, queue_name: str | None = None) -> None:
        self.connection = Redis.from_url(redis_url or settings.redis_url)
        self.queue = Queue(queue_name or settings.video_processing_queue_name, connection=self.connection)

    def summary(self) -> dict:
        try:
            self.connection.ping()
            queued_jobs = len(self.queue)
            active_jobs = self._registry_count(StartedJobRegistry)
            failed_jobs = self._registry_count(FailedJobRegistry)
        except Exception as error:
            return {
                "redis_status": "down",
                "redis_detail": type(error).__name__,
                "worker_status": "warning",
                "worker_detail": "Queue unavailable",
                "queued_jobs": 0,
                "active_jobs": 0,
                "failed_jobs": 0,
            }

        worker_status = "ok" if active_jobs or queued_jobs or failed_jobs == 0 else "warning"
        worker_detail = (
            f"{queued_jobs} queued, {active_jobs} active, {failed_jobs} failed"
        )
        return {
            "redis_status": "ok",
            "redis_detail": "Healthy",
            "worker_status": worker_status,
            "worker_detail": worker_detail,
            "queued_jobs": queued_jobs,
            "active_jobs": active_jobs,
            "failed_jobs": failed_jobs,
        }

    def jobs(self) -> list[AdminQueueJobResponse]:
        try:
            queued = [self._job_response(job, "queued") for job in self.queue.jobs]
            started = self._registry_jobs(StartedJobRegistry, "started")
            failed = self._registry_jobs(FailedJobRegistry, "failed")
        except Exception:
            return []

        return [job for job in queued + started + failed if job is not None]

    def delete_job(self, job_id: str) -> bool:
        if Job is None:
            return False
        try:
            job = Job.fetch(job_id, connection=self.connection)
        except Exception:
            return False
        job.delete()
        return True

    def requeue_job(self, job_id: str) -> AdminQueueJobResponse | None:
        if Job is None:
            return None
        try:
            job = Job.fetch(job_id, connection=self.connection)
        except Exception:
            return None

        video_id = self._video_id(job)
        if video_id == "-":
            return None

        try:
            job.delete()
            queued_job = self.queue.enqueue(
                "app.workers.video_processing.process_video_job",
                video_id,
                job_id=job_id,
                retry=getattr(job, "retry", None),
                job_timeout=settings.video_processing_job_timeout_seconds,
            )
        except Exception:
            return None

        return self._job_response(queued_job, "queued")

    def clear_failed_jobs(self) -> int:
        if FailedJobRegistry is None or Job is None:
            return 0
        registry = FailedJobRegistry(self.queue.name, connection=self.connection)
        deleted = 0
        for job_id in registry.get_job_ids():
            if self.delete_job(job_id):
                deleted += 1
        return deleted

    def _registry_count(self, registry_class) -> int:
        if registry_class is None:
            return 0
        return len(registry_class(self.queue.name, connection=self.connection))

    def _registry_jobs(self, registry_class, status: str) -> list[AdminQueueJobResponse]:
        if registry_class is None or Job is None:
            return []
        registry = registry_class(self.queue.name, connection=self.connection)
        jobs = []
        for job_id in registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=self.connection)
            except Exception:
                continue
            response = self._job_response(job, status)
            if response is not None:
                jobs.append(response)
        return jobs

    def _job_response(self, job, status: str) -> AdminQueueJobResponse | None:
        if job is None:
            return None
        return AdminQueueJobResponse(
            id=job.id,
            video_id=self._video_id(job),
            status=status,
            attempts=self._attempts(job),
            enqueued_at=self._enqueued_at(job),
        )

    def _video_id(self, job) -> str:
        if getattr(job, "args", None):
            return str(job.args[0])
        if str(job.id).startswith("video-processing-"):
            value = str(job.id).removeprefix("video-processing-")
            try:
                UUID(value)
            except ValueError:
                return "-"
            return value
        return "-"

    def _attempts(self, job) -> int:
        meta = getattr(job, "meta", None) or {}
        if "attempt" in meta:
            try:
                return int(meta["attempt"])
            except (TypeError, ValueError):
                return 0
        return 0

    def _enqueued_at(self, job) -> datetime | None:
        return getattr(job, "enqueued_at", None) or getattr(job, "created_at", None)
