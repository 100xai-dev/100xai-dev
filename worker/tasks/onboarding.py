import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.services.onboarding_pipeline import run_onboarding_pipeline_job

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


def run_onboarding_pipeline(*, job_id: str, brand_id: str, db: Session | None = None) -> None:
    if db is not None:
        run_onboarding_pipeline_job(db, job_id=job_id, brand_id=brand_id)
        return

    session: Session = _get_session_factory()()
    try:
        run_onboarding_pipeline_job(session, job_id=job_id, brand_id=brand_id)
    finally:
        session.close()
