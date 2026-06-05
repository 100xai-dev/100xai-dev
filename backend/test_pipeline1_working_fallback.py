#!/usr/bin/env python3
"""
Working Pipeline 1 Test with Fallback APIs
Uses OpenAI as fallback for keyword generation when primary APIs are down
"""

import sys
import os
import asyncio
import json
from uuid import uuid4

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.seo_research import (
    KeywordSeed,
    fetch_apify_keyword_suggestions,
    normalize_all,
    dedupe_by,
    score_keywords,
)
from app.config import get_settings


async def fallback_keyword_generation(primary_keyword: str, limit: int = 50) -> list[dict]:
    """Generate keywords using OpenAI as fallback when primary APIs are down."""
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("⚠️  No OpenAI API key - using mock data")
        return generate_mock_keywords(primary_keyword, limit)
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=settings.openai_api_key)
        
        prompt = f"""Generate {limit} keyword suggestions related to '{primary_keyword}' for SEO and content marketing.

Include a mix of:
- Related terms and synonyms
- Long-tail keywords
- Question-based keywords
- Commercial intent keywords
- Informational keywords

Return as a JSON array of objects with this format:
[
  {{"keyword": "digital marketing strategy", "source": "related_terms"}},
  {{"keyword": "how to do digital marketing", "source": "questions"}},
  {{"keyword": "best digital marketing tools", "source": "commercial_intent"}}
]

Only return the JSON array, no explanations."""

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7
            )
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        try:
            keywords_data = json.loads(content)
            if isinstance(keywords_data, list):
                print(f"✅ OpenAI generated {len(keywords_data)} keywords")
                return keywords_data
        except json.JSONDecodeError:
            print("⚠️  OpenAI returned invalid JSON, using mock data")
            
    except Exception as e:
        print(f"⚠️  OpenAI failed: {e}, using mock data")
    
    return generate_mock_keywords(primary_keyword, limit)


def generate_mock_keywords(primary_keyword: str, limit: int = 50) -> list[dict]:
    """Generate mock keyword data for testing."""
    base_terms = primary_keyword.split()
    main_term = base_terms[0] if base_terms else "marketing"
    
    mock_keywords = [
        # Related terms
        {"keyword": f"{primary_keyword} strategy", "source": "related_terms"},
        {"keyword": f"{primary_keyword} tips", "source": "related_terms"},
        {"keyword": f"{primary_keyword} guide", "source": "related_terms"},
        {"keyword": f"{primary_keyword} best practices", "source": "related_terms"},
        {"keyword": f"{primary_keyword} tools", "source": "related_terms"},
        
        # Questions
        {"keyword": f"how to {primary_keyword}", "source": "questions"},
        {"keyword": f"what is {primary_keyword}", "source": "questions"},
        {"keyword": f"why {primary_keyword}", "source": "questions"},
        {"keyword": f"when to use {primary_keyword}", "source": "questions"},
        
        # Commercial intent
        {"keyword": f"best {primary_keyword} service", "source": "commercial_intent"},
        {"keyword": f"{primary_keyword} agency", "source": "commercial_intent"},
        {"keyword": f"hire {primary_keyword} expert", "source": "commercial_intent"},
        {"keyword": f"{primary_keyword} consultant", "source": "commercial_intent"},
        
        # Long tail
        {"keyword": f"{primary_keyword} for small business", "source": "long_tail"},
        {"keyword": f"{primary_keyword} for beginners", "source": "long_tail"},
        {"keyword": f"{main_term} automation software", "source": "long_tail"},
        {"keyword": f"{main_term} ROI measurement", "source": "long_tail"},
        
        # Industry specific
        {"keyword": f"B2B {primary_keyword}", "source": "industry_specific"},
        {"keyword": f"B2C {primary_keyword}", "source": "industry_specific"},
        {"keyword": f"ecommerce {primary_keyword}", "source": "industry_specific"},
        {"keyword": f"SaaS {primary_keyword}", "source": "industry_specific"},
    ]
    
    return mock_keywords[:limit]


