"""Test SerpApi integration to verify functionality."""

import asyncio
from app.services.seo_research import (
    serpapi_fetch_serp_data,
    serpapi_fetch_serp_for_analysis,
    serpapi_fetch_autocomplete_keywords,
    serpapi_fetch_related_keywords,
    KeywordSeed
)


async def test_serpapi_integration():
    """Test all SerpApi functions."""
    print("🔧 Testing SerpApi Integration")
    print("=" * 50)
    
    # Test basic SERP data
    print("\n1. Testing basic SERP data...")
    serp_data = await serpapi_fetch_serp_data("digital marketing")
    if serp_data:
        print("✅ Basic SERP data working!")
        print(f"   Found {len(serp_data.get('organic', []))} organic results")
    else:
        print("⚠️  No SERP data returned (API key may not be set)")
    
    # Test SERP analysis
    print("\n2. Testing SERP analysis...")
    analysis_data = await serpapi_fetch_serp_for_analysis("seo tips")
    if analysis_data:
        print("✅ SERP analysis working!")
        print(f"   Found {len(analysis_data.get('organic', []))} organic results")
        print(f"   Total results: {analysis_data.get('total_results', 0)}")
    else:
        print("⚠️  No analysis data returned")
    
    # Test autocomplete
    print("\n3. Testing autocomplete...")
    seed = KeywordSeed("content marketing", "United States", "English")
    autocomplete_data = await serpapi_fetch_autocomplete_keywords(seed)
    if autocomplete_data:
        print("✅ Autocomplete working!")
        print(f"   Found {len(autocomplete_data)} suggestions")
        if autocomplete_data:
            print(f"   Example: {autocomplete_data[0].get('value', 'N/A')}")
    else:
        print("⚠️  No autocomplete data returned")
    
    # Test related keywords
    print("\n4. Testing related keywords...")
    related_data = await serpapi_fetch_related_keywords(seed)
    if related_data:
        print("✅ Related keywords working!")
        print(f"   Found {len(related_data)} related keywords")
        if related_data:
            print(f"   Example: {related_data[0].get('keyword', 'N/A')}")
    else:
        print("⚠️  No related keywords returned")
    
    print("\n🎉 SerpApi integration test complete!")
    print("\nNote: If you see '⚠️' warnings, make sure to:")
    print("1. Set SERPAPI_API_KEY in your .env file") 
    print("2. Sign up at https://serpapi.com/ for a free account")
    print("3. Get 100 free searches per month")


if __name__ == "__main__":
    asyncio.run(test_serpapi_integration())