"""Canonical RQ worker launcher.

Registers every queue the application enqueues to. Historically the launcher
listened on only ``onboarding/purge/default`` while the dispatcher enqueued to
``blog/keyword_research/serp_analysis/content_generation/publisher`` as well, so
those jobs were never consumed. This launcher listens on all of them by default.

Run locally (from the ``backend/`` directory):

    PYTHONPATH=. venv/bin/python -m worker.main

Override the queue list for horizontal scaling:

    WORKER_QUEUES="content_generation,publisher" PYTHONPATH=. venv/bin/python -m worker.main
"""

import logging
import os

from app.config import get_settings

logger = logging.getLogger("worker.main")

# The complete set of queues the codebase enqueues to. Keep in sync with
# app.queue (ONBOARDING/PURGE/BLOG/KEYWORD_RESEARCH/SERP_ANALYSIS/PUBLISHER) and
# the CONTENT_GENERATION_QUEUE constant in app.services.job_dispatcher, plus RQ's
# implicit "default" queue.
ALL_QUEUES = [
    "onboarding",
    "purge",
    "default",
    "blog",
    "keyword_research",
    "serp_analysis",
    "content_generation",
    "publisher",
]


def _resolve_queue_names() -> list[str]:
    """Queues to listen on: WORKER_QUEUES override (comma-separated) or all."""
    override = os.getenv("WORKER_QUEUES", "").strip()
    if override:
        names = [q.strip() for q in override.split(",") if q.strip()]
        if names:
            return names
    return list(ALL_QUEUES)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = get_settings()

    try:
        import redis
        from rq import Queue, Worker
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SystemExit("Install worker dependencies from backend/requirements.txt first") from exc

    # Make the failure mode visible: log the queues and the resolved import path
    # of the tasks package the dispatcher's string targets must resolve against.
    import worker.tasks as tasks_pkg

    queue_names = _resolve_queue_names()
    logger.info("Worker starting; tasks package resolved to: %s", os.path.dirname(tasks_pkg.__file__))
    logger.info("Listening on queues: %s", ", ".join(queue_names))

    redis_conn = redis.from_url(settings.redis_url)
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    worker = Worker(queues, connection=redis_conn)
    # with_scheduler=True powers JobDispatcher.enqueue_publish_blog_at (enqueue_at).
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
