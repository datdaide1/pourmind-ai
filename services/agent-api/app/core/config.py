from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, Optional
from uuid import UUID
import os
from pathlib import Path

# Resolve configuration from the repository root without machine-specific paths.
REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = REPO_ROOT / ".env"

class Settings(BaseSettings):
    # Runtime identity boundary for Regular Guest Intelligence. Demo principals
    # are intentionally limited to non-production environments.
    # Fail closed when a deployment forgets to declare its environment. Local
    # and staging must opt into demo-principal eligibility explicitly.
    APP_ENV: Literal["local", "staging", "production"] = "production"
    REGULAR_GUEST_ENABLED: bool = False
    DEMO_BAR_ID: Optional[UUID] = None
    DEMO_BAR_TOKEN: str = ""

    # Session capability authentication. Use at least 32 random bytes in production.
    SESSION_TOKEN_SECRET: str = ""

    # LLM Settings
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    MAX_CHAT_MESSAGE_CHARS: int = 4000
    MAX_CHAT_HISTORY_MESSAGES: int = 20
    CHAT_RATE_LIMIT_REQUESTS: int = 10
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 60
    CHAT_MAX_CONCURRENCY: int = 2
    SEARCH_MAX_LIMIT: int = 20

    API_RATE_LIMIT_REQUESTS: int = 60
    API_RATE_LIMIT_WINDOW_SECONDS: int = 60
    MAX_REQUEST_BODY_BYTES: int = 16384

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    OPENAI_API_BASE: str = "https://openrouter.ai/api/v1"
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""

    @property
    def gemini_keys_list(self) -> list[str]:
        if not self.GEMINI_API_KEYS:
            return []
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]

    # Qdrant (Cloud)
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    # PostgreSQL (Supabase)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432

    POSTGRES_SSL: bool = True
    # Redis (Upstash)
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, 
        env_file_encoding='utf-8', 
        extra='ignore'
    )

    @property
    def postgres_url(self) -> str:
        from urllib.parse import quote_plus
        safe_user = quote_plus(self.POSTGRES_USER)
        safe_password = quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql+asyncpg://{safe_user}:{safe_password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
