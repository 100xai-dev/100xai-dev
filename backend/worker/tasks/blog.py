"""Worker tasks for the blog pipeline (Pipeline 3)."""

import logging

from app.db import get_db
from app.services.blog_pipeline import run_blog_research_and_brief, run_blog_writing

logger = logging.getLogger(__name__)


def run_blog_brief(*, job_id: str) -> None:
    """RQ worker task: Stage 1+2 — SERP research + brief generation."""
    logger.info("Starting blog brief task for job %s", job_id)
    db = next(get_db())
    try:
        run_blog_research_and_brief(db, job_id=job_id)
        logger.info("Blog brief task completed for job %s", job_id)
    except Exception as e:
        logger.error("Blog brief task failed for job %s: %s", job_id, e)
        raise
    finally:
        db.close()


def run_blog_write(*, job_id: str) -> None:
    """RQ worker task: Stage 3 — section writing after brief approval."""
    logger.info("Starting blog write task for job %s", job_id)
    db = next(get_db())
    try:
        run_blog_writing(db, job_id=job_id)
        logger.info("Blog write task completed for job %s", job_id)
    except Exception as e:
        logger.error("Blog write task failed for job %s: %s", job_id, e)
        raise
    finally:
        db.close()
