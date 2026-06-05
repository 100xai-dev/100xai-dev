#!/usr/bin/env python3

"""Test Pipeline 2 SERP Analysis with SerpAPI integration."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from app.services.seo_research import serpapi_fetch_serp_for_analysis

async def test_serpapi_serp_fetch():
    """Test SerpAPI SERP fetching for Pipeline 2."""
    print("🔍 Testing SerpAPI SERP Fetch for Pipeline 2")
    print("=" * 50)
    
    # Test keyword
    keyword = "artificial intelligence guide"
    location = "India"
    language = "English"
    device = "mobile"
    
    print(f"📋 Test Parameters:")
    print(f"   Keyword: {keyword}")
    print(f"   Location: {location}")
    print(f"   Language: {language}")
    print(f"   Device: {device}")
    print()
    
    try:
        # Fetch SERP data using SerpAPI
        print("🚀 Fetching SERP data...")
        serp_data = await serpapi_fetch_serp_for_analysis(
            keyword=keyword,
            location_name=location,
            language_name=language,
            device=device
        )
        
        if serp_data:
            print("✅ SerpAPI SERP fetch successful!")
            print(f"📊 Results summary:")
            print(f"   Total results: {serp_data.get('total_results', 'Unknown')}")
            print(f"   Organic results: {len(serp_data.get('organic', []))}")
            print()
            
            # Display top 5 competitors
            organic_results = serp_data.get('organic', [])
            if organic_results:
                print("🎯 Top 5 Competitors Found:")
                for i, result in enumerate(organic_results[:5]):
                    rank = result.get('rank_absolute', i + 1)
                    title = result.get('title', 'No title')[:60]
                    url = result.get('url', 'No URL')[:80]
                    domain = result.get('domain', 'Unknown domain')
                    
                    print(f"   #{rank}. {title}")
                    print(f"        {domain}")
                    print(f"        {url}")
                    print()
                    
                return True
            else:
                print("❌ No organic results found")
                return False
        else:
            print("❌ SerpAPI SERP fetch failed - no data returned")
            return False
            
    except Exception as e:
        print(f"❌ SerpAPI test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🧪 Pipeline 2 - SerpAPI Integration Test")
    print("=" * 60)
    print()
    
    # Test SerpAPI SERP fetching
    serp_success = await test_serpapi_serp_fetch()
    
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   SerpAPI SERP Fetch: {'✅ PASS' if serp_success else '❌ FAIL'}")
    
    if serp_success:
        print("\n🎉 Pipeline 2 SerpAPI Integration: READY!")
        print("   • No more DataForSEO dependency for SERP data")
        print("   • Uses SerpAPI for competitor discovery")
        print("   • Apify still handles competitor page crawling")
        print("   • AI analysis with Anthropic unchanged")
    else:
        print("\n⚠️  Pipeline 2 SerpAPI Integration: NEEDS ATTENTION")
        print("   • Check SERPAPI_API_KEY environment variable")
        print("   • Verify SerpAPI account status")
        
    return serp_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)