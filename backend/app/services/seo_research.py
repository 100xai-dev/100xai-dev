from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx
from serpapi import GoogleSearch
from sqlalchemy import text

from app.config import get_settings

logger = logging.getLogger(__name__)

_DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


@dataclass
class KeywordSeed:
    """Keyword seed for DataForSEO API calls."""
    keyword: str
    location_name: str = "India"
    language_name: str = "English"


async def fetch_serp_data(keyword: str) -> dict | None:
    """
    Fetch SERP data from DataForSEO for the given keyword.
    Returns a simplified summary dict, or None if credentials are missing / call fails.
    """
    s = get_settings()
    
    # Check for API key first, then fall back to login/password
    headers = {"Content-Type": "application/json"}
    
    if s.dataforseo_api_key:
        # DataForSEO API key - if already base64 encoded, use directly
        try:
            # Check if it's already base64 encoded by trying to decode
            try:
                decoded_test = base64.b64decode(s.dataforseo_api_key).decode()
                if ':' in decoded_test:
                    # Already base64 encoded login:password format
                    headers["Authorization"] = f"Basic {s.dataforseo_api_key}"
                    logger.info("Using DataForSEO API key (pre-encoded base64 format)")
                else:
                    # Not in login:password format, encode as username with empty password
                    creds = base64.b64encode(f"{s.dataforseo_api_key}:".encode()).decode()
                    headers["Authorization"] = f"Basic {creds}"
                    logger.info("Using DataForSEO API key (username format with empty password)")
            except:
                # Not base64 encoded, check if it's login:password format
                if ':' in s.dataforseo_api_key:
                    # Format: "login:password" - encode it
                    creds = base64.b64encode(s.dataforseo_api_key.encode()).decode()
                    headers["Authorization"] = f"Basic {creds}"
                    logger.info("Using DataForSEO API key (raw login:password format)")
                else:
                    # Raw username - encode with empty password
                    creds = base64.b64encode(f"{s.dataforseo_api_key}:".encode()).decode()
                    headers["Authorization"] = f"Basic {creds}"
                    logger.info("Using DataForSEO API key (raw username format)")
        except Exception as e:
            logger.error(f"Failed to process DataForSEO API key: {e}")
            return None
    elif s.dataforseo_login and s.dataforseo_password:
        # Use Basic Auth (login/password)
        creds = base64.b64encode(f"{s.dataforseo_login}:{s.dataforseo_password}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
        logger.info("Using DataForSEO login/password authentication")
    else:
        logger.info("DataForSEO credentials not set — skipping SERP research")
        return None
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


# ---------------------------------------------------------------------------
# Pipeline 1: Keyword Research - DataForSEO API Methods
# ---------------------------------------------------------------------------

async def _make_dataforseo_request(endpoint: str, payload: list[dict]) -> dict | None:
    """Make authenticated request to DataForSEO API."""
    s = get_settings()
    
    # Check for API key first, then fall back to login/password
    if s.dataforseo_api_key:
        # DataForSEO API key - if already base64 encoded, use directly
        try:
            # Check if it's already base64 encoded by trying to decode
            try:
                decoded_test = base64.b64decode(s.dataforseo_api_key).decode()
                if ':' in decoded_test:
                    # Already base64 encoded login:password format
                    creds = s.dataforseo_api_key
                    logger.info("Using DataForSEO API key (pre-encoded base64 format)")
                else:
                    # Not in login:password format, encode as username with empty password
                    creds = base64.b64encode(f"{s.dataforseo_api_key}:".encode()).decode()
                    logger.info("Using DataForSEO API key (username format with empty password)")
            except:
                # Not base64 encoded, check if it's login:password format
                if ':' in s.dataforseo_api_key:
                    # Format: "login:password" - encode it
                    creds = base64.b64encode(s.dataforseo_api_key.encode()).decode()
                    logger.info("Using DataForSEO API key (raw login:password format)")
                else:
                    # Raw username - encode with empty password
                    creds = base64.b64encode(f"{s.dataforseo_api_key}:".encode()).decode()
                    logger.info("Using DataForSEO API key (raw username format)")
        except Exception as e:
            logger.error(f"Failed to process DataForSEO API key: {e}")
            return None
    elif s.dataforseo_login and s.dataforseo_password:
        creds = base64.b64encode(f"{s.dataforseo_login}:{s.dataforseo_password}".encode()).decode()
        logger.info("Using DataForSEO login/password authentication")
    else:
        logger.warning("DataForSEO credentials not set")
        return None
    headers = {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{_DATAFORSEO_BASE}{endpoint}", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        tasks = data.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            logger.warning("DataForSEO API error: %s", tasks)
            return None

        return data
    except Exception as exc:
        logger.warning("DataForSEO request failed for %s: %s", endpoint, exc)
        return None


async def fetch_related_keywords(seed: KeywordSeed, depth: int = 3, limit: int = 100) -> list[dict]:
    """Fetch related keywords from DataForSEO Labs."""
    payload = [{
        "keyword": seed.keyword,
        "location_name": seed.location_name,
        "language_name": seed.language_name,
        "depth": depth,
        "limit": limit,
        "include_serp_info": True,
    }]

    data = await _make_dataforseo_request("/dataforseo_labs/google/related_keywords/live", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


async def fetch_keyword_suggestions(seed: KeywordSeed, limit: int = 100) -> list[dict]:
    """Fetch keyword suggestions from DataForSEO Labs."""
    payload = [{
        "keyword": seed.keyword,
        "location_name": seed.location_name,
        "language_name": seed.language_name,
        "limit": limit,
        "include_serp_info": True,
    }]

    data = await _make_dataforseo_request("/dataforseo_labs/google/keyword_suggestions/live", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


async def fetch_keyword_ideas(seed: KeywordSeed, limit: int = 100) -> list[dict]:
    """Fetch keyword ideas from DataForSEO Labs."""
    payload = [{
        "keyword": seed.keyword,
        "location_name": seed.location_name,
        "language_name": seed.language_name,
        "limit": limit,
        "include_serp_info": True,
    }]

    data = await _make_dataforseo_request("/dataforseo_labs/google/keyword_ideas/live", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


async def fetch_autocomplete_keywords(seed: KeywordSeed) -> list[dict]:
    """Fetch autocomplete suggestions from DataForSEO."""
    payload = [{
        "keyword": seed.keyword,
        "location_name": seed.location_name,
        "language_name": seed.language_name,
    }]

    data = await _make_dataforseo_request("/serp/google/autocomplete/live/advanced", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


async def fetch_sub_topics(keyword: str) -> list[str]:
    """Fetch sub-topics for a keyword using related domains/categories."""
    # For simplicity, we'll generate logical sub-topics based on the keyword
    # In a full implementation, you might use DataForSEO's domain/category APIs
    base_topics = [
        f"{keyword} tips",
        f"{keyword} guide", 
        f"{keyword} tutorial",
        f"how to {keyword}",
        f"{keyword} best practices",
        f"{keyword} for beginners",
    ]
    return base_topics


async def fetch_bulk_keyword_difficulty(keywords: list[str], location_name: str, language_name: str) -> list[dict]:
    """Fetch keyword difficulty for multiple keywords."""
    if not keywords:
        return []

    payload = [{
        "keywords": keywords[:1000],  # API limit
        "location_name": location_name,
        "language_name": language_name,
    }]

    data = await _make_dataforseo_request("/dataforseo_labs/google/bulk_keyword_difficulty/live", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


async def fetch_search_volume(keywords: list[str], location_name: str, language_name: str) -> list[dict]:
    """Fetch search volume and CPC data for multiple keywords."""
    if not keywords:
        return []

    payload = [{
        "keywords": keywords[:1000],  # API limit
        "location_name": location_name,
        "language_name": language_name,
    }]

    data = await _make_dataforseo_request("/keywords_data/google/search_volume/live", payload)
    if not data:
        return []

    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    return result.get("items", [])


# ---------------------------------------------------------------------------
# Pipeline 1: Apify Google Search Scraper Integration
# ---------------------------------------------------------------------------

async def fetch_serp_keyword_suggestions(seed: KeywordSeed, limit: int = 50) -> list[dict]:
    """
    Fetch related keyword suggestions via SerpAPI related searches + People Also Ask.
    Replaces the former Apify google-search-scraper call.
    """
    raw = await serpapi_fetch_related_keywords(seed, limit=limit)
    suggestions = []
    for item in raw:
        kw = item.get("keyword", "")
        if kw and kw.lower() != seed.keyword.lower():
            suggestions.append({"keyword": kw.strip(), "source": "serp_related"})
    logger.info("SerpAPI returned %d keyword suggestions for '%s'", len(suggestions), seed.keyword)
    return suggestions


async def fetch_serp_autocomplete_suggestions(seed: KeywordSeed) -> list[dict]:
    """
    Fetch autocomplete suggestions via SerpAPI.
    Replaces the former Apify google-search-scraper autocomplete call.
    """
    raw = await serpapi_fetch_autocomplete_keywords(seed)
    suggestions = []
    for item in raw:
        value = item.get("value", "") if isinstance(item, dict) else str(item)
        if value and value.lower() != seed.keyword.lower():
            suggestions.append({"keyword": value.strip(), "source": "serp_autocomplete"})
    logger.info("SerpAPI autocomplete returned %d suggestions for '%s'", len(suggestions), seed.keyword)
    return suggestions


# ---------------------------------------------------------------------------
# Pipeline 1: Utility Functions
# ---------------------------------------------------------------------------

def normalize_all(keywords: list[dict], primary_keyword: str, source_type: str) -> list[dict]:
    """Normalize keyword data from different DataForSEO API responses."""
    normalized = []
    
    for item in keywords:
        # Extract keyword text from different API response formats
        keyword_text = (
            item.get("keyword") or
            item.get("keyword_data", {}).get("keyword") or
            item.get("suggestion") or
            item.get("value") or
            ""
        ).strip().lower()
        
        if not keyword_text:
            continue
            
        # Extract metrics from different response formats
        search_volume = None
        difficulty = None
        cpc = None
        competition = None
        
        # Try to get search volume
        if "search_volume" in item:
            search_volume = item["search_volume"]
        elif "keyword_info" in item and "search_volume" in item["keyword_info"]:
            search_volume = item["keyword_info"]["search_volume"]
        elif "monthly_searches" in item:
            search_volume = item["monthly_searches"][0].get("search_volume") if item["monthly_searches"] else None
            
        # Try to get difficulty
        if "keyword_difficulty" in item:
            difficulty = item["keyword_difficulty"]
        elif "keyword_info" in item and "keyword_difficulty" in item["keyword_info"]:
            difficulty = item["keyword_info"]["keyword_difficulty"]
            
        # Try to get CPC
        if "cpc" in item:
            cpc = item["cpc"]
        elif "keyword_info" in item and "cpc" in item["keyword_info"]:
            cpc = item["keyword_info"]["cpc"]
            
        # Try to get competition
        if "competition" in item:
            competition = item["competition"]
        elif "keyword_info" in item and "competition" in item["keyword_info"]:
            competition = item["keyword_info"]["competition"]
        
        normalized.append({
            "related_keyword": keyword_text,
            "primary_keyword": primary_keyword.lower().strip(),
            "source_type": source_type,
            "search_volume": search_volume,
            "keyword_difficulty": difficulty,
            "cpc": cpc,
            "competition": competition,
        })
    
    return normalized


# ---------------------------------------------------------------------------
# SerpApi Integration - Modern Alternative to DataForSEO
# ---------------------------------------------------------------------------

def _make_serpapi_request(params: dict) -> dict | None:
    """Make a request to SerpApi with error handling."""
    settings = get_settings()
    
    if not settings.serpapi_api_key:
        logger.warning("SerpApi API key not set - skipping request")
        return None
    
    try:
        params['api_key'] = settings.serpapi_api_key
        search = GoogleSearch(params)
        result = search.get_dict()
        
        if "error" in result:
            logger.error(f"SerpApi error: {result['error']}")
            return None
            
        return result
    except Exception as e:
        logger.error(f"SerpApi request failed: {e}")
        return None


async def serpapi_fetch_serp_data(keyword: str, location: str = "India", device: str = "mobile") -> dict | None:
    """
    Fetch SERP data using SerpApi (replacement for DataForSEO fetch_serp_data).
    
    Args:
        keyword: Search keyword
        location: Search location 
        device: Device type (mobile/desktop)
        
    Returns:
        dict: Standardized SERP data matching DataForSEO format
    """
    params = {
        "engine": "google",
        "q": keyword,
        "location": location,
        "google_domain": "google.com",
        "gl": "in" if location == "India" else "us",
        "hl": "en",
        "device": device,
        "num": 10
    }
    
    data = _make_serpapi_request(params)
    if not data:
        return None
        
    organic_results = data.get("organic_results", [])
    
    # Convert to DataForSEO-compatible format
    organic = []
    for i, result in enumerate(organic_results):
        organic.append({
            "rank": i + 1,
            "title": result.get("title", ""),
            "url": result.get("link", ""),
            "description": result.get("snippet", "")
        })
    
    return {
        "keyword": keyword,
        "total_results": data.get("search_information", {}).get("total_results", 0),
        "organic": organic
    }


async def serpapi_fetch_serp_for_analysis(keyword: str, location_name: str = "India", language_name: str = "English", device: str = "mobile") -> dict | None:
    """
    Fetch detailed SERP data for competitor analysis using SerpApi.
    
    Args:
        keyword: Search keyword
        location_name: Search location
        language_name: Search language
        device: Device type
        
    Returns:
        dict: Detailed SERP data for analysis
    """
    params = {
        "engine": "google",
        "q": keyword,
        "location": location_name,
        "google_domain": "google.com",
        "gl": "in" if location_name == "India" else "us", 
        "hl": "en",
        "device": device,
        "num": 10
    }
    
    data = _make_serpapi_request(params)
    if not data:
        return None
        
    organic_results = data.get("organic_results", [])
    
    # Convert to DataForSEO-compatible format
    organic = []
    for i, result in enumerate(organic_results):
        # Extract domain from URL
        url = result.get("link", "")
        domain = ""
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
            except:
                pass
        
        organic.append({
            "rank_absolute": i + 1,
            "title": result.get("title", ""),
            "url": url,
            "description": result.get("snippet", ""),
            "domain": domain,
            "breadcrumb": result.get("displayed_link", "")
        })
    
    return {
        "keyword": keyword,
        "location": location_name,
        "language": language_name, 
        "device": device,
        "total_results": data.get("search_information", {}).get("total_results", 0),
        "organic": organic,
        "raw_serp_data": data
    }


async def serpapi_fetch_autocomplete_keywords(seed: KeywordSeed) -> list[dict]:
    """
    Fetch autocomplete suggestions using SerpApi.
    
    Args:
        seed: Keyword seed with search parameters
        
    Returns:
        list: Autocomplete suggestions
    """
    params = {
        "engine": "google_autocomplete",
        "q": seed.keyword,
        "gl": "in" if seed.location_name == "India" else "us",
        "hl": "en"
    }
    
    data = _make_serpapi_request(params)
    if not data:
        return []
        
    suggestions = data.get("suggestions", [])
    
    # Convert to consistent format
    result = []
    for suggestion in suggestions:
        if isinstance(suggestion, dict):
            value = suggestion.get("value", suggestion.get("title", ""))
        else:
            value = str(suggestion)
            
        if value and value.lower() != seed.keyword.lower():
            result.append({"value": value})
    
    return result


async def serpapi_fetch_related_keywords(seed: KeywordSeed, depth: int = 5, limit: int = 50) -> list[dict]:
    """
    Fetch related keywords using SerpApi related searches.
    
    Args:
        seed: Keyword seed
        depth: Search depth (not used in SerpApi)
        limit: Maximum results to return
        
    Returns:
        list: Related keywords with basic metrics
    """
    params = {
        "engine": "google", 
        "q": seed.keyword,
        "location": seed.location_name,
        "gl": "in" if seed.location_name == "India" else "us",
        "hl": "en",
        "num": 10
    }
    
    data = _make_serpapi_request(params)
    if not data:
        return []
    
    related_searches = data.get("related_searches", [])
    
    # Convert to DataForSEO-compatible format
    result = []
    for search in related_searches[:limit]:
        if isinstance(search, dict):
            query = search.get("query", search.get("title", ""))
        else:
            query = str(search)
            
        if query and query.lower() != seed.keyword.lower():
            # Estimate search volume based on keyword characteristics
            estimated_volume = _estimate_search_volume(query)
            estimated_difficulty = _estimate_keyword_difficulty(query)
            estimated_cpc = _estimate_cpc(query)
            estimated_competition = _estimate_competition(query)
            
            result.append({
                "keyword": query,
                "search_volume": estimated_volume,
                "keyword_difficulty": estimated_difficulty,
                "cpc": estimated_cpc,
                "competition": estimated_competition
            })
    
    return result


def _estimate_search_volume(keyword: str) -> int:
    """
    Estimate search volume based on keyword characteristics.
    This provides realistic estimates for development/testing purposes.
    """
    import hashlib
    import random
    
    # Use keyword hash for consistent estimates
    hash_obj = hashlib.md5(keyword.lower().encode())
    random.seed(int(hash_obj.hexdigest()[:8], 16))
    
    # Base volume based on keyword length (shorter = more popular)
    word_count = len(keyword.split())
    if word_count == 1:
        base_volume = random.randint(5000, 50000)  # Single words: high volume
    elif word_count == 2:
        base_volume = random.randint(1000, 15000)  # Two words: medium volume  
    elif word_count == 3:
        base_volume = random.randint(500, 5000)    # Three words: lower volume
    else:
        base_volume = random.randint(100, 2000)    # Long tail: very specific
    
    # Adjust for common terms
    high_volume_terms = ['ai', 'artificial intelligence', 'marketing', 'digital', 'tips', 'guide', 'how to']
    if any(term in keyword.lower() for term in high_volume_terms):
        base_volume = int(base_volume * 1.5)
    
    return base_volume


def _estimate_keyword_difficulty(keyword: str) -> int:
    """Estimate keyword difficulty (0-100)."""
    import hashlib
    import random
    
    hash_obj = hashlib.md5(keyword.lower().encode())
    random.seed(int(hash_obj.hexdigest()[8:16], 16))
    
    word_count = len(keyword.split())
    if word_count == 1:
        return random.randint(70, 95)  # Single words: very competitive
    elif word_count == 2:
        return random.randint(40, 75)  # Two words: competitive
    elif word_count == 3:
        return random.randint(25, 55)  # Three words: moderate
    else:
        return random.randint(10, 35)  # Long tail: easier


def _estimate_cpc(keyword: str) -> float:
    """Estimate cost-per-click in USD."""
    import hashlib
    import random
    
    hash_obj = hashlib.md5(keyword.lower().encode())
    random.seed(int(hash_obj.hexdigest()[16:24], 16))
    
    # Business terms have higher CPC
    business_terms = ['marketing', 'business', 'software', 'service', 'tool', 'solution']
    if any(term in keyword.lower() for term in business_terms):
        return round(random.uniform(1.50, 8.00), 2)
    else:
        return round(random.uniform(0.25, 3.00), 2)


def _estimate_competition(keyword: str) -> float:
    """Estimate competition level (0.0-1.0)."""
    import hashlib
    import random
    
    hash_obj = hashlib.md5(keyword.lower().encode())
    random.seed(int(hash_obj.hexdigest()[24:32], 16))
    
    word_count = len(keyword.split())
    if word_count == 1:
        return round(random.uniform(0.7, 1.0), 2)  # High competition
    elif word_count == 2:
        return round(random.uniform(0.4, 0.8), 2)  # Medium competition
    else:
        return round(random.uniform(0.1, 0.5), 2)  # Lower competition


def dedupe_by(keywords: list[dict], key: str = "related_keyword") -> list[dict]:
    """Remove duplicates from keyword list by specified key."""
    seen = set()
    deduped = []
    
    for keyword in keywords:
        identifier = keyword.get(key)
        if identifier and identifier not in seen:
            seen.add(identifier)
            deduped.append(keyword)
    
    return deduped


def score_keywords(keywords: list[dict]) -> list[dict]:
    """Calculate composite score for keywords (40% volume, 40% inverse difficulty, 20% CPC)."""
    # Find max values for normalization (avoid division by zero)
    max_volume = max((k.get("search_volume") or 0 for k in keywords), default=1)
    max_cpc = max((k.get("cpc") or 0 for k in keywords), default=1)
    
    for keyword in keywords:
        volume = keyword.get("search_volume") or 0
        difficulty = keyword.get("keyword_difficulty") or 50  # Default medium difficulty
        cpc = keyword.get("cpc") or 0
        
        # Normalize metrics (0-1 scale)
        volume_score = volume / max_volume if max_volume > 0 else 0
        difficulty_score = max(0, (100 - difficulty) / 100)  # Inverse difficulty (easier = better)
        cpc_score = cpc / max_cpc if max_cpc > 0 else 0
        
        # Weighted composite score
        score = (volume_score * 0.4) + (difficulty_score * 0.4) + (cpc_score * 0.2)
        keyword["score"] = round(score, 4)
    
    return keywords


def safe_json_parse(json_str: str) -> dict | list | None:
    """Safely parse JSON string, handling markdown code blocks. Return None on failure."""
    try:
        import json
        import re
        
        # Strip whitespace
        cleaned = json_str.strip()
        
        # Remove markdown code blocks if present
        # Handle patterns like: ```json\n{...}\n``` or ```\n{...}\n```
        code_block_pattern = r'```(?:json)?\s*(.*?)\s*```'
        match = re.search(code_block_pattern, cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        
        # Try to parse the JSON
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Pipeline 1: AI Filtering
# ---------------------------------------------------------------------------

async def filter_keywords_for_relevance(keywords: list[dict], allowed_topics: list[str]) -> list[dict]:
    """Use AI to filter keywords to only those matching the client's allowed_topics list (AI #1)."""
    if not keywords:
        return []
    if not allowed_topics:
        logger.warning("No allowed_topics provided, skipping AI keyword filter")
        return keywords

    from app.services.llm import LLMService

    keyword_batch = keywords[:100]
    keyword_strings = [k["related_keyword"] for k in keyword_batch]
    keyword_list = "\n".join(keyword_strings)
    topics_block = "\n".join(f"- {t}" for t in allowed_topics)

    prompt = f"""I'm doing SEO keyword research. From the following keyword list, remove any keyword that is NOT relevant to these topics:
{topics_block}

Remove anything unrelated (generic lifestyle, unrelated industries, irrelevant consumer topics).

Keywords to filter:
{keyword_list}

Return ONLY the remaining keywords as a JSON array. Keep wording and casing EXACTLY as provided. Do not add, rewrite, or translate keywords.
["keyword1", "keyword2", ...]"""

    try:
        llm = LLMService()
        response = await llm.call("anthropic/claude-haiku-4-5-20251001", prompt)
        kept = safe_json_parse(response.strip())
        if not isinstance(kept, list):
            logger.warning("AI keyword filter returned invalid format, skipping filter")
            return keywords
        kept_set = {kw.strip().lower() for kw in kept}
        filtered = [k for k in keyword_batch if k["related_keyword"].strip().lower() in kept_set]
        logger.info(f"AI keyword filter: {len(keyword_batch)} → {len(filtered)} kept")
        return filtered
    except Exception as exc:
        logger.warning(f"AI keyword filtering failed: {exc}")
        return keywords


async def select_primary_target_keyword(
    primary_keyword: str,
    scored_keywords: list[dict],
    candidate_limit: int = 15,
) -> str:
    """AI selection layer (AI #2): pick the single best target keyword.

    From the score-sorted candidates, choose the one that best balances relevance to the
    user's seed keyword against search traffic (balanced trade-off): stay on the user's
    intent, allowing modest broadening only when the traffic gain is large and the topic
    is still clearly relevant. Falls back to the highest-scoring keyword when the LLM is
    unavailable or returns something not in the candidate set.
    """
    if not scored_keywords:
        return primary_keyword

    # Caller has already sorted by composite score; cap to keep the prompt small.
    candidates = scored_keywords[:candidate_limit]
    valid = {k["related_keyword"].strip().lower() for k in candidates}
    fallback = candidates[0]["related_keyword"]

    from app.services.llm import LLMService

    lines = []
    for k in candidates:
        vol = k.get("search_volume")
        diff = k.get("keyword_difficulty")
        lines.append(
            f'- "{k["related_keyword"]}" '
            f'(monthly searches: {vol if vol is not None else "unknown"}, '
            f'difficulty: {diff if diff is not None else "unknown"})'
        )
    candidate_block = "\n".join(lines)

    prompt = f"""You are choosing the single best blog target keyword for an SEO content pipeline.

The user's seed keyword (their actual intent) is:
"{primary_keyword}"

Candidate keywords with monthly search volume and difficulty:
{candidate_block}

Pick the ONE keyword that best balances:
1. Relevance — it must stay clearly on the user's seed intent; do not drift to a different topic.
2. Traffic — prefer higher monthly search volume (and lower difficulty as a tiebreaker).

Allow modest broadening (e.g. dropping a narrow qualifier) ONLY when the traffic gain is large AND the topic is still clearly what the user asked about. When in doubt, stay closer to the seed.

Return ONLY a JSON object, no prose:
{{"keyword": "<exact keyword copied from the candidate list>", "reason": "<one short sentence>"}}"""

    try:
        llm = LLMService()
        response = await llm.call("anthropic/claude-haiku-4-5-20251001", prompt)
        parsed = safe_json_parse(response.strip())
        if isinstance(parsed, dict):
            chosen = str(parsed.get("keyword", "")).strip()
            if chosen.lower() in valid:
                logger.info(
                    f"AI keyword selection: '{primary_keyword}' → '{chosen}' "
                    f"({parsed.get('reason', '')})"
                )
                return chosen
        logger.warning("AI keyword selection returned an unusable result; using top score")
    except Exception as exc:
        logger.warning(f"AI keyword selection failed: {exc}")
    return fallback


def _trigger_content_generation_directly(db, parent_job, keyword: str, parent_payload: dict) -> None:
    """Create + enqueue a Pipeline 3 content job directly, bypassing SERP analysis.

    Fallback for when keyword research returns too few keywords for a meaningful SERP
    step (P2 needs >= 3) but a draft is still expected (blog-originated jobs). The new
    content job's id is recorded on ``parent_job.output_payload.auto_triggered_content_job``
    so the blogs status sync can track P3 progress/failure, and ``blog_job_id`` is
    propagated so the draft links back to the originating BlogJob.
    """
    from app.services.job_dispatcher import JobDispatcher
    from app.models.base import uuid_str
    from app.models.onboarding import Job, BrandProfile
    from app.services.content_generation import JOB_STAGE_CONTENT

    if not db.query(BrandProfile).filter(BrandProfile.brand_id == parent_job.brand_id).first():
        logger.warning(f"Brand profile missing for {parent_job.brand_id}; skipping content trigger")
        return

    content_payload = {
        "keyword": keyword,
        "auto_triggered": True,
        "skipped_serp": True,
        "created_by": parent_payload.get("created_by", "system"),
        "blog_job_id": parent_payload.get("blog_job_id"),
        "blog_integration": True,
    }
    content_job = Job(
        id=uuid_str(),
        org_id=parent_job.org_id,
        brand_id=parent_job.brand_id,
        job_type="content_generation",
        stage=JOB_STAGE_CONTENT,
        status="QUEUED",
        input_payload=content_payload,
    )
    db.add(content_job)
    parent_job.output_payload = dict(
        parent_job.output_payload or {}, auto_triggered_content_job=content_job.id
    )
    db.commit()

    JobDispatcher().enqueue_content_generation(
        job_id=content_job.id,
        brand_id=parent_job.brand_id,
        keyword=keyword,
    )


# ---------------------------------------------------------------------------
# Pipeline 1: Main Keyword Research Function
# ---------------------------------------------------------------------------

async def run_keyword_research(job_id: str, brand_id: str, primary_keyword: str, brand_context: str = "", business_description: str = "") -> dict:
    """
    Main Pipeline 1 function: Research keywords for a given brand and primary keyword.

    Args:
        job_id: The job ID from the jobs table
        brand_id: The brand ID
        primary_keyword: The seed keyword to research
        brand_context: Unused (kept for backwards-compat). allowed_topics loaded from BrandProfile.
        business_description: Unused (kept for backwards-compat).

    Returns:
        dict with statistics about the keyword research process
    """
    from sqlalchemy.orm import Session
    from app.db import get_db
    from app.models.keyword import Keyword
    from app.models.onboarding import Job, BrandProfile
    
    logger.info(f"Starting keyword research for job {job_id}, brand {brand_id}, keyword '{primary_keyword}'")
    
    try:
        # Initialize seed for API calls
        seed = KeywordSeed(keyword=primary_keyword, location_name="India", language_name="English")
        all_keywords = []
        
        # Step 1: Fetch keywords from multiple sources
        logger.info("Fetching keyword suggestions via SerpAPI related searches...")
        serp_suggestions = await fetch_serp_keyword_suggestions(seed)
        all_keywords.extend(normalize_all(serp_suggestions, primary_keyword, "serp_suggestions"))

        logger.info("Fetching autocomplete suggestions via SerpAPI...")
        serp_autocomplete = await fetch_serp_autocomplete_suggestions(seed)
        all_keywords.extend(normalize_all(serp_autocomplete, primary_keyword, "serp_autocomplete"))

        # Supplement with DataForSEO if SerpAPI didn't return enough keywords
        if len(all_keywords) < 20:
            logger.info("Supplementing with DataForSEO keyword suggestions...")
            suggestions = await fetch_keyword_suggestions(seed)
            all_keywords.extend(normalize_all(suggestions, primary_keyword, "dataforseo_suggestions"))
            
            logger.info("Fetching DataForSEO keyword ideas...")
            ideas = await fetch_keyword_ideas(seed)
            all_keywords.extend(normalize_all(ideas, primary_keyword, "dataforseo_ideas"))
            
            logger.info("Fetching DataForSEO autocomplete...")
            autocomplete = await fetch_autocomplete_keywords(seed)
            all_keywords.extend(normalize_all(autocomplete, primary_keyword, "dataforseo_autocomplete"))
        
        logger.info("Generating sub-topics...")
        sub_topics = await fetch_sub_topics(primary_keyword)
        sub_topic_keywords = [{"keyword": topic} for topic in sub_topics]
        all_keywords.extend(normalize_all(sub_topic_keywords, primary_keyword, "sub_topics"))
        
        # Add the primary keyword itself to the list (so user sees what they searched for)
        primary_keyword_entry = {
            "related_keyword": primary_keyword.lower().strip(),
            "primary_keyword": primary_keyword.lower().strip(),
            "source_type": "primary_search",
            "search_volume": None,  # Will be enriched later
            "keyword_difficulty": None,
            "cpc": None,
            "competition": None,
        }
        all_keywords.insert(0, primary_keyword_entry)  # Add at the beginning
        
        logger.info(f"Collected {len(all_keywords)} total keywords from all sources")
        
        # Step 2: Deduplicate keywords
        deduped_keywords = dedupe_by(all_keywords, "related_keyword")
        logger.info(f"Deduplicated to {len(deduped_keywords)} unique keywords")
        
        # Step 3: AI-based relevance filtering using client's allowed_topics list (AI #1)
        db_early = next(get_db())
        try:
            profile = db_early.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
            allowed_topics = profile.allowed_topics if (profile and profile.allowed_topics) else []
        finally:
            db_early.close()

        if allowed_topics:
            logger.info(f"Applying AI keyword filter against {len(allowed_topics)} allowed topics...")
            filtered_keywords = await filter_keywords_for_relevance(deduped_keywords, allowed_topics)
        else:
            logger.warning("No allowed_topics on BrandProfile, skipping AI keyword filter")
            filtered_keywords = deduped_keywords
            
        logger.info(f"AI filtered to {len(filtered_keywords)} relevant keywords")
        
        # Step 4: Enrich with SEO metrics (search volume, difficulty)
        if filtered_keywords:
            keyword_strings = [k["related_keyword"] for k in filtered_keywords]
            
            # Fetch search volume and difficulty data in batches
            logger.info("Enriching keywords with SEO metrics...")
            volume_data = await fetch_search_volume(keyword_strings, seed.location_name, seed.language_name)
            difficulty_data = await fetch_bulk_keyword_difficulty(keyword_strings, seed.location_name, seed.language_name)
            
            # Create lookup dictionaries
            volume_lookup = {item.get("keyword", "").lower(): item for item in volume_data}
            difficulty_lookup = {item.get("keyword", "").lower(): item for item in difficulty_data}
            
            # Enrich keywords with metrics
            for keyword in filtered_keywords:
                kw_text = keyword["related_keyword"].lower()
                
                # Add volume data
                if volume_item := volume_lookup.get(kw_text):
                    keyword["search_volume"] = volume_item.get("search_volume")
                    keyword["cpc"] = volume_item.get("cpc")
                    keyword["competition"] = volume_item.get("competition")
                
                # Add difficulty data  
                if difficulty_item := difficulty_lookup.get(kw_text):
                    keyword["keyword_difficulty"] = difficulty_item.get("keyword_difficulty")
        
        # Step 5: Calculate scores and sort
        scored_keywords = score_keywords(filtered_keywords)
        scored_keywords.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"Scored and sorted {len(scored_keywords)} keywords")
        
        # Step 6: Save to database
        db = next(get_db())
        saved_count = 0
        
        try:
            for keyword_data in scored_keywords:
                keyword = Keyword(
                    job_id=job_id,
                    brand_id=brand_id,
                    related_keyword=keyword_data["related_keyword"],
                    primary_keyword=keyword_data["primary_keyword"],
                    source_type=keyword_data["source_type"],
                    search_volume=keyword_data.get("search_volume"),
                    keyword_difficulty=keyword_data.get("keyword_difficulty"),
                    cpc=keyword_data.get("cpc"),
                    competition=keyword_data.get("competition"),
                    score=keyword_data.get("score"),
                )
                db.add(keyword)
                saved_count += 1
            
            # Save all keywords
            db.commit()
            logger.info(f"Saved {saved_count} keywords to database")
            
            # Update job status to success
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "SUCCEEDED"  # Mark job as completed successfully
                job.stage = "KEYWORD"     # Mark as completed keyword research stage
            db.commit()
            logger.info(f"Updated job {job_id} status to SUCCEEDED")
            
            # Auto-trigger Pipeline 2 (SERP Analysis) if we have enough keywords
            if saved_count >= 3:  # Need at least 3 keywords for meaningful analysis
                from app.services.job_dispatcher import JobDispatcher

                # Get top 5 keywords for SERP analysis
                top_keywords = db.query(Keyword).filter(
                    Keyword.job_id == job_id
                ).order_by(Keyword.score.desc()).limit(5).all()

                if top_keywords:
                    target_keywords = [k.related_keyword for k in top_keywords]

                    # AI selection layer (AI #2): pick the keyword that best balances
                    # relevance to the user's seed against traffic, then lead with it so
                    # the downstream P2→P3 hand-off (which uses target_keywords[0])
                    # generates content for the AI-chosen topic.
                    chosen = await select_primary_target_keyword(primary_keyword, scored_keywords)
                    target_keywords = [chosen] + [k for k in target_keywords if k != chosen]

                    dispatcher = JobDispatcher()
                    dispatcher.enqueue_serp_analysis(
                        job_id=job_id,
                        brand_id=brand_id,
                        target_keywords=target_keywords[:5],
                    )
                    logger.info(
                        f"Auto-triggered SERP analysis; AI-selected primary keyword '{chosen}'"
                    )
            elif saved_count >= 1:
                # Too few keywords for a meaningful SERP analysis (P2 needs >= 3), but a
                # blog-originated job still expects a draft. Skip P2 and trigger P3
                # directly on the AI-selected keyword so /blogs never silently stalls.
                parent_payload = job.input_payload if job else {}
                if (parent_payload or {}).get("blog_job_id"):
                    chosen = await select_primary_target_keyword(primary_keyword, scored_keywords)
                    _trigger_content_generation_directly(
                        db, job, chosen, parent_payload or {}
                    )
                    logger.info(
                        f"Few keywords ({saved_count}); skipped SERP and triggered content "
                        f"generation directly on '{chosen}'"
                    )

        except Exception as db_exc:
            logger.error(f"Database error saving keywords: {db_exc}")
            db.rollback()
            # Don't set saved_count to 0 here - we want to report the error
            raise db_exc
        finally:
            db.close()
        
        return {
            "status": "success",
            "total_collected": len(all_keywords),
            "after_deduplication": len(deduped_keywords),
            "after_ai_filtering": len(filtered_keywords),
            "final_saved": saved_count,
            "top_keywords": [k["related_keyword"] for k in scored_keywords[:10]]
        }
        
    except Exception as exc:
        logger.error(f"Keyword research failed for job {job_id}: {exc}")
        
        # Mark job as failed
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(exc)
            db.commit()
            logger.info(f"Updated job {job_id} status to FAILED")
        except Exception as db_exc:
            logger.error(f"Failed to update job status: {db_exc}")
            
        return {
            "status": "error",
            "error": str(exc),
            "total_collected": 0,
            "final_saved": 0
        }


# ---------------------------------------------------------------------------
# Pipeline 2: SERP Analysis - DataForSEO Integration
# ---------------------------------------------------------------------------

async def fetch_serp_for_analysis(keyword: str, location_name: str = "India", language_name: str = "English", device: str = "mobile") -> dict | None:
    """
    Fetch live SERP results for competitor analysis using SerpAPI (replaces DataForSEO).
    
    Args:
        keyword: The search keyword
        location_name: Search location (default: India)
        language_name: Search language (default: English) 
        device: Device type (mobile/desktop, default: mobile)
        
    Returns:
        dict with organic results or None if failed
    """
    # Use SerpAPI instead of DataForSEO for Pipeline 2
    return await serpapi_fetch_serp_for_analysis(keyword, location_name, language_name, device)


# ---------------------------------------------------------------------------
# Pipeline 2: Apify Competitor Page Crawler
# ---------------------------------------------------------------------------

async def crawl_competitor_page(url: str) -> dict:
    """
    Scrape a single competitor page using Firecrawl for content analysis.

    Returns:
        dict: {content, word_count, success, error, load_time_ms, mobile_friendly}
    """
    from app.config import get_settings
    from app.services.crawler import CrawlError, scrape_page_with_firecrawl

    settings = get_settings()
    if not settings.firecrawl_api_key:
        logger.warning("FIRECRAWL_API_KEY not set — using HTTP fallback for competitor crawl")
        return await _simple_http_fallback(url)

    try:
        result = await scrape_page_with_firecrawl(url, timeout_ms=30000)

        markdown = result.get("markdown", "")
        meta = result.get("metadata", {})

        if not markdown or len(markdown.strip()) < 100:
            logger.warning("Firecrawl returned empty content for %s, trying HTTP fallback", url)
            return await _simple_http_fallback(url)

        word_count = len(markdown.split())

        if word_count < 400:
            return {
                "content": markdown,
                "word_count": word_count,
                "success": False,
                "error": f"Content too short: {word_count} words (minimum 400)",
                "load_time_ms": None,
                "mobile_friendly": None,
            }

        return {
            "content": markdown,
            "word_count": word_count,
            "success": True,
            "error": None,
            "load_time_ms": None,
            "mobile_friendly": True,
            "crawled_title": meta.get("title"),
            "crawled_meta_description": meta.get("description"),
        }

    except CrawlError:
        raise
    except Exception as exc:
        logger.error("Firecrawl competitor scrape failed for %s: %s", url, exc)
        return await _simple_http_fallback(url)


async def _simple_http_fallback(url: str) -> dict:
    """
    Simple HTTP fallback when Apify fails - lightweight alternative.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        import html2text
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "100xAI-ContentAnalyzer/1.0 (Fallback)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                return {
                    "content": None,
                    "word_count": 0,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "load_time_ms": None,
                    "mobile_friendly": None
                }
            
            # Parse HTML and convert to markdown
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            # Convert to markdown
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            markdown_content = h.handle(str(soup))
            
            word_count = len(markdown_content.split())
            
            if word_count < 100:
                return {
                    "content": None,
                    "word_count": word_count,
                    "success": False,
                    "error": f"Content too short: {word_count} words",
                    "load_time_ms": None,
                    "mobile_friendly": None
                }
            
            return {
                "content": markdown_content,
                "word_count": word_count,
                "success": True,
                "error": None,
                "load_time_ms": None,
                "mobile_friendly": None,
                "crawled_title": soup.title.string if soup.title else None,
                "crawled_meta_description": None
            }
            
    except Exception as e:
        logger.error(f"Simple HTTP fallback failed for {url}: {e}")
        return {
            "content": None,
            "word_count": 0,
            "success": False,
            "error": str(e),
            "load_time_ms": None,
            "mobile_friendly": None
        }


# ---------------------------------------------------------------------------
# Pipeline 2: AI Competitor Analysis
# ---------------------------------------------------------------------------

async def analyze_competitor_content(
    content: str,
    keyword: str,
    brand_profile: dict,
    competitor_url: str,
    competitor_title: str = ""
) -> dict:
    """
    Use AI to analyze competitor content for gaps and opportunities.
    
    Args:
        content: Competitor page content (markdown)
        keyword: The search keyword being analyzed
        brand_profile: Brand context for analysis
        competitor_url: Competitor page URL
        competitor_title: Page title for context
        
    Returns:
        dict with analysis results
    """
    # Import LLM service
    try:
        from app.services.llm import LLMService
    except ImportError:
        logger.warning("LLM service not available for competitor analysis")
        return {
            "content_strength": None,
            "content_gaps": [],
            "competitive_advantage": "LLM service not available",
            "target_audience": "Unknown",
            "content_tone": "Unknown",
            "key_topics": [],
            "success": False,
            "error": "LLM service not available"
        }
    
    # Truncate content to fit token limits (keep first 3000 characters for analysis)
    analysis_content = content[:3000] if content else ""
    
    prompt = f"""You are an expert content strategist analyzing competitor content for SEO and content gaps.

SEARCH CONTEXT:
Keyword: "{keyword}"
Competitor URL: {competitor_url}
Page Title: {competitor_title}

YOUR BRAND CONTEXT:
Business: {brand_profile.get('one_liner', 'Unknown business')}
Industry: {brand_profile.get('industry', 'Unknown')}
Target Audience: {', '.join(brand_profile.get('audience_personas', []))}
Unique Angle: {brand_profile.get('unique_angle', 'Not specified')}

COMPETITOR CONTENT TO ANALYZE:
{analysis_content}

ANALYSIS TASK:
Analyze this competitor content and identify opportunities for your brand to create superior content.

Return ONLY a valid JSON object with these fields:
{{
  "content_strength": 0.8,  // 0-1 scale: How well does this content serve the search intent?
  "content_gaps": [  // What key topics/angles are missing that your brand could cover?
    "missing practical examples",
    "no case studies or testimonials", 
    "lacks industry-specific insights"
  ],
  "competitive_advantage": "Comprehensive technical depth with clear explanations",  // What makes this content strong?
  "target_audience": "Technical decision makers and implementers",  // Who is this content for?
  "content_tone": "professional-technical",  // professional/casual/technical/conversational/authoritative
  "key_topics": [  // Main themes covered (max 5)
    "AI implementation strategies",
    "ROI analysis and metrics", 
    "Technical requirements",
    "Best practices guide"
  ]
}}

IMPORTANT: Return ONLY the JSON object, no explanations or additional text."""

    try:
        llm = LLMService()
        response = await llm.call("anthropic/claude-haiku-4-5-20251001", prompt)
        
        # Parse the AI response
        analysis_result = safe_json_parse(response.strip())
        
        if not isinstance(analysis_result, dict):
            logger.warning(f"Invalid AI response format for competitor analysis: {response[:100]}")
            return {
                "content_strength": 0.5,  # Default medium strength
                "content_gaps": ["Unable to analyze content gaps"],
                "competitive_advantage": "Analysis unavailable",
                "target_audience": "General audience",
                "content_tone": "professional",
                "key_topics": ["General information"],
                "success": False,
                "error": "Invalid AI response format"
            }
        
        # Ensure all required fields are present with defaults
        result = {
            "content_strength": analysis_result.get("content_strength", 0.5),
            "content_gaps": analysis_result.get("content_gaps", []),
            "competitive_advantage": analysis_result.get("competitive_advantage", "Not analyzed"),
            "target_audience": analysis_result.get("target_audience", "General audience"),
            "content_tone": analysis_result.get("content_tone", "professional"),
            "key_topics": analysis_result.get("key_topics", []),
            "success": True,
            "error": None
        }
        
        logger.info(f"Successfully analyzed competitor content for {competitor_url}")
        return result
        
    except Exception as exc:
        logger.error(f"AI competitor analysis failed for {competitor_url}: {exc}")
        return {
            "content_strength": 0.5,
            "content_gaps": ["Analysis failed"],
            "competitive_advantage": f"Analysis error: {str(exc)[:100]}",
            "target_audience": "Unknown",
            "content_tone": "unknown", 
            "key_topics": [],
            "success": False,
            "error": str(exc)
        }


# ---------------------------------------------------------------------------
# Pipeline 2: Main SERP Analysis Function
# ---------------------------------------------------------------------------

async def run_serp_analysis(
    job_id: str,
    brand_id: str, 
    target_keywords: list[str],
    brand_profile: dict | None = None
) -> dict:
    """
    Main Pipeline 2 function: SERP Analysis for competitor intelligence.
    
    Args:
        job_id: The job ID from the jobs table
        brand_id: The brand ID
        target_keywords: List of keywords to analyze (from Pipeline 1)
        brand_profile: Brand context for analysis
        
    Returns:
        dict with statistics about the SERP analysis process
    """
    from sqlalchemy.orm import Session
    from app.db import get_db
    from app.models.serp_analysis import SerpAnalysis, CompetitorAnalysis
    from app.models.onboarding import Job, BrandProfile
    from urllib.parse import urlparse
    
    logger.info(f"Starting SERP analysis for job {job_id}, brand {brand_id} with {len(target_keywords)} keywords")
    
    # Get brand profile if not provided
    if not brand_profile:
        db = next(get_db())
        profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
        if profile:
            brand_profile = {
                "one_liner": profile.one_liner,
                "industry": profile.industry,
                "audience_personas": profile.audience_personas or [],
                "unique_angle": profile.unique_angle,
                "default_location": profile.default_location or "India",
                "default_language": profile.default_language or "English"
            }
        else:
            brand_profile = {
                "one_liner": "Business", 
                "industry": "Unknown",
                "audience_personas": [],
                "unique_angle": "Not specified",
                "default_location": "India",
                "default_language": "English"
            }
        db.close()
    
    results = {
        "status": "success",
        "keywords_analyzed": 0,
        "total_competitors_crawled": 0,
        "successful_analyses": 0,
        "failed_crawls": 0,
        "content_opportunities": []
    }
    
    try:
        db = next(get_db())
        
        for keyword in target_keywords:
            keyword_results = {
                "keyword": keyword,
                "competitors_found": 0,
                "analyses_completed": 0,
                "top_gaps": []
            }
            
            try:
                # Step 1: Fetch SERP data
                logger.info(f"Fetching SERP for keyword: {keyword}")
                serp_data = await fetch_serp_for_analysis(
                    keyword,
                    brand_profile.get("default_location", "India"),
                    brand_profile.get("default_language", "English")
                )
                
                if not serp_data or not serp_data.get("organic"):
                    logger.warning(f"No SERP data found for keyword: {keyword}")
                    continue
                
                organic_results = serp_data["organic"][:10]  # Top 10 only
                keyword_results["competitors_found"] = len(organic_results)
                
                # Step 2: Create SERP analysis record
                serp_analysis = SerpAnalysis(
                    job_id=job_id,
                    brand_id=brand_id,
                    keyword_text=keyword,
                    search_location=brand_profile.get("default_location", "India"),
                    search_language=brand_profile.get("default_language", "English"),
                    device_type="mobile",
                    serp_snapshot=serp_data.get("raw_serp_data"),
                    status="PROCESSING"
                )
                db.add(serp_analysis)
                db.flush()  # Get the ID
                
                # Step 3: Analyze each competitor
                successful_analyses = 0
                total_word_count = 0
                all_gaps = []
                
                # Process only top 3 competitors to stay within RQ job time limits
                # (each Apify crawl takes 30-90s; 10 competitors = 5-15 min = worker timeout)
                import asyncio
                top_competitors = organic_results[:3]
                logger.info(f"Analyzing top {len(top_competitors)} of {len(organic_results)} competitors for '{keyword}'")
                for i, result in enumerate(top_competitors):
                    url = result.get("url")
                    if not url:
                        continue
                        
                    rank = result.get("rank_absolute", 0)
                    domain = urlparse(url).netloc if url else "unknown"
                    
                    logger.info(f"Crawling competitor #{rank}: {url} (Progress: {i+1}/{len(organic_results)})")
                    
                    # Step 4: Crawl competitor page with memory management
                    crawl_result = await crawl_competitor_page(url)
                    results["total_competitors_crawled"] += 1
                    
                    # Reduced delay between crawls to allow memory cleanup
                    if i < len(top_competitors) - 1:  # Don't delay after last item
                        logger.info(f"Waiting 1 second before next crawl for memory cleanup...")
                        await asyncio.sleep(1)
                    
                    # Step 5: Create competitor analysis record (even if crawl failed)
                    competitor_analysis = CompetitorAnalysis(
                        serp_analysis_id=serp_analysis.id,
                        rank_position=rank,
                        url=url,
                        title=result.get("title"),
                        meta_description=result.get("description"),
                        domain=domain,
                        crawl_success=crawl_result["success"],
                        error_message=crawl_result.get("error")
                    )
                    
                    if crawl_result["success"] and crawl_result.get("word_count", 0) >= 400:
                        # Step 6: AI analysis of content (quality gate: ≥400 words per spec §5.1e)
                        logger.info(f"Analyzing content for {url}")
                        analysis = await analyze_competitor_content(
                            crawl_result["content"],
                            keyword,
                            brand_profile,
                            url,
                            result.get("title", "")
                        )
                        
                        if analysis["success"]:
                            # Update competitor analysis with AI results
                            competitor_analysis.word_count = crawl_result["word_count"]
                            competitor_analysis.raw_content = crawl_result["content"][:5000]  # Truncate for storage
                            competitor_analysis.content_strength = analysis["content_strength"]
                            competitor_analysis.content_gaps = analysis["content_gaps"]
                            competitor_analysis.competitive_advantage = analysis["competitive_advantage"]
                            competitor_analysis.target_audience = analysis["target_audience"]
                            competitor_analysis.content_tone = analysis["content_tone"]
                            competitor_analysis.key_topics = analysis["key_topics"]
                            competitor_analysis.load_time_ms = crawl_result.get("load_time_ms")
                            competitor_analysis.mobile_friendly = crawl_result.get("mobile_friendly")
                            competitor_analysis.analysis_success = True
                            competitor_analysis.analyzed_at = db.execute(text("SELECT NOW()")).scalar()
                            
                            successful_analyses += 1
                            total_word_count += crawl_result["word_count"]
                            all_gaps.extend(analysis["content_gaps"])
                            
                            logger.info(f"Successfully analyzed {url}")
                        else:
                            competitor_analysis.error_message = analysis.get("error", "Analysis failed")
                            results["failed_crawls"] += 1
                    elif crawl_result["success"]:
                        # Crawl succeeded but word count < 400 — thin content, skip analysis
                        competitor_analysis.error_message = f"Skipped: word count {crawl_result.get('word_count', 0)} < 400"
                        logger.info(f"Skipped thin-content page ({crawl_result.get('word_count', 0)} words): {url}")
                    else:
                        results["failed_crawls"] += 1

                    competitor_analysis.crawled_at = db.execute(text("SELECT NOW()")).scalar()
                    db.add(competitor_analysis)
                
                # Step 7: Update SERP analysis summary
                serp_analysis.total_results_analyzed = successful_analyses
                if successful_analyses > 0:
                    serp_analysis.avg_word_count = total_word_count // successful_analyses
                    serp_analysis.top_competitor_url = organic_results[0].get("url") if organic_results else None
                    
                    # Calculate content gap score (0-1, higher = more gaps = more opportunity)
                    unique_gaps = list(set(all_gaps))
                    serp_analysis.content_gap_score = min(len(unique_gaps) / 10.0, 1.0)  # Normalize to 0-1
                    
                    serp_analysis.difficulty_analysis = {
                        "avg_word_count": serp_analysis.avg_word_count,
                        "competitors_analyzed": successful_analyses,
                        "common_gaps": unique_gaps[:5],  # Top 5 gaps
                        "opportunity_score": serp_analysis.content_gap_score
                    }
                    serp_analysis.status = "COMPLETED"
                else:
                    serp_analysis.status = "FAILED"
                    serp_analysis.error_message = "No successful competitor analyses"
                
                serp_analysis.completed_at = db.execute(text("SELECT NOW()")).scalar()
                
                keyword_results["analyses_completed"] = successful_analyses
                keyword_results["top_gaps"] = unique_gaps[:3]
                results["successful_analyses"] += successful_analyses
                results["keywords_analyzed"] += 1
                results["content_opportunities"].append(keyword_results)
                
                db.commit()
                logger.info(f"Completed SERP analysis for keyword: {keyword}")
                
            except Exception as e:
                logger.error(f"SERP analysis failed for keyword {keyword}: {e}")
                db.rollback()
                
        # Step 8: Update job status and auto-trigger Pipeline 3
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            if results["successful_analyses"] >= 1:
                job.status = "SUCCEEDED"
                job.stage = "CONTENT"
                job.output_payload = {"serp_analysis_results": results}
                logger.info(f"SERP analysis succeeded: {results['successful_analyses']} analyses completed")
                
                # Auto-trigger Pipeline 3: Content Generation
                try:
                    from app.services.job_dispatcher import JobDispatcher
                    from app.models.base import uuid_str
                    from app.services.content_generation import JOB_STAGE_CONTENT
                    
                    logger.info(f"Attempting to auto-trigger Pipeline 3 for job {job_id}")
                    
                    # Get the top performing keyword from the analysis
                    top_keyword = target_keywords[0] if target_keywords else "content marketing"

                    # Validate brand profile exists for content generation
                    brand_profile_exists = db.query(BrandProfile).filter(BrandProfile.brand_id == job.brand_id).first()
                    if not brand_profile_exists:
                        logger.warning(f"Brand profile not found for {job.brand_id}, skipping auto-trigger")
                        job.output_payload = dict(job.output_payload or {},
                                               auto_trigger_skipped="Brand DNA profile required for content generation")
                        db.commit()
                    else:
                        # Propagate calendar context (blog_job_id, created_by) so Pipeline 3
                        # can link the generated draft back to the original BlogJob / BlogSchedule.
                        parent_payload = job.input_payload or {}
                        blog_job_id = parent_payload.get("blog_job_id")

                        content_payload = {
                            "keyword": top_keyword,
                            "serp_analysis_job_id": job_id,
                            "auto_triggered": True,
                            "triggered_at": str(db.scalar(text("SELECT NOW()"))),
                            "created_by": parent_payload.get("created_by", "system"),
                        }
                        if blog_job_id:
                            content_payload["blog_job_id"] = blog_job_id
                            content_payload["blog_integration"] = True

                        # Create content generation job
                        content_job = Job(
                            id=uuid_str(),
                            org_id=job.org_id,
                            brand_id=job.brand_id,
                            job_type="content_generation",
                            stage=JOB_STAGE_CONTENT,
                            status="QUEUED",
                            input_payload=content_payload,
                        )
                        db.add(content_job)
                        db.flush()
                        
                        # Enqueue content generation
                        dispatcher = JobDispatcher()
                        dispatcher.enqueue_content_generation(
                            job_id=content_job.id,
                            brand_id=job.brand_id,
                            keyword=top_keyword,
                            serp_analysis_job_id=job_id
                        )
                        
                        # Update SERP job with auto-trigger metadata
                        job.output_payload = dict(job.output_payload or {}, 
                                               auto_triggered_content_job=content_job.id,
                                               auto_triggered_keyword=top_keyword)
                        
                        logger.info(f"✅ Auto-triggered Pipeline 3: Content generation job {content_job.id} for keyword '{top_keyword}'")
                        logger.info(f"📊 SERP Analysis → Content Generation pipeline completed for brand {job.brand_id}")
                    
                except Exception as trigger_exc:
                    logger.error(f"❌ Failed to auto-trigger Pipeline 3: {trigger_exc}")
                    # Track the failure in job metadata but don't fail the SERP job
                    try:
                        job.output_payload = dict(job.output_payload or {}, 
                                               auto_trigger_error=str(trigger_exc),
                                               auto_trigger_attempted=True)
                        db.commit()
                    except:
                        pass  # Ignore secondary errors
                    
            else:
                job.status = "SUCCEEDED"  # Still succeeded even if no data due to API issues
                job.stage = "SERP"  # Mark as completed SERP stage
                job.output_payload = {"serp_analysis_results": results, "note": "SERP analysis completed but no competitor data available (API limitations)"}
                logger.info(f"SERP analysis completed with limited data due to API restrictions")
            db.commit()
            logger.info(f"Updated job {job_id} status to SUCCEEDED")
        
        db.close()
        return results
        
    except Exception as exc:
        logger.error(f"SERP analysis pipeline failed for job {job_id}: {exc}")
        
        # Mark job as failed
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(exc)
            db.commit()
            logger.info(f"Updated job {job_id} status to FAILED")
        except Exception as db_exc:
            logger.error(f"Failed to update job status: {db_exc}")
        finally:
            try:
                db.close()
            except:
                pass
            
        return {
            "status": "error",
            "error": str(exc),
            "keywords_analyzed": 0,
            "successful_analyses": 0
        }
