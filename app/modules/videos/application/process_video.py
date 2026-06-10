from uuid import UUID

from app.modules.videos.domain.ports import VideoRepository, VideoTranscoder
from app.modules.videos.domain.video import Video


class ProcessVideo:
    def __init__(
        self,
        video_repository: VideoRepository,
        video_transcoder: VideoTranscoder,
    ) -> None:
        self.video_repository = video_repository
        self.video_transcoder = video_transcoder

    def execute(self, video_id: UUID, *, raise_on_error: bool = False) -> Video | None:
        self.video_repository.mark_processing(video_id)
        try:
            result = self.video_transcoder.transcode(video_id)
        except Exception:
            failed_video = self.video_repository.mark_failed(video_id)
            if raise_on_error:
                raise
            return failed_video

        return self.video_repository.mark_processed(video_id, result)
