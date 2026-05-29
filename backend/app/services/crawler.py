from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
import trafilatura

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

KEYWORD_SCORES: dict[str, int] = {
    "about": 10,
    "team": 8,
    "company": 8,
    "services": 9,
    "products": 9,
    "solutions": 9,
    "features": 7,
    "pricing": 6,
    "contact": 5,
    "blog": 6,
    "insights": 6,
    "resources": 6,
    "articles": 6,
    "case-study": 7,
    "case-studies": 7,
    "customers": 7,
    "faq": 5,
    "careers": 2,
    "jobs": 2,
    "privacy": 0,
    "terms": 0,
    "legal": 0,
}


@dataclass
class PageExtraction:
    url: str
    raw_text: str
    normalized_text: str
    metadata: dict
    word_count: int


@dataclass
class CrawlResult:
    pages: list[PageExtraction] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)
    robots_skipped: list[str] = field(default_factory=list)
    partial_crawl: bool = False


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def _canonicalize(url: str) -> str:
    """Normalize a URL: strip trailing slash, lowercase scheme+host."""
    parsed = urlparse(url)
    normalized = parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower())
    path = normalized.path.rstrip("/") or "/"
    return normalized._replace(path=path).geturl()


def _same_domain(url: str, base: str) -> bool:
    """True if url is under the same registered domain as base."""
    try:
        base_host = urlparse(base).netloc.lower()
        url_host = urlparse(url).netloc.lower()
        # Accept www/non-www variants
        return base_host == url_host or base_host == f"www.{url_host}" or f"www.{base_host}" == url_host
    except Exception:
        return False


def _score_url(url: str) -> int:
    path = urlparse(url).path.lower()
    return sum(v for k, v in KEYWORD_SCORES.items() if k in path)


def rank_by_path_keywords(urls: list[str]) -> list[str]:
    """Return urls sorted by brand-signal value (highest first)."""
    return sorted(set(urls), key=_score_url, reverse=True)


# ---------------------------------------------------------------------------
# Sitemap discovery (no Playwright needed)
# ---------------------------------------------------------------------------

async def _fetch_sitemap_urls(seed_url: str, client: httpx.AsyncClient) -> list[str]:
    """Try to parse sitemap.xml / sitemap_index.xml / robots.txt for sitemap links."""
    base = _canonicalize(seed_url)
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        f"{root}/sitemap.xml",
        f"{root}/sitemap_index.xml",
    ]

    urls: list[str] = []
    for sitemap_url in candidates:
        try:
            resp = await client.get(sitemap_url, timeout=10)
            if resp.status_code != 200:
                continue
            content_type = resp.headers.get("content-type", "")
            if "xml" not in content_type and "text/plain" not in content_type:
                continue
            # Parse sitemap XML
            try:
                root_el = ElementTree.fromstring(resp.text)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                # Try loc tags (standard sitemap)
                locs = root_el.findall(".//sm:loc", ns) or root_el.findall(".//loc")
                urls = [loc.text.strip() for loc in locs if loc.text]
                if urls:
                    break
            except ElementTree.ParseError:
                pass
        except Exception:
            continue

    return [u for u in urls if _same_domain(u, seed_url)]


# ---------------------------------------------------------------------------
# Homepage link extraction (lightweight, no Playwright)
# ---------------------------------------------------------------------------

async def _extract_homepage_links(seed_url: str, client: httpx.AsyncClient) -> list[str]:
    try:
        resp = await client.get(seed_url, timeout=15)
        if resp.status_code != 200:
            return []
        # Simple regex link extraction — avoids bs4 import cost here
        raw_links = re.findall(r'href=["\']([^"\'#?]+)["\']', resp.text)
        resolved = []
        for link in raw_links:
            try:
                full = urljoin(seed_url, link)
                if _same_domain(full, seed_url):
                    resolved.append(_canonicalize(full))
            except Exception:
                pass
        return resolved
    except Exception:
        return []


