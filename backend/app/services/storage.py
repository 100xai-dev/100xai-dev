"""Thin S3-compatible storage helper (MinIO in dev, any S3 in prod).

Used for hosting images the backend produces itself (e.g. logo-branded
featured images). Uploads are public-read: the URLs are embedded in blog
posts and fetched by external publishers (WordPress, Ghost, ...).
"""

import json
import logging

import boto3
from botocore.client import Config

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageNotConfigured(Exception):
    """Raised when S3 credentials/endpoint are missing from settings."""


def _make_client(settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _ensure_public_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }],
        }
        try:
            client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        except Exception as exc:
            logger.warning("Could not set public-read policy on %s: %s", bucket, exc)


def upload_public_image(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload image bytes and return a publicly reachable URL."""
    settings = get_settings()
    if not (settings.s3_endpoint_url and settings.s3_access_key and settings.s3_secret_key):
        raise StorageNotConfigured("S3_ENDPOINT_URL / S3_ACCESS_KEY / S3_SECRET_KEY not set")

    client = _make_client(settings)
    _ensure_public_bucket(client, settings.s3_bucket)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    base = (settings.s3_public_url or settings.s3_endpoint_url).rstrip("/")
    return f"{base}/{settings.s3_bucket}/{key}"
