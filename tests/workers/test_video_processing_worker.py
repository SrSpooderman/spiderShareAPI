from app.workers.video_processing import _enqueue_pending_videos
from app.modules.videos.domain.video import VideoProcessingStatus
from tests.factories import make_video
from tests.fakes import FakeVideoProcessingQueue, FakeVideoRepository


def test_enqueue_pending_videos_enqueues_only_pending_videos() -> None:
    pending_video = make_video(processing_status=VideoProcessingStatus.PENDING)
    ready_video = make_video(processing_status=VideoProcessingStatus.READY)
    failed_video = make_video(processing_status=VideoProcessingStatus.FAILED)
    queue = FakeVideoProcessingQueue()
    repository = FakeVideoRepository([pending_video, ready_video, failed_video])

    count = _enqueue_pending_videos(repository, queue)

    assert count == 1
    assert queue.enqueued == [pending_video.id]
    assert queue.force_flags == [False]
