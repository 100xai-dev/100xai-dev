from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://100xai:100xai@localhost:5432/100xai"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me-at-least-32-chars"
    jwt_expiry_hours: int = 24
    token_encryption_key: str | None = None
    token_encryption_key_id: str = "v1"
    # Optional JSON map of historical keys for rotation, e.g.
    # TOKEN_ENCRYPTION_KEYRING='{"v1": "...", "v2": "..."}' with active = token_encryption_key_id.
    token_encryption_keyring: str | None = None
    openrouter_api_key: str | None = None
    extraction_model: str = "anthropic/claude-3-5-sonnet"
    extraction_model_fallback: str = "openai/gpt-4o"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "100xai-brand-knowledge"
    s3_bucket: str = "100xai-uploads"
    crawler_user_agent: str = "100xAI-Crawler/1.0 (+https://100xai.example/bot)"
    crawler_max_pages: int = 12
    crawler_page_timeout_sec: int = 20
    crawler_host_delay_sec: int = 1
    apify_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
