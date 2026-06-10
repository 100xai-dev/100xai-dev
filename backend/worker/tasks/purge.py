import logging

log = logging.getLogger(__name__)


def purge_brand(*, job_id: str, brand_id: str) -> None:
    """Placeholder. Real cleanup lands in a later slice."""
    log.info("[placeholder] purge job=%s brand=%s", job_id, brand_id)


def purge_expired_raw_text() -> None:
    raise NotImplementedError("raw text purge job not implemented")