def generate_mock_metrics(keywords: list[dict]) -> list[dict]:
    """Generate realistic mock search volume and difficulty data."""
    import hashlib
    import random
    
    for keyword_data in keywords:
        keyword = keyword_data.get("keyword") or keyword_data.get("related_keyword", "unknown")
        
        # Use keyword hash for consistent "metrics"
        hash_obj = hashlib.md5(keyword.lower().encode())
        random.seed(int(hash_obj.hexdigest()[:8], 16))
        
        # Generate realistic metrics based on keyword characteristics
        word_count = len(keyword.split())
        is_question = keyword.lower().startswith(("how", "what", "why", "when", "where"))
        is_commercial = any(term in keyword.lower() for term in ["best", "buy", "service", "agency", "tool", "software"])
        
        # Search volume (shorter keywords = higher volume generally)
        if word_count <= 2:
            base_volume = random.randint(5000, 50000)
        elif word_count <= 3:
            base_volume = random.randint(1000, 15000)
        elif word_count <= 4:
            base_volume = random.randint(500, 5000)
        else:
            base_volume = random.randint(100, 2000)
        
        # Adjust for keyword type
        if is_commercial:
            base_volume = int(base_volume * 1.2)  # Commercial keywords often searched more
        if is_question:
            base_volume = int(base_volume * 0.8)  # Questions often less volume but high intent
        
        # Keyword difficulty (shorter = harder generally)
        if word_count <= 2:
            difficulty = random.randint(70, 95)
        elif word_count <= 3:
            difficulty = random.randint(40, 75)
        elif word_count <= 4:
            difficulty = random.randint(25, 55)
        else:
            difficulty = random.randint(10, 35)
        
        # CPC (commercial intent = higher CPC)
        if is_commercial:
            cpc = round(random.uniform(2.0, 8.0), 2)
        elif is_question:
            cpc = round(random.uniform(0.5, 2.5), 2)
        else:
            cpc = round(random.uniform(0.8, 4.0), 2)
        
        # Competition (0.0 to 1.0)
        if is_commercial:
            competition = round(random.uniform(0.6, 1.0), 2)
        else:
            competition = round(random.uniform(0.2, 0.8), 2)
        
        keyword_data.update({
            "search_volume": base_volume,
            "keyword_difficulty": difficulty,
            "cpc": cpc,
            "competition": competition
        })
    
    return keywords


