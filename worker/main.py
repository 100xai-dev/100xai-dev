from app.config import get_settings


def main() -> None:
    settings = get_settings()
    try:
        import redis
        from rq import Queue, Worker
        from rq.connections import Connection
    except ImportError as exc:
        raise SystemExit("Install worker dependencies from backend/requirements.txt first") from exc

    redis_conn = redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker([Queue("onboarding"), Queue("default")])
        worker.work()


if __name__ == "__main__":
    main()

