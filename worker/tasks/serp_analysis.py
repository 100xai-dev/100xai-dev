import asyncio
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.services.seo_research import run_serp_analysis

log = logging.getLogger(__name__)


def _build_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    connect_args = (
        {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    )
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


# One engine + sessionmaker per worker process. Reusing across tasks avoids
# the per-job engine churn that prevents connection pooling.
_SESSION_FACTORY: sessionmaker[Session] | None = None


def _get_session_factory() -> sessionmaker[Session]:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = _build_session_factory()
    return _SESSION_FACTORY


def run_serp_analysis_pipeline(
    *, 
    job_id: str, 
    brand_id: str, 
    target_keywords: list[str],
    brand_profile: dict | None = None,
    db: Session | None = None
) -> dict:
    """
    RQ worker task for Pipeline 2: SERP Analysis.
    
    Args:
        job_id: The job ID from the jobs table
        brand_id: The brand ID
        target_keywords: List of keywords to analyze (from Pipeline 1)
        brand_profile: Optional brand context for analysis
        db: Optional database session (mainly for testing)
        
    Returns:
        dict with statistics about the SERP analysis process
    """
    log.info(f"Starting SERP analysis worker task for job {job_id}")
    
    if db is not None:
        # For testing or direct calls with existing session
        return asyncio.run(run_serp_analysis(
            job_id=job_id,
            brand_id=brand_id,
            target_keywords=target_keywords,
            brand_profile=brand_profile
        ))

    session: Session = _get_session_factory()()
    try:
        # Run the async SERP analysis function
        result = asyncio.run(run_serp_analysis(
            job_id=job_id,
            brand_id=brand_id,
            target_keywords=target_keywords,
            brand_profile=brand_profile
        ))
        
        log.info(f"SERP analysis completed for job {job_id}: {result.get('status')}")
        return result
        
    except Exception as exc:
        log.error(f"SERP analysis worker task failed for job {job_id}: {exc}")
        raise
    finally:
        session.close()