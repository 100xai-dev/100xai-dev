from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

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


# ---------------------------------------------------------------------------
# Pipeline 1: Keyword Research - DataForSEO API Methods
# ---------------------------------------------------------------------------

async def _make_dataforseo_request(endpoint: str, payload: list[dict]) -> dict | None:
    """Make authenticated request to DataForSEO API."""
    s = get_settings()
    if not s.dataforseo_login or not s.dataforseo_password:
        logger.warning("DataForSEO credentials not set")
        return None

    creds = base64.b64encode(f"{s.dataforseo_login}:{s.dataforseo_password}".encode()).decode()
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

    data = await _make_dataforseo_request("/keywords_data/google/autocomplete/live", payload)
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
    """Safely parse JSON string, return None on failure."""
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Pipeline 1: AI Filtering
# ---------------------------------------------------------------------------

async def filter_keywords_for_relevance(keywords: list[dict], brand_context: str, business_description: str) -> list[dict]:
    """Use AI to filter keywords for brand relevance and commercial intent."""
    if not keywords:
        return []
        
    # Import LLM service
    from app.services.llm import get_llm_service
    
    # Prepare keyword list for analysis (limit to prevent token overflow)
    keyword_batch = keywords[:100]  # Process in batches for large lists
    keyword_list = "\n".join([f"- {k['related_keyword']} (vol: {k.get('search_volume', 'N/A')})" for k in keyword_batch])
    
    prompt = f"""You are an SEO keyword analyst. Analyze the following keywords for relevance to the given brand.

BRAND CONTEXT:
{brand_context}

BUSINESS DESCRIPTION:
{business_description}

KEYWORDS TO ANALYZE:
{keyword_list}

INSTRUCTIONS:
1. Filter keywords that are relevant to this brand's business, products, or services
2. Prioritize keywords with commercial intent (buying signals, product searches, service inquiries)
3. Exclude generic, overly broad, or completely unrelated keywords
4. Include informational keywords that could drive qualified traffic

Return ONLY a JSON array of relevant keyword strings in this exact format:
["keyword1", "keyword2", "keyword3"]

Do not include explanations or additional text."""

    try:
        llm = get_llm_service()
        response = await llm.call("claude-3-5-sonnet-20241022", prompt)
        
        # Parse the response to get the filtered keyword list
        relevant_keywords = safe_json_parse(response.strip())
        
        if not isinstance(relevant_keywords, list):
            logger.warning("LLM returned invalid format for keyword filtering")
            return keywords  # Return original if filtering fails
        
        # Filter original keywords to match AI-selected ones
        relevant_set = set(kw.lower() for kw in relevant_keywords)
        filtered = [k for k in keyword_batch if k["related_keyword"].lower() in relevant_set]
        
        logger.info(f"AI filtered {len(keyword_batch)} keywords down to {len(filtered)} relevant ones")
        return filtered
        
    except Exception as exc:
        logger.warning(f"AI keyword filtering failed: {exc}")
        return keywords  # Return original keywords if AI filtering fails


# ---------------------------------------------------------------------------
# Pipeline 1: Main Keyword Research Function
# ---------------------------------------------------------------------------

