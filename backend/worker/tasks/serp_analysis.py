"""Worker task for SERP analysis pipeline."""

import asyncio
from app.services.seo_research import run_serp_analysis


def run_serp_analysis_pipeline(
    *, 
    job_id: str, 
    brand_id: str, 
    target_keywords: list[str],
    brand_profile: dict | None = None
) -> dict:
    """RQ worker task for SERP analysis pipeline."""
    return asyncio.run(run_serp_analysis(
        job_id=job_id,
        brand_id=brand_id,
        target_keywords=target_keywords,
        brand_profile=brand_profile
    ))