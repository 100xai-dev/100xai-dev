from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models import BrandProfile, IntegrationAccount
from app.repositories.brands import get_active_job, get_brand, list_brands
from app.schemas.brand import (
    ApproveBrandResponse,
    BrandCreate,
    BrandCreateResponse,
    BrandListResponse,
    BrandSummary,
)
from app.schemas.brand_profile import BrandProfileContent, BrandProfileFull, BrandProfilePatch
from app.services.brand_service import approve_brand, create_brand, patch_profile, submit_manual_profile

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
    return BrandListResponse(
        items=[_brand_summary(db, brand.id, current_user.org_id) for brand in list_brands(db, current_user.org_id)]
    )


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
) -> Response:
    require_role(current_user.role, {"admin"})
    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    db.delete(brand)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


def _brand_summary(db: Session, brand_id: str, org_id: str) -> BrandSummary:
    brand = get_brand(db, brand_id, org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    active_job = get_active_job(db, brand.id)
    integrations = db.query(IntegrationAccount).filter(IntegrationAccount.brand_id == brand.id).all()
    readiness = {"wordpress": None, "shopify": None, "webflow": None, "custom_api": None}
    for integration in integrations:
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

