import logging
import logging.config
import json
import re
from contextvars import ContextVar
from uuid import uuid4

from config.settings import settings


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
user_id_context: ContextVar[str] = ContextVar("user_id", default="-")
username_context: ContextVar[str] = ContextVar("username", default="-")
user_role_context: ContextVar[str] = ContextVar("user_role", default="-")
auth_status_context: ContextVar[str] = ContextVar("auth_status", default="anonymous")
client_ip_context: ContextVar[str] = ContextVar("client_ip", default="-")
user_agent_context: ContextVar[str] = ContextVar("user_agent", default="-")
worker_name_context: ContextVar[str] = ContextVar("worker_name", default="-")
job_id_context: ContextVar[str] = ContextVar("job_id", default="-")
video_id_context: ContextVar[str] = ContextVar("video_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        record.user_id = user_id_context.get()
        record.username = username_context.get()
        record.user_role = user_role_context.get()
        record.auth_status = auth_status_context.get()
        record.client_ip = client_ip_context.get()
        record.user_agent = user_agent_context.get()
        record.worker_name = worker_name_context.get()
        record.job_id = job_id_context.get()
        record.video_id = video_id_context.get()
        return True


class SensitiveDataFilter(logging.Filter):
    """Avoid leaking credentials if a dependency includes them in an error."""

    _patterns = (
        re.compile(r"(?i)(authorization|token|password|secret|api[_-]?key)(=|:)([^\s,;]+)"),
        re.compile(r"(?i)bearer\s+[^\s,;]+"),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = self._patterns[0].sub(
            lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
            message,
        )
        message = self._patterns[1].sub("Bearer [REDACTED]", message)
        record.msg = message
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "client_ip": getattr(record, "client_ip", "-"),
            "auth_status": getattr(record, "auth_status", "anonymous"),
            "user_id": getattr(record, "user_id", "-"),
            "username": getattr(record, "username", "-"),
            "user_role": getattr(record, "user_role", "-"),
            "worker": getattr(record, "worker_name", "-"),
            "job_id": getattr(record, "job_id", "-"),
            "video_id": getattr(record, "video_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    default_level = "DEBUG" if settings.app_env.lower() in {"local", "dev", "development"} else "INFO"
    level = (settings.log_level or default_level).upper()
    formatter = "json" if settings.log_format == "json" else "pretty"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": RequestContextFilter,
                },
                "sensitive_data": {"()": SensitiveDataFilter},
            },
            "formatters": {
                "pretty": {
                    "format": (
                        "%(asctime)s %(levelname)s [%(name)s] "
                        "request_id=%(request_id)s client_ip=%(client_ip)s "
                        "auth_status=%(auth_status)s user_id=%(user_id)s "
                        "username=%(username)s user_role=%(user_role)s "
                        "worker=%(worker_name)s job_id=%(job_id)s video_id=%(video_id)s "
                        'user_agent="%(user_agent)s" %(message)s'
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "json": {"()": JsonFormatter},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "filters": ["request_context", "sensitive_data"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": level,
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger governed by SpiderShare's central logging policy."""
    return logging.getLogger(name)


def new_request_id() -> str:
    return str(uuid4())


def set_request_id(request_id: str):
    return request_id_context.set(request_id)


def set_user_id(user_id: str):
    return user_id_context.set(user_id)


def set_username(username: str):
    return username_context.set(username)


def set_user_role(user_role: str):
    return user_role_context.set(user_role)


def set_auth_status(auth_status: str):
    return auth_status_context.set(auth_status)


def set_client_ip(client_ip: str):
    return client_ip_context.set(client_ip)


def set_user_agent(user_agent: str):
    return user_agent_context.set(user_agent)


def set_worker_name(worker_name: str):
    return worker_name_context.set(worker_name)


def set_job_id(job_id: str):
    return job_id_context.set(job_id)


def set_video_id(video_id: str):
    return video_id_context.set(video_id)


def reset_request_id(token) -> None:
    request_id_context.reset(token)


def reset_user_id(token) -> None:
    user_id_context.reset(token)


def reset_username(token) -> None:
    username_context.reset(token)


def reset_user_role(token) -> None:
    user_role_context.reset(token)


def reset_auth_status(token) -> None:
    auth_status_context.reset(token)


def reset_client_ip(token) -> None:
    client_ip_context.reset(token)


def reset_user_agent(token) -> None:
    user_agent_context.reset(token)


def reset_worker_name(token) -> None:
    worker_name_context.reset(token)


def reset_job_id(token) -> None:
    job_id_context.reset(token)


def reset_video_id(token) -> None:
    video_id_context.reset(token)
