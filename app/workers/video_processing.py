from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from redis import Redis
from rq import Queue, Worker, get_current_job

from app.modules.admin.infrastructure.events import SqlAlchemyAdminEventRecorder
from app.modules.videos.application.process_video import ProcessVideo
from app.modules.videos.infrastructure.repository import SqlAlchemyVideoRepository
from app.modules.users.infrastructure.models import UserModel
from app.shared.infrastructure.db.session import SessionLocal
from app.shared.infrastructure.jaimito_logging import JaimitoWorkerLogger
from app.shared.infrastructure.logging import (
    configure_logging,
    get_logger,
    reset_job_id,
    reset_video_id,
    reset_worker_name,
    set_job_id,
    set_video_id,
    set_worker_name,
)
from app.shared.infrastructure.providers.discord_webhook import (
    DiscordWebhookError,
    DiscordWebhookNotifier,
)
from app.shared.infrastructure.providers.storage.video_transcoder import FfmpegVideoTranscoder
from config.settings import settings

logger = get_logger(__name__)
jaimito_logger = JaimitoWorkerLogger(logger)


def _notify_discord_video_ready(video, *, job_id: str) -> None:
    try:
        result = DiscordWebhookNotifier().notify_video_ready(video)
    except DiscordWebhookError as error:
        logger.warning(
            "Discord webhook failed video_id=%s reason=%s",
            video.id,
            str(error),
        )
        _record_worker_event(
            event_type="discord.webhook.failed",
            level="warning",
            message="Discord webhook failed",
            video_id=str(video.id),
            job_id=job_id,
            metadata={"reason": str(error)},
        )
        return

    if not result.sent:
        logger.info(
            "Discord webhook skipped video_id=%s reason=%s",
            video.id,
            result.reason,
        )
        return

    logger.info("Discord webhook sent video_id=%s", video.id)
    _record_worker_event(
        event_type="discord.webhook.sent",
        message="Discord webhook sent",
        video_id=str(video.id),
        job_id=job_id,
    )


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    if "@" not in parsed.netloc:
        return url
    host = parsed.netloc.rsplit("@", maxsplit=1)[-1]
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def _record_worker_event(
    *,
    event_type: str,
    message: str,
    level: str = "info",
    video_id: str | None = None,
    job_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        with SessionLocal() as db:
            SqlAlchemyAdminEventRecorder(db).worker_event(
                event_type=event_type,
                level=level,
                message=message,
                video_id=video_id,
                job_id=job_id,
                metadata=metadata,
            )
    except Exception:
        logger.exception("Failed to record worker event event_type=%s", event_type)


def process_video_job(video_id: str) -> None:
    configure_logging()
    parsed_video_id = UUID(video_id)
    job = get_current_job()
    current_job_id = job.id if job is not None else "-"
    worker_name_token = set_worker_name("jaimito_worker")
    job_id_token = set_job_id(current_job_id)
    video_id_token = set_video_id(video_id)
    jaimito_logger.job_started(video_id=video_id, job_id=current_job_id)
    _record_worker_event(
        event_type="video.job.received",
        message="Video processing job received",
        video_id=video_id,
        job_id=current_job_id,
    )
    logger.info(
        "event=video.job.received video_id=%s job_id=%s worker=jaimito_worker",
        video_id,
        current_job_id,
    )
    try:
        with SessionLocal() as db:
            video_repository = SqlAlchemyVideoRepository(db)
            video_transcoder = FfmpegVideoTranscoder()
            processed_video = ProcessVideo(video_repository, video_transcoder).execute(
                parsed_video_id,
                raise_on_error=True,
                job_id=current_job_id,
            )
            if processed_video is not None:
                _notify_discord_video_ready(processed_video, job_id=current_job_id)
    except Exception as error:
        jaimito_logger.job_failed(
            video_id=video_id,
            job_id=current_job_id,
            error_type=type(error).__name__,
        )
        _record_worker_event(
            event_type="video.processing.failed",
            level="error",
            message=str(error),
            video_id=video_id,
            job_id=current_job_id,
            metadata={"error_type": type(error).__name__},
        )
        raise
    else:
        jaimito_logger.job_finished(video_id=video_id, job_id=current_job_id)
        _record_worker_event(
            event_type="video.processing.completed",
            message="Video processing completed",
            video_id=video_id,
            job_id=current_job_id,
        )
    finally:
        reset_video_id(video_id_token)
        reset_job_id(job_id_token)
        reset_worker_name(worker_name_token)


def main() -> None:
    configure_logging()
    worker_name_token = set_worker_name("jaimito_worker")
    redis_connection = Redis.from_url(settings.redis_url)
    queue = Queue(settings.video_processing_queue_name, connection=redis_connection)
    safe_redis_url = _safe_url(settings.redis_url)
    jaimito_logger.waking_up(
        queue_name=settings.video_processing_queue_name,
        redis_url=safe_redis_url,
    )
    _record_worker_event(
        event_type="jaimito.worker.waking_up",
        message="Worker waking up",
        metadata={
            "queue": settings.video_processing_queue_name,
            "redis_url": safe_redis_url,
        },
    )
    redis_connection.ping()
    jaimito_logger.redis_ready(queue_name=settings.video_processing_queue_name)
    _record_worker_event(
        event_type="jaimito.worker.redis_ready",
        message="Redis is ready",
        metadata={"queue": settings.video_processing_queue_name},
    )
    logger.info(
        "event=video.worker.started queue=%s redis_url=%s",
        settings.video_processing_queue_name,
        safe_redis_url,
    )
    try:
        jaimito_logger.waiting_for_jobs(queue_name=settings.video_processing_queue_name)
        _record_worker_event(
            event_type="jaimito.worker.waiting",
            message="Worker waiting for jobs",
            metadata={"queue": settings.video_processing_queue_name},
        )
        Worker([queue], connection=redis_connection).work()
    finally:
        jaimito_logger.shutting_down(queue_name=settings.video_processing_queue_name)
        _record_worker_event(
            event_type="jaimito.worker.shutting_down",
            message="Worker shutting down",
            metadata={"queue": settings.video_processing_queue_name},
        )
        reset_worker_name(worker_name_token)


if __name__ == "__main__":
    main()
