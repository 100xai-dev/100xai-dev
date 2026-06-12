"""Tests for the S3/MinIO storage helper."""

import pytest

from app.services import storage


class FakeS3Client:
    def __init__(self):
        self.put_calls = []
        self.bucket_created = False

    def head_bucket(self, Bucket):
        raise Exception("no such bucket")

    def create_bucket(self, Bucket):
        self.bucket_created = True

    def put_bucket_policy(self, Bucket, Policy):
        self.policy = Policy

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append(
            {"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType}
        )


class FakeSettings:
    s3_endpoint_url = "http://minio:9000"
    s3_access_key = "test-key"
    s3_secret_key = "test-secret"
    s3_bucket = "test-bucket"
    s3_public_url = "http://localhost:9000"


def test_upload_public_image_puts_object_and_returns_public_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeS3Client()
    monkeypatch.setattr(storage, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(storage, "_make_client", lambda settings: fake)

    url = storage.upload_public_image("branded/job1-featured.jpg", b"jpegbytes")

    assert fake.bucket_created is True
    assert len(fake.put_calls) == 1
    call = fake.put_calls[0]
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == "branded/job1-featured.jpg"
    assert call["Body"] == b"jpegbytes"
    assert call["ContentType"] == "image/jpeg"
    assert url == "http://localhost:9000/test-bucket/branded/job1-featured.jpg"


def test_upload_public_image_raises_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Unconfigured(FakeSettings):
        s3_endpoint_url = None
        s3_access_key = None
        s3_secret_key = None

    monkeypatch.setattr(storage, "get_settings", lambda: Unconfigured())

    with pytest.raises(storage.StorageNotConfigured):
        storage.upload_public_image("k.jpg", b"x")
