#!/usr/bin/env python3
"""
Debug why frontend shows no keywords despite successful Pipeline 1
"""

import sys
import os
from sqlalchemy import text

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Job, Brand


def check_database_keywords():
    """Check if keywords were actually saved to the database."""
    print("🔍 Checking Database for Keywords")
    print("=" * 40)
    
    db = next(get_db())
    
    try:
        # Check recent jobs
        print("1️⃣ Recent keyword research jobs:")
        recent_jobs = db.query(Job).filter(
            Job.job_type == "keyword_research"
        ).order_by(Job.created_at.desc()).limit(5).all()
        
        if not recent_jobs:
            print("❌ No keyword research jobs found!")
            return False
        
        for job in recent_jobs:
            print(f"   • Job {job.id[:8]}... | Status: {job.status} | Brand: {job.brand_id[:8]}... | Created: {job.created_at}")
        
        # Check the specific job from the logs
        job_id = "5a7a8307-70f4-4e82-ade4-568e9e615df1"
        brand_id = "f44fcde5-d3c6-4250-a6ec-86b2a06a63a7"
        
        print(f"\n2️⃣ Checking specific job from logs:")
        print(f"   Job ID: {job_id}")
        print(f"   Brand ID: {brand_id}")
        
        # Check if job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            print(f"✅ Job found: {job.status} | Stage: {job.stage}")
        else:
            print("❌ Job not found in database")
            return False
        
        # Check if brand exists
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            print(f"✅ Brand found: {brand.name} | Status: {brand.status}")
        else:
            print("❌ Brand not found in database")
            return False
        
        # Check keywords for this brand/job
        print(f"\n3️⃣ Checking keywords for brand {brand.name}:")
        
        # Keywords by brand
        brand_keywords = db.query(Keyword).filter(
            Keyword.brand_id == brand_id
        ).all()
        print(f"   Total keywords for brand: {len(brand_keywords)}")
        
        # Keywords by job
        job_keywords = db.query(Keyword).filter(
            Keyword.job_id == job_id
        ).all()
        print(f"   Keywords for this job: {len(job_keywords)}")
        
        if job_keywords:
            print(f"✅ Keywords found! Sample keywords:")
            for i, kw in enumerate(job_keywords[:5], 1):
                print(f"   {i}. {kw.related_keyword} | Score: {kw.score} | Source: {kw.source_type}")
            return True
        else:
            print("❌ No keywords found for this job")
            
            # Check if there are any keywords at all
            total_keywords = db.query(Keyword).count()
            print(f"   Total keywords in database: {total_keywords}")
            
            if total_keywords > 0:
                print("   Sample keywords from other jobs:")
                sample_keywords = db.query(Keyword).limit(3).all()
                for kw in sample_keywords:
                    print(f"   • {kw.related_keyword} (Brand: {kw.brand_id[:8]}...)")
            
            return False
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        db.close()


def check_job_status_flow():
    """Check if the job status flow is working correctly."""
    print("\n🔄 Checking Job Status Flow")
    print("=" * 40)
    
    db = next(get_db())
    
    try:
        job_id = "5a7a8307-70f4-4e82-ade4-568e9e615df1"
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print("❌ Job not found")
            return False
        
        print(f"Job Status: {job.status}")
        print(f"Job Stage: {job.stage}")
        print(f"Created: {job.created_at}")
        print(f"Updated: {job.updated_at}")
        
        # Check what the frontend expects
        if job.status == "SUCCEEDED":
            print("✅ Job marked as SUCCEEDED - frontend should show completed")
        elif job.status == "FAILED":
            print("❌ Job marked as FAILED - frontend should show error")
        elif job.status in ["QUEUED", "PROCESSING"]:
            print("⏳ Job still processing - frontend should show loading")
        else:
            print(f"⚠️  Unknown job status: {job.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking job status: {e}")
        return False
    finally:
        db.close()


