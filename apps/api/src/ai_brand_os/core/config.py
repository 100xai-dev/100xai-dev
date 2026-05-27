from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "100xAI"
    app_env: str = "local"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    database_url: str = "postgresql+psycopg://100xai:100xai@localhost:5432/100xai"
    redis_url: str = "redis://localhost:6379/0"
    openrouter_api_key: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

