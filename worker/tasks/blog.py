import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.services.blog_pipeline import run_blog_research_and_brief, run_blog_writing

log = logging.getLogger(__name__)

_SESSION_FACTORY: sessionmaker[Session] | None = None


def _get_session_factory() -> sessionmaker[Session]:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        settings = get_settings()
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        _SESSION_FACTORY = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _SESSION_FACTORY


def run_blog_brief(*, job_id: str) -> None:
    session: Session = _get_session_factory()()
    try:
        run_blog_research_and_brief(session, job_id=job_id)
    finally:
        session.close()


def run_blog_write(*, job_id: str) -> None:
    session: Session = _get_session_factory()()
    try:
        run_blog_writing(session, job_id=job_id)
    finally:
        session.close()
