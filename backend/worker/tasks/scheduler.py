"""Worker tasks for the publishing scheduler system."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from app.db import get_db
from app.models.schedule import (
    BlogSchedule, 
    PublishingQueue, 
    ScheduleStatus
)
from app.models.blog import BlogDraft
from app.services.publishers.base import PublisherFactory, PublishingError

logger = logging.getLogger(__name__)


def _slugify(title: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:200]


def _draft_payload(schedule: "BlogSchedule", draft) -> Dict[str, Any]:
    """Build the channel-agnostic content dict consumed by PublisherFactory publishers."""
    return {
        "title": draft.title or schedule.title,
        "content": draft.html_content or "",
        "excerpt": draft.meta_description or "",
        "slug": _slugify(draft.title or schedule.title),
        "tags": schedule.tags or [],
        "categories": schedule.categories or [],
        "featured_image_url": draft.featured_image_url,
        "meta_description": draft.meta_description or "",
        "status": "publish",
    }


def _publish_channel(db, schedule, job, draft, channel: str) -> str:
    """Publish ``draft`` to a single channel, returning the public URL.

    WordPress reuses the proven legacy provider (``wp_publish.publish_blog_draft``,
    Application Passwords / OAuth — same path as manual approve). All other channels
    (webhook, shopify, ghost) go through ``PublisherFactory`` with credentials
    resolved from the brand's connected IntegrationAccount.
    """
    import asyncio

    if channel == "wordpress":
        from app.services.wp_publish import publish_blog_draft
        return asyncio.run(publish_blog_draft(db, schedule.brand_id, job, draft, status="publish"))

    from app.models import IntegrationAccount
    from app.routers.integrations import _credentials_for_account

    account = (
        db.query(IntegrationAccount)
        .filter(
            IntegrationAccount.brand_id == schedule.brand_id,
            IntegrationAccount.provider == channel,
            IntegrationAccount.status == "active",
        )
        .first()
    ) or (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == schedule.brand_id, IntegrationAccount.provider == channel)
        .first()
    )
    if not account:
        raise PublishingError(f"No {channel} integration connected for this brand")

    config = {**(account.config or {}), **_credentials_for_account(account, db)}
    # Per-schedule overrides (if any) win over the account defaults.
    config.update((schedule.channel_configs or {}).get(channel, {}))

    publisher = PublisherFactory.get_publisher(channel=channel, config=config)
    result = publisher.publish(_draft_payload(schedule, draft))
    if account.status != "active":
        account.status = "active"
    return result.get("url") or ""


def publish_approved_schedule(schedule_id: str) -> None:
    """Publish a reviewer-approved schedule across all its target channels.

    Entered only after a human approves the generated draft (schedules.approve sets
    the schedule to PUBLISHING and enqueues this task). Fans out over
    ``target_channels`` so WordPress and webhook (and other channels) publish in one
    pass, with isolated per-channel failure handling.
    """
    logger.info("Publishing approved schedule %s", schedule_id)
    db = next(get_db())
    try:
        from app.models.blog import BlogJob

        schedule = db.query(BlogSchedule).filter(BlogSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning("Schedule %s not found; skipping", schedule_id)
            return
        if schedule.status in (ScheduleStatus.PUBLISHED, ScheduleStatus.CANCELLED):
            logger.info("Schedule %s already %s; skipping", schedule_id, schedule.status)
            return

        job = db.query(BlogJob).filter(BlogJob.id == schedule.blog_job_id).first() if schedule.blog_job_id else None
        draft = job.draft if job else None
        if not job or not draft:
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = "No generated draft available to publish"
            db.commit()
            logger.error("Schedule %s has no draft to publish", schedule_id)
            return

        channels = schedule.target_channels or ["wordpress"]
        published: Dict[str, str] = {}
        errors: Dict[str, str] = {}
        for channel in channels:
            try:
                published[channel] = _publish_channel(db, schedule, job, draft, channel)
            except Exception as exc:  # noqa: BLE001 - isolate per-channel failures
                logger.exception("Publish to %s failed for schedule %s", channel, schedule_id)
                errors[channel] = str(exc)

        schedule.published_urls = {**(schedule.published_urls or {}), **published}
        if published and not errors:
            schedule.status = ScheduleStatus.PUBLISHED
            schedule.published_at = datetime.now(timezone.utc)
            schedule.last_error = None
            draft.approved = True
            draft.approved_at = datetime.now(timezone.utc)
            job.status = "PUBLISHED"
        else:
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = "; ".join(f"{c}: {e}" for c, e in errors.items())
            schedule.retry_count = (schedule.retry_count or 0) + 1
        db.commit()
        logger.info("Schedule %s publish result: published=%s errors=%s", schedule_id, list(published), list(errors))
    finally:
        db.close()


def publish_scheduled_blog(schedule_id: str) -> None:
    """DEPRECATED — legacy time-triggered auto-publish (pre review-gate).

    No longer enqueued: scheduled posts now require explicit reviewer approval
    (see ``publish_approved_schedule``). Kept for any in-flight RQ jobs.

    Auto-publish a scheduled blog's generated draft to WordPress at its due time.
    """
    import asyncio

    from app.models.blog import BlogJob
    from app.services.wp_publish import WPPublishError, publish_blog_draft

    logger.info("Auto-publishing scheduled blog %s", schedule_id)
    db = next(get_db())
    try:
        schedule = db.query(BlogSchedule).filter(BlogSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning("Schedule %s not found; skipping", schedule_id)
            return
        if schedule.status in (ScheduleStatus.PUBLISHED, ScheduleStatus.CANCELLED):
            logger.info("Schedule %s already %s; skipping", schedule_id, schedule.status)
            return

        job = db.query(BlogJob).filter(BlogJob.id == schedule.blog_job_id).first() if schedule.blog_job_id else None
        draft = job.draft if job else None
        if not job or not draft:
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = "Article was not generated in time for publishing"
            db.commit()
            logger.error("Schedule %s has no draft to publish", schedule_id)
            return

        schedule.status = ScheduleStatus.PUBLISHING
        db.commit()

        try:
            url = asyncio.run(publish_blog_draft(db, schedule.brand_id, job, draft, status="publish"))
        except WPPublishError as exc:
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = str(exc)
            schedule.retry_count = (schedule.retry_count or 0) + 1
            db.commit()
            logger.error("Auto-publish failed for schedule %s: %s", schedule_id, exc)
            raise

        schedule.status = ScheduleStatus.PUBLISHED
        schedule.published_at = datetime.now(timezone.utc)
        schedule.published_urls = {**(schedule.published_urls or {}), "wordpress": url}
        schedule.last_error = None
        draft.approved = True
        draft.approved_at = datetime.now(timezone.utc)
        job.status = "PUBLISHED"
        db.commit()
        logger.info("Schedule %s auto-published: %s", schedule_id, url)
    finally:
        db.close()


def run_publishing_scheduler() -> None:
    """
    Cron-based scheduler that runs every 5 minutes.
    Checks for schedules due for publishing and queues them.
    """
    logger.info("Running publishing scheduler")
    db = next(get_db())
    
    try:
        # Find schedules that are due for publishing
        now = datetime.now(timezone.utc)
        due_schedules = db.query(BlogSchedule).filter(
            BlogSchedule.status == ScheduleStatus.SCHEDULED,
            BlogSchedule.scheduled_at <= now,
            BlogSchedule.auto_publish == True
        ).all()
        
        logger.info(f"Found {len(due_schedules)} schedules due for publishing")
        
        for schedule in due_schedules:
            try:
                # Update status to PUBLISHING
                schedule.status = ScheduleStatus.PUBLISHING
                db.commit()
                
                # Create publishing queue entries for each channel
                for channel in schedule.target_channels:
                    # Check if queue entry already exists
                    existing_queue = db.query(PublishingQueue).filter(
                        PublishingQueue.schedule_id == schedule.id,
                        PublishingQueue.channel == channel
                    ).first()
                    
                    if not existing_queue:
                        queue_entry = PublishingQueue(
                            schedule_id=schedule.id,
                            channel=channel,
                            scheduled_for=schedule.scheduled_at,
                            channel_config=schedule.channel_configs.get(channel, {}),
                            priority=5  # Normal priority
                        )
                        db.add(queue_entry)
                        logger.info(f"Queued schedule {schedule.id} for channel {channel}")
                
                db.commit()
                
                # Enqueue the actual publishing task
                from app.services.job_dispatcher import JobDispatcher
                dispatcher = JobDispatcher()
                dispatcher.enqueue_publish_schedule(schedule_id=schedule.id)
                
            except Exception as e:
                logger.error(f"Failed to queue schedule {schedule.id}: {e}")
                schedule.status = ScheduleStatus.FAILED
                schedule.last_error = str(e)
                schedule.retry_count += 1
                db.commit()
    
    except Exception as e:
        logger.error(f"Publishing scheduler failed: {e}")
        raise
    finally:
        db.close()


def process_publishing_queue(schedule_id: str) -> None:
    """
    Process publishing for a specific schedule across all its target channels.
    """
    logger.info(f"Processing publishing queue for schedule {schedule_id}")
    db = next(get_db())
    
    try:
        # Get the schedule
        schedule = db.query(BlogSchedule).filter(
            BlogSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return
            
        # Get the content to publish
        content = None
        if schedule.blog_draft_id:
            content = db.query(BlogDraft).filter(
                BlogDraft.id == schedule.blog_draft_id
            ).first()
        
        if not content:
            logger.error(f"No content found for schedule {schedule_id}")
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = "No content available for publishing"
            db.commit()
            return
        
        # Get pending queue entries for this schedule
        queue_entries = db.query(PublishingQueue).filter(
            PublishingQueue.schedule_id == schedule_id,
            PublishingQueue.status == "PENDING"
        ).all()
        
        published_channels = []
        failed_channels = []
        
        for queue_entry in queue_entries:
            try:
                queue_entry.processing_started_at = datetime.now(timezone.utc)
                queue_entry.attempt_count += 1
                db.commit()
                
                logger.info(f"Publishing to {queue_entry.channel} for schedule {schedule_id}")
                
                # Get the appropriate publisher
                publisher = PublisherFactory.get_publisher(
                    channel=queue_entry.channel,
                    config=queue_entry.channel_config
                )
                
                # Prepare content for publishing
                publish_data = {
                    "title": content.title or schedule.title,
                    "content": content.html_content or "",
                    "excerpt": schedule.meta_description,
                    "tags": schedule.tags,
                    "categories": schedule.categories,
                    "slug": schedule.slug,
                    "featured_image_url": content.featured_image_url,
                    "meta_description": schedule.meta_description
                }
                
                # Publish the content
                result = publisher.publish(publish_data)
                
                # Update queue entry with success
                queue_entry.status = "COMPLETED"
                queue_entry.processing_completed_at = datetime.now(timezone.utc)
                queue_entry.published_url = result.get("url")
                queue_entry.external_id = result.get("external_id")
                
                published_channels.append(queue_entry.channel)
                
                # Update schedule published_urls
                if schedule.published_urls is None:
                    schedule.published_urls = {}
                schedule.published_urls[queue_entry.channel] = result.get("url")
                
                logger.info(f"Successfully published to {queue_entry.channel}: {result.get('url')}")
                
            except PublishingError as e:
                logger.error(f"Publishing failed for {queue_entry.channel}: {e}")
                queue_entry.status = "FAILED"
                queue_entry.last_error = str(e)
                failed_channels.append(queue_entry.channel)
                
            except Exception as e:
                logger.error(f"Unexpected error publishing to {queue_entry.channel}: {e}")
                queue_entry.status = "FAILED"
                queue_entry.last_error = f"Unexpected error: {str(e)}"
                failed_channels.append(queue_entry.channel)
            
            finally:
                queue_entry.processing_completed_at = datetime.now(timezone.utc)
                db.commit()
        
        # Update overall schedule status
        if published_channels and not failed_channels:
            # All channels published successfully
            schedule.status = ScheduleStatus.PUBLISHED
            schedule.published_at = datetime.now(timezone.utc)
            schedule.last_error = None
            logger.info(f"Schedule {schedule_id} published successfully to all channels")
            
        elif published_channels and failed_channels:
            # Partial success - some channels failed
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = f"Failed channels: {', '.join(failed_channels)}"
            schedule.retry_count += 1
            logger.warning(f"Schedule {schedule_id} partially published. Failed: {failed_channels}")
            
        else:
            # All channels failed
            schedule.status = ScheduleStatus.FAILED
            schedule.last_error = f"All channels failed: {', '.join(failed_channels)}"
            schedule.retry_count += 1
            logger.error(f"Schedule {schedule_id} failed to publish to any channel")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to process publishing queue for schedule {schedule_id}: {e}")
        # Update schedule status on unexpected error
        try:
            schedule = db.query(BlogSchedule).filter(
                BlogSchedule.id == schedule_id
            ).first()
            if schedule:
                schedule.status = ScheduleStatus.FAILED
                schedule.last_error = f"Processing error: {str(e)}"
                schedule.retry_count += 1
                db.commit()
        except:
            pass  # Don't fail on cleanup
        raise
    finally:
        db.close()


def retry_failed_publishing(schedule_id: str, max_retries: int = 3) -> None:
    """
    Retry publishing for a failed schedule.
    """
    logger.info(f"Retrying failed publishing for schedule {schedule_id}")
    db = next(get_db())
    
    try:
        schedule = db.query(BlogSchedule).filter(
            BlogSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return
            
        if schedule.retry_count >= max_retries:
            logger.error(f"Schedule {schedule_id} exceeded max retries ({max_retries})")
            return
            
        if schedule.status != ScheduleStatus.FAILED:
            logger.warning(f"Schedule {schedule_id} is not in FAILED status, current: {schedule.status}")
            return
        
        # Reset failed queue entries to PENDING for retry
        failed_queue_entries = db.query(PublishingQueue).filter(
            PublishingQueue.schedule_id == schedule_id,
            PublishingQueue.status == "FAILED"
        ).all()
        
        for entry in failed_queue_entries:
            entry.status = "PENDING"
            entry.last_error = None
            entry.processing_started_at = None
            entry.processing_completed_at = None
        
        # Reset schedule status
        schedule.status = ScheduleStatus.PUBLISHING
        schedule.last_error = None
        
        db.commit()
        
        # Re-enqueue the publishing task
        from app.services.job_dispatcher import JobDispatcher
        dispatcher = JobDispatcher()
        dispatcher.enqueue_publish_schedule(schedule_id=schedule_id)
        
        logger.info(f"Retry queued for schedule {schedule_id}")
        
    except Exception as e:
        logger.error(f"Failed to retry schedule {schedule_id}: {e}")
        raise
    finally:
        db.close()


def cleanup_old_queue_entries(days_old: int = 30) -> None:
    """
    Cleanup old completed/failed publishing queue entries.
    """
    logger.info(f"Cleaning up publishing queue entries older than {days_old} days")
    db = next(get_db())
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        # Delete completed entries older than cutoff
        deleted_count = db.query(PublishingQueue).filter(
            PublishingQueue.status.in_(["COMPLETED", "FAILED"]),
            PublishingQueue.processing_completed_at < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old publishing queue entries")
        
    except Exception as e:
        logger.error(f"Failed to cleanup publishing queue: {e}")
        raise
    finally:
        db.close()