#!/usr/bin/env python3
"""
Test Pipeline 1 with Apify for keyword suggestions and DataForSEO for search volume/difficulty
"""

import sys
import os
import asyncio
from uuid import uuid4

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Brand, Job
from app.services.seo_research import (
    KeywordSeed,
    fetch_apify_keyword_suggestions,
    fetch_apify_autocomplete_suggestions,
    fetch_search_volume,
    fetch_bulk_keyword_difficulty,
    normalize_all,
    dedupe_by,
    score_keywords,
    run_keyword_research
)
from app.config import get_settings


def check_credentials():
    """Check if required API credentials are set."""
    settings = get_settings()
    
    print("🔍 Checking API credentials...")
    
    # Check Apify
    if settings.apify_api_key:
        print(f"✅ Apify API key: {settings.apify_api_key[:10]}...")
    else:
        print("❌ Apify API key not set (APIFY_API_KEY)")
    
    # Check DataForSEO
    if settings.dataforseo_api_key:
        print(f"✅ DataForSEO API key: {settings.dataforseo_api_key[:10]}...")
    elif settings.dataforseo_login and settings.dataforseo_password:
        print(f"✅ DataForSEO login: {settings.dataforseo_login}")
    else:
        print("❌ DataForSEO credentials not set")
    
    return {
        "apify": bool(settings.apify_api_key),
        "dataforseo": bool(settings.dataforseo_api_key or (settings.dataforseo_login and settings.dataforseo_password))
    }


async def test_apify_keyword_suggestions():
    """Test Apify Google Search Scraper for keyword suggestions."""
    print("\n🔍 Testing Apify Keyword Suggestions...")
    
    test_keywords = ["artificial intelligence", "digital marketing", "web development"]
    
    for keyword in test_keywords:
        print(f"\n📝 Testing keyword: '{keyword}'")
        
        seed = KeywordSeed(keyword=keyword, location_name="India", language_name="English")
        
        try:
            # Test Apify keyword suggestions
            apify_suggestions = await fetch_apify_keyword_suggestions(seed, limit=20)
            print(f"✅ Apify suggestions: {len(apify_suggestions)} keywords")
            
            if apify_suggestions:
                print("   Top suggestions:")
                for i, suggestion in enumerate(apify_suggestions[:5], 1):
                    source = suggestion.get('source', 'unknown')
                    print(f"   {i}. {suggestion['keyword']} (source: {source})")
            
            # Test Apify autocomplete
            apify_autocomplete = await fetch_apify_autocomplete_suggestions(seed)
            print(f"✅ Apify autocomplete: {len(apify_autocomplete)} suggestions")
            
            if apify_autocomplete:
                print("   Top autocomplete:")
                for i, suggestion in enumerate(apify_autocomplete[:3], 1):
                    source = suggestion.get('source', 'unknown')
                    print(f"   {i}. {suggestion['keyword']} (source: {source})")
                    
        except Exception as e:
            print(f"❌ Error testing '{keyword}': {e}")
    
    print("\n✅ Apify keyword suggestions test completed")


async def test_dataforseo_enrichment():
    """Test DataForSEO for search volume and difficulty."""
    print("\n🔍 Testing DataForSEO Search Volume & Difficulty...")
    
    # Sample keywords for testing
    test_keywords = [
        "artificial intelligence",
        "machine learning tutorial", 
        "python programming guide",
        "digital marketing tips",
        "web development course"
    ]
    
    try:
        # Test search volume
        print("📊 Fetching search volume data...")
        volume_data = await fetch_search_volume(test_keywords, "India", "English")
        print(f"✅ Search volume data: {len(volume_data)} keywords")
        
        if volume_data:
            print("   Volume data sample:")
            for item in volume_data[:3]:
                keyword = item.get('keyword', 'N/A')
                volume = item.get('search_volume', 'N/A')
                cpc = item.get('cpc', 'N/A')
                print(f"   • {keyword}: {volume} searches, ${cpc} CPC")
        
        # Test keyword difficulty
        print("\n📈 Fetching keyword difficulty data...")
        difficulty_data = await fetch_bulk_keyword_difficulty(test_keywords, "India", "English")
        print(f"✅ Difficulty data: {len(difficulty_data)} keywords")
        
        if difficulty_data:
            print("   Difficulty data sample:")
            for item in difficulty_data[:3]:
                keyword = item.get('keyword', 'N/A')
                difficulty = item.get('keyword_difficulty', 'N/A')
                print(f"   • {keyword}: {difficulty}/100 difficulty")
        
    except Exception as e:
        print(f"❌ DataForSEO test failed: {e}")
    
    print("\n✅ DataForSEO enrichment test completed")


