from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.brands import router as brands_router
from app.routers.jobs import router as jobs_router
from app.routers.brand_sources import router as brand_sources_router
from app.routers.integrations import router as integrations_router

app = FastAPI(title="100xAI", version="0.2.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
app.include_router(brands_router, prefix="/v1")
app.include_router(jobs_router, prefix="/v1")
app.include_router(brand_sources_router, prefix="/v1")
app.include_router(integrations_router, prefix="/v1")
