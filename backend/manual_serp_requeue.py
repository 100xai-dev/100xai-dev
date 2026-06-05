#!/usr/bin/env python3
"""
Manual script to re-enqueue a SERP analysis job.
Usage: python manual_serp_requeue.py <job_id>
"""

import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import get_database_url
from app.models import Job, Keyword
from app.services.job_dispatcher import JobDispatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    """Create a database session."""
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def re_enqueue_serp_analysis(job_id: str):
    """Re-enqueue a SERP analysis job by job ID."""
    
    db = get_db_session()
    try:
        # Find the job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job with ID {job_id} not found")
            return False
            
        logger.info(f"Found job: {job.id}, type: {job.job_type}, status: {job.status}, brand_id: {job.brand_id}")
        
        # Verify it's a SERP analysis job
        if job.job_type != "serp_analysis":
            logger.error(f"Job {job_id} is not a SERP analysis job (type: {job.job_type})")
            return False
            
        # Get target keywords - use top keywords from the brand
        keywords = db.query(Keyword).filter(
            Keyword.brand_id == job.brand_id
        ).order_by(Keyword.score.desc().nullslast()).limit(5).all()
        
        if not keywords:
            logger.error(f"No keywords found for brand {job.brand_id}")
            return False
            
        target_keywords = [k.related_keyword for k in keywords]
        logger.info(f"Using {len(target_keywords)} keywords: {target_keywords}")
        
        # Re-enqueue the job
        dispatcher = JobDispatcher()
        try:
            dispatcher.enqueue_serp_analysis(
                job_id=job.id,
                brand_id=job.brand_id,
                target_keywords=target_keywords
            )
            
            # Update job status
            job.status = "QUEUED"
            job.stage = "KEYWORD"
            job.error_message = None
            db.commit()
            
            logger.info(f"Successfully re-enqueued SERP analysis job {job_id}")
            logger.info(f"Job status updated to: {job.status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            db.rollback()
            return False
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python manual_serp_requeue.py <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    logger.info(f"Attempting to re-enqueue SERP analysis job: {job_id}")
    
    success = re_enqueue_serp_analysis(job_id)
    if success:
        print(f"✓ Successfully re-enqueued job {job_id}")
        sys.exit(0)
    else:
        print(f"✗ Failed to re-enqueue job {job_id}")
        sys.exit(1)