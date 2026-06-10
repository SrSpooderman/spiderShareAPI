from uuid import UUID

from redis import Redis
from rq import Queue, Retry

from app.modules.videos.domain.ports import VideoProcessingQueue
from config.settings import settings


class RqVideoProcessingQueue(VideoProcessingQueue):
    def __init__(self, redis_url: str | None = None, queue_name: str | None = None) -> None:
        self.connection = Redis.from_url(redis_url or settings.redis_url)
        self.queue = Queue(
            queue_name or settings.video_processing_queue_name,
            connection=self.connection,
        )

    def enqueue(self, video_id: UUID) -> None:
        job_id = f"video-processing:{video_id}"
        existing_job = self.queue.fetch_job(job_id)
        if existing_job is not None and existing_job.get_status() in {
            "queued",
            "started",
            "deferred",
            "scheduled",
        }:
            return
        if existing_job is not None:
            existing_job.delete()

        self.queue.enqueue(
            "app.workers.video_processing.process_video_job",
            str(video_id),
            job_id=job_id,
            retry=Retry(max=settings.video_processing_max_attempts),
            job_timeout=settings.video_processing_job_timeout_seconds,
        )
