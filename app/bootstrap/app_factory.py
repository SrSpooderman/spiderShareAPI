import logging
from time import perf_counter

from fastapi import FastAPI
from starlette.requests import Request

from app.modules.auth.entrypoints.routes import router as auth_router
from app.modules.steam.entrypoints.routes import router as steam_router
from app.modules.users.entrypoints.routes import router as users_router
from app.modules.videos.entrypoints.routes import router as videos_router
from app.shared.infrastructure.logging import (
    configure_logging,
    new_request_id,
    reset_request_id,
    reset_user_id,
    set_request_id,
    set_user_id,
)
from config.settings import settings


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SpiderShare")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        request_id_token = set_request_id(request_id)
        user_id_token = set_user_id("-")
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "Unhandled request error method=%s path=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                duration_ms,
            )
            reset_user_id(user_id_token)
            reset_request_id(request_id_token)
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id

        log_method = logger.info
        if response.status_code >= 500:
            log_method = logger.error
        elif response.status_code >= 400:
            log_method = logger.warning

        log_method(
            "Request completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        reset_user_id(user_id_token)
        reset_request_id(request_id_token)
        return response

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {"version": settings.app_version}

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(steam_router)
    app.include_router(videos_router)

    return app
