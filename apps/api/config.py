from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/contentfinder"
    REDIS_URL: str = "redis://redis:6379/0"

    STORAGE_MODE: str = "local"
    LOCAL_MEDIA_ROOT: str = "/data/media"
    INGEST_ROOT: str = "/data/ingest"

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    WHISPER_MODEL_SIZE: str = "base"
    OCR_PROVIDER: str = "easyocr"

    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"


settings = Settings()
