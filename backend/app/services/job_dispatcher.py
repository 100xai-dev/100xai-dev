from app import queue


class JobDispatcher:
    """Thin RQ wrapper. Always called after the DB commit."""

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
