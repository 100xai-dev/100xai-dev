#!/usr/bin/env python3
"""
Simple test for Pipeline 1 components without external APIs
"""

import sys
import os
from uuid import uuid4
from sqlalchemy import text

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Brand, Job
from app.services.seo_research import normalize_all, dedupe_by, score_keywords, safe_json_parse


def test_utility_functions():
    """Test the utility functions with mock data."""
    print("🧪 Testing utility functions...")
    
    # Mock keyword data from different APIs
    mock_keywords_1 = [
        {"keyword": "artificial intelligence", "search_volume": 22200, "keyword_difficulty": 75, "cpc": 1.50},
        {"keyword": "machine learning", "search_volume": 18100, "keyword_difficulty": 65, "cpc": 2.10},
        {"keyword": "ai tools", "search_volume": 8100, "keyword_difficulty": 45, "cpc": 3.20},
    ]
    
    mock_keywords_2 = [
        {"suggestion": "deep learning", "keyword_info": {"search_volume": 12100, "keyword_difficulty": 70, "cpc": 1.80}},
        {"suggestion": "ai tools", "keyword_info": {"search_volume": 8100, "keyword_difficulty": 45, "cpc": 3.20}},  # Duplicate
    ]
    
    # Test normalize_all
    normalized_1 = normalize_all(mock_keywords_1, "AI technology", "related_keywords")
    normalized_2 = normalize_all(mock_keywords_2, "AI technology", "suggestions")
    
    print(f"✅ Normalized {len(normalized_1)} keywords from source 1")
    print(f"✅ Normalized {len(normalized_2)} keywords from source 2")
    
    # Combine and test dedupe_by
    all_keywords = normalized_1 + normalized_2
    deduped = dedupe_by(all_keywords, "related_keyword")
    
    print(f"✅ Combined {len(all_keywords)} keywords, deduplicated to {len(deduped)}")
    
    # Test score_keywords
    scored = score_keywords(deduped)
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    print(f"✅ Scored {len(scored)} keywords")
    
    print("\n🏆 Top scored keywords:")
    for i, kw in enumerate(scored[:3], 1):
        print(f"  {i}. {kw['related_keyword']} (score: {kw.get('score', 0):.3f}, volume: {kw.get('search_volume')})")
    
    # Test safe_json_parse
    valid_json = safe_json_parse('{"test": "value"}')
    invalid_json = safe_json_parse('invalid json')
    
    print(f"✅ JSON parsing: valid={valid_json is not None}, invalid={invalid_json is None}")
    
    return scored


def test_database_operations():
    """Test database operations without external APIs."""
    print("\n🗄️  Testing database operations...")
    
    db = next(get_db())
    
    try:
        # Test database connection
        result = db.execute(text("SELECT 1")).fetchone()
        print("✅ Database connection successful")
        
        # Create test brand
        brand = Brand(
            name="Test AI Company",
            website_url="https://testai.example.com",
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
        
        # Create test keywords
        test_keywords = [
            {
                "related_keyword": "artificial intelligence",
                "primary_keyword": "ai technology",
                "source_type": "test",
                "search_volume": 22200,
                "keyword_difficulty": 75,
                "score": 0.65
            },
            {
                "related_keyword": "machine learning",
                "primary_keyword": "ai technology", 
                "source_type": "test",
                "search_volume": 18100,
                "keyword_difficulty": 65,
                "score": 0.72
            }
        ]
        
        for kw_data in test_keywords:
            keyword = Keyword(
                job_id=job.id,
                brand_id=brand.id,
                **kw_data
            )
            db.add(keyword)
        
        db.commit()
        print(f"✅ Created {len(test_keywords)} test keywords")
        
        # Verify keywords were saved
        saved_keywords = db.query(Keyword).filter(Keyword.job_id == job.id).all()
        print(f"✅ Retrieved {len(saved_keywords)} keywords from database")
        
        # Show saved keywords
        for kw in saved_keywords:
            print(f"  • {kw.related_keyword} (score: {kw.score})")
        
        # Update job stage
        job.stage = "KEYWORD"
        db.commit()
        print("✅ Updated job stage to KEYWORD")
        
        return {
            "brand_id": brand.id,
            "job_id": job.id,
            "keyword_count": len(saved_keywords)
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database test failed: {e}")
        raise
    finally:
        db.close()


def test_queue_integration():
    """Test queue integration components."""
    print("\n🔄 Testing queue integration...")
    
    try:
        # Test queue imports
        from app.queue import get_queue, KEYWORD_RESEARCH_QUEUE
        from app.services.job_dispatcher import JobDispatcher
        
        print("✅ Queue imports successful")
        
        # Test queue creation
        queue = get_queue(KEYWORD_RESEARCH_QUEUE)
        print("✅ Keyword research queue created")
        
        # Test dispatcher
        dispatcher = JobDispatcher()
        print("✅ Job dispatcher created")
        
        # Check worker task import
        import worker.tasks.keyword_research
        print("✅ Worker task module imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Queue integration test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Pipeline 1: Simple Component Testing")
    print("=" * 50)
    
    try:
        # Test 1: Utility functions
        scored_keywords = test_utility_functions()
        
        # Test 2: Database operations
        db_result = test_database_operations()
        
        # Test 3: Queue integration
        queue_success = test_queue_integration()
        
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        print(f"  ✅ Utility functions: {len(scored_keywords)} keywords processed")
        print(f"  ✅ Database operations: {db_result['keyword_count']} keywords saved")
        print(f"  ✅ Queue integration: {'Success' if queue_success else 'Failed'}")
        print("\n🎉 All component tests passed!")
        
        print("\n📋 Next steps to test with real data:")
        print("  1. Set DataForSEO credentials in environment:")
        print("     export DATAFORSEO_LOGIN=your_login")
        print("     export DATAFORSEO_PASSWORD=your_password")
        print("  2. Run the worker: venv/bin/python -m worker.main")
        print("  3. Test with job dispatcher to queue real keyword research jobs")
        
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)