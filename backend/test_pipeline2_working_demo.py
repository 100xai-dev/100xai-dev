#!/usr/bin/env python3
"""
Pipeline 2 Working Demo - Test SERP Analysis with working APIs
"""

import sys
import os
import asyncio

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.seo_research import (
    serpapi_fetch_serp_for_analysis,
    crawl_competitor_page,
    analyze_competitor_content
)


def check_pipeline2_apis():
    """Check what APIs are available for Pipeline 2."""
    print("🔍 Checking Pipeline 2 API Status")
    print("-" * 40)
    
    settings = get_settings()
    
    # Check SerpAPI
    if settings.serpapi_api_key:
        print(f"✅ SerpAPI: {settings.serpapi_api_key[:10]}...")
    else:
        print("❌ SerpAPI not configured")
    
    # Check Apify (for competitor crawling)
    if settings.apify_api_key:
        print(f"✅ Apify: {settings.apify_api_key[:10]}...")
    else:
        print("❌ Apify not configured")
    
    # Check LLM (for AI analysis)
    if settings.anthropic_api_key:
        print(f"✅ Anthropic: {settings.anthropic_api_key[:10]}...")
    elif settings.openai_api_key:
        print(f"✅ OpenAI: {settings.openai_api_key[:10]}...")
    else:
        print("❌ No LLM API configured")
    
    # Check DataForSEO (backup SERP)
    if settings.dataforseo_api_key:
        print(f"⚠️  DataForSEO: Account paused (contact support)")
    else:
        print("❌ DataForSEO not available")
    
    return {
        "serpapi": bool(settings.serpapi_api_key),
        "apify": bool(settings.apify_api_key),
        "llm": bool(settings.anthropic_api_key or settings.openai_api_key),
        "dataforseo": False  # Account is paused
    }


async def test_serp_fetching():
    """Test SERP data fetching with available APIs."""
    print("\n🔍 Testing SERP Data Fetching...")
    
    keyword = "artificial intelligence"
    print(f"📝 Target keyword: '{keyword}'")
    
    try:
        # Test SerpAPI for SERP data
        print("🔄 Fetching SERP data with SerpAPI...")
        serp_data = await serpapi_fetch_serp_for_analysis(keyword, "India", "English")
        
        if serp_data and serp_data.get("organic"):
            organic_results = serp_data["organic"]
            print(f"✅ SerpAPI returned {len(organic_results)} organic results")
            
            print("\n🏆 Top 5 SERP Results:")
            print("-" * 80)
            print(f"{'Rank':<4} {'Title':<50} {'Domain':<20}")
            print("-" * 80)
            
            for result in organic_results[:5]:
                rank = result.get("rank_absolute", "N/A")
                title = result.get("title", "No title")[:47]
                domain = result.get("domain", "No domain")[:17]
                print(f"{rank:<4} {title:<50} {domain:<20}")
            
            return serp_data
        else:
            print("❌ No SERP data returned")
            return None
            
    except Exception as e:
        print(f"❌ SERP fetch failed: {e}")
        return None


