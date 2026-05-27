from fastapi import FastAPI

from app.routers.brands import router as brands_router
from app.routers.jobs import router as jobs_router

app = FastAPI(title="100xAI", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


app.include_router(brands_router, prefix="/v1")
app.include_router(jobs_router, prefix="/v1")

