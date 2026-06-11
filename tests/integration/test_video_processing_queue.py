import os
from uuid import uuid4

import pytest
from redis import Redis

from app.modules.videos.infrastructure.queue import (
    RqVideoProcessingQueue,
    video_processing_job_id,
)


@pytest.mark.integration
def test_rq_video_processing_queue_enqueues_idempotent_job() -> None:
    redis_url = os.getenv("REDIS_INTEGRATION_URL")
    if not redis_url:
        pytest.skip("Set REDIS_INTEGRATION_URL to run Redis integration tests")

    queue_name = f"video-processing-test-{uuid4()}"
    redis_connection = Redis.from_url(redis_url)
    redis_connection.ping()
    redis_connection.delete(f"rq:queue:{queue_name}")

    queue = RqVideoProcessingQueue(redis_url=redis_url, queue_name=queue_name)
    video_id = uuid4()

    try:
        queue.enqueue(video_id)
        queue.enqueue(video_id)

        job = queue.queue.fetch_job(video_processing_job_id(video_id))
        assert job is not None
        assert job.id == video_processing_job_id(video_id)
        assert len(queue.queue) == 1
    finally:
        queue.queue.empty()
        redis_connection.delete(f"rq:queue:{queue_name}")