async def test_competitor_crawling():
    """Test competitor page crawling."""
    print("\n🕷️  Testing Competitor Page Crawling...")
    
    # Test URLs - use reliable sites
    test_urls = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://openai.com/api/",
        "https://www.ibm.com/watson"
    ]
    
    crawl_results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}️⃣ Crawling: {url}")
        try:
            result = await crawl_competitor_page(url)
            
            print(f"   Success: {result['success']}")
            print(f"   Word count: {result.get('word_count', 0)}")
            print(f"   Load time: {result.get('load_time_ms', 'N/A')} ms")
            
            if result['success'] and result.get('content'):
                preview = result['content'][:150].replace('\n', ' ')
                print(f"   Preview: {preview}...")
                crawl_results.append(result)
            else:
                print(f"   Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"   ❌ Crawl failed: {e}")
            
        # Small delay to be polite
        await asyncio.sleep(1)
    
    print(f"\n✅ Successfully crawled {len(crawl_results)}/{len(test_urls)} pages")
    return crawl_results


async def test_ai_competitor_analysis():
    """Test AI-powered competitor content analysis."""
    print("\n🤖 Testing AI Competitor Analysis...")
    
    # Mock competitor content for analysis
    mock_content = """
# The Complete Guide to Artificial Intelligence in 2024

Artificial Intelligence (AI) has become a cornerstone of modern technology, transforming industries from healthcare to finance. This comprehensive guide explores the current state of AI, its applications, and future prospects.

## What is Artificial Intelligence?

AI refers to computer systems that can perform tasks that typically require human intelligence. These tasks include:

- **Machine Learning**: Systems that improve automatically through experience
- **Natural Language Processing**: Understanding and generating human language  
- **Computer Vision**: Interpreting and understanding visual information
- **Robotics**: Physical robots that can interact with the world

## Current AI Applications

### Healthcare
- Medical diagnosis assistance
- Drug discovery acceleration
- Personalized treatment plans
- Medical imaging analysis

### Business
- Customer service automation
- Predictive analytics
- Fraud detection
- Supply chain optimization

### Technology
- Search algorithms
- Recommendation systems
- Voice assistants
- Autonomous vehicles

## Challenges and Considerations

While AI offers tremendous potential, several challenges remain:

1. **Data Privacy**: Protecting user information
2. **Algorithmic Bias**: Ensuring fair and unbiased systems
3. **Job Displacement**: Managing workforce transitions
4. **Regulation**: Developing appropriate governance frameworks

## The Future of AI

Experts predict AI will continue to evolve, with developments in:
- General artificial intelligence (AGI)
- Quantum-enhanced AI
- Edge computing integration
- Ethical AI frameworks

AI will likely become even more integrated into daily life, requiring careful consideration of its societal impacts.
"""

    # Mock brand profile for analysis
    brand_profile = {
        "one_liner": "AI consulting firm helping businesses implement intelligent automation",
        "industry": "Technology Consulting", 
        "audience_personas": ["CTOs", "Tech Directors", "Innovation Leaders"],
        "unique_angle": "Practical AI implementation with ROI focus"
    }
    
    try:
        print("🔄 Analyzing competitor content...")
        analysis = await analyze_competitor_content(
            content=mock_content,
            keyword="artificial intelligence",
            brand_profile=brand_profile,
            competitor_url="https://example.com/ai-guide-2024",
            competitor_title="The Complete Guide to Artificial Intelligence in 2024"
        )
        
        if analysis and analysis.get("success"):
            print("✅ AI analysis successful")
            print(f"\n📊 Analysis Results:")
            print(f"   Content strength: {analysis.get('content_strength', 'N/A')}/1.0")
            print(f"   Target audience: {analysis.get('target_audience', 'N/A')}")
            print(f"   Content tone: {analysis.get('content_tone', 'N/A')}")
            print(f"   Competitive advantage: {analysis.get('competitive_advantage', 'N/A')}")
            
            # Content gaps
            gaps = analysis.get('content_gaps', [])
            if gaps:
                print(f"\n🎯 Content Gaps Identified ({len(gaps)}):")
                for i, gap in enumerate(gaps[:5], 1):
                    print(f"   {i}. {gap}")
            
            # Key topics
            topics = analysis.get('key_topics', [])
            if topics:
                print(f"\n📝 Key Topics Covered:")
                print(f"   {', '.join(topics)}")
            
            return analysis
        else:
            print(f"❌ AI analysis failed: {analysis.get('error', 'Unknown')}")
            return None
            
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return None


async def demo_pipeline2_workflow():
    """Demonstrate the complete Pipeline 2 workflow."""
    print("\n🚀 Pipeline 2 Complete Workflow Demo")
    print("=" * 60)
    
    keyword = "machine learning"
    print(f"🎯 Analyzing keyword: '{keyword}'")
    
    # Step 1: Get SERP data
    print("\n1️⃣ Step 1: Fetch SERP Data")
    serp_data = await serpapi_fetch_serp_for_analysis(keyword)
    
    if not serp_data or not serp_data.get("organic"):
        print("❌ No SERP data available - cannot continue workflow")
        return None
    
    organic_results = serp_data["organic"][:3]  # Top 3 for demo
    print(f"✅ Found {len(organic_results)} competitors to analyze")
    
    # Step 2: Crawl competitor pages
    print("\n2️⃣ Step 2: Crawl Competitor Pages")
    competitor_data = []
    
    for i, result in enumerate(organic_results, 1):
        url = result.get("url", "")
        title = result.get("title", "No title")
        
        print(f"\n   {i}. Crawling: {title[:50]}...")
        print(f"      URL: {url}")
        
        try:
            crawl_result = await crawl_competitor_page(url)
            
            if crawl_result["success"]:
                print(f"      ✅ Success: {crawl_result['word_count']} words")
                competitor_data.append({
                    "rank": result.get("rank_absolute", i),
                    "title": title,
                    "url": url,
                    "domain": result.get("domain", ""),
                    "crawl_result": crawl_result
                })
            else:
                print(f"      ❌ Failed: {crawl_result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Be polite with delays
        await asyncio.sleep(2)
    
    print(f"\n✅ Successfully crawled {len(competitor_data)} competitor pages")
    
    # Step 3: AI Analysis
    print("\n3️⃣ Step 3: AI Competitor Analysis")
    
    brand_profile = {
        "one_liner": "Machine learning consultancy for business transformation",
        "industry": "AI/ML Consulting",
        "audience_personas": ["Data Scientists", "ML Engineers", "Business Leaders"],
        "unique_angle": "End-to-end ML implementation with business impact focus"
    }
    
    analyzed_competitors = []
    
    for i, comp in enumerate(competitor_data, 1):
        print(f"\n   {i}. Analyzing: {comp['title'][:40]}...")
        
        try:
            analysis = await analyze_competitor_content(
                content=comp['crawl_result']['content'],
                keyword=keyword,
                brand_profile=brand_profile,
                competitor_url=comp['url'],
                competitor_title=comp['title']
            )
            
            if analysis and analysis.get("success"):
                print(f"      ✅ Content strength: {analysis.get('content_strength', 0):.2f}")
                print(f"      🎯 Gaps found: {len(analysis.get('content_gaps', []))}")
                
                comp['analysis'] = analysis
                analyzed_competitors.append(comp)
            else:
                print(f"      ❌ Analysis failed")
                
        except Exception as e:
            print(f"      ❌ Analysis error: {e}")
    
    # Step 4: Generate insights
    print("\n4️⃣ Step 4: Generate Content Opportunities")
    
    if analyzed_competitors:
        print(f"✅ Analyzed {len(analyzed_competitors)} competitors")
        
        # Aggregate content gaps
        all_gaps = []
        total_strength = 0
        
        for comp in analyzed_competitors:
            analysis = comp['analysis']
            all_gaps.extend(analysis.get('content_gaps', []))
            total_strength += analysis.get('content_strength', 0)
        
        # Find most common gaps
        gap_counts = {}
        for gap in all_gaps:
            gap_counts[gap] = gap_counts.get(gap, 0) + 1
        
        common_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)
        avg_strength = total_strength / len(analyzed_competitors) if analyzed_competitors else 0
        
        print(f"\n📊 Content Opportunity Analysis:")
        print(f"   Average competitor content strength: {avg_strength:.2f}/1.0")
        print(f"   Total content gaps identified: {len(all_gaps)}")
        
        if common_gaps:
            print(f"\n🎯 Top Content Opportunities:")
            for i, (gap, count) in enumerate(common_gaps[:5], 1):
                print(f"   {i}. {gap} (missing in {count}/{len(analyzed_competitors)} competitors)")
        
        return {
            "keyword": keyword,
            "serp_results": len(organic_results),
            "crawled_pages": len(competitor_data),
            "analyzed_competitors": len(analyzed_competitors),
            "avg_content_strength": avg_strength,
            "content_gaps": len(all_gaps),
            "top_opportunities": [gap for gap, count in common_gaps[:5]]
        }
    else:
        print("❌ No competitors successfully analyzed")
        return None


async def main():
    """Main Pipeline 2 demo."""
    print("🚀 Pipeline 2 (SERP Analysis) Working Demo")
    print("=" * 50)
    
    # Check API status
    apis = check_pipeline2_apis()
    
    if not any([apis["serpapi"], apis["apify"], apis["llm"]]):
        print("\n❌ No working APIs found for Pipeline 2")
        print("   Configure SerpAPI, Apify, and LLM APIs to test Pipeline 2")
        return
    
    print(f"\n✅ Available APIs: {sum(apis.values())}/4")
    
    try:
        # Test individual components
        print("\n" + "="*50)
        print("COMPONENT TESTS")
        print("="*50)
        
        # Test SERP fetching
        serp_data = await test_serp_fetching()
        
        # Test competitor crawling
        crawl_results = await test_competitor_crawling()
        
        # Test AI analysis
        analysis_result = await test_ai_competitor_analysis()
        
        # Demo complete workflow
        print("\n" + "="*50)
        print("COMPLETE WORKFLOW DEMO")
        print("="*50)
        
        workflow_result = await demo_pipeline2_workflow()
        
        # Final summary
        print("\n" + "="*50)
        print("🎉 Pipeline 2 Demo Results")
        print("="*50)
        
        print(f"✅ SERP fetching: {'Working' if serp_data else 'Failed'}")
        print(f"✅ Competitor crawling: {'Working' if crawl_results else 'Failed'}")
        print(f"✅ AI analysis: {'Working' if analysis_result else 'Failed'}")
        print(f"✅ Complete workflow: {'Working' if workflow_result else 'Failed'}")
        
        if workflow_result:
            print(f"\n📈 Workflow Performance:")
            print(f"   Keyword analyzed: {workflow_result['keyword']}")
            print(f"   SERP results found: {workflow_result['serp_results']}")
            print(f"   Pages crawled: {workflow_result['crawled_pages']}")
            print(f"   Competitors analyzed: {workflow_result['analyzed_competitors']}")
            print(f"   Content gaps found: {workflow_result['content_gaps']}")
            print(f"   Avg competitor strength: {workflow_result['avg_content_strength']:.2f}")
            
            if workflow_result['top_opportunities']:
                print(f"\n🎯 Top Content Opportunities:")
                for i, opp in enumerate(workflow_result['top_opportunities'], 1):
                    print(f"   {i}. {opp}")
        
        print(f"\n💡 Pipeline 2 Status: {'🟢 Ready for Production' if workflow_result else '🟡 Needs API Configuration'}")
        
    except Exception as e:
        print(f"\n❌ Pipeline 2 demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())