async def run_keyword_research(job_id: str, brand_id: str, primary_keyword: str, brand_context: str, business_description: str) -> dict:
    """
    Main Pipeline 1 function: Research keywords for a given brand and primary keyword.
    
    Args:
        job_id: The job ID from the jobs table
        brand_id: The brand ID 
        primary_keyword: The seed keyword to research
        brand_context: Brand DNA context for AI filtering
        business_description: Business description for relevance filtering
        
    Returns:
        dict with statistics about the keyword research process
    """
    from sqlalchemy.orm import Session
    from app.db import get_db
    from app.models.keyword import Keyword
    from app.models.onboarding import Job
    
    logger.info(f"Starting keyword research for job {job_id}, brand {brand_id}, keyword '{primary_keyword}'")
    
    try:
        # Initialize seed for API calls
        seed = KeywordSeed(keyword=primary_keyword, location_name="India", language_name="English")
        all_keywords = []
        
        # Step 1: Fetch keywords from multiple sources
        logger.info("Fetching related keywords...")
        related_keywords = await fetch_related_keywords(seed)
        all_keywords.extend(normalize_all(related_keywords, primary_keyword, "related_keywords"))
        
        logger.info("Fetching keyword suggestions...")
        suggestions = await fetch_keyword_suggestions(seed)
        all_keywords.extend(normalize_all(suggestions, primary_keyword, "suggestions"))
        
        logger.info("Fetching keyword ideas...")
        ideas = await fetch_keyword_ideas(seed)
        all_keywords.extend(normalize_all(ideas, primary_keyword, "ideas"))
        
        logger.info("Fetching autocomplete keywords...")
        autocomplete = await fetch_autocomplete_keywords(seed)
        all_keywords.extend(normalize_all(autocomplete, primary_keyword, "autocomplete"))
        
        logger.info("Generating sub-topics...")
        sub_topics = await fetch_sub_topics(primary_keyword)
        sub_topic_keywords = [{"keyword": topic} for topic in sub_topics]
        all_keywords.extend(normalize_all(sub_topic_keywords, primary_keyword, "sub_topics"))
        
        logger.info(f"Collected {len(all_keywords)} total keywords from all sources")
        
        # Step 2: Deduplicate keywords
        deduped_keywords = dedupe_by(all_keywords, "related_keyword")
        logger.info(f"Deduplicated to {len(deduped_keywords)} unique keywords")
        
        # Step 3: AI-based relevance filtering
        if brand_context and business_description:
            logger.info("Applying AI relevance filtering...")
            filtered_keywords = await filter_keywords_for_relevance(deduped_keywords, brand_context, business_description)
        else:
            logger.warning("No brand context provided, skipping AI filtering")
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
        
        db.commit()
        logger.info(f"Saved {saved_count} keywords to database")
        
        # Update job status
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.stage = "KEYWORD"  # Mark as completed keyword research stage
        db.commit()
        
        # Auto-trigger Pipeline 2 (SERP Analysis) if we have enough keywords
        if saved_count >= 3:  # Need at least 3 keywords for meaningful analysis
            from app.services.job_dispatcher import JobDispatcher
            
            # Get top 5 keywords for SERP analysis
            top_keywords = db.query(Keyword).filter(
                Keyword.job_id == job_id
            ).order_by(Keyword.score.desc()).limit(5).all()
            
            if top_keywords:
                dispatcher = JobDispatcher()
                dispatcher.enqueue_serp_analysis(
                    job_id=job_id,
                    brand_id=brand_id,
                    target_keywords=[k.related_keyword for k in top_keywords]
                )
                logger.info(f"Auto-triggered SERP analysis for {len(top_keywords)} top keywords")
        
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
                job.error_message = str(exc)
            db.commit()
        except Exception:
            pass
            
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
    Fetch live SERP results for competitor analysis.
    
    Args:
        keyword: The search keyword
        location_name: Search location (default: India)
        language_name: Search language (default: English) 
        device: Device type (mobile/desktop, default: mobile)
        
    Returns:
        dict with organic results or None if failed
    """
    payload = [{
        "keyword": keyword,
        "location_name": location_name,
        "language_name": language_name,
        "device": device,
        "depth": 10,  # Top 10 results
        "os": "android" if device == "mobile" else "windows"
    }]
    
    data = await _make_dataforseo_request("/serp/google/organic/live/advanced", payload)
    if not data:
        return None
    
    # Extract and clean organic results
    result = data.get("tasks", [{}])[0].get("result", [{}])[0]
    items = result.get("items", [])
    
    organic_results = []
    for i, item in enumerate(items):
        if item.get("type") == "organic":
            organic_results.append({
                "rank_absolute": item.get("rank_absolute", i + 1),
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
                "domain": item.get("domain"),
                "breadcrumb": item.get("breadcrumb"),
            })
    
    return {
        "keyword": keyword,
        "location": location_name,
        "language": language_name,
        "device": device,
        "total_results": result.get("se_results_count"),
        "organic": organic_results[:10],  # Top 10 only
        "raw_serp_data": data  # Store full response for debugging
    }


# ---------------------------------------------------------------------------
# Pipeline 2: Apify Competitor Page Crawler
# ---------------------------------------------------------------------------

async def crawl_competitor_page(url: str) -> dict:
    """
    Crawl a competitor page using Apify for content analysis.
    
    Args:
        url: The competitor page URL to crawl
        
    Returns:
        dict with crawl results: {content: str, word_count: int, success: bool, error: str}
    """
    from app.config import get_settings
    from app.services.crawler import _make_apify_request  # Reuse existing Apify infrastructure
    
    settings = get_settings()
    if not settings.apify_api_key:
        logger.warning("Apify token not set - skipping competitor page crawl")
        return {
            "content": None,
            "word_count": 0,
            "success": False,
            "error": "Apify token not configured",
            "load_time_ms": None,
            "mobile_friendly": None
        }
    
    # Configure for single page crawl optimized for content extraction
    crawl_input = {
        "startUrls": [{"url": url}],
        "crawlerType": "playwright:adaptive",  # Use browser rendering
        "maxRequestsPerCrawl": 1,  # Single page only
        "maxSessionRotations": 1,
        "blockMedia": True,  # Skip images/videos for performance
        "removeElementsCssSelector": "nav, footer, header, .ads, .sidebar, .navigation, script, style",
        "outputFormats": ["markdown"],
        "proxyConfiguration": {"useApifyProxy": True},
        "saveScreenshots": False,  # We don't need screenshots for content analysis
        "saveHtmlToFile": False,
        "requestTimeout": 30000,  # 30 second timeout
        "pageTimeout": 30000
    }
    
    try:
        # Use the same Apify actor as the main crawler
        result = await _make_apify_request(
            actor_name="apify/website-content-crawler",
            run_input=crawl_input,
            timeout_seconds=60  # Allow up to 60 seconds for crawl
        )
        
        if not result or not result.get("items"):
            return {
                "content": None,
                "word_count": 0,
                "success": False,
                "error": "No content returned from Apify",
                "load_time_ms": None,
                "mobile_friendly": None
            }
        
        item = result["items"][0]
        markdown_content = item.get("markdown", "")
        
        if not markdown_content or len(markdown_content.strip()) < 100:
            return {
                "content": None,
                "word_count": 0,
                "success": False,
                "error": "Content too short or empty",
                "load_time_ms": item.get("loadTime"),
                "mobile_friendly": None
            }
        
        # Calculate word count (approximate)
        word_count = len(markdown_content.split())
        
        # Check if meets quality threshold
        if word_count < 400:
            return {
                "content": markdown_content,
                "word_count": word_count,
                "success": False,
                "error": f"Content too short: {word_count} words (minimum 400)",
                "load_time_ms": item.get("loadTime"),
                "mobile_friendly": None
            }
        
        return {
            "content": markdown_content,
            "word_count": word_count,
            "success": True,
            "error": None,
            "load_time_ms": item.get("loadTime"),
            "mobile_friendly": True,  # Apify handles mobile rendering
            "crawled_title": item.get("title"),
            "crawled_meta_description": item.get("description")
        }
        
    except Exception as exc:
        logger.error(f"Apify competitor crawl failed for {url}: {exc}")
        return {
            "content": None,
            "word_count": 0,
            "success": False,
            "error": str(exc),
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
        from app.services.llm import get_llm_service
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
        llm = get_llm_service()
        response = await llm.call("claude-3-5-sonnet-20241022", prompt)
        
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
                
                for result in organic_results:
                    url = result.get("url")
                    if not url:
                        continue
                        
                    rank = result.get("rank_absolute", 0)
                    domain = urlparse(url).netloc if url else "unknown"
                    
                    logger.info(f"Crawling competitor #{rank}: {url}")
                    
                    # Step 4: Crawl competitor page
                    crawl_result = await crawl_competitor_page(url)
                    results["total_competitors_crawled"] += 1
                    
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
                    
                    if crawl_result["success"]:
                        # Step 6: AI analysis of content
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
                            competitor_analysis.analyzed_at = db.execute("SELECT NOW()").scalar()
                            
                            successful_analyses += 1
                            total_word_count += crawl_result["word_count"]
                            all_gaps.extend(analysis["content_gaps"])
                            
                            logger.info(f"Successfully analyzed {url}")
                        else:
                            competitor_analysis.error_message = analysis.get("error", "Analysis failed")
                            results["failed_crawls"] += 1
                    else:
                        results["failed_crawls"] += 1
                    
                    competitor_analysis.crawled_at = db.execute("SELECT NOW()").scalar()
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
                
                serp_analysis.completed_at = db.execute("SELECT NOW()").scalar()
                
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
                
        # Step 8: Update job status
        if results["successful_analyses"] >= 1:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.stage = "CONTENT"
                job.output_payload = {"serp_analysis_results": results}
                db.commit()
                logger.info(f"Advanced job {job_id} to CONTENT stage")
        
        db.close()
        return results
        
    except Exception as exc:
        logger.error(f"SERP analysis pipeline failed for job {job_id}: {exc}")
        
        # Mark job as failed
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.error_message = str(exc)
            db.commit()
            db.close()
        except Exception:
            pass
            
        return {
            "status": "error",
            "error": str(exc),
            "keywords_analyzed": 0,
            "successful_analyses": 0
        }
