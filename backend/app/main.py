from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re

from app.routers.auth import router as auth_router
from app.routers.blogs import router as blogs_router
from app.routers.brands import router as brands_router
from app.routers.jobs import router as jobs_router
from app.routers.brand_sources import router as brand_sources_router
from app.routers.integrations import router as integrations_router
from app.routers.content_generation import router as content_generation_router

app = FastAPI(title="100xAI", version="0.2.0", docs_url="/docs")

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
        
        # Allow local development and ngrok domains
        if origin and (
            origin.startswith("http://localhost:") or
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
app.include_router(content_generation_router, prefix="/v1")
