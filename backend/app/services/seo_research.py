from __future__ import annotations

import base64
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


async def fetch_serp_data(keyword: str) -> dict | None:
    """
    Fetch SERP data from DataForSEO for the given keyword.
    Returns a simplified summary dict, or None if credentials are missing / call fails.
    """
    s = get_settings()
    if not s.dataforseo_login or not s.dataforseo_password:
        logger.info("DataForSEO credentials not set — skipping SERP research")
        return None

    creds = base64.b64encode(f"{s.dataforseo_login}:{s.dataforseo_password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
    }
    payload = [
        {
            "keyword": keyword,
            "location_name": "India",
            "language_name": "English",
            "depth": 10,
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_DATAFORSEO_BASE}/serp/google/organic/live/advanced",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        tasks = data.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            logger.warning("DataForSEO returned non-200 task: %s", tasks)
            return None

        results = tasks[0].get("result", [{}])[0]
        items = results.get("items", [])

        organic = [
            {
                "rank": i.get("rank_absolute"),
                "title": i.get("title"),
                "url": i.get("url"),
                "description": i.get("description"),
            }
            for i in items
            if i.get("type") == "organic"
        ][:10]

        return {
            "keyword": keyword,
            "total_results": results.get("se_results_count"),
            "organic": organic,
        }

    except Exception as exc:
        logger.warning("DataForSEO request failed for '%s': %s", keyword, exc)
        return None


def format_serp_for_prompt(serp: dict | None) -> str:
    """Convert SERP data to a prompt-friendly text block."""
    if not serp:
        return ""
    lines = [f"Top results for '{serp['keyword']}':"]
    for item in serp.get("organic", []):
        lines.append(f"#{item['rank']} {item['title']} — {item['url']}")
        if item.get("description"):
            lines.append(f"   {item['description'][:120]}")
    return "\n".join(lines)
