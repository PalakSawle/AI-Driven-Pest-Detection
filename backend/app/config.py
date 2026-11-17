"""Application settings, loaded from environment variables (see .env.example)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore", protected_namespaces=("settings_",))

    app_name: str = "AgriGuard AI"
    environment: str = "development"

    # Database: SQLite locally, PostgreSQL (Supabase) in production.
    database_url: str = f"sqlite:///{BASE_DIR / 'agriguard.db'}"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    reset_token_expire_minutes: int = 30

    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"

    # Model
    model_path: str = str(BASE_DIR / "weights" / "best.onnx")
    model_meta_path: str = str(BASE_DIR / "weights" / "model_meta.json")
    conf_threshold: float = 0.25
    low_conf_threshold: float = 0.40
    iou_threshold: float = 0.45
    max_upload_mb: int = 8

    # Storage: "local" or "supabase"
    storage_backend: str = "local"
    upload_dir: str = str(BASE_DIR / "uploads")
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "detections"

    # LLM: "anthropic", "openai", "gemini" or "none"
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""

    # Weather: Open-Meteo needs no key; "openweather" needs WEATHER_API_KEY.
    weather_provider: str = "open-meteo"
    weather_api_key: str = ""

    # Optional email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Rate limits
    rate_limit_detect: str = "20/minute"
    rate_limit_chat: str = "30/minute"
    rate_limit_auth: str = "10/minute"

    # First admin (created on startup if set)
    admin_email: str = ""
    admin_password: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
