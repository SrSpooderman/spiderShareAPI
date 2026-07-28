from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpiderShare"
    app_version: str = "1.2.0"
    app_root_path: str = ""
    app_env: str = "local"
    app_debug: bool = True
    log_level: str | None = None
    log_format: str = "pretty"
    cors_allowed_origins: Annotated[list[str], NoDecode] = []
    database_url: str
    video_storage_path: str = "/app/storage/videos"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_authorization_endpoint: str | None = None
    oidc_token_endpoint: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_scope: str = "openid profile email"
    oidc_redirect_uri: str | None = None
    oidc_allowed_frontend_domains: Annotated[list[str], NoDecode] = []
    oidc_frontend_callback_path: str = "/login/oidc/callback"
    oidc_default_role: str = "user"
    super_admin_username: str | None = None
    super_admin_password: str | None = None
    steam_web_api_key: str | None = None
    steam_web_api_base_url: str = "https://api.steampowered.com"
    steamgriddb_api_key: str | None = None
    steamgriddb_api_base_url: str = "https://www.steamgriddb.com/api/v2"
    max_video_size_bytes: int | None = 524_288_000
    max_video_duration_seconds: int | None = 300
    max_video_tags: int = 6
    max_video_reactions_per_user: int = 2
    video_allowed_mime_types: list[str] = ["video/mp4", "video/webm"]
    redis_url: str = "redis://redis:6379/0"
    video_processing_queue_name: str = "video-processing"
    video_processing_max_attempts: int = 3
    video_processing_job_timeout_seconds: int = 900
    backoffice_api_base_url: str | None = None
    public_clip_base_url: str | None = None
    discord_webhook_enabled: bool = False
    discord_webhook_url: str | None = None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("oidc_allowed_frontend_domains", mode="before")
    @classmethod
    def parse_oidc_allowed_frontend_domains(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [domain.strip() for domain in value.split(",") if domain.strip()]
        return value

    @field_validator("app_root_path")
    @classmethod
    def normalize_app_root_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized == "/":
            return ""
        return normalized if normalized.startswith("/") else f"/{normalized}"

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"pretty", "json"}:
            raise ValueError("log_format must be 'pretty' or 'json'")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper().strip()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be a standard logging level")
        return normalized

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
