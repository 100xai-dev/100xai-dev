from functools import lru_cache
from typing import Any

from app.config import get_settings

ONBOARDING_QUEUE = "onboarding"
PURGE_QUEUE = "purge"
BLOG_QUEUE = "blog"
KEYWORD_RESEARCH_QUEUE = "keyword_research"
SERP_ANALYSIS_QUEUE = "serp_analysis"
PUBLISHER_QUEUE = "publisher"


@lru_cache(maxsize=1)
def get_redis() -> Any:
    from redis import Redis

    return Redis.from_url(get_settings().redis_url)


@lru_cache(maxsize=8)
def get_queue(name: str) -> Any:
    from rq import Queue

    # Set a default job timeout of 20 minutes (1200 seconds)
    # Individual jobs can override this with their own timeout
    return Queue(name=name, connection=get_redis(), default_timeout=1200)

