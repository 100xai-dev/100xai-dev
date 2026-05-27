from fastapi import APIRouter

from ai_brand_os.schemas.brand import BrandCreate, BrandRead

router = APIRouter(tags=["v1"])


@router.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.post("/brands", response_model=BrandRead)
def create_brand(payload: BrandCreate) -> BrandRead:
    # Placeholder boundary for the first implementation slice:
    # persist brand, enqueue crawl job, return onboarding status.
    return BrandRead(
        id="placeholder-brand-id",
        name=payload.name,
        website=payload.website,
        industry=payload.industry,
        status="pending_crawl",
    )

