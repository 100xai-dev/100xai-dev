from datetime import datetime


class RecoverableError(Exception):
    pass


class UnrecoverableError(Exception):
    pass


def run_onboarding_pipeline(job_id: str) -> None:
    # The full crawl/extract/ingest pipeline is wired in the next implementation slice.
    # This placeholder gives RQ a stable import target from day one.
    raise NotImplementedError(f"onboarding pipeline not implemented for job {job_id}")


def utc_now() -> datetime:
    return datetime.utcnow()

