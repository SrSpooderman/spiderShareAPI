import logging
import logging.config
from contextvars import ContextVar
from uuid import uuid4

from config.settings import settings


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
user_id_context: ContextVar[str] = ContextVar("user_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        record.user_id = user_id_context.get()
        return True


def configure_logging() -> None:
    level = "DEBUG" if settings.app_env.lower() in {"local", "dev", "development"} else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": RequestContextFilter,
                },
            },
            "formatters": {
                "console": {
                    "format": (
                        "%(asctime)s %(levelname)s [%(name)s] "
                        "request_id=%(request_id)s user_id=%(user_id)s %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "filters": ["request_context"],
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


def new_request_id() -> str:
    return str(uuid4())


def set_request_id(request_id: str):
    return request_id_context.set(request_id)


def set_user_id(user_id: str):
    return user_id_context.set(user_id)


def reset_request_id(token) -> None:
    request_id_context.reset(token)


def reset_user_id(token) -> None:
    user_id_context.reset(token)
