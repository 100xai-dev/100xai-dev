"""Worker task for brand onboarding pipeline."""

from app.db import get_db
from app.services.onboarding_pipeline import run_onboarding_pipeline_job


def run_onboarding_pipeline(*, job_id: str, brand_id: str) -> None:
    """RQ worker task for brand onboarding."""
    with next(get_db()) as db:
        run_onboarding_pipeline_job(db, job_id=job_id, brand_id=brand_id)