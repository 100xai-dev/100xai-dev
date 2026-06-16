# app/routers/content_generation.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.base import uuid_str
from app.models.onboarding import Brand, BrandProfile, Job
from app.repositories.brands import get_brand
from app.schemas.content_generation import ContentGenerationRequest, ContentGenerationResponse
from app.services.job_dispatcher import JobDispatcher
from app.services.content_generation import JOB_STAGE_CONTENT
from app.services.billing import enforce_plan_limit, require_active_subscription
from app.services.billing_plans import RESOURCE_BLOGS

router = APIRouter(tags=["content-generation"])


@router.post(
    "/brands/{brand_id}/content-generation",
    response_model=ContentGenerationResponse,
    status_code=status.HTTP_201_CREATED
)
def trigger_content_generation(
    brand_id: str,
    payload: ContentGenerationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ContentGenerationResponse:
    """Trigger Pipeline 3 content generation"""
    require_role(current_user.role, {"admin", "team_member"})
    require_active_subscription(db, current_user.org_id)
    enforce_plan_limit(db, current_user.org_id, RESOURCE_BLOGS)

    # Verify brand exists and is ready
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand.status != "READY":
        raise HTTPException(status_code=400, detail="Brand must be READY for content generation")

    # Verify brand profile exists
    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Brand DNA profile not found")

    # Create content generation job
    job = Job(
        id=uuid_str(),
        org_id=current_user.org_id,
        brand_id=brand_id,
        job_type="content_generation",
        stage=JOB_STAGE_CONTENT,
        status="QUEUED",
        input_payload={
            "keyword": payload.keyword,
            "serp_analysis_job_id": payload.serp_analysis_job_id,
            "triggered_by": current_user.id,
        }
    )
    db.add(job)
    db.flush()

    # Enqueue for processing
    dispatcher = JobDispatcher()
    dispatcher.enqueue_content_generation(
        job_id=job.id,
        brand_id=brand_id,
        keyword=payload.keyword,
        serp_analysis_job_id=payload.serp_analysis_job_id
    )

    db.commit()
    
    return ContentGenerationResponse(
        job_id=job.id,
        status="queued",
        message=f"Content generation started for keyword: {payload.keyword}"
    )