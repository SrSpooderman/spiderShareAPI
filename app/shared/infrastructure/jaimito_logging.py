import logging


class JaimitoWorkerLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def waking_up(self, *, queue_name: str, redis_url: str) -> None:
        self.logger.info(
            "event=jaimito.worker.waking_up dicho=\"Ea, que ya ha amanecio y "
            "Jaimito se pone al tajo\" queue=%s redis_url=%s",
            queue_name,
            redis_url,
        )

    def redis_ready(self, *, queue_name: str) -> None:
        self.logger.info(
            "event=jaimito.worker.redis_ready dicho=\"Ole, Redis responde; "
            "ya tenemos la plaza abierta\" queue=%s",
            queue_name,
        )

    def waiting_for_jobs(self, *, queue_name: str) -> None:
        self.logger.info(
            "event=jaimito.worker.waiting dicho=\"Aqui me quedo, con la gorra "
            "puesta, esperando videos\" queue=%s",
            queue_name,
        )

    def job_started(self, *, video_id: str, job_id: str) -> None:
        self.logger.info(
            "event=jaimito.job.started dicho=\"Mira, miarma, este video lo cojo "
            "yo con cuidadito\" video_id=%s job_id=%s",
            video_id,
            job_id,
        )

    def job_finished(self, *, video_id: str, job_id: str) -> None:
        self.logger.info(
            "event=jaimito.job.finished dicho=\"Ea, video despachao; mas apanao "
            "que una silla en la puerta\" video_id=%s job_id=%s",
            video_id,
            job_id,
        )

    def job_failed(self, *, video_id: str, job_id: str, error_type: str) -> None:
        self.logger.exception(
            "event=jaimito.job.failed dicho=\"Ay, que esto se ha torcio; "
            "vamos a mirar el avio\" video_id=%s job_id=%s error_type=%s",
            video_id,
            job_id,
            error_type,
        )

    def shutting_down(self, *, queue_name: str) -> None:
        self.logger.info(
            "event=jaimito.worker.shutting_down dicho=\"Bueno, cierro la silla "
            "y recojo los bartulos\" queue=%s",
            queue_name,
        )
