import logging
from time import perf_counter
from uuid import UUID

from app.modules.videos.domain.ports import VideoRepository, VideoTranscoder
from app.modules.videos.domain.video import Video


logger = logging.getLogger(__name__)


class ProcessVideo:
    def __init__(
        self,
        video_repository: VideoRepository,
        video_transcoder: VideoTranscoder,
    ) -> None:
        self.video_repository = video_repository
        self.video_transcoder = video_transcoder

    def execute(self, video_id: UUID, *, raise_on_error: bool = False) -> Video | None:
        started_at = perf_counter()
        processing_video = self.video_repository.mark_processing(video_id)
        if processing_video is None:
            logger.warning("Video processing skipped reason=not_found video_id=%s", video_id)
            return None

        logger.info(
            "Video processing started video_id=%s owner_id=%s",
            video_id,
            processing_video.owner_id,
        )
        try:
            result = self.video_transcoder.transcode(video_id)
        except Exception as error:
            failed_video = self.video_repository.mark_failed(video_id)
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "Video processing failed video_id=%s owner_id=%s duration_ms=%.2f "
                "error_type=%s",
                video_id,
                processing_video.owner_id,
                duration_ms,
                type(error).__name__,
            )
            if raise_on_error:
                raise
            return failed_video

        processed_video = self.video_repository.mark_processed(video_id, result)
        duration_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "Video processing completed video_id=%s owner_id=%s duration_ms=%.2f "
            "width=%s height=%s variants=%s",
            video_id,
            processing_video.owner_id,
            duration_ms,
            result.width,
            result.height,
            len(result.variants),
        )
        return processed_video
