from enum import StrEnum


class JobState(StrEnum):
    new = "NEW"
    running = "RUNNING"
    waiting_approval = "WAITING_APPROVAL"
    approved = "APPROVED"
    rejected = "REJECTED"
    published = "PUBLISHED"
    failed = "FAILED"


class BlogStage(StrEnum):
    new = "NEW"
    keyword = "KEYWORD"
    content = "CONTENT"
    draft = "DRAFT"
    published = "PUBLISHED"
    failed = "FAILED"