# ---------------------------------------------------------------------------
# URL discovery algorithm (spec §8.2)
# ---------------------------------------------------------------------------

async def discover_urls(seed_url: str, max_urls: int = 12) -> list[str]:
    """
    Returns up to max_urls deduplicated URLs from the same domain.
    Steps: homepage → sitemap → homepage link fallback → blog index posts.
    """
    homepage = _canonicalize(seed_url)
    urls: list[str] = [homepage]

    async with httpx.AsyncClient(
        headers={"User-Agent": "100xAI-Crawler/1.0 (+https://100xai.example/bot)"},
        follow_redirects=True,
    ) as client:
        # Step 2: sitemap
        sitemap_urls = await _fetch_sitemap_urls(seed_url, client)
        if sitemap_urls:
            ranked = rank_by_path_keywords(sitemap_urls)
            for u in ranked:
                if u not in urls:
                    urls.append(u)
                if len(urls) >= max_urls:
                    break

        # Step 3: fallback to homepage links
        if len(urls) < max_urls:
            page_links = await _extract_homepage_links(seed_url, client)
            ranked = rank_by_path_keywords(page_links)
            for link in ranked:
                if link not in urls:
                    urls.append(link)
                if len(urls) >= max_urls:
                    break

    return urls[:max_urls]


# ---------------------------------------------------------------------------
# Per-page extraction (trafilatura; Playwright optional)
# ---------------------------------------------------------------------------

async def _fetch_with_httpx(url: str) -> str | None:
    """Lightweight fetch without Playwright. Good for static/SSR pages."""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "100xAI-Crawler/1.0 (+https://100xai.example/bot)"},
            follow_redirects=True,
            timeout=20,
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception as exc:
        logger.debug("httpx fetch failed for %s: %s", url, exc)
    return None


