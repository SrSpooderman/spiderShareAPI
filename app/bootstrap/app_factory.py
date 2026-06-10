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
    reset_auth_status,
    reset_client_ip,
    reset_request_id,
    reset_user_agent,
    reset_user_id,
    reset_user_role,
    reset_username,
    set_auth_status,
    set_client_ip,
    set_request_id,
    set_user_agent,
    set_user_id,
    set_user_role,
    set_username,
)
from config.settings import settings


logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return _clean_header_value(
            forwarded_for.split(",", maxsplit=1)[0],
            max_length=80,
        )

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return _clean_header_value(real_ip, max_length=80)

    if request.client is None:
        return "-"

    return request.client.host


def _clean_header_value(value: str | None, *, max_length: int = 200) -> str:
    if not value:
        return "-"

    cleaned = " ".join(value.replace('"', "'").split())
    return cleaned[:max_length] if cleaned else "-"


def _restore_authenticated_user_context(request: Request) -> None:
    user = getattr(request.state, "authenticated_user", None)
    if user is None:
        return

    set_auth_status("authenticated")
    set_user_id(str(user.id))
    set_username(user.username)
    set_user_role(user.role.value)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SpiderShare")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = _clean_header_value(
            request.headers.get("X-Request-ID"),
            max_length=80,
        )
        if request_id == "-":
            request_id = new_request_id()
        authorization = request.headers.get("Authorization", "")
        initial_auth_status = (
            "token_present" if authorization.lower().startswith("bearer ") else "anonymous"
        )
        request_id_token = set_request_id(request_id)
        client_ip_token = set_client_ip(_client_ip(request))
        user_agent_token = set_user_agent(_clean_header_value(request.headers.get("User-Agent")))
        auth_status_token = set_auth_status(initial_auth_status)
        user_id_token = set_user_id("-")
        username_token = set_username("-")
        user_role_token = set_user_role("-")
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
            reset_user_role(user_role_token)
            reset_username(username_token)
            reset_user_id(user_id_token)
            reset_auth_status(auth_status_token)
            reset_user_agent(user_agent_token)
            reset_client_ip(client_ip_token)
            reset_request_id(request_id_token)
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        _restore_authenticated_user_context(request)

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

        reset_user_role(user_role_token)
        reset_username(username_token)
        reset_user_id(user_id_token)
        reset_auth_status(auth_status_token)
        reset_user_agent(user_agent_token)
        reset_client_ip(client_ip_token)
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
