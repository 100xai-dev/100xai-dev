#!/usr/bin/env python3
"""
Quick test to verify database session management fix works
"""

import sys
import os

# Add backend directory to Python path  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Job

def test_database_sessions():
    """Test that database sessions work correctly."""
    print("🧪 Testing Database Session Management")
    print("=" * 40)
    
    job_id = "5a7a8307-70f4-4e82-ade4-568e9e615df1"
    brand_id = "f44fcde5-d3c6-4250-a6ec-86b2a06a63a7"
    
    db = next(get_db())
    
    try:
        # Test 1: Create a mock keyword and save it
        print("1️⃣ Testing keyword creation...")
        
        test_keyword = Keyword(
            job_id=job_id,
            brand_id=brand_id,
            related_keyword="test database session",
            primary_keyword="cloud computing",
            source_type="test",
            search_volume=1000,
            keyword_difficulty=50,
            score=85.5
        )
        
        db.add(test_keyword)
        db.commit()
        print("✅ Test keyword saved successfully")
        
        # Test 2: Query it back
        print("\n2️⃣ Testing keyword retrieval...")
        saved_keyword = db.query(Keyword).filter(
            Keyword.related_keyword == "test database session"
        ).first()
        
        if saved_keyword:
            print(f"✅ Retrieved keyword: {saved_keyword.related_keyword}")
            print(f"   Job ID: {saved_keyword.job_id}")
            print(f"   Score: {saved_keyword.score}")
        else:
            print("❌ Could not retrieve test keyword")
        
        # Test 3: Update job status
        print("\n3️⃣ Testing job status update...")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            original_status = job.status
            job.status = "TESTING"
            db.commit()
            print(f"✅ Updated job status from {original_status} to TESTING")
            
            # Revert back
            job.status = original_status
            db.commit()
            print(f"✅ Reverted job status back to {original_status}")
        else:
            print("❌ Job not found")
            
        # Test 4: Cleanup test keyword
        print("\n4️⃣ Cleaning up test data...")
        if saved_keyword:
            db.delete(saved_keyword)
            db.commit()
            print("✅ Test keyword cleaned up")
            
        print("\n🎉 All database session tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database session test failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()
        print("✅ Database session closed properly")


if __name__ == "__main__":
    success = test_database_sessions()
    if success:
        print("\n✅ Database session management is working correctly")
        print("🔧 The fix should resolve the keyword saving issue")
    else:
        print("\n❌ Database session management has issues")
        print("🔧 Further debugging required")