async def _fetch_with_playwright(url: str) -> str | None:
    """JS-rendering fallback via Playwright. Used when httpx returns thin HTML."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="100xAI-Crawler/1.0 (+https://100xai.example/bot)"
            )
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.debug("Playwright fetch failed for %s: %s", url, exc)
    return None


def _is_thin_html(html: str) -> bool:
    """True if the page is likely a JS shell with no real content."""
    text = trafilatura.extract(html, favor_recall=True)
    return not text or len(text) < 200


async def fetch_and_extract(url: str, host_delay: float = 1.0) -> PageExtraction | None:
    """
    Fetches a page and extracts structured content via trafilatura.
    Falls back to Playwright for JS-rendered pages.
    """
    await asyncio.sleep(host_delay)  # politeness
    html = await _fetch_with_httpx(url)

    if not html or _is_thin_html(html):
        logger.debug("httpx returned thin content for %s, trying Playwright", url)
        pw_html = await _fetch_with_playwright(url)
        if pw_html:
            html = pw_html

    if not html:
        return None

    main_text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    if not main_text or len(main_text) < 200:
        main_text = trafilatura.extract(html, favor_recall=True)
    if not main_text or len(main_text) < 200:
        return None

    # Build metadata via simple regex (avoids bs4 dependency in this module)
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    meta_desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not meta_desc_match:
        meta_desc_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
    meta_description = meta_desc_match.group(1).strip() if meta_desc_match else ""

    h1_matches = re.findall(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    h2_matches = re.findall(r"<h2[^>]*>([^<]+)</h2>", html, re.IGNORECASE)

    normalized = " ".join(main_text.split())
    word_count = len(normalized.split())

    metadata = {
        "title": title,
        "meta_description": meta_description,
        "h1": [h.strip() for h in h1_matches[:3]],
        "h2": [h.strip() for h in h2_matches[:10]],
        "word_count": word_count,
    }

    return PageExtraction(
        url=url,
        raw_text=main_text,
        normalized_text=normalized,
        metadata=metadata,
        word_count=word_count,
    )


# ---------------------------------------------------------------------------
# Apify Website Content Crawler
# ---------------------------------------------------------------------------

async def _crawl_with_apify(seed_url: str, max_pages: int) -> CrawlResult:
    """
    Calls Apify's Website Content Crawler actor and maps results to CrawlResult.
    Raises CrawlError if the actor run fails or returns no pages.
    """
    from apify_client import ApifyClient
    from app.config import get_settings

    api_key = get_settings().apify_api_key
    if not api_key:
        raise CrawlError("APIFY_API_KEY is not configured")

    client = ApifyClient(api_key)
    run_input = {
        "startUrls": [{"url": seed_url}],
        "crawlerType": "playwright:adaptive",
        "maxCrawlPages": max_pages,
        "outputFormats": ["markdown"],
        "removeCookieWarnings": True,
        "blockMedia": True,
    }

    logger.info("Starting Apify crawl for %s (max %d pages)", seed_url, max_pages)
    run = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.actor("apify/website-content-crawler").call(run_input=run_input),
    )

    run_status = run.status if hasattr(run, "status") else run.get("status")
    if not run or run_status != "SUCCEEDED":
        raise CrawlError(f"Apify run did not succeed: status={run_status}")

    result = CrawlResult()
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    items = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: list(client.dataset(dataset_id).iterate_items()),
    )

    for item in items:
        url = item.get("url") or item.get("loadedUrl", "")
        text = item.get("markdown") or item.get("text") or ""
        if not text or len(text.strip()) < 200:
            result.failed_urls.append(url)
            continue

        normalized = " ".join(text.split())
        word_count = len(normalized.split())
        metadata = {
            "title": item.get("metadata", {}).get("title") or item.get("title", ""),
            "meta_description": item.get("metadata", {}).get("description", ""),
            "h1": [],
            "h2": [],
            "word_count": word_count,
        }
        result.pages.append(PageExtraction(
            url=url,
            raw_text=text,
            normalized_text=normalized,
            metadata=metadata,
            word_count=word_count,
        ))
        logger.info("Apify extracted %d words from %s", word_count, url)

    if not result.pages:
        raise CrawlError(f"Apify returned no extractable pages from {seed_url}")

    logger.info("Apify crawl complete: %d pages, %d failed", len(result.pages), len(result.failed_urls))
    return result


# ---------------------------------------------------------------------------
# Full crawl orchestration (spec §8)
# ---------------------------------------------------------------------------

async def crawl_brand_website(
    seed_url: str,
    max_pages: int = 12,
    host_delay: float = 1.0,
) -> CrawlResult:
    """
    Crawls seed_url using Apify if APIFY_API_KEY is set, otherwise falls back
    to the in-house httpx + Playwright crawler.
    """
    from app.config import get_settings
    if get_settings().apify_api_key:
        return await _crawl_with_apify(seed_url, max_pages)

    # --- in-house fallback ---
    result = CrawlResult()
    urls = await discover_urls(seed_url, max_urls=max_pages)
    logger.info("Discovered %d URLs from %s (in-house crawler)", len(urls), seed_url)

    for url in urls:
        try:
            page = await fetch_and_extract(url, host_delay=host_delay)
            if page:
                result.pages.append(page)
                logger.info("Extracted %d words from %s", page.word_count, url)
            else:
                result.failed_urls.append(url)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            result.failed_urls.append(url)

    homepage = _canonicalize(seed_url)
    homepage_extracted = any(p.url == homepage or _canonicalize(p.url) == homepage for p in result.pages)
    if not result.pages:
        raise CrawlError(f"No pages successfully extracted from {seed_url}")
    if not homepage_extracted and result.pages:
        result.partial_crawl = True
        logger.warning("Homepage not extracted; proceeding with %d other pages", len(result.pages))

    return result


class CrawlError(Exception):
    """Raised when crawling fails unrecoverably."""