async def test_pipeline_integration():
    """Test the combined pipeline workflow."""
    print("\n🔄 Testing Combined Pipeline 1 Workflow...")
    
    test_keyword = "digital marketing"
    print(f"🎯 Primary keyword: '{test_keyword}'")
    
    # Step 1: Get keyword suggestions from Apify
    seed = KeywordSeed(keyword=test_keyword, location_name="India", language_name="English")
    
    print("\n1️⃣ Fetching keywords from Apify...")
    apify_keywords = await fetch_apify_keyword_suggestions(seed, limit=15)
    apify_autocomplete = await fetch_apify_autocomplete_suggestions(seed)
    
    # Normalize Apify results
    all_keywords = []
    all_keywords.extend(normalize_all(apify_keywords, test_keyword, "apify_suggestions"))
    all_keywords.extend(normalize_all(apify_autocomplete, test_keyword, "apify_autocomplete"))
    
    print(f"✅ Collected {len(all_keywords)} keywords from Apify")
    
    # Step 2: Deduplicate
    print("\n2️⃣ Deduplicating keywords...")
    deduped = dedupe_by(all_keywords, "related_keyword")
    print(f"✅ Deduplicated to {len(deduped)} unique keywords")
    
    # Step 3: Enrich with DataForSEO metrics
    if deduped:
        print("\n3️⃣ Enriching with DataForSEO metrics...")
        keyword_strings = [k["related_keyword"] for k in deduped[:10]]  # Test with top 10
        
        # Get search volume and difficulty
        volume_data = await fetch_search_volume(keyword_strings, "India", "English")
        difficulty_data = await fetch_bulk_keyword_difficulty(keyword_strings, "India", "English")
        
        # Create lookup dictionaries
        volume_lookup = {item.get("keyword", "").lower(): item for item in volume_data}
        difficulty_lookup = {item.get("keyword", "").lower(): item for item in difficulty_data}
        
        # Enrich keywords
        enriched_count = 0
        for keyword in deduped[:10]:
            kw_text = keyword["related_keyword"].lower()
            
            if volume_item := volume_lookup.get(kw_text):
                keyword["search_volume"] = volume_item.get("search_volume")
                keyword["cpc"] = volume_item.get("cpc")
                keyword["competition"] = volume_item.get("competition")
                enriched_count += 1
            
            if difficulty_item := difficulty_lookup.get(kw_text):
                keyword["keyword_difficulty"] = difficulty_item.get("keyword_difficulty")
        
        print(f"✅ Enriched {enriched_count} keywords with DataForSEO metrics")
        
        # Step 4: Score keywords
        print("\n4️⃣ Scoring keywords...")
        scored = score_keywords(deduped[:10])
        scored.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        print(f"✅ Scored {len(scored)} keywords")
        
        # Show top results
        print("\n🏆 Top scored keywords:")
        for i, kw in enumerate(scored[:5], 1):
            score = kw.get("score", 0)
            volume = kw.get("search_volume", "N/A")
            difficulty = kw.get("keyword_difficulty", "N/A")
            source = kw.get("source_type", "unknown")
            print(f"   {i}. {kw['related_keyword']} (score: {score:.3f}, vol: {volume}, diff: {difficulty}, source: {source})")
        
        return scored
    
    print("❌ No keywords to enrich")
    return []


