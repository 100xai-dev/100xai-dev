"""Worker task for brand onboarding pipeline."""

from app.db import get_db
from app.services.onboarding_pipeline import run_onboarding_pipeline_job, run_reingest_job


def run_onboarding_pipeline(*, job_id: str, brand_id: str) -> None:
    """RQ worker task for brand onboarding."""
    with next(get_db()) as db:
        run_onboarding_pipeline_job(db, job_id=job_id, brand_id=brand_id)


def run_reingest(*, job_id: str, brand_id: str) -> None:
    """RQ worker task: re-embed an existing brand's knowledge + DNA into Pinecone."""
    with next(get_db()) as db:
        run_reingest_job(db, job_id=job_id, brand_id=brand_id)