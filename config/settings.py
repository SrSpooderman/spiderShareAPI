from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpiderShare"
    app_env: str = "local"
    app_debug: bool = True
    database_url: str
    video_storage_path: str = "/app/storage/videos"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    super_admin_username: str | None = None
    super_admin_password: str | None = None
    steam_web_api_key: str | None = None
    steam_web_api_base_url: str = "https://api.steampowered.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
