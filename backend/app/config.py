from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env paths relative to this file so the worker loads them
# correctly regardless of the working directory it is started from.
_THIS_DIR = Path(__file__).parent          # backend/app/
_BACKEND_ENV = _THIS_DIR.parent / ".env"   # backend/.env
_ROOT_ENV = _THIS_DIR.parent.parent / ".env"  # 100xai/.env (fallback)


class Settings(BaseSettings):
    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://100xai:100xai@localhost:5432/100xai"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me-at-least-32-chars"
    jwt_expiry_hours: int = 24
    access_token_expiry_minutes: int = 15
    refresh_token_secret: str = "dev-refresh-secret-change-me-at-least-32-chars"
    refresh_token_expiry_days: int = 30
    token_encryption_key: str | None = None
    token_encryption_key_id: str = "v1"
    # Optional JSON map of historical keys for rotation, e.g.
    # TOKEN_ENCRYPTION_KEYRING='{"v1": "...", "v2": "..."}' with active = token_encryption_key_id.
    token_encryption_keyring: str | None = None
    openrouter_api_key: str | None = None
    extraction_model: str = "anthropic/claude-haiku-4-5-20251001"
    extraction_model_fallback: str = "openai/gpt-4o"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "100xai-brand-knowledge"
    # Serverless spec used only when the index must be created (create-if-missing).
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    s3_bucket: str = "100xai-uploads"
    crawler_user_agent: str = "100xAI-Crawler/1.0 (+https://100xai.example/bot)"
    crawler_max_pages: int = 20
    crawler_page_timeout_sec: int = 20
    crawler_host_delay_sec: int = 1
    firecrawl_api_key: str | None = None
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    dataforseo_api_key: str | None = None  # alternative: "login:password" combined
    serpapi_api_key: str | None = None  # SerpApi API key for SERP data
    anthropic_api_key: str | None = None
    leonardo_api_key: str | None = None
    placid_api_key: str | None = None
    blog_model: str = "anthropic/claude-haiku-4-5-20251001"
    blog_section_max_tokens: int = 2000
    blog_brief_max_tokens: int = 3000

    model_config = SettingsConfigDict(
        env_file=[str(_ROOT_ENV), str(_BACKEND_ENV)],  # root first, backend overrides
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
