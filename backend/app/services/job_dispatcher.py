from app import queue

BLOG_QUEUE = "blog"
KEYWORD_RESEARCH_QUEUE = "keyword_research"
SERP_ANALYSIS_QUEUE = "serp_analysis"
CONTENT_GENERATION_QUEUE = "content_generation"
PUBLISHER_QUEUE = "publisher"


class JobDispatcher:
    """Thin RQ wrapper. Always called after the DB commit."""

    def enqueue_blog_brief(self, *, job_id: str) -> None:
        queue.get_queue(BLOG_QUEUE).enqueue(
            "worker.tasks.blog.run_blog_brief",
            kwargs={"job_id": job_id},
            job_id=f"brief_{job_id}",
            job_timeout=600,  # 10 minutes — covers SERP fetch + LLM brief generation
        )

    def enqueue_blog_write(self, *, job_id: str) -> None:
        queue.get_queue(BLOG_QUEUE).enqueue(
            "worker.tasks.blog.run_blog_write",
            kwargs={"job_id": job_id},
            job_id=f"write_{job_id}",
            job_timeout=900,  # 15 minutes — covers parallel section writing (3 batches × LLM)
        )

    def enqueue_onboarding(self, *, job_id: str, brand_id: str, max_retries: int = 3) -> None:
        retry = _maybe_retry(max_retries)
        queue.get_queue(queue.ONBOARDING_QUEUE).enqueue(
            "worker.tasks.onboarding.run_onboarding_pipeline",
            kwargs={"job_id": job_id, "brand_id": brand_id},
            job_id=job_id,
            retry=retry,
        )

    def enqueue_reingest(self, *, job_id: str, brand_id: str, max_retries: int = 2) -> None:
        """Re-embed an existing brand's knowledge + DNA (no re-crawl). Onboarding queue."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(queue.ONBOARDING_QUEUE).enqueue(
            "worker.tasks.onboarding.run_reingest",
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
            job_timeout=600,  # 10 minutes — covers Apify calls + AI filtering
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
            job_timeout=900,  # 15 minutes — covers SerpAPI + 3 keywords × 3 Apify crawls + AI analysis
            retry=retry,
        )

    def enqueue_content_generation(
        self,
        *,
        job_id: str,
        brand_id: str,
        keyword: str,
        serp_analysis_job_id: str | None = None,
        max_retries: int = 1
    ) -> None:
        """Enqueue Pipeline 3: Content Generation task."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(CONTENT_GENERATION_QUEUE).enqueue(
            "worker.tasks.content_generation.run_content_generation_pipeline_task",
            kwargs={
                "job_id": job_id,
            },
            job_id=f"content_gen_{job_id}",
            retry=retry,
        )

    def enqueue_publish_blog_at(self, *, schedule_id: str, run_at) -> None:
        """Schedule a blog auto-publish to fire at ``run_at`` (UTC datetime).

        Uses RQ's scheduler (worker must run with --with-scheduler). Runs on the
        BLOG_QUEUE, which the worker already listens on.
        """
        queue.get_queue(BLOG_QUEUE).enqueue_at(
            run_at,
            "worker.tasks.scheduler.publish_scheduled_blog",
            kwargs={"schedule_id": schedule_id},
            job_id=f"sched_publish_{schedule_id}",
            job_timeout=600,
        )

    def enqueue_publish_schedule(self, *, schedule_id: str, max_retries: int = 2) -> None:
        """Enqueue publishing task for a schedule."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(PUBLISHER_QUEUE).enqueue(
            "worker.tasks.scheduler.process_publishing_queue",
            kwargs={"schedule_id": schedule_id},
            job_id=f"publish_{schedule_id}",
            job_timeout=600,  # 10 minutes for publishing across channels
            retry=retry,
        )

    def enqueue_publish_approved_schedule(self, *, schedule_id: str, max_retries: int = 2) -> None:
        """Publish a reviewer-approved schedule across its target channels.

        Replaces the old time-triggered auto-publish: a schedule only reaches this
        path once a human approves the generated draft (see schedules.approve).
        """
        retry = _maybe_retry(max_retries)
        queue.get_queue(PUBLISHER_QUEUE).enqueue(
            "worker.tasks.scheduler.publish_approved_schedule",
            kwargs={"schedule_id": schedule_id},
            job_id=f"publish_approved_{schedule_id}",
            job_timeout=600,
            retry=retry,
        )

    def enqueue_retry_publishing(self, *, schedule_id: str, max_retries: int = 3) -> None:
        """Enqueue retry publishing task for a failed schedule."""
        retry = _maybe_retry(max_retries)
        queue.get_queue(PUBLISHER_QUEUE).enqueue(
            "worker.tasks.scheduler.retry_failed_publishing",
            kwargs={"schedule_id": schedule_id, "max_retries": max_retries},
            job_id=f"retry_publish_{schedule_id}",
            job_timeout=600,
            retry=retry,
        )

    def enqueue_publishing_scheduler(self) -> None:
        """Enqueue the main publishing scheduler (called by cron)."""
        queue.get_queue(PUBLISHER_QUEUE).enqueue(
            "worker.tasks.scheduler.run_publishing_scheduler",
            job_id="publishing_scheduler",
            job_timeout=300,  # 5 minutes
        )

    def enqueue_cleanup_queue(self, *, days_old: int = 30) -> None:
        """Enqueue cleanup task for old publishing queue entries."""
        queue.get_queue(PUBLISHER_QUEUE).enqueue(
            "worker.tasks.scheduler.cleanup_old_queue_entries",
            kwargs={"days_old": days_old},
            job_id="cleanup_publishing_queue",
            job_timeout=300,
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
