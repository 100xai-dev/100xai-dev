import asyncio
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.services.seo_research import run_keyword_research

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


def run_keyword_research_pipeline(
    *, job_id: str, brand_id: str, primary_keyword: str, 
    brand_context: str = "", business_description: str = "",
    db: Session | None = None
) -> dict:
    """
    RQ worker task for Pipeline 1: Keyword Research.
    
    Args:
        job_id: The job ID from the jobs table
        brand_id: The brand ID
        primary_keyword: The seed keyword to research
        brand_context: Brand DNA context for AI filtering
        business_description: Business description for relevance filtering
        db: Optional database session (mainly for testing)
        
    Returns:
        dict with statistics about the keyword research process
    """
    log.info(f"Starting keyword research worker task for job {job_id}")
    
    if db is not None:
        # For testing or direct calls with existing session
        return asyncio.run(run_keyword_research(
            job_id=job_id,
            brand_id=brand_id,
            primary_keyword=primary_keyword,
            brand_context=brand_context,
            business_description=business_description
        ))

    session: Session = _get_session_factory()()
    try:
        # Run the async keyword research function
        result = asyncio.run(run_keyword_research(
            job_id=job_id,
            brand_id=brand_id,
            primary_keyword=primary_keyword,
            brand_context=brand_context,
            business_description=business_description
        ))
        
        log.info(f"Keyword research completed for job {job_id}: {result.get('status')}")
        return result
        
    except Exception as exc:
        log.error(f"Keyword research worker task failed for job {job_id}: {exc}")
        raise
    finally:
        session.close()