from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re

from app.routers.auth import router as auth_router
from app.routers.blogs import router as blogs_router
from app.routers.brands import router as brands_router
from app.routers.jobs import router as jobs_router
from app.routers.brand_sources import router as brand_sources_router
from app.routers.integrations import router as integrations_router
from app.routers.wpcom_oauth import router as wpcom_oauth_router
from app.routers.content_generation import router as content_generation_router
from app.routers.schedules import router as schedules_router
from app.routers.publishing import router as publishing_router
from app.routers.billing import router as billing_router
from app.routers.persona import router as persona_router
from app.config import get_settings as _get_settings

_settings = _get_settings()
_is_dev = _settings.app_env == "development"

app = FastAPI(
    title="100xAI",
    version="0.2.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
)

# CORS: allow the production frontends, local dev, and any ngrok tunnel.
# Starlette's CORSMiddleware answers preflight OPTIONS correctly for every
# allowed origin (returning 200 with the right headers) instead of falling
# through to the route and returning a spurious 405.
_allowed_origins = {
    "https://app.100xai.co",
    "https://www.100xai.co",
    "https://100xai.co",
    "http://localhost:3000",
    # Always trust the explicitly configured frontend (strip any trailing slash
    # so it matches the browser's slash-less Origin header).
    _settings.frontend_url.rstrip("/"),
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_allowed_origins),
    allow_origin_regex=r"https://[^/]+\.(ngrok\.io|ngrok\.app|ngrok-free\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(auth_router, prefix="/v1")
app.include_router(blogs_router, prefix="/v1")
app.include_router(brands_router, prefix="/v1")
app.include_router(jobs_router, prefix="/v1")
app.include_router(brand_sources_router, prefix="/v1")
app.include_router(integrations_router, prefix="/v1")
app.include_router(wpcom_oauth_router, prefix="/v1")
app.include_router(content_generation_router, prefix="/v1")
app.include_router(schedules_router)
app.include_router(publishing_router, prefix="/v1")
app.include_router(billing_router, prefix="/v1")
app.include_router(persona_router, prefix="/v1")
