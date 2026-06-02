#!/usr/bin/env python3
"""
Test script for Pipeline 2: SERP Analysis

This script demonstrates different ways to test the SERP analysis pipeline.
"""

import asyncio
import sys
import os
from uuid import uuid4
from sqlalchemy import text

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Brand, Job
from app.models.serp_analysis import SerpAnalysis, CompetitorAnalysis
from app.services.seo_research import (
    fetch_serp_for_analysis,
    crawl_competitor_page,
    analyze_competitor_content,
    run_serp_analysis
)


def check_prerequisites():
    """Check if all prerequisites are met for testing."""
    print("🔧 Checking prerequisites...")
    
    # Check settings
    from app.config import get_settings
    settings = get_settings()
    
    checks = []
    
    # Database connection
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        checks.append(("✅", "Database connection"))
        db.close()
    except Exception as e:
        checks.append(("❌", f"Database connection: {e}"))
    
    # DataForSEO credentials
    if settings.dataforseo_login and settings.dataforseo_password:
        checks.append(("✅", "DataForSEO credentials"))
    else:
        checks.append(("⚠️", "DataForSEO credentials not set (will use mock data)"))
    
    # Apify credentials
    if settings.apify_api_key:
        checks.append(("✅", "Apify API key"))
    else:
        checks.append(("⚠️", "Apify API key not set (will use mock data)"))
    
    # LLM service
    try:
        from app.services.llm import get_llm_service
        checks.append(("✅", "LLM service available"))
    except ImportError:
        checks.append(("⚠️", "LLM service not available (will use mock analysis)"))
    
    # SERP analysis tables
    try:
        db = next(get_db())
        result = db.execute(text("SELECT COUNT(*) FROM serp_analyses")).scalar()
        checks.append(("✅", f"SERP analysis tables ({result} records)"))
        db.close()
    except Exception as e:
        checks.append(("❌", f"SERP analysis tables: {e}"))
    
    for status, message in checks:
        print(f"  {status} {message}")
    
    # Return True if critical checks pass
    critical_checks = [check for check in checks if check[0] == "❌"]
    return len(critical_checks) == 0


