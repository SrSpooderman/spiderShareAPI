import logging
from uuid import UUID

from redis import Redis
from rq import Queue, Worker

from app.modules.videos.application.process_video import ProcessVideo
from app.modules.videos.infrastructure.repository import SqlAlchemyVideoRepository
from app.shared.infrastructure.db.session import SessionLocal
from app.shared.infrastructure.providers.storage.video_transcoder import FfmpegVideoTranscoder
from config.settings import settings

logger = logging.getLogger(__name__)


def process_video_job(video_id: str) -> None:
    parsed_video_id = UUID(video_id)
    with SessionLocal() as db:
        video_repository = SqlAlchemyVideoRepository(db)
        video_transcoder = FfmpegVideoTranscoder()
        ProcessVideo(video_repository, video_transcoder).execute(
            parsed_video_id,
            raise_on_error=True,
        )


def main() -> None:
    redis_connection = Redis.from_url(settings.redis_url)
    queue = Queue(settings.video_processing_queue_name, connection=redis_connection)
    logger.info("Starting video worker for queue %s", settings.video_processing_queue_name)
    Worker([queue], connection=redis_connection).work()


if __name__ == "__main__":
    main()
