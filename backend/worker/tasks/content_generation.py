# worker/tasks/content_generation.py
import asyncio
import logging

from app.db import get_db
from app.services.content_generation import run_content_generation_pipeline

logger = logging.getLogger(__name__)


def run_content_generation_pipeline_task(job_id: str) -> None:
    """RQ worker task for Pipeline 3 content generation"""
    logger.info(f"Starting content generation pipeline task for job {job_id}")
    
    db = next(get_db())
    try:
        asyncio.run(run_content_generation_pipeline(db, job_id))
        logger.info(f"Content generation pipeline completed for job {job_id}")
    except Exception as e:
        logger.error(f"Content generation pipeline failed for job {job_id}: {e}")
        raise
    finally:
        db.close()