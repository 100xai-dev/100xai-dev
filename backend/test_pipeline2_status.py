#!/usr/bin/env python3
"""
Pipeline 2 Status Check - Show what's working and what needs configuration
"""

import sys
import os
import asyncio

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings


async def check_serpapi():
    """Check SerpAPI configuration and functionality."""
    print("1️⃣ SerpAPI (SERP Data Fetching)")
    print("-" * 40)
    
    settings = get_settings()
    
    if not settings.serpapi_api_key:
        print("❌ SerpAPI not configured")
        print("   💡 Get API key from: https://serpapi.com/")
        print("   🔧 Set SERPAPI_API_KEY in .env file")
        return False
    
    print(f"⚙️  SerpAPI key found: {settings.serpapi_api_key[:10]}...")
    
    try:
        from serpapi import GoogleSearch
        
        # Test with a simple query
        test_params = {
            "engine": "google",
            "q": "artificial intelligence",
            "api_key": settings.serpapi_api_key,
            "num": 3,
            "location": "India"
        }
        
        search = GoogleSearch(test_params)
        result = search.get_dict()
        
        if "error" in result:
            print(f"❌ SerpAPI error: {result['error']}")
            print("   💡 Check your API key at: https://serpapi.com/manage-api-key")
            return False
        
        organic_results = result.get("organic_results", [])
        print(f"✅ SerpAPI working: Found {len(organic_results)} organic results")
        
        if organic_results:
            print(f"   📄 Sample result: {organic_results[0].get('title', 'No title')[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ SerpAPI test failed: {e}")
        return False


async def check_apify_crawling():
    """Check Apify competitor crawling functionality."""
    print("\n2️⃣ Apify (Competitor Page Crawling)")
    print("-" * 40)
    
    settings = get_settings()
    
    if not settings.apify_api_key:
        print("❌ Apify not configured")
        print("   💡 Get API key from: https://console.apify.com/")
        print("   🔧 Set APIFY_API_KEY in .env file")
        return False
    
    print(f"⚙️  Apify key found: {settings.apify_api_key[:10]}...")
    
    try:
        from app.services.seo_research import crawl_competitor_page
        
        # Test with a reliable URL
        test_url = "https://en.wikipedia.org/wiki/Machine_learning"
        print(f"🔄 Testing crawl: {test_url}")
        
        result = await crawl_competitor_page(test_url)
        
        if result["success"]:
            print(f"✅ Apify crawling working: {result['word_count']} words extracted")
            print(f"   ⏱️  Load time: {result.get('load_time_ms', 'N/A')} ms")
            
            if result.get('content'):
                preview = result['content'][:100].replace('\n', ' ')
                print(f"   📝 Content preview: {preview}...")
            
            return True
        else:
            print(f"❌ Apify crawl failed: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ Apify test failed: {e}")
        return False


async def check_llm_analysis():
    """Check LLM-powered competitor analysis."""
    print("\n3️⃣ LLM (AI Competitor Analysis)")
    print("-" * 40)
    
    settings = get_settings()
    
    # Check available LLM APIs
    llm_available = False
    llm_type = None
    
    if settings.anthropic_api_key:
        llm_available = True
        llm_type = "Anthropic Claude"
        print(f"⚙️  Anthropic API key found: {settings.anthropic_api_key[:10]}...")
    elif settings.openai_api_key:
        llm_available = True
        llm_type = "OpenAI"
        print(f"⚙️  OpenAI API key found: {settings.openai_api_key[:10]}...")
    else:
        print("❌ No LLM API configured")
        print("   💡 Get Anthropic key from: https://console.anthropic.com/")
        print("   💡 Get OpenAI key from: https://platform.openai.com/")
        print("   🔧 Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file")
        return False
    
    try:
        from app.services.seo_research import analyze_competitor_content
        
        # Test with mock content
        mock_content = """
        # Machine Learning Guide
        
        Machine learning is a subset of artificial intelligence that focuses on algorithms that improve automatically through experience. This comprehensive guide covers the fundamentals, applications, and best practices for implementing ML solutions in business environments.
        
        ## Key Concepts
        - Supervised Learning
        - Unsupervised Learning  
        - Deep Learning
        - Neural Networks
        
        ## Applications
        - Predictive Analytics
        - Image Recognition
        - Natural Language Processing
        - Recommendation Systems
        """
        
        brand_profile = {
            "one_liner": "AI consulting firm specializing in machine learning implementations",
            "industry": "Technology Consulting",
            "audience_personas": ["Data Scientists", "ML Engineers"], 
            "unique_angle": "Practical ML with business ROI focus"
        }
        
        print(f"🔄 Testing AI analysis with {llm_type}...")
        
        analysis = await analyze_competitor_content(
            content=mock_content,
            keyword="machine learning",
            brand_profile=brand_profile,
            competitor_url="https://example.com/ml-guide",
            competitor_title="Machine Learning Guide"
        )
        
        if analysis and analysis.get("success"):
            print(f"✅ LLM analysis working: Content strength {analysis.get('content_strength', 0):.2f}")
            
            gaps = analysis.get('content_gaps', [])
            if gaps:
                print(f"   🎯 Content gaps identified: {len(gaps)}")
                print(f"   📝 Sample gap: {gaps[0] if gaps else 'None'}")
            
            topics = analysis.get('key_topics', [])
            if topics:
                print(f"   📚 Topics identified: {', '.join(topics[:3])}")
            
            return True
        else:
            print(f"❌ LLM analysis failed: {analysis.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ LLM analysis test failed: {e}")
        return False


