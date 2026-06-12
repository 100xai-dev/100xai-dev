import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.base import uuid_str
from app.models.blog import BlogBrief, BlogDraft, BlogJob
from app.models.onboarding import Brand, BrandProfile, Job
from app.repositories.brands import get_brand
from app.schemas.blog import (
    ApproveBriefRequest,
    ApproveArticleRequest,
    BlogJobCreate,
    BlogJobListOut,
    BlogJobOut,
)
from app.services.job_dispatcher import JobDispatcher

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blogs"])


async def _publish_to_wordpress(db: Session, brand_id: str, job: BlogJob, draft: BlogDraft) -> str:
    """Publish an approved draft live to WordPress, mapping failures to HTTP errors."""
    from app.services.wp_publish import WPPublishError, publish_blog_draft

    try:
        return await publish_blog_draft(db, brand_id, job, draft, status="publish")
    except WPPublishError as exc:
        job.error_message = f"Publish failed: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail=f"WordPress publish failed: {exc}")


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

    # Run the full pipeline (P1 keyword research → P2 SERP analysis → P3 content
    # generation). The AI selection layer in P1 picks the best target keyword —
    # relevant to the user's seed and high-traffic — instead of writing blindly for
    # the typed keyword. The chain auto-advances P1→P2→P3 via the job dispatcher.
    job_id = uuid_str()

    # Create the BlogJob for UI compatibility. The eventually-generated draft links
    # back here via blog_job_id (propagated through the pipeline payloads).
    blog_job = BlogJob(
        id=job_id,
        org_id=current_user.org_id,
        brand_id=brand_id,
        created_by=current_user.id,
        keyword=keyword,
        status="GENERATING",
    )
    db.add(blog_job)

    # Pipeline 1 (keyword research) job. P1→P2 reuse this same job row; P2→P3 spawns a
    # separate content_generation job carrying blog_job_id so its draft links to this
    # BlogJob (see content_generation.run_content_generation_pipeline).
    pipeline_job = Job(
        id=job_id,  # Share the BlogJob id so blog_job_id linkage is implicit.
        org_id=current_user.org_id,
        brand_id=brand_id,
        job_type="keyword_research",
        status="QUEUED",
        stage="KEYWORD",
        input_payload={
            "keyword": keyword,
            "created_by": current_user.id,
            "blog_job_id": job_id,     # Link the final draft back to this BlogJob.
            "blog_integration": True,  # Flag: originated from the blog UI.
            "include_image": payload.include_image,
        },
    )
    db.add(pipeline_job)
    db.commit()

    JobDispatcher().enqueue_keyword_research(
        job_id=job_id,
        brand_id=brand_id,
        primary_keyword=keyword,
        brand_context=profile.one_liner or "",
        business_description=profile.industry or "",
    )

    return BlogJobOut.model_validate(blog_job)


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
    blog_job = _get_blog_job(db, job_id, current_user.org_id)
    
    # Sync status from the pipeline. The job sharing this BlogJob's id runs P1→P2;
    # P2→P3 spawns a separate content_generation job (recorded on the P1/P2 job's
    # output_payload as ``auto_triggered_content_job``) whose draft links back here.
    pipeline_job = db.query(Job).filter(Job.id == job_id).first()

    if pipeline_job:
        content_job_id = (pipeline_job.output_payload or {}).get("auto_triggered_content_job")
        content_job = (
            db.query(Job).filter(Job.id == content_job_id).first() if content_job_id else None
        )
        # The generated draft (keyed to this BlogJob's id) is the completion signal —
        # the P1/P2 job reaches SUCCEEDED well before P3 finishes writing.
        draft = db.query(BlogDraft).filter(BlogDraft.job_id == job_id).first()

        if draft and draft.html_content:
            new_status = "PENDING_REVIEW"
        elif pipeline_job.status == "FAILED" or (content_job and content_job.status == "FAILED"):
            # FAILED is terminal — map it explicitly so the UI stops polling.
            new_status = "FAILED"
        elif content_job and content_job.stage in ("DRAFT", "IMAGE"):
            new_status = "WRITING"
        else:
            new_status = "GENERATING"

        if new_status != blog_job.status:
            blog_job.status = new_status
            err = (content_job and content_job.error_message) or pipeline_job.error_message
            if err:
                blog_job.error_message = err
            db.commit()

    return BlogJobOut.model_validate(blog_job)


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

    # Check if this is a Pipeline 3 job
    pipeline_job = db.query(Job).filter(
        Job.id == job_id,
        Job.job_type == "content_generation"
    ).first()
    
    if pipeline_job:
        # Pipeline 3 jobs skip the brief process - they generate complete articles
        raise HTTPException(status_code=400, detail="Pipeline 3 jobs do not require brief approval - content is generated automatically")

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
    job.status = "WRITING"  # Set status BEFORE enqueue so the API response reflects the new state

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

    # The job sharing this BlogJob's id is the pipeline entrypoint (keyword_research
    # for new jobs; content_generation for legacy ones). Retry restarts the chain
    # from that entrypoint.
    pipeline_job = db.query(Job).filter(
        Job.id == job_id,
        Job.job_type.in_(["keyword_research", "content_generation"]),
    ).first()

    if pipeline_job:
        keyword = (pipeline_job.input_payload or {}).get("keyword", "content")
        # Reset the pipeline job to its starting stage.
        pipeline_job.status = "QUEUED"
        pipeline_job.stage = "KEYWORD" if pipeline_job.job_type == "keyword_research" else "CONTENT"
        pipeline_job.error_message = None
        pipeline_job.error_details = None
        pipeline_job.started_at = None
        pipeline_job.finished_at = None
        pipeline_job.output_payload = None  # Clear stale auto_triggered_content_job linkage.

        job.status = "GENERATING"
        job.error_message = None
        db.commit()

        if pipeline_job.job_type == "keyword_research":
            JobDispatcher().enqueue_keyword_research(
                job_id=job_id,
                brand_id=brand_id,
                primary_keyword=keyword,
            )
        else:
            JobDispatcher().enqueue_content_generation(
                job_id=job_id,
                brand_id=brand_id,
                keyword=keyword,
            )
    else:
        # Legacy blog pipeline
        job.status = "NEW"
        job.error_message = None
        db.commit()
        JobDispatcher().enqueue_blog_brief(job_id=job.id)
    
    return BlogJobOut.model_validate(job)


@router.post("/brands/{brand_id}/blogs/{job_id}/approve-article", response_model=BlogJobOut)
async def approve_article(
    brand_id: str,
    job_id: str,
    payload: ApproveArticleRequest | None = None,
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

    # Actually publish the approved draft live to the connected WordPress site.
    published_url = await _publish_to_wordpress(db, brand_id, job, draft)

    job.status = "PUBLISHED"
    job.error_message = None
    db.commit()
    db.refresh(job)

    logger.info("Blog %s published live to WordPress: %s", job_id, published_url)
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