async def test_working_pipeline():
    """Test the complete pipeline with working/fallback APIs."""
    print("🚀 Testing Complete Pipeline 1 with Fallback APIs")
    print("=" * 60)
    
    primary_keyword = "digital marketing"
    print(f"🎯 Primary keyword: '{primary_keyword}'")
    
    # Step 1: Try Apify first, fallback to OpenAI/mock
    print("\n1️⃣ Fetching keyword suggestions...")
    
    seed = KeywordSeed(keyword=primary_keyword, location_name="India", language_name="English")
    apify_keywords = []
    
    try:
        apify_keywords = await fetch_apify_keyword_suggestions(seed, limit=20)
        if apify_keywords:
            print(f"✅ Apify returned {len(apify_keywords)} keywords")
        else:
            print("⚠️  Apify returned no keywords, using fallback...")
    except Exception as e:
        print(f"⚠️  Apify failed: {str(e)[:50]}..., using fallback...")
    
    # Fallback keyword generation
    if len(apify_keywords) < 10:  # Use fallback if we don't have enough
        print("🔄 Using fallback keyword generation...")
        fallback_keywords = await fallback_keyword_generation(primary_keyword, limit=30)
        print(f"✅ Fallback generated {len(fallback_keywords)} keywords")
    else:
        fallback_keywords = []
    
    # Step 2: Normalize and combine keywords
    print("\n2️⃣ Processing keywords...")
    all_keywords = []
    
    if apify_keywords:
        all_keywords.extend(normalize_all(apify_keywords, primary_keyword, "apify"))
    
    if fallback_keywords:
        all_keywords.extend(normalize_all(fallback_keywords, primary_keyword, "fallback"))
    
    print(f"✅ Combined {len(all_keywords)} total keywords")
    
    # Step 3: Deduplicate
    print("\n3️⃣ Deduplicating keywords...")
    deduped = dedupe_by(all_keywords, "related_keyword")
    print(f"✅ Deduplicated to {len(deduped)} unique keywords")
    
    # Step 4: Add mock metrics (since DataForSEO is down)
    print("\n4️⃣ Adding SEO metrics (mock data)...")
    keywords_with_metrics = generate_mock_metrics(deduped.copy())
    print(f"✅ Added metrics to {len(keywords_with_metrics)} keywords")
    
    # Step 5: Score and rank keywords
    print("\n5️⃣ Scoring and ranking keywords...")
    scored_keywords = score_keywords(keywords_with_metrics)
    scored_keywords.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"✅ Scored {len(scored_keywords)} keywords")
    
    # Step 6: Show results
    print("\n🏆 Top 10 Keywords:")
    print("-" * 80)
    print(f"{'Rank':<4} {'Keyword':<35} {'Score':<7} {'Volume':<8} {'Diff':<5} {'CPC':<6} {'Source'}")
    print("-" * 80)
    
    for i, kw in enumerate(scored_keywords[:10], 1):
        keyword = kw["related_keyword"][:32]
        score = f"{kw.get('score', 0):.3f}"
        volume = str(kw.get('search_volume', 'N/A'))[:7]
        difficulty = str(kw.get('keyword_difficulty', 'N/A'))[:4]
        cpc = f"${kw.get('cpc', 0):.2f}"[:5]
        source = kw.get('source_type', 'N/A')[:10]
        
        print(f"{i:<4} {keyword:<35} {score:<7} {volume:<8} {difficulty:<5} {cpc:<6} {source}")
    
    # Step 7: Analyze keyword distribution
    print("\n📊 Keyword Analysis:")
    sources = {}
    difficulty_ranges = {"Easy (0-30)": 0, "Medium (31-60)": 0, "Hard (61-100)": 0}
    volume_ranges = {"Low (0-1K)": 0, "Medium (1K-10K)": 0, "High (10K+)": 0}
    
    for kw in scored_keywords:
        # Source distribution
        source = kw.get('source_type', 'unknown')
        sources[source] = sources.get(source, 0) + 1
        
        # Difficulty distribution
        diff = kw.get('keyword_difficulty', 50)
        if diff <= 30:
            difficulty_ranges["Easy (0-30)"] += 1
        elif diff <= 60:
            difficulty_ranges["Medium (31-60)"] += 1
        else:
            difficulty_ranges["Hard (61-100)"] += 1
        
        # Volume distribution
        vol = kw.get('search_volume', 0)
        if vol < 1000:
            volume_ranges["Low (0-1K)"] += 1
        elif vol < 10000:
            volume_ranges["Medium (1K-10K)"] += 1
        else:
            volume_ranges["High (10K+)"] += 1
    
    print(f"   📈 Sources: {dict(sources)}")
    print(f"   📉 Difficulty: {dict(difficulty_ranges)}")
    print(f"   📊 Volume: {dict(volume_ranges)}")
    
    return scored_keywords


async def main():
    """Main test function."""
    try:
        scored_keywords = await test_working_pipeline()
        
        print("\n" + "=" * 60)
        print("🎉 Pipeline 1 Test Completed Successfully!")
        print(f"✅ Processed {len(scored_keywords)} keywords")
        print(f"✅ Top keyword: '{scored_keywords[0]['related_keyword']}' (score: {scored_keywords[0].get('score', 0):.3f})")
        
        print("\n💡 Integration Status:")
        print("  ✅ Keyword generation (with fallbacks)")
        print("  ✅ Keyword normalization and deduplication") 
        print("  ✅ SEO metrics simulation")
        print("  ✅ Keyword scoring and ranking")
        print("  ✅ Complete pipeline workflow")
        
        print("\n🔧 Next Steps to Go Live:")
        print("  1. Contact DataForSEO support (support@dataforseo.com)")
        print("  2. Test Apify with correct input format")
        print("  3. Replace mock metrics with real API data")
        print("  4. Add database integration")
        print("  5. Test with real brand data")
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())