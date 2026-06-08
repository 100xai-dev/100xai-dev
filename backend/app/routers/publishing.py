"""API endpoints for publishing system monitoring and management."""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db import get_db
from app.deps import get_current_user
from app.models.core import User
from app.models.onboarding import Brand
from app.models.schedule import (
    BlogSchedule, 
    PublishingQueue, 
    ScheduleStatus,
    ContentCalendar
)
from app.models.blog import BlogDraft
from app.schemas.schedule import (
    PublishingStatsResponse,
    PublishingQueueResponse,
    FailedPublishingResponse,
    ChannelStatsResponse
)
from app.services.publishers.base import PublisherFactory
from app.services.job_dispatcher import JobDispatcher

router = APIRouter(prefix="/publishing", tags=["publishing"])


@router.get("/stats", response_model=PublishingStatsResponse)
async def get_publishing_stats(
    brand_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get publishing statistics for a brand."""
    # Verify brand access
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.org_id == current_user.org_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get publishing statistics
    stats = db.query(
        func.count(BlogSchedule.id).label("total_schedules"),
        func.count(func.case([(BlogSchedule.status == ScheduleStatus.PUBLISHED, 1)])).label("published_count"),
        func.count(func.case([(BlogSchedule.status == ScheduleStatus.FAILED, 1)])).label("failed_count"),
        func.count(func.case([(BlogSchedule.status == ScheduleStatus.SCHEDULED, 1)])).label("pending_count"),
    ).filter(
        BlogSchedule.brand_id == brand_id,
        BlogSchedule.created_at >= start_date
    ).first()
    
    # Get channel breakdown
    channel_stats = db.query(
        PublishingQueue.channel,
        func.count(PublishingQueue.id).label("total_jobs"),
        func.count(func.case([(PublishingQueue.status == "COMPLETED", 1)])).label("completed_jobs"),
        func.count(func.case([(PublishingQueue.status == "FAILED", 1)])).label("failed_jobs"),
    ).join(BlogSchedule).filter(
        BlogSchedule.brand_id == brand_id,
        BlogSchedule.created_at >= start_date
    ).group_by(PublishingQueue.channel).all()
    
    # Get recent activity
    recent_activity = db.query(BlogSchedule).filter(
        BlogSchedule.brand_id == brand_id,
        BlogSchedule.published_at >= start_date
    ).order_by(desc(BlogSchedule.published_at)).limit(10).all()
    
    return {
        "brand_id": brand_id,
        "period_days": days,
        "total_schedules": stats.total_schedules or 0,
        "published_count": stats.published_count or 0,
        "failed_count": stats.failed_count or 0,
        "pending_count": stats.pending_count or 0,
        "success_rate": (stats.published_count / max(stats.total_schedules, 1)) * 100,
        "channel_stats": [
            {
                "channel": stat.channel,
                "total_jobs": stat.total_jobs,
                "completed_jobs": stat.completed_jobs,
                "failed_jobs": stat.failed_jobs,
                "success_rate": (stat.completed_jobs / max(stat.total_jobs, 1)) * 100
            }
            for stat in channel_stats
        ],
        "recent_activity": [
            {
                "id": activity.id,
                "title": activity.title,
                "status": activity.status,
                "published_at": activity.published_at,
                "channels": activity.target_channels,
                "published_urls": activity.published_urls
            }
            for activity in recent_activity
        ]
    }


@router.get("/queue", response_model=List[PublishingQueueResponse])
async def get_publishing_queue(
    brand_id: str = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current publishing queue for a brand."""
    # Verify brand access
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.org_id == current_user.org_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Build query
    query = db.query(PublishingQueue).join(BlogSchedule).filter(
        BlogSchedule.brand_id == brand_id
    )
    
    if status:
        query = query.filter(PublishingQueue.status == status)
    
    queue_entries = query.order_by(
        PublishingQueue.scheduled_for,
        PublishingQueue.priority.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": entry.id,
            "schedule_id": entry.schedule_id,
            "channel": entry.channel,
            "status": entry.status,
            "scheduled_for": entry.scheduled_for,
            "processing_started_at": entry.processing_started_at,
            "processing_completed_at": entry.processing_completed_at,
            "attempt_count": entry.attempt_count,
            "last_error": entry.last_error,
            "published_url": entry.published_url,
            "external_id": entry.external_id,
            "schedule": {
                "title": entry.schedule.title,
                "status": entry.schedule.status
            }
        }
        for entry in queue_entries
    ]


