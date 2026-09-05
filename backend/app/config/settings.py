import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application
    APP_NAME: str = "KHOJAI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/khojai",
        description="Async database connection string",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # Authentication & Security
    JWT_SECRET: str = "replace_this_with_a_super_secret_cryptographic_key_32_chars_min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_NAME: str = "app_session_id"
    COOKIE_SECURE: bool = False
    COOKIE_SAME_SITE: str = "lax"

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long for cryptographic security.")
        return v

    @property
    def is_cookie_secure(self) -> bool:
        """Enforce HTTPS cookie security in production."""
        return True if self.APP_ENV == "production" else self.COOKIE_SECURE

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # AI & LLM Configuration
    AI_PROVIDER: str = "local"  # "local", "gemini", "openai"
    AI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    AI_MODEL_NAME: str = "khojai-explorer-v1"
    AI_TEMPERATURE: float = 0.7
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 3
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL_NAME: str = "text-embedding-004"

    # Media & Storage
    STORAGE_BACKEND: str = "local"
    MEDIA_DIR: str = "./media"
    MAX_UPLOAD_SIZE_MB: int = 5

    # Travel Provider APIs
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    AMADEUS_BASE_URL: str = "https://test.api.amadeus.com"
    GOOGLE_MAPS_API_KEY: str = ""
    TRAVEL_CACHE_TTL_SECONDS: int = 3600
    TRAVEL_API_TIMEOUT_SECONDS: float = 10.0
    TRAVEL_API_MAX_RETRIES: int = 2
    TRAVEL_DEFAULT_PROVIDER: str = "amadeus"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL.lower()

    @property
    def sync_database_url(self) -> str:
        """Helper for Alembic or sync operations if needed."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        elif url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url


# Singleton instance
settings = Settings()
