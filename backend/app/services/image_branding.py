"""Stamp a brand logo onto generated featured images.

The overlay is deterministic (Pillow), not generative: image models cannot
faithfully reproduce an exact logo, so the logo is composited after
generation. The branded JPEG is uploaded to S3/MinIO via the storage
service. Every step fails soft — callers fall back to the unbranded image
when this module returns None.
"""

import logging
from io import BytesIO

import httpx
from PIL import Image

from app.services.storage import upload_public_image

logger = logging.getLogger(__name__)

# Logo width as a fraction of the base image width, and the margin from the
# bottom-right corner as a fraction of the base width.
LOGO_WIDTH_RATIO = 0.18
MARGIN_RATIO = 0.04


def overlay_logo(base_bytes: bytes, logo_bytes: bytes) -> bytes:
    """Paste the logo bottom-right onto the base image; return JPEG bytes."""
    base = Image.open(BytesIO(base_bytes)).convert("RGB")
    logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")

    target_width = max(1, int(base.width * LOGO_WIDTH_RATIO))
    scale = target_width / logo.width
    target_height = max(1, int(logo.height * scale))
    logo = logo.resize((target_width, target_height), Image.LANCZOS)

    margin = int(base.width * MARGIN_RATIO)
    position = (base.width - logo.width - margin, base.height - logo.height - margin)
    base.paste(logo, position, logo)  # third arg = alpha mask

    out = BytesIO()
    base.save(out, "JPEG", quality=90)
    return out.getvalue()


async def brand_featured_image(image_url: str, logo_url: str, key: str) -> str | None:
    """Download image + logo, overlay, upload; return the hosted URL or None."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            logo_resp = await client.get(logo_url)
            logo_resp.raise_for_status()

        branded = overlay_logo(img_resp.content, logo_resp.content)
        # boto3 is sync; acceptable here — this runs inside an RQ worker task,
        # not the API event loop.
        return upload_public_image(key, branded)
    except Exception as exc:
        logger.warning("Logo branding failed (%s); falling back to unbranded image", exc)
        return None