@router.get("/failures", response_model=List[FailedPublishingResponse])
async def get_failed_publishing(
    brand_id: str = Query(...),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent failed publishing attempts for a brand."""
    # Verify brand access
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.org_id == current_user.org_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Calculate date range
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get failed publishing attempts
    failed_jobs = db.query(PublishingQueue).join(BlogSchedule).filter(
        BlogSchedule.brand_id == brand_id,
        PublishingQueue.status == "FAILED",
        PublishingQueue.processing_completed_at >= start_date
    ).order_by(desc(PublishingQueue.processing_completed_at)).limit(limit).all()
    
    return [
        {
            "id": job.id,
            "schedule_id": job.schedule_id,
            "channel": job.channel,
            "failed_at": job.processing_completed_at,
            "attempt_count": job.attempt_count,
            "last_error": job.last_error,
            "can_retry": job.attempt_count < 3,  # Max retry limit
            "schedule": {
                "title": job.schedule.title,
                "slug": job.schedule.slug
            }
        }
        for job in failed_jobs
    ]


@router.post("/retry/{queue_id}")
async def retry_failed_publishing(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry a failed publishing job."""
    # Get the queue entry
    queue_entry = db.query(PublishingQueue).join(BlogSchedule).filter(
        PublishingQueue.id == queue_id,
        BlogSchedule.org_id == current_user.org_id
    ).first()
    
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Publishing job not found")
    
    if queue_entry.status != "FAILED":
        raise HTTPException(status_code=400, detail="Job is not in failed state")
    
    if queue_entry.attempt_count >= 3:
        raise HTTPException(status_code=400, detail="Job has exceeded maximum retry attempts")
    
    # Reset the queue entry for retry
    queue_entry.status = "PENDING"
    queue_entry.last_error = None
    queue_entry.processing_started_at = None
    queue_entry.processing_completed_at = None
    
    # Update schedule status if needed
    if queue_entry.schedule.status == ScheduleStatus.FAILED:
        queue_entry.schedule.status = ScheduleStatus.PUBLISHING
        queue_entry.schedule.last_error = None
    
    db.commit()
    
    # Re-enqueue the publishing task
    dispatcher = JobDispatcher()
    dispatcher.enqueue_publish_schedule(schedule_id=queue_entry.schedule_id)
    
    return {"message": "Publishing job queued for retry", "queue_id": queue_id}


@router.get("/channels")
async def get_supported_channels():
    """Get list of supported publishing channels."""
    channels = PublisherFactory.get_supported_channels()
    
    # Add metadata for each channel
    channel_info = {
        "wordpress": {
            "name": "WordPress",
            "description": "Publish to WordPress sites using REST API",
            "requires_auth": True,
            "auth_fields": ["site_url", "username", "password"]
        },
        "webhook": {
            "name": "Custom Webhook",
            "description": "Publish to any site using custom webhooks",
            "requires_auth": True,
            "auth_fields": ["webhook_url", "auth_type", "auth_token"]
        },
        "shopify": {
            "name": "Shopify Blog",
            "description": "Publish to Shopify store blogs",
            "requires_auth": True,
            "auth_fields": ["shop_name", "access_token"]
        },
        "ghost": {
            "name": "Ghost",
            "description": "Publish to Ghost publications",
            "requires_auth": True,
            "auth_fields": ["site_url", "admin_api_key"]
        }
    }
    
    return [
        {
            "channel": channel,
            **channel_info.get(channel, {
                "name": channel.title(),
                "description": f"Publish to {channel}",
                "requires_auth": True,
                "auth_fields": []
            })
        }
        for channel in channels
    ]


@router.post("/test-connection")
async def test_publisher_connection(
    channel: str,
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Test connection to a publishing channel."""
    try:
        publisher = PublisherFactory.get_publisher(channel, config)
        is_valid = publisher.test_connection()
        
        if is_valid:
            return {
                "success": True,
                "message": f"Successfully connected to {channel}",
                "tested_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "message": f"Connection test failed for {channel}",
                "tested_at": datetime.now(timezone.utc).isoformat()
            }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Unsupported channel: {channel}")
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "tested_at": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health")
async def get_publishing_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall publishing system health status."""
    # Check for stuck jobs (processing for more than 1 hour)
    stuck_jobs = db.query(PublishingQueue).filter(
        PublishingQueue.status == "PENDING",
        PublishingQueue.processing_started_at != None,
        PublishingQueue.processing_started_at < datetime.now(timezone.utc) - timedelta(hours=1)
    ).count()
    
    # Check for high failure rate in last 24 hours
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_stats = db.query(
        func.count(PublishingQueue.id).label("total"),
        func.count(func.case([(PublishingQueue.status == "FAILED", 1)])).label("failed")
    ).filter(
        PublishingQueue.processing_completed_at >= yesterday
    ).first()
    
    failure_rate = 0
    if recent_stats.total > 0:
        failure_rate = (recent_stats.failed / recent_stats.total) * 100
    
    # Determine health status
    is_healthy = stuck_jobs == 0 and failure_rate < 10
    
    return {
        "healthy": is_healthy,
        "stuck_jobs": stuck_jobs,
        "failure_rate_24h": failure_rate,
        "total_jobs_24h": recent_stats.total,
        "failed_jobs_24h": recent_stats.failed,
        "supported_channels": PublisherFactory.get_supported_channels(),
        "checked_at": datetime.now(timezone.utc).isoformat()
    }