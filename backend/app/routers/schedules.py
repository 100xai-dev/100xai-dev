"""Blog scheduling and calendar management endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.deps import CurrentUser, get_current_user
from app.db import get_db
from app.models.base import uuid_str
from app.models.blog import BlogJob
from app.models.onboarding import Brand, BrandProfile, Job
from app.models.schedule import BlogSchedule, ContentSource, ScheduleStatus
from app.schemas.schedule import BulkScheduleRequest
from app.services.job_dispatcher import JobDispatcher

router = APIRouter(prefix="/v1/schedules", tags=["schedules"])


def _resolve_to_utc(date_str: str, time_str: str, tz_str: str) -> datetime:
    """Combine 'YYYY-MM-DD' + 'HH:MM' in tz_str and return an aware UTC datetime."""
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date '{date_str}', expected YYYY-MM-DD")
    try:
        hh, mm = (int(p) for p in time_str.strip().split(":")[:2])
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail=f"Invalid time '{time_str}', expected HH:MM")
    try:
        tz = ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, ValueError):
        tz = timezone.utc
    local = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
    return local.astimezone(timezone.utc)


def _get_brand(db: Session, brand_id: str, org_id: str) -> Brand:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == org_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.post("/brands/{brand_id}/bulk", response_model=dict, status_code=201)
def create_schedules_bulk(
    brand_id: str,
    body: BulkScheduleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Schedule blog content across one or more days in a single request.

    For each (date, keyword): kicks off article generation immediately and creates
    a SCHEDULED BlogSchedule that auto-publishes to WordPress at the chosen time on
    that day.
    """
    require_role(current_user.role, {"admin", "team_member"})
    brand = _get_brand(db, brand_id, current_user.org_id)

    if brand.status != "READY":
        raise HTTPException(status_code=400, detail="brand must be READY before scheduling blogs")
    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="brand DNA profile not found")

    dispatcher = JobDispatcher()
    created = []
    publish_jobs = []  # (schedule_id, run_at) — enqueued after commit

    for item in body.items:
        keyword = item.keyword.strip()
        if not keyword:
            continue
        scheduled_at = _resolve_to_utc(item.date, body.time, body.timezone_str)

        # 1. Kick off generation now so the draft is ready before the publish date.
        job_id = uuid_str()
        db.add(BlogJob(
            id=job_id,
            org_id=current_user.org_id,
            brand_id=brand_id,
            created_by=current_user.id,
            keyword=keyword,
            status="GENERATING",
        ))
        db.add(Job(
            id=job_id,
            org_id=current_user.org_id,
            brand_id=brand_id,
            job_type="content_generation",
            status="QUEUED",
            stage="CONTENT",
            input_payload={"keyword": keyword, "created_by": current_user.id, "blog_integration": True},
        ))

        # 2. Create the schedule row.
        schedule_id = uuid_str()
        db.add(BlogSchedule(
            id=schedule_id,
            org_id=current_user.org_id,
            brand_id=brand_id,
            title=keyword,
            scheduled_at=scheduled_at,
            timezone=body.timezone_str,
            blog_job_id=job_id,
            target_keyword=keyword,
            target_channels=body.channels or ["wordpress"],
            content_source=ContentSource.AI_GENERATED,
            auto_publish=True,
            status=ScheduleStatus.SCHEDULED,
            created_by=current_user.id,
        ))

        created.append({
            "schedule_id": schedule_id,
            "blog_job_id": job_id,
            "keyword": keyword,
            "scheduled_at": scheduled_at.isoformat(),
        })
        publish_jobs.append((schedule_id, scheduled_at, job_id, keyword))

    if not created:
        raise HTTPException(status_code=422, detail="No valid items to schedule")

    db.commit()

    # After commit: enqueue generation now + the timed auto-publish.
    for schedule_id, scheduled_at, job_id, keyword in publish_jobs:
        dispatcher.enqueue_content_generation(job_id=job_id, brand_id=brand_id, keyword=keyword)
        dispatcher.enqueue_publish_blog_at(schedule_id=schedule_id, run_at=scheduled_at)

    return {"created": created, "count": len(created)}


@router.get("/{schedule_id}", response_model=dict)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a specific schedule."""
    schedule = db.query(BlogSchedule).filter(
        BlogSchedule.id == schedule_id,
        BlogSchedule.org_id == current_user.org_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "id": schedule.id,
        "title": schedule.title,
        "scheduled_at": schedule.scheduled_at,
        "brand_id": schedule.brand_id,
        "blog_job_id": schedule.blog_job_id,
        "target_keyword": schedule.target_keyword,
        "target_channels": schedule.target_channels,
        "status": schedule.status,
        "published_urls": schedule.published_urls,
        "last_error": schedule.last_error,
        "created_at": schedule.created_at,
    }


@router.get("/brands/{brand_id}/calendar", response_model=List[dict])
def get_brand_calendar(
    brand_id: str,
    year: int = Query(..., description="Calendar year"),
    month: int = Query(..., ge=1, le=12, description="Calendar month (1-12)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get scheduled posts for a brand in a given month."""
    require_role(current_user.role, {"admin", "team_member", "viewer"})
    _get_brand(db, brand_id, current_user.org_id)

    # Month range [start, next_month_start) — avoids DB-specific date extraction.
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)

    schedules = db.query(BlogSchedule).filter(
        BlogSchedule.brand_id == brand_id,
        BlogSchedule.org_id == current_user.org_id,
        BlogSchedule.scheduled_at >= start,
        BlogSchedule.scheduled_at < end,
    ).order_by(BlogSchedule.scheduled_at).all()

    return [{
        "id": s.id,
        "title": s.title,
        "scheduled_at": s.scheduled_at,
        "status": s.status,
        "target_keyword": s.target_keyword,
        "target_channels": s.target_channels,
        "blog_job_id": s.blog_job_id,
        "published_urls": s.published_urls,
        "last_error": s.last_error,
    } for s in schedules]


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete (cancel) a schedule."""
    require_role(current_user.role, {"admin", "team_member"})

    schedule = db.query(BlogSchedule).filter(
        BlogSchedule.id == schedule_id,
        BlogSchedule.org_id == current_user.org_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status == ScheduleStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Cannot delete a published schedule")

    db.delete(schedule)
    db.commit()
    return {"message": "Schedule deleted successfully"}
