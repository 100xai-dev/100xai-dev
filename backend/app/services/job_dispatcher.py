from app import queue

BLOG_QUEUE = "blog"
KEYWORD_RESEARCH_QUEUE = "keyword_research"
SERP_ANALYSIS_QUEUE = "serp_analysis"


class JobDispatcher:
    """Thin RQ wrapper. Always called after the DB commit."""

    def enqueue_blog_brief(self, *, job_id: str) -> None:
        queue.get_queue(BLOG_QUEUE).enqueue(
            "worker.tasks.blog.run_blog_brief",
            kwargs={"job_id": job_id},
            job_id=f"brief_{job_id}",
        )

    def enqueue_blog_write(self, *, job_id: str) -> None:
        queue.get_queue(BLOG_QUEUE).enqueue(
            "worker.tasks.blog.run_blog_write",
            kwargs={"job_id": job_id},
            job_id=f"write_{job_id}",
        )

    def enqueue_onboarding(self, *, job_id: str, brand_id: str, max_retries: int = 3) -> None:
        retry = _maybe_retry(max_retries)
        queue.get_queue(queue.ONBOARDING_QUEUE).enqueue(
            "worker.tasks.onboarding.run_onboarding_pipeline",
            kwargs={"job_id": job_id, "brand_id": brand_id},
            job_id=job_id,
            retry=retry,
        )

    def enqueue_purge(self, *, job_id: str, brand_id: str) -> None:
        queue.get_queue(queue.PURGE_QUEUE).enqueue(
            "worker.tasks.purge.purge_brand",
            kwargs={"job_id": job_id, "brand_id": brand_id},
            job_id=job_id,
        )

    def enqueue_keyword_research(
        self, 
        *, 
        job_id: str, 
        brand_id: str, 
        primary_keyword: str,
        brand_context: str = "",
        business_description: str = "",
        max_retries: int = 2
    ) -> None:
        """Enqueue Pipeline 1: Keyword Research task."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(KEYWORD_RESEARCH_QUEUE).enqueue(
            "worker.tasks.keyword_research.run_keyword_research_pipeline",
            kwargs={
                "job_id": job_id,
                "brand_id": brand_id,
                "primary_keyword": primary_keyword,
                "brand_context": brand_context,
                "business_description": business_description,
            },
            job_id=f"keyword_research_{job_id}",
            retry=retry,
        )

    def enqueue_serp_analysis(
        self,
        *,
        job_id: str,
        brand_id: str,
        target_keywords: list[str],
        brand_profile: dict | None = None,
        max_retries: int = 2
    ) -> None:
        """Enqueue Pipeline 2: SERP Analysis task."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(SERP_ANALYSIS_QUEUE).enqueue(
            "worker.tasks.serp_analysis.run_serp_analysis_pipeline",
            kwargs={
                "job_id": job_id,
                "brand_id": brand_id,
                "target_keywords": target_keywords,
                "brand_profile": brand_profile,
            },
            job_id=f"serp_analysis_{job_id}",
            retry=retry,
        )


def _maybe_retry(max_retries: int):
    """Build an RQ Retry config if RQ is installed. Returns None for tests/local."""
    if max_retries <= 0:
        return None
    try:
        from rq import Retry

        # Exponential-ish backoff: 30s, 2m, 5m.
        intervals = [30, 120, 300][:max_retries]
        return Retry(max=max_retries, interval=intervals)
    except ImportError:
        return None
