from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpiderShare"
    app_version: str = "1.0.0"
    app_env: str = "local"
    app_debug: bool = True
    cors_allowed_origins: list[str] = ["http://localhost:5173"]
    database_url: str
    video_storage_path: str = "/app/storage/videos"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    super_admin_username: str | None = None
    super_admin_password: str | None = None
    steam_web_api_key: str | None = None
    steam_web_api_base_url: str = "https://api.steampowered.com"
    max_video_size_bytes: int | None = 524_288_000
    max_video_duration_seconds: int | None = 300
    max_video_tags: int = 6
    max_video_reactions_per_user: int = 2
    video_allowed_mime_types: list[str] = ["video/mp4", "video/webm"]
    redis_url: str = "redis://redis:6379/0"
    video_processing_queue_name: str = "video-processing"
    video_processing_max_attempts: int = 3
    video_processing_job_timeout_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
