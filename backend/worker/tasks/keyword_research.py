"""Worker task for keyword research pipeline."""

import asyncio
from app.services.seo_research import run_keyword_research


def run_keyword_research_pipeline(
    *, 
    job_id: str, 
    brand_id: str, 
    primary_keyword: str,
    brand_context: str = "",
    business_description: str = ""
) -> dict:
    """RQ worker task for keyword research pipeline."""
    return asyncio.run(run_keyword_research(
        job_id=job_id,
        brand_id=brand_id,
        primary_keyword=primary_keyword,
        brand_context=brand_context,
        business_description=business_description
    ))