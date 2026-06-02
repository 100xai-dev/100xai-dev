#!/usr/bin/env python3
"""
Simple test to verify keyword storage works
"""

import sys
import os
from uuid import uuid4

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Brand


def test_keyword_storage():
    """Test that we can store keywords in the database."""
    print("🧪 Testing keyword storage...")
    
    db = next(get_db())
    
    try:
        # Get existing brand
        brand = db.query(Brand).filter(Brand.status == "READY").first()
        if not brand:
            print("❌ No READY brand found")
            return
            
        print(f"✅ Using brand: {brand.name} (ID: {brand.id})")
        
        # Use real job ID from database
        real_job_id = "113aa181-1f18-4c43-a1a2-48ca7107e6e9"
        print(f"✅ Using real job ID: {real_job_id}")
        
        # Create test keywords
        test_keywords = [
            {
                "job_id": real_job_id,
                "brand_id": brand.id,
                "related_keyword": "artificial intelligence",
                "primary_keyword": "ai technology",
                "source_type": "test",
                "search_volume": 22200,
                "keyword_difficulty": 75,
                "cpc": 1.50,
                "score": 0.65
            },
            {
                "job_id": real_job_id,
                "brand_id": brand.id,
                "related_keyword": "machine learning",
                "primary_keyword": "ai technology",
                "source_type": "test", 
                "search_volume": 18100,
                "keyword_difficulty": 65,
                "cpc": 2.10,
                "score": 0.72
            }
        ]
        
        # Add keywords
        for kw_data in test_keywords:
            keyword = Keyword(**kw_data)
            db.add(keyword)
        
        db.commit()
        print(f"✅ Added {len(test_keywords)} test keywords")
        
        # Verify they were saved
        saved = db.query(Keyword).filter(Keyword.job_id == real_job_id).all()
        print(f"✅ Retrieved {len(saved)} keywords from database")
        
        for kw in saved:
            print(f"  • {kw.related_keyword} (score: {kw.score}, volume: {kw.search_volume})")
        
        # Clean up
        db.query(Keyword).filter(Keyword.job_id == real_job_id).delete()
        db.commit()
        print("✅ Cleaned up test data")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Test failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Simple Keyword Storage Test")
    print("=" * 40)
    
    success = test_keyword_storage()
    
    if success:
        print("\n🎉 ✅ Keyword storage test PASSED!")
        print("\n📋 Pipeline 1 is ready for use. You can:")
        print("  1. Use the dispatcher: JobDispatcher().enqueue_keyword_research(...)")
        print("  2. Run worker to process jobs: venv/bin/python -m worker.main")
        print("  3. Call directly: await run_keyword_research(...)")
    else:
        print("\n❌ Keyword storage test FAILED!")
        sys.exit(1)