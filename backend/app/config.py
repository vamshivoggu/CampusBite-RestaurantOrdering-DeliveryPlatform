"""Application settings loaded from environment variables (or a local .env file)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CampusBite API"
    environment: str = "development"
    log_level: str = "INFO"

    # Database – PostgreSQL in Docker, SQLite fallback for quick local runs/tests
    database_url: str = "sqlite:///./campusbite.db"

    # Auth
    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # CORS (comma separated)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0
    ai_rate_limit_per_minute: int = 5
    ai_max_orders_in_context: int = 30

    # Background reminders
    reminder_threshold_minutes: int = 15
    reminder_scan_interval_seconds: int = 60
    enable_reminder_scheduler: bool = True

    # Business
    delivery_fee: float = 30.0
    currency: str = "INR"
    seed_demo_data: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
