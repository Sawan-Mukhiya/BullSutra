import os
from pathlib import Path
from typing import Literal, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = os.getenv("ENV_FILE") or str(API_DIR / ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            "../.env",
            "../../.env",
            API_DIR / ".env",
            ENV_FILE_PATH,
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: Literal["local", "test", "prod"] = "local"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bullsutra"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://postgres:postgres@localhost:5432/bullsutra"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "bullsutra"

    JWT_SECRET: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:3000"
    API_KEY_PEPPER: str = "0123456789abcdef0123456789abcdef"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    LLM_PROVIDER: Literal["gemini", "ollama", "omniroute", "fake"] = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_FALLBACK_PROVIDER: str = "ollama"
    LLM_FALLBACK_MODEL: str = "qwen2.5:3b-instruct"
    GOOGLE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OMNIROUTE_BASE_URL: str = "http://localhost:20128/v1"
    OMNIROUTE_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 45
    LLM_MAX_RETRIES: int = 2

    SENTIMENT_MODEL: str = "ProsusAI/finbert"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    SCRAPER_USER_AGENT: str = "BullSutraBot/1.0 (academic project; contact: info@bullsutra.local)"
    SCRAPER_CONTACT_EMAIL: str = "info@bullsutra.local"
    SCRAPER_DELAY_SECONDS: float = 2.5
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    ENABLE_SCHEDULER: bool = True
    WORKER_CONCURRENCY: int = 2
    RATE_LIMIT_DEFAULT: str = "120/minute"
    HF_HOME: str = "data/models"
    PRICE_SOURCE: str = "nepse_api"
    ADMIN_NOTIFY_WEBHOOK: str = ""

    DATASETS_DIR: str = "data/datasets"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = os.getenv("ENV", "local")
        if env == "prod":
            if len(v) < 32 or "0123456789abcdef" in v:
                raise ValueError("In prod, JWT_SECRET must be at least 32 characters and not use default placeholder")
        return v

settings = Settings()
