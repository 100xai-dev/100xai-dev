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

# Custom CORS middleware to handle ngrok domains
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NgrokCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            if origin and (
                origin.startswith("http://localhost:") or
                origin == _settings.frontend_url or
                (origin.startswith("https://") and (".ngrok.io" in origin or ".ngrok.app" in origin or ".ngrok-free.app" in origin))
            ):
                return Response(
                    content="",
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, User-Agent, DNT, Cache-Control, X-Mx-ReqToken, Keep-Alive, X-Requested-With, If-Modified-Since",
                        "Access-Control-Max-Age": "86400"
                    }
                )
        
        response = await call_next(request)
        
        # Allow local development, ngrok, and configured production frontend
        if origin and (
            origin.startswith("http://localhost:") or
            origin == _settings.frontend_url or
            (origin.startswith("https://") and (".ngrok.io" in origin or ".ngrok.app" in origin or ".ngrok-free.app" in origin))
        ):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, User-Agent, DNT, Cache-Control, X-Mx-ReqToken, Keep-Alive, X-Requested-With, If-Modified-Since"
        
        return response

app.add_middleware(NgrokCORSMiddleware)


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
