from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobRead(BaseModel):
    id: str
    brand_id: str | None
    job_type: str
    status: str
    stage: str | None
    progress: dict[str, Any]
    attempt_count: int
    max_attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