async def check_database_integration():
    """Check database tables for Pipeline 2."""
    print("\n4️⃣ Database (SERP Analysis Tables)")
    print("-" * 40)
    
    try:
        from app.db import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Check SERP analysis tables
        tables_to_check = [
            ("serp_analyses", "Main SERP analysis records"),
            ("competitor_analyses", "Individual competitor analysis records")
        ]
        
        all_tables_exist = True
        
        for table_name, description in tables_to_check:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                print(f"✅ {table_name}: {result} records ({description})")
            except Exception as e:
                print(f"❌ {table_name}: Not accessible ({e})")
                all_tables_exist = False
        
        db.close()
        
        if all_tables_exist:
            print("✅ Database schema ready for Pipeline 2")
            return True
        else:
            print("⚠️  Some database tables missing - run alembic migrations")
            return False
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


def show_pipeline2_implementation():
    """Show what's already implemented in Pipeline 2."""
    print("\n📋 Pipeline 2 Implementation Status")
    print("=" * 50)
    
    implemented_features = [
        "✅ SERP data fetching (SerpAPI + DataForSEO fallback)",
        "✅ Competitor page crawling (Apify + in-house fallback)", 
        "✅ AI content analysis (Anthropic + OpenAI)",
        "✅ Content gap identification",
        "✅ Competitive advantage analysis",
        "✅ Database schema for storing results",
        "✅ Worker task integration (RQ queues)",
        "✅ Job dispatcher for automated triggering",
        "✅ Pipeline orchestration from Pipeline 1 keywords"
    ]
    
    print("🏗️  What's Already Built:")
    for feature in implemented_features:
        print(f"   {feature}")
    
    print(f"\n🔧 Configuration Needed:")
    print("   1. SerpAPI key for SERP data (primary)")
    print("   2. Apify key for competitor crawling (primary)")
    print("   3. LLM API key for content analysis (Anthropic or OpenAI)")
    print("   4. DataForSEO account restoration (backup SERP)")
    
    print(f"\n🚀 Ready Features:")
    print("   • Can analyze any keyword's SERP landscape") 
    print("   • Crawls top 10 competitor pages automatically")
    print("   • AI identifies content gaps and opportunities")
    print("   • Stores structured analysis for content planning")
    print("   • Auto-triggers after Pipeline 1 keyword research")


async def main():
    """Main Pipeline 2 status check."""
    print("🔍 Pipeline 2 (SERP Analysis) Status Check")
    print("=" * 50)
    
    # Test each component
    results = {}
    
    results['serpapi'] = await check_serpapi()
    results['apify'] = await check_apify_crawling()  
    results['llm'] = await check_llm_analysis()
    results['database'] = await check_database_integration()
    
    # Show implementation status
    show_pipeline2_implementation()
    
    # Summary
    working_components = sum(results.values())
    total_components = len(results)
    
    print(f"\n📊 Pipeline 2 Status Summary")
    print("=" * 50)
    print(f"✅ Working components: {working_components}/{total_components}")
    
    for component, status in results.items():
        emoji = "✅" if status else "❌"
        print(f"   {emoji} {component.upper()}")
    
    if working_components >= 3:
        print(f"\n🟢 Pipeline 2 is MOSTLY READY!")
        print("   Configure the remaining APIs and you're good to go!")
    elif working_components >= 2:
        print(f"\n🟡 Pipeline 2 is PARTIALLY READY")
        print("   A few more API configurations needed")
    else:
        print(f"\n🔴 Pipeline 2 needs more configuration")
        print("   Set up the missing API keys to test")
    
    print(f"\n🎯 Next Steps:")
    if not results['serpapi']:
        print("   1. Get SerpAPI key: https://serpapi.com/manage-api-key")
    if not results['apify']:
        print("   2. Verify Apify key: https://console.apify.com/")
    if not results['llm']:
        print("   3. Set up LLM API (Anthropic or OpenAI)")
    if not results['database']:
        print("   4. Run database migrations: alembic upgrade head")
    
    if working_components == total_components:
        print("\n🎉 All systems ready! Pipeline 2 can process keywords from Pipeline 1!")


if __name__ == "__main__":
    asyncio.run(main())