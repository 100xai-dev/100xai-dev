from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models import Brand, BrandProfile, Job, Keyword
from app.repositories.brands import get_brand
from app.schemas.brand import (
    ApproveBrandResponse,
    BrandCreate,
    BrandCreateResponse,
    BrandListResponse,
    BrandSummary,
)
from app.schemas.brand_profile import BrandProfileContent, BrandProfileFull, BrandProfilePatch
from app.schemas.keyword import KeywordListResponse, KeywordOut, KeywordResearchRequest, KeywordResearchResponse, KeywordStatsResponse
from app.services.brand_service import approve_brand, create_brand, delete_brand_immediately, patch_profile, submit_manual_profile

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandCreateResponse, status_code=status.HTTP_201_CREATED)
def create_brand_endpoint(
    payload: BrandCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandCreateResponse:
    require_role(current_user.role, {"admin", "team_member"})
    brand, job = create_brand(db, payload, current_user)
    return BrandCreateResponse(
        brand_id=brand.id,
        status=brand.status,
        dna_source=brand.dna_source,
        job_id=job.id if job else None,
    )


@router.get("", response_model=BrandListResponse)
def list_brands_endpoint(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandListResponse:
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    return BrandListResponse(items=_list_brand_summaries(db, current_user.org_id))


@router.get("/{brand_id}", response_model=BrandSummary)
def get_brand_endpoint(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandSummary:
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return _brand_summary(db, brand.id, current_user.org_id)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand_endpoint(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    require_role(current_user.role, {"admin"})
    delete_brand_immediately(db, brand_id, current_user)


@router.post("/{brand_id}/profile", response_model=BrandProfileFull, status_code=status.HTTP_201_CREATED)
def submit_profile_endpoint(
    brand_id: str,
    payload: BrandProfileContent,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandProfileFull:
    require_role(current_user.role, {"admin", "team_member"})
    return _profile_to_schema(submit_manual_profile(db, brand_id, payload, current_user))


@router.get("/{brand_id}/profile", response_model=BrandProfileFull)
def get_profile_endpoint(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandProfileFull:
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return _profile_to_schema(profile)


@router.patch("/{brand_id}/profile", response_model=BrandProfileFull)
def patch_profile_endpoint(
    brand_id: str,
    payload: BrandProfilePatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BrandProfileFull:
    require_role(current_user.role, {"admin", "team_member"})
    return _profile_to_schema(patch_profile(db, brand_id, payload, current_user))


@router.post("/{brand_id}/approve", response_model=ApproveBrandResponse)
def approve_brand_endpoint(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ApproveBrandResponse:
    profile = approve_brand(db, brand_id, current_user)
    return ApproveBrandResponse(
        brand_id=brand_id,
        status="READY",
        locked_at=profile.locked_at,
        locked_by=profile.locked_by,
    )


_ACTIVE_JOB_STATUSES = ("QUEUED", "NEW", "RUNNING")
_CHANNELS = ("wordpress", "shopify", "webflow", "custom_api")


def _build_summary(brand: Brand) -> BrandSummary:
    active_jobs = sorted(
        (j for j in brand.jobs if j.status in _ACTIVE_JOB_STATUSES),
        key=lambda j: j.created_at,
        reverse=True,
    )
    active_job = active_jobs[0] if active_jobs else None
    readiness: dict[str, str | None] = {c: None for c in _CHANNELS}
    for integration in brand.integration_accounts:
        if integration.provider in readiness:
            readiness[integration.provider] = integration.status
    return BrandSummary(
        id=brand.id,
        name=brand.name,
        website_url=brand.website_url,
        dna_source=brand.dna_source,
        status=brand.status,
        failure_reason=brand.failure_reason,
        created_by=brand.created_by,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
        channel_readiness=readiness,
        active_job=(
            {
                "id": active_job.id,
                "status": active_job.status,
                "stage": active_job.stage,
                "progress": active_job.progress,
            }
            if active_job
            else None
        ),
    )


def _list_brand_summaries(db: Session, org_id: str) -> list[BrandSummary]:
    stmt = (
        select(Brand)
        .where(Brand.org_id == org_id)
        .options(selectinload(Brand.jobs), selectinload(Brand.integration_accounts))
        .order_by(Brand.created_at.desc())
    )
    return [_build_summary(b) for b in db.execute(stmt).scalars().all()]


def _brand_summary(db: Session, brand_id: str, org_id: str) -> BrandSummary:
    stmt = (
        select(Brand)
        .where(Brand.id == brand_id, Brand.org_id == org_id)
        .options(selectinload(Brand.jobs), selectinload(Brand.integration_accounts))
    )
    brand = db.execute(stmt).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return _build_summary(brand)


def _profile_to_schema(profile: BrandProfile) -> BrandProfileFull:
    return BrandProfileFull(
        id=profile.id,
        brand_id=profile.brand_id,
        name=profile.name,
        site_url=profile.site_url,
        one_liner=profile.one_liner,
        industry=profile.industry,
        allowed_topics=profile.allowed_topics or [],
        disallowed_topics=profile.disallowed_topics or [],
        audience_personas=profile.audience_personas or [],
        tone_rules=profile.tone_rules,
        banned_phrases=profile.banned_phrases or [],
        unique_angle=profile.unique_angle,
        ctas=profile.ctas or [],
        proof_points=profile.proof_points or [],
        messaging_guardrails=profile.messaging_guardrails or [],
        compliance_keywords=profile.compliance_keywords or [],
        image_subject_hints=profile.image_subject_hints,
        image_palette=profile.image_palette,
        visual_direction=profile.visual_direction,
        internal_links=profile.internal_links or [],
        placid_template_id=profile.placid_template_id,
        image_output_bucket=profile.image_output_bucket,
        default_location=profile.default_location,
        default_language=profile.default_language,
        publish_adapter=profile.publish_adapter,
        publish_config=profile.publish_config or {},
        generation_source=profile.generation_source,
        prompt_version=profile.prompt_version,
        extraction_model=profile.extraction_model,
        locked=profile.locked,
        locked_at=profile.locked_at,
        locked_by=profile.locked_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ---------------------------------------------------------------------------
# Keyword Research Endpoints
# ---------------------------------------------------------------------------

@router.post("/{brand_id}/keywords/research", response_model=KeywordResearchResponse)
def start_keyword_research(
    brand_id: str,
    payload: KeywordResearchRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> KeywordResearchResponse:
    """Start keyword research for a brand."""
    require_role(current_user.role, {"admin", "team_member"})
    
    # Verify brand exists and user has access
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    # Get brand profile for context
    brand_profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
    brand_context = ""
    business_description = ""
    
    if brand_profile:
        brand_context = f"{brand_profile.one_liner}. Industry: {brand_profile.industry or 'Unknown'}. Unique angle: {brand_profile.unique_angle}"
        business_description = brand_profile.tone_rules or brand_profile.one_liner
    
    # Create job
    job = Job(
        brand_id=brand_id,
        org_id=current_user.org_id,
        job_type="keyword_research",
        status="QUEUED",
        stage="NEW",
        input_payload={"seed_keyword": payload.seed_keyword}
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Enqueue the keyword research job
    from app.services.job_dispatcher import JobDispatcher
    dispatcher = JobDispatcher()
    dispatcher.enqueue_keyword_research(
        job_id=job.id,
        brand_id=brand_id,
        primary_keyword=payload.seed_keyword,
        brand_context=brand_context,
        business_description=business_description
    )
    
    return KeywordResearchResponse(
        job_id=job.id,
        brand_id=brand_id,
        seed_keyword=payload.seed_keyword,
        status="QUEUED",
        message=f"Keyword research started for '{payload.seed_keyword}'. This may take 5-10 minutes."
    )


@router.get("/{brand_id}/keywords", response_model=KeywordListResponse)
def list_keywords(
    brand_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> KeywordListResponse:
    """List keywords discovered for a brand."""
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    
    # Verify brand exists and user has access
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    # Get latest keyword research job
    latest_job = db.query(Job).filter(
        Job.brand_id == brand_id,
        Job.job_type == "keyword_research"
    ).order_by(Job.created_at.desc()).first()
    
    # Determine research status
    research_status = "never_run"
    if latest_job:
        if latest_job.status in ["QUEUED", "RUNNING"]:
            research_status = "processing"
        elif latest_job.status == "SUCCEEDED":
            research_status = "completed"
        elif latest_job.status == "FAILED":
            research_status = "failed"
    
    # Get keywords with pagination
    keywords_query = db.query(Keyword).filter(Keyword.brand_id == brand_id).order_by(Keyword.score.desc().nullslast())
    total = keywords_query.count()
    keywords = keywords_query.offset(offset).limit(limit).all()
    
    keyword_outs = [
        KeywordOut(
            id=kw.id,
            related_keyword=kw.related_keyword,
            primary_keyword=kw.primary_keyword,
            source_type=kw.source_type,
            search_volume=kw.search_volume,
            keyword_difficulty=kw.keyword_difficulty,
            cpc=kw.cpc,
            competition=kw.competition,
            search_intent=kw.search_intent,
            score=kw.score,
            created_at=kw.created_at
        )
        for kw in keywords
    ]
    
    return KeywordListResponse(
        keywords=keyword_outs,
        total=total,
        brand_id=brand_id,
        latest_job_id=latest_job.id if latest_job else None,
        research_status=research_status
    )


@router.get("/{brand_id}/keywords/stats", response_model=KeywordStatsResponse)
def get_keyword_stats(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> KeywordStatsResponse:
    """Get keyword research statistics for a brand."""
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    
    # Verify brand exists and user has access
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    keywords = db.query(Keyword).filter(Keyword.brand_id == brand_id).all()
    
    if not keywords:
        return KeywordStatsResponse(
            total_keywords=0,
            avg_search_volume=None,
            avg_difficulty=None,
            top_sources={},
            completion_rate=0.0
        )
    
    # Calculate statistics
    volumes = [k.search_volume for k in keywords if k.search_volume is not None]
    difficulties = [k.keyword_difficulty for k in keywords if k.keyword_difficulty is not None]
    
    avg_volume = sum(volumes) / len(volumes) if volumes else None
    avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else None
    
    # Count by source type
    source_counts = {}
    for kw in keywords:
        source_counts[kw.source_type] = source_counts.get(kw.source_type, 0) + 1
    
    # Calculate completion rate (keywords with all metrics)
    complete_keywords = sum(1 for k in keywords if all([
        k.search_volume is not None,
        k.keyword_difficulty is not None,
        k.score is not None
    ]))
    completion_rate = complete_keywords / len(keywords) if keywords else 0.0
    
    return KeywordStatsResponse(
        total_keywords=len(keywords),
        avg_search_volume=avg_volume,
        avg_difficulty=avg_difficulty,
        top_sources=source_counts,
        completion_rate=completion_rate
    )
