from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path

# Resolve configuration from the repository root without machine-specific paths.
REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = REPO_ROOT / ".env"

class Settings(BaseSettings):
    # LLM Settings
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