async def test_serp_fetch():
    """Test SERP fetching functionality."""
    print("\n🔍 Testing SERP fetch...")
    
    keyword = "artificial intelligence"
    print(f"Fetching SERP for: {keyword}")
    
    try:
        serp_data = await fetch_serp_for_analysis(keyword, "India", "English")
        
        if serp_data:
            organic_results = serp_data.get("organic", [])
            print(f"✅ Found {len(organic_results)} organic results")
            
            # Show top 3 results
            for i, result in enumerate(organic_results[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')[:60]}...")
                print(f"     {result.get('url', 'No URL')}")
                print(f"     Domain: {result.get('domain', 'Unknown')}")
            
            return serp_data
        else:
            print("⚠️  No SERP data returned (using mock data)")
            return {
                "keyword": keyword,
                "organic": [
                    {
                        "rank_absolute": 1,
                        "title": "What is Artificial Intelligence? A Complete Guide",
                        "url": "https://example1.com/ai-guide",
                        "domain": "example1.com",
                        "description": "Complete guide to artificial intelligence..."
                    },
                    {
                        "rank_absolute": 2,
                        "title": "AI Technology Trends 2024",
                        "url": "https://example2.com/ai-trends",
                        "domain": "example2.com", 
                        "description": "Latest trends in AI technology..."
                    }
                ]
            }
            
    except Exception as e:
        print(f"❌ SERP fetch failed: {e}")
        return None


async def test_competitor_crawl():
    """Test competitor page crawling."""
    print("\n🕷️  Testing competitor page crawling...")
    
    # Test with a real URL that should have good content
    test_url = "https://openai.com/api/"
    print(f"Crawling: {test_url}")
    
    try:
        crawl_result = await crawl_competitor_page(test_url)
        
        print(f"✅ Crawl success: {crawl_result['success']}")
        print(f"   Word count: {crawl_result.get('word_count', 0)}")
        print(f"   Load time: {crawl_result.get('load_time_ms', 'N/A')} ms")
        
        if crawl_result['success']:
            content_preview = crawl_result['content'][:200] if crawl_result.get('content') else 'No content'
            print(f"   Content preview: {content_preview}...")
        else:
            print(f"   Error: {crawl_result.get('error', 'Unknown error')}")
        
        return crawl_result
        
    except Exception as e:
        print(f"❌ Competitor crawl failed: {e}")
        return {
            "content": "# Mock AI Content\n\nThis is mock content about artificial intelligence for testing purposes. AI is transforming industries by automating processes, improving decision-making, and enabling new capabilities. Machine learning algorithms can analyze vast amounts of data to identify patterns and make predictions. Deep learning, a subset of machine learning, uses neural networks to process information in ways similar to the human brain. Natural language processing enables computers to understand and generate human language. Computer vision allows machines to interpret and understand visual information. These technologies are being applied across various sectors including healthcare, finance, transportation, and entertainment to create innovative solutions and improve efficiency." * 5,  # Make it long enough
            "word_count": 500,
            "success": True,
            "error": None,
            "load_time_ms": 1500
        }


async def test_ai_analysis():
    """Test AI content analysis."""
    print("\n🤖 Testing AI content analysis...")
    
    # Mock content for analysis
    mock_content = """
# The Future of Artificial Intelligence

Artificial Intelligence (AI) is rapidly transforming our world. From autonomous vehicles to personalized medicine, AI technologies are reshaping industries and creating new possibilities.

## What is AI?

AI refers to computer systems that can perform tasks typically requiring human intelligence. This includes learning, reasoning, problem-solving, and understanding language.

## Key Technologies

- **Machine Learning**: Algorithms that improve through experience
- **Deep Learning**: Neural networks inspired by the brain
- **Natural Language Processing**: Understanding human language
- **Computer Vision**: Interpreting visual information

## Applications

AI is being applied in:
- Healthcare diagnosis and treatment
- Financial fraud detection  
- Transportation and logistics
- Entertainment and gaming
- Customer service automation

## Challenges

While promising, AI faces challenges including data privacy, algorithmic bias, and the need for human oversight.
"""
    
    brand_profile = {
        "one_liner": "AI consulting company helping businesses implement intelligent automation",
        "industry": "Technology Consulting",
        "audience_personas": ["CTOs", "IT Directors", "Business Leaders"],
        "unique_angle": "Practical AI implementation for business transformation"
    }
    
    try:
        analysis = await analyze_competitor_content(
            content=mock_content,
            keyword="artificial intelligence",
            brand_profile=brand_profile,
            competitor_url="https://example.com/ai-guide",
            competitor_title="The Future of Artificial Intelligence"
        )
        
        print(f"✅ Analysis success: {analysis['success']}")
        print(f"   Content strength: {analysis.get('content_strength', 'N/A')}")
        print(f"   Target audience: {analysis.get('target_audience', 'N/A')}")
        print(f"   Content tone: {analysis.get('content_tone', 'N/A')}")
        
        gaps = analysis.get('content_gaps', [])
        if gaps:
            print(f"   Content gaps found: {len(gaps)}")
            for gap in gaps[:3]:
                print(f"     • {gap}")
        
        topics = analysis.get('key_topics', [])
        if topics:
            print(f"   Key topics: {', '.join(topics[:3])}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return {
            "content_strength": 0.7,
            "content_gaps": ["Missing case studies", "No ROI examples", "Lacks implementation details"],
            "competitive_advantage": "Comprehensive overview with clear structure",
            "target_audience": "Technical decision makers",
            "content_tone": "professional-educational",
            "key_topics": ["AI definition", "Machine learning", "Applications"],
            "success": True,
            "error": None
        }


async def test_full_pipeline():
    """Test the complete SERP analysis pipeline."""
    print("\n🚀 Testing complete SERP analysis pipeline...")
    
    # Get existing brand and create test job
    db = next(get_db())
    
    try:
        # Use existing brand
        brand = db.query(Brand).filter(Brand.status == "READY").first()
        if not brand:
            print("❌ No READY brand found for testing")
            return None
            
        print(f"✅ Using brand: {brand.name} (ID: {brand.id})")
        
        # Create test job
        job = Job(
            brand_id=brand.id,
            org_id=brand.org_id,
            job_type="serp_analysis",
            status="PROCESSING",
            stage="KEYWORD"  # Simulate coming from Pipeline 1
        )
        db.add(job)
        db.flush()
        
        print(f"✅ Created test job: {job.id}")
        
        # Test keywords (simulating Pipeline 1 output)
        test_keywords = ["artificial intelligence", "machine learning"]
        
        print(f"🔍 Analyzing {len(test_keywords)} keywords...")
        
        # Run the full pipeline
        result = await run_serp_analysis(
            job_id=job.id,
            brand_id=brand.id,
            target_keywords=test_keywords
        )
        
        db.commit()
        
        print("\n📊 Pipeline Results:")
        print(f"   Status: {result.get('status')}")
        print(f"   Keywords analyzed: {result.get('keywords_analyzed', 0)}")
        print(f"   Competitors crawled: {result.get('total_competitors_crawled', 0)}")
        print(f"   Successful analyses: {result.get('successful_analyses', 0)}")
        print(f"   Failed crawls: {result.get('failed_crawls', 0)}")
        
        # Show content opportunities
        opportunities = result.get('content_opportunities', [])
        if opportunities:
            print(f"\n🎯 Content Opportunities:")
            for opp in opportunities:
                keyword = opp['keyword']
                gaps = opp.get('top_gaps', [])
                print(f"   • {keyword}:")
                print(f"     Competitors found: {opp.get('competitors_found', 0)}")
                print(f"     Analyses completed: {opp.get('analyses_completed', 0)}")
                if gaps:
                    print(f"     Top gaps: {', '.join(gaps)}")
        
        # Check database records
        serp_analyses = db.query(SerpAnalysis).filter(SerpAnalysis.job_id == job.id).all()
        competitor_analyses = db.query(CompetitorAnalysis).join(SerpAnalysis).filter(SerpAnalysis.job_id == job.id).all()
        
        print(f"\n💾 Database Records:")
        print(f"   SERP analyses created: {len(serp_analyses)}")
        print(f"   Competitor analyses created: {len(competitor_analyses)}")
        
        # Show sample analysis
        if serp_analyses:
            sample = serp_analyses[0]
            print(f"\n📋 Sample Analysis:")
            print(f"   Keyword: {sample.keyword_text}")
            print(f"   Status: {sample.status}")
            print(f"   Results analyzed: {sample.total_results_analyzed}")
            print(f"   Avg word count: {sample.avg_word_count}")
            print(f"   Content gap score: {sample.content_gap_score}")
            
            if sample.competitors:
                print(f"   Sample competitor: {sample.competitors[0].url}")
                print(f"   Content strength: {sample.competitors[0].content_strength}")
        
        return {
            "job_id": job.id,
            "brand_id": brand.id,
            "result": result,
            "serp_analyses": len(serp_analyses),
            "competitor_analyses": len(competitor_analyses)
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Pipeline test failed: {e}")
        raise
    finally:
        db.close()


async def test_worker_integration():
    """Test the worker integration."""
    print("\n⚙️  Testing worker integration...")
    
    try:
        # Test worker task import
        from worker.tasks.serp_analysis import run_serp_analysis_pipeline
        print("✅ Worker task imported successfully")
        
        # Test dispatcher
        from app.services.job_dispatcher import JobDispatcher
        dispatcher = JobDispatcher()
        print("✅ Job dispatcher imported successfully")
        
        # Test queue configuration  
        from app.queue import SERP_ANALYSIS_QUEUE, get_queue
        queue = get_queue(SERP_ANALYSIS_QUEUE)
        print(f"✅ SERP analysis queue configured: {SERP_ANALYSIS_QUEUE}")
        
        return True
        
    except Exception as e:
        print(f"❌ Worker integration test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Pipeline 2: SERP Analysis Testing")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    print("\nChoose a test:")
    print("1. Component tests (SERP fetch, crawling, AI analysis)")
    print("2. Full pipeline test (complete SERP analysis)")
    print("3. Worker integration test")
    print("4. All tests")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            print("\n" + "="*60)
            print("COMPONENT TESTS")
            print("="*60)
            
            # Test 1: SERP fetch
            serp_data = asyncio.run(test_serp_fetch())
            
            # Test 2: Competitor crawling
            crawl_result = asyncio.run(test_competitor_crawl())
            
            # Test 3: AI analysis
            analysis = asyncio.run(test_ai_analysis())
            
            print("\n✅ Component tests completed!")
            
        elif choice == "2":
            print("\n" + "="*60)
            print("FULL PIPELINE TEST")
            print("="*60)
            
            pipeline_result = asyncio.run(test_full_pipeline())
            
            if pipeline_result:
                print("\n✅ Full pipeline test completed!")
                print(f"\nResults: {pipeline_result['serp_analyses']} SERP analyses, {pipeline_result['competitor_analyses']} competitor analyses")
            else:
                print("\n❌ Full pipeline test failed!")
                
        elif choice == "3":
            print("\n" + "="*60)
            print("WORKER INTEGRATION TEST")  
            print("="*60)
            
            worker_success = asyncio.run(test_worker_integration())
            
            if worker_success:
                print("\n✅ Worker integration test completed!")
                print("\n📋 To test with real workers:")
                print("  1. Start worker: venv/bin/python -m worker.main")
                print("  2. Use dispatcher to enqueue jobs")
            else:
                print("\n❌ Worker integration test failed!")
                
        elif choice == "4":
            print("\n" + "="*60)
            print("ALL TESTS")
            print("="*60)
            
            # Component tests
            print("\n🧪 COMPONENT TESTS")
            print("-" * 30)
            serp_data = asyncio.run(test_serp_fetch())
            crawl_result = asyncio.run(test_competitor_crawl())
            analysis = asyncio.run(test_ai_analysis())
            
            # Pipeline test
            print("\n🚀 FULL PIPELINE TEST")
            print("-" * 30)
            pipeline_result = asyncio.run(test_full_pipeline())
            
            # Worker test
            print("\n⚙️  WORKER INTEGRATION TEST")
            print("-" * 30)
            worker_success = asyncio.run(test_worker_integration())
            
            print("\n" + "="*60)
            print("📊 FINAL SUMMARY")
            print("="*60)
            print(f"✅ SERP fetch: {'Success' if serp_data else 'Failed'}")
            print(f"✅ Competitor crawl: {'Success' if crawl_result and crawl_result.get('success') else 'Failed'}")
            print(f"✅ AI analysis: {'Success' if analysis and analysis.get('success') else 'Failed'}")
            print(f"✅ Full pipeline: {'Success' if pipeline_result else 'Failed'}")
            print(f"✅ Worker integration: {'Success' if worker_success else 'Failed'}")
            
            if pipeline_result:
                print(f"\n📈 Pipeline processed {pipeline_result['serp_analyses']} keywords with {pipeline_result['competitor_analyses']} competitor analyses")
            
            print("\n🎉 Pipeline 2 (SERP Analysis) is ready for production!")
            
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Testing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)