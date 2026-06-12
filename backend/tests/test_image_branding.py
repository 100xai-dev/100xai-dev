"""Tests for the logo-overlay image branding service."""

import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.services import image_branding


def _png_bytes(size, color) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


def test_overlay_logo_keeps_size_and_stamps_bottom_right() -> None:
    base = _png_bytes((1024, 576), (10, 10, 10, 255))      # near-black 16:9 base
    logo = _png_bytes((400, 200), (255, 0, 0, 255))        # solid red logo

    out = image_branding.overlay_logo(base, logo)

    img = Image.open(BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (1024, 576)
    # A pixel inside the bottom-right stamp area is now red-ish, not black.
    r, g, b = img.convert("RGB").getpixel((1024 - 60, 576 - 60))
    assert r > 150 and g < 100 and b < 100
    # The top-left corner is untouched.
    r2, g2, b2 = img.convert("RGB").getpixel((20, 20))
    assert r2 < 60 and g2 < 60 and b2 < 60


def test_overlay_logo_respects_transparency() -> None:
    base = _png_bytes((1000, 500), (10, 10, 10, 255))
    logo = _png_bytes((300, 150), (0, 255, 0, 0))  # fully transparent logo

    out = image_branding.overlay_logo(base, logo)

    img = Image.open(BytesIO(out)).convert("RGB")
    # Transparent logo leaves the bottom-right corner dark.
    r, g, b = img.getpixel((1000 - 50, 500 - 50))
    assert r < 60 and g < 60 and b < 60


def test_brand_featured_image_returns_none_on_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url):
            raise RuntimeError("network down")

    monkeypatch.setattr(image_branding.httpx, "AsyncClient", FailingClient)

    result = asyncio.run(image_branding.brand_featured_image(
        "https://cdn.example/img.jpg",
        "https://acme.example/logo.png",
        "branded/x.jpg",
    ))
    assert result is None


def test_brand_featured_image_overlays_and_uploads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _png_bytes((640, 360), (10, 10, 10, 255))
    logo = _png_bytes((100, 50), (255, 0, 0, 255))
    responses = {
        "https://cdn.example/img.jpg": base,
        "https://acme.example/logo.png": logo,
    }

    class FakeResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): ...

    class FakeClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResponse(responses[url])

    uploaded = {}

    def fake_upload(key, data, content_type="image/jpeg"):
        uploaded["key"] = key
        uploaded["data"] = data
        return f"http://localhost:9000/test-bucket/{key}"

    monkeypatch.setattr(image_branding.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(image_branding, "upload_public_image", fake_upload)

    result = asyncio.run(image_branding.brand_featured_image(
        "https://cdn.example/img.jpg",
        "https://acme.example/logo.png",
        "branded/job1-featured.jpg",
    ))

    assert result == "http://localhost:9000/test-bucket/branded/job1-featured.jpg"
    assert uploaded["key"] == "branded/job1-featured.jpg"
    stamped = Image.open(BytesIO(uploaded["data"])).convert("RGB")
    r, g, b = stamped.getpixel((640 - 40, 360 - 40))
    assert r > 150  # red logo landed bottom-right


def test_brand_featured_image_returns_none_on_corrupt_logo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _png_bytes((640, 360), (10, 10, 10, 255))
    responses = {
        "https://cdn.example/img.jpg": base,
        "https://acme.example/logo.svg": b"<svg>not a raster image</svg>",
    }

    class FakeResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): ...

    class FakeClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResponse(responses[url])

    monkeypatch.setattr(image_branding.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(image_branding.brand_featured_image(
        "https://cdn.example/img.jpg",
        "https://acme.example/logo.svg",
        "branded/x.jpg",
    ))
    assert result is None


def test_overlay_logo_clamps_tall_logos() -> None:
    base = _png_bytes((1024, 576), (10, 10, 10, 255))
    tall_logo = _png_bytes((10, 1000), (255, 0, 0, 255))  # extreme portrait logo

    out = image_branding.overlay_logo(base, tall_logo)

    img = Image.open(BytesIO(out)).convert("RGB")
    assert img.size == (1024, 576)
    # Logo height is clamped to 25% of base height, so the upper-middle of the
    # image must remain untouched (no full-height stripe).
    r, g, b = img.getpixel((1024 - 30, 100))
    assert r < 60 and g < 60 and b < 60