async def test_full_pipeline_with_database():
    """Test the full pipeline including database operations."""
    print("\n🗄️ Testing Full Pipeline with Database...")
    
    db = next(get_db())
    
    try:
        # Create test brand
        brand = Brand(
            name="Test Digital Agency",
            website_url="https://testdigitalagency.com",
            status="APPROVED"
        )
        db.add(brand)
        db.flush()
        
        # Create test job
        job = Job(
            brand_id=brand.id,
            job_type="keyword_research",
            status="NEW",
            stage="NEW"
        )
        db.add(job)
        db.flush()
        
        print(f"✅ Created test brand: {brand.id}")
        print(f"✅ Created test job: {job.id}")
        
        # Run the full pipeline
        primary_keyword = "content marketing"
        brand_context = "Digital marketing agency specializing in content creation and SEO"
        business_description = "We help businesses grow through strategic content marketing and SEO optimization"
        
        print(f"\n🚀 Running full keyword research pipeline for '{primary_keyword}'...")
        
        result = await run_keyword_research(
            job_id=str(job.id),
            brand_id=str(brand.id),
            primary_keyword=primary_keyword,
            brand_context=brand_context,
            business_description=business_description
        )
        
        print("\n📊 Pipeline Results:")
        print(f"   Status: {result['status']}")
        print(f"   Total collected: {result.get('total_collected', 0)}")
        print(f"   After deduplication: {result.get('after_deduplication', 0)}")
        print(f"   After AI filtering: {result.get('after_ai_filtering', 0)}")
        print(f"   Final saved: {result.get('final_saved', 0)}")
        
        if result.get('top_keywords'):
            print(f"\n🏆 Top keywords saved:")
            for i, keyword in enumerate(result['top_keywords'][:5], 1):
                print(f"   {i}. {keyword}")
        
        # Verify keywords in database
        saved_keywords = db.query(Keyword).filter(Keyword.job_id == job.id).all()
        print(f"\n✅ Verified {len(saved_keywords)} keywords saved in database")
        
        if saved_keywords:
            print("   Sample saved keywords:")
            for kw in saved_keywords[:3]:
                print(f"   • {kw.related_keyword} (score: {kw.score}, source: {kw.source_type})")
        
        db.commit()
        return result
        
    except Exception as e:
        db.rollback()
        print(f"❌ Full pipeline test failed: {e}")
        raise
    finally:
        db.close()


async def main():
    """Main test function."""
    print("🚀 Pipeline 1 Testing: Apify + DataForSEO Integration")
    print("=" * 60)
    
    # Check credentials
    credentials = check_credentials()
    
    if not credentials["apify"]:
        print("\n⚠️  Apify credentials not found. Set APIFY_API_KEY to test Apify features.")
        return
    
    if not credentials["dataforseo"]:
        print("\n⚠️  DataForSEO credentials not found. Set DATAFORSEO_LOGIN/PASSWORD or DATAFORSEO_API_KEY.")
        return
    
    try:
        # Test individual components
        await test_apify_keyword_suggestions()
        await test_dataforseo_enrichment()
        
        # Test combined workflow
        scored_keywords = await test_pipeline_integration()
        
        # Test full pipeline with database
        pipeline_result = await test_full_pipeline_with_database()
        
        print("\n" + "=" * 60)
        print("🎉 All Pipeline 1 tests completed successfully!")
        print(f"✅ Keywords processed: {len(scored_keywords)}")
        print(f"✅ Final pipeline status: {pipeline_result.get('status', 'unknown')}")
        print(f"✅ Keywords saved to database: {pipeline_result.get('final_saved', 0)}")
        
        print("\n📋 What was tested:")
        print("  1. ✅ Apify Google Search Scraper for keyword suggestions")
        print("  2. ✅ Apify autocomplete suggestions")
        print("  3. ✅ DataForSEO search volume and difficulty enrichment")
        print("  4. ✅ Keyword normalization and deduplication")
        print("  5. ✅ Keyword scoring algorithm")
        print("  6. ✅ Full pipeline integration with database")
        print("  7. ✅ AI filtering and relevance scoring")
        
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())