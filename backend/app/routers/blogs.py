from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.base import uuid_str
from app.models.blog import BlogBrief, BlogDraft, BlogJob
from app.models.onboarding import Brand, BrandProfile
from app.repositories.brands import get_brand
from app.schemas.blog import (
    ApproveBriefRequest,
    ApproveArticleRequest,
    BlogJobCreate,
    BlogJobListOut,
    BlogJobOut,
)
from app.services.job_dispatcher import JobDispatcher

router = APIRouter(tags=["blogs"])


def _get_blog_job(db: Session, job_id: str, org_id: str) -> BlogJob:
    job = db.query(BlogJob).filter(
        BlogJob.id == job_id,
        BlogJob.org_id == org_id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="blog job not found")
    return job


@router.post("/brands/{brand_id}/blogs", response_model=BlogJobOut, status_code=status.HTTP_201_CREATED)
def create_blog_job(
    brand_id: str,
    payload: BlogJobCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})

    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")
    if brand.status != "READY":
        raise HTTPException(status_code=400, detail="brand must be READY before generating blogs")

    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="brand DNA profile not found")

    keyword = payload.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=422, detail="keyword cannot be empty")

    job = BlogJob(
        id=uuid_str(),
        org_id=current_user.org_id,
        brand_id=brand_id,
        created_by=current_user.id,
        keyword=keyword,
        status="NEW",
    )
    db.add(job)
    db.commit()

    JobDispatcher().enqueue_blog_brief(job_id=job.id)
    return BlogJobOut.model_validate(job)


@router.get("/brands/{brand_id}/blogs", response_model=BlogJobListOut)
def list_blog_jobs(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobListOut:
    require_role(current_user.role, {"admin", "team_member", "viewer"})

    brand = get_brand(db, brand_id, current_user.org_id)
    if not brand:
        raise HTTPException(status_code=404, detail="brand not found")

    jobs = (
        db.query(BlogJob)
        .filter(BlogJob.brand_id == brand_id, BlogJob.org_id == current_user.org_id)
        .order_by(BlogJob.created_at.desc())
        .all()
    )
    return BlogJobListOut(items=[BlogJobOut.model_validate(j) for j in jobs])


@router.get("/brands/{brand_id}/blogs/{job_id}", response_model=BlogJobOut)
def get_blog_job(
    brand_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    job = _get_blog_job(db, job_id, current_user.org_id)
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/approve-brief", response_model=BlogJobOut)
def approve_brief(
    brand_id: str,
    job_id: str,
    payload: ApproveBriefRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})
    job = _get_blog_job(db, job_id, current_user.org_id)

    if job.status != "PENDING_BRIEF_REVIEW":
        raise HTTPException(status_code=400, detail=f"cannot approve brief in status {job.status}")

    brief = job.brief
    if not brief:
        raise HTTPException(status_code=404, detail="brief not found")

    if payload.selected_title:
        brief.selected_title = payload.selected_title

    brief.approved = True
    brief.approved_at = datetime.now(timezone.utc)
    brief.approved_by = current_user.id

    db.commit()
    JobDispatcher().enqueue_blog_write(job_id=job.id)

    db.refresh(job)
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/reject-brief", response_model=BlogJobOut)
def reject_brief(
    brand_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})
    job = _get_blog_job(db, job_id, current_user.org_id)

    if job.status != "PENDING_BRIEF_REVIEW":
        raise HTTPException(status_code=400, detail=f"cannot reject brief in status {job.status}")

    job.status = "REJECTED"
    db.commit()
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/retry", response_model=BlogJobOut)
def retry_blog(
    brand_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})
    job = _get_blog_job(db, job_id, current_user.org_id)

    if job.status not in {"REJECTED", "FAILED"}:
        raise HTTPException(status_code=400, detail="only REJECTED or FAILED jobs can be retried")

    job.status = "NEW"
    job.error_message = None
    db.commit()

    JobDispatcher().enqueue_blog_brief(job_id=job.id)
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/approve-article", response_model=BlogJobOut)
def approve_article(
    brand_id: str,
    job_id: str,
    payload: ApproveArticleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})
    job = _get_blog_job(db, job_id, current_user.org_id)

    if job.status != "PENDING_REVIEW":
        raise HTTPException(status_code=400, detail=f"cannot approve article in status {job.status}")

    draft = job.draft
    if not draft:
        raise HTTPException(status_code=404, detail="draft not found")

    draft.approved = True
    draft.approved_at = datetime.now(timezone.utc)
    draft.approved_by = current_user.id
    job.status = "PUBLISHED"
    db.commit()

    db.refresh(job)
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/reject-article", response_model=BlogJobOut)
def reject_article(
    brand_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BlogJobOut:
    require_role(current_user.role, {"admin", "team_member"})
    job = _get_blog_job(db, job_id, current_user.org_id)

    if job.status != "PENDING_REVIEW":
        raise HTTPException(status_code=400, detail=f"cannot reject article in status {job.status}")

    job.status = "REJECTED"
    db.commit()
    return BlogJobOut.model_validate(job)
