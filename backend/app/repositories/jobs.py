from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Job


class JobsRepository:
    """Tenant-scoped access to the jobs table. Does not commit."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        org_id: str,
        brand_id: str,
        job_type: str,
        input_payload: dict,
        stage: str | None = None,
    ) -> Job:
        job = Job(
            org_id=org_id,
            brand_id=brand_id,
            job_type=job_type,
            status="QUEUED",
            stage=stage,
            input_payload=input_payload,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get(self, *, job_id: str, org_id: str) -> Job | None:
        return self._session.query(Job).filter(Job.id == job_id, Job.org_id == org_id).one_or_none()

    def mark_running(self, *, job_id: str) -> None:
        job = self._session.query(Job).filter(Job.id == job_id).one()
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)

    def mark_done(self, *, job_id: str, result: dict) -> None:
        job = self._session.query(Job).filter(Job.id == job_id).one()
        job.status = "SUCCEEDED"
        job.output_payload = result
        job.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, *, job_id: str, error: str) -> None:
        job = self._session.query(Job).filter(Job.id == job_id).one()
        job.status = "FAILED"
        job.error_message = error
        job.finished_at = datetime.now(timezone.utc)

