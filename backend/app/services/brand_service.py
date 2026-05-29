import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.deps import CurrentUser
from app.models import Brand, BrandProfile, Job
from app.repositories.brands import get_brand
from app.repositories.jobs import JobsRepository
from app.schemas.brand import BrandCreate, DNASource
from app.schemas.brand_profile import BrandProfileContent, BrandProfilePatch
from app.services.audit import write_audit
from app.services.job_dispatcher import JobDispatcher
from app.services.manual_sources import materialize_manual_sources

logger = logging.getLogger(__name__)


def create_brand(db: Session, payload: BrandCreate, user: CurrentUser) -> tuple[Brand, Job | None]:
    brand = Brand(
        org_id=user.org_id,
        name=payload.name,
        website_url=str(payload.website_url) if payload.website_url else None,
        dna_source=payload.dna_source.value,
        status="CRAWLING" if payload.dna_source == DNASource.CRAWL else "DRAFT",
        created_by=user.id,
    )
    db.add(brand)
    db.flush()

    job = None
    if payload.dna_source == DNASource.CRAWL:
        job = JobsRepository(db).create(
            org_id=user.org_id,
            brand_id=brand.id,
            job_type="brand.onboard",
            stage="CRAWLING",
            input_payload={
                "brand_id": brand.id,
                "seed_url": str(payload.website_url),
                "manual_hints": payload.manual_hints,
                "uploaded_source_ids": payload.uploaded_source_ids,
            },
        )
    write_audit(
        db,
        org_id=user.org_id,
        user_id=user.id,
        brand_id=brand.id,
        action="brand.created",
        resource_type="brand",
        resource_id=brand.id,
        metadata={"dna_source": payload.dna_source.value},
    )
    db.commit()
    db.refresh(brand)
    if job:
        db.refresh(job)
        try:
            JobDispatcher().enqueue_onboarding(job_id=job.id, brand_id=brand.id)
        except Exception:
            logger.exception("enqueue failed for job %s", job.id)
    return brand, job


def request_delete(db: Session, brand_id: str, user: CurrentUser) -> Job:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    brand = get_brand(db, brand_id, user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if brand.status == "PENDING_DELETE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="brand already pending delete")

    brand.status = "PENDING_DELETE"
    job = JobsRepository(db).create(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="brand.purge",
        stage="PENDING_DELETE",
        input_payload={"brand_id": brand.id},
    )
    write_audit(
        db,
        org_id=user.org_id,
        user_id=user.id,
        brand_id=brand.id,
        action="brand.delete_requested",
        resource_type="brand",
        resource_id=brand.id,
    )
    db.commit()
    db.refresh(job)
    try:
        JobDispatcher().enqueue_purge(job_id=job.id, brand_id=brand.id)
    except Exception:
        logger.exception("enqueue purge failed for job %s", job.id)
    return job


def submit_manual_profile(
    db: Session,
    brand_id: str,
    payload: BrandProfileContent,
    user: CurrentUser,
) -> BrandProfile:
    brand = get_brand(db, brand_id, user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if brand.dna_source != "manual" or brand.status != "DRAFT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile submit not allowed")

    profile = BrandProfile(
        brand_id=brand.id,
        **_profile_content_dict(payload),
        generation_source="manual",
        prompt_version=None,
        extraction_model=None,
        raw_extraction=None,
    )
    db.add(profile)
    for source in materialize_manual_sources(brand.id, payload):
        db.add(source)
    brand.status = "PENDING_REVIEW"
    write_audit(
        db,
        org_id=user.org_id,
        user_id=user.id,
        brand_id=brand.id,
        action="brand.profile_submitted_manual",
        resource_type="brand_profile",
        metadata={"generation_source": "manual"},
    )
    db.flush()
    return profile


def patch_profile(
    db: Session,
    brand_id: str,
    payload: BrandProfilePatch,
    user: CurrentUser,
) -> BrandProfile:
    brand = get_brand(db, brand_id, user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if brand.status != "PENDING_REVIEW" or profile.locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="locked profile cannot be edited")

    updates = payload.model_dump(exclude_unset=True, mode="json")
    for key, value in updates.items():
        setattr(profile, key, value)
    write_audit(
        db,
        org_id=user.org_id,
        user_id=user.id,
        brand_id=brand.id,
        action="brand.profile_edited",
        resource_type="brand_profile",
        resource_id=profile.id,
        metadata={"changed_fields": sorted(updates.keys())},
    )
    db.flush()
    return profile


def approve_brand(db: Session, brand_id: str, user: CurrentUser) -> BrandProfile:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    brand = get_brand(db, brand_id, user.org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if brand.status != "PENDING_REVIEW":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="brand is not pending review")
    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="brand profile missing")

    now = datetime.now(timezone.utc)
    profile.locked = True
    profile.locked_at = now
    profile.locked_by = user.id
    brand.status = "READY"
    write_audit(
        db,
        org_id=user.org_id,
        user_id=user.id,
        brand_id=brand.id,
        action="brand.approved",
        resource_type="brand_profile",
        resource_id=profile.id,
    )
    db.flush()
    return profile


def _profile_content_dict(payload: BrandProfileContent) -> dict:
    data = payload.model_dump(mode="json")
    data.setdefault("disallowed_topics", [])
    data.setdefault("proof_points", [])
    data.setdefault("messaging_guardrails", [])
    data.setdefault("compliance_keywords", [])
    data["internal_links"] = []
    data["placid_template_id"] = None
    data["image_output_bucket"] = None
    data["default_location"] = "United States"
    data["default_language"] = "English"
    data["publish_adapter"] = "none"
    data["publish_config"] = {}
    return data