def check_api_response_format():
    """Simulate what the frontend API call should return."""
    print("\n📡 Simulating Frontend API Call")
    print("=" * 40)
    
    brand_id = "f44fcde5-d3c6-4250-a6ec-86b2a06a63a7"
    
    db = next(get_db())
    
    try:
        # Simulate GET /v1/brands/{brand_id}/keywords
        keywords = db.query(Keyword).filter(
            Keyword.brand_id == brand_id
        ).order_by(Keyword.score.desc().nullslast()).limit(50).all()
        
        # Simulate GET /v1/brands/{brand_id}/keywords/stats
        total_keywords = len(keywords)
        avg_volume = sum(k.search_volume for k in keywords if k.search_volume) / len([k for k in keywords if k.search_volume]) if any(k.search_volume for k in keywords) else None
        avg_difficulty = sum(k.keyword_difficulty for k in keywords if k.keyword_difficulty) / len([k for k in keywords if k.keyword_difficulty]) if any(k.keyword_difficulty for k in keywords) else None
        
        # Get latest job
        latest_job = db.query(Job).filter(
            Job.brand_id == brand_id,
            Job.job_type == "keyword_research"
        ).order_by(Job.created_at.desc()).first()
        
        print(f"API Response would be:")
        print(f"  Keywords: {len(keywords)}")
        print(f"  Avg Volume: {avg_volume}")
        print(f"  Avg Difficulty: {avg_difficulty}")
        print(f"  Latest Job: {latest_job.id[:8]}... ({latest_job.status})" if latest_job else "No job")
        print(f"  Research Status: {'completed' if latest_job and latest_job.status == 'SUCCEEDED' else 'processing' if latest_job else 'never_run'}")
        
        if keywords:
            print(f"\n  Sample keywords that should appear:")
            for i, kw in enumerate(keywords[:3], 1):
                print(f"    {i}. {kw.related_keyword} (score: {kw.score})")
        else:
            print(f"\n  ❌ No keywords to display - this is why frontend is empty!")
        
        return len(keywords) > 0
        
    except Exception as e:
        print(f"❌ Error simulating API response: {e}")
        return False
    finally:
        db.close()


def suggest_fixes():
    """Suggest potential fixes for the issue."""
    print("\n🛠️ Potential Fixes")
    print("=" * 40)
    
    print("1. ✅ Check if worker completed successfully:")
    print("   - Job says 'Successfully completed' in logs")
    print("   - But keywords might not be saved to database")
    
    print("\n2. 🔄 Refresh the frontend page:")
    print("   - Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)")
    print("   - Check browser console for API errors")
    
    print("\n3. 🔍 Check browser network tab:")
    print("   - Open DevTools → Network")
    print("   - Look for API calls to /keywords")
    print("   - Check if they return 200 OK with data")
    
    print("\n4. 🚀 Restart backend and try again:")
    print("   - Backend might have crashed after job completion")
    print("   - Restart: python -m uvicorn app.main:app --reload")
    
    print("\n5. 📱 Check correct brand ID in URL:")
    print("   - URL should be: /brands/f44fcde5-d3c6-4250-a6ec-86b2a06a63a7/keywords")
    print("   - Make sure you're looking at the right brand")
    
    print("\n6. 🔐 Authentication issues:")
    print("   - Make sure you're logged in")
    print("   - JWT token might have expired")


def main():
    """Main debug function."""
    print("🐛 Debugging Frontend Keywords Display Issue")
    print("=" * 50)
    
    # Step 1: Check database
    keywords_exist = check_database_keywords()
    
    # Step 2: Check job status
    job_status_ok = check_job_status_flow()
    
    # Step 3: Simulate API response
    api_response_ok = check_api_response_format()
    
    # Step 4: Provide solutions
    suggest_fixes()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    
    if keywords_exist:
        print("✅ Keywords exist in database")
        if job_status_ok:
            print("✅ Job status is correct")
            print("🔍 Issue is likely in frontend API calls or authentication")
        else:
            print("⚠️  Job status might be wrong")
    else:
        print("❌ No keywords in database - worker didn't save results")
        print("🔍 Issue is in the keyword research pipeline saving data")
    
    print(f"\n💡 Most likely cause:")
    if not keywords_exist:
        print("   Worker completed but didn't save keywords to database")
        print("   Check worker logs for database connection issues")
    else:
        print("   Frontend API authentication or brand ID mismatch")
        print("   Check browser console and network requests")


if __name__ == "__main__":
    main()