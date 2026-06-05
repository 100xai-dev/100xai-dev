#!/usr/bin/env python3
"""
Fix the completed job that didn't save keywords properly
"""

import sys
import os
import asyncio

# Add backend directory to Python path  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.keyword import Keyword
from app.models.onboarding import Job
from app.services.seo_research import run_keyword_research


def update_job_status():
    """Update the job status manually and rerun if needed."""
    print("🛠️ Fixing Completed Job")
    print("=" * 30)
    
    job_id = "5a7a8307-70f4-4e82-ade4-568e9e615df1" 
    brand_id = "f44fcde5-d3c6-4250-a6ec-86b2a06a63a7"
    
    db = next(get_db())
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print("❌ Job not found")
            return False
        
        print(f"Current job status: {job.status}")
        print(f"Current job stage: {job.stage}")
        
        # Check if keywords exist
        keywords = db.query(Keyword).filter(Keyword.job_id == job_id).count()
        print(f"Keywords in database: {keywords}")
        
        if keywords == 0:
            print("\n⚠️  No keywords found - job didn't save results")
            print("This indicates a database transaction or exception during saving")
            
            # Update job to failed so we can retry
            job.status = "FAILED"
            job.error_message = "Keywords not saved to database"
            db.commit()
            print("✅ Updated job status to FAILED so it can be retried")
            
            return False
        else:
            # Keywords exist, just update job status
            job.status = "SUCCEEDED"
            db.commit()
            print("✅ Updated job status to SUCCEEDED")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


async def rerun_keyword_research():
    """Rerun the keyword research pipeline if it didn't save properly."""
    print("\n🔄 Re-running Keyword Research")
    print("=" * 35)
    
    job_id = "5a7a8307-70f4-4e82-ade4-568e9e615df1"
    brand_id = "f44fcde5-d3c6-4250-a6ec-86b2a06a63a7"
    primary_keyword = "cloud computing"
    brand_context = "Tilohri offers pure and natural handcrafted apparel, celebrating tradition..."
    business_description = "Communicate with warmth and authenticity. Emphasize the connection between..."
    
    try:
        print(f"🎯 Running keyword research for: {primary_keyword}")
        print(f"🏢 Brand: {brand_id[:8]}...")
        
        result = await run_keyword_research(
            job_id=job_id,
            brand_id=brand_id,
            primary_keyword=primary_keyword,
            brand_context=brand_context,
            business_description=business_description
        )
        
        print("\n📊 Results:")
        print(f"  Status: {result['status']}")
        print(f"  Total collected: {result.get('total_collected', 0)}")
        print(f"  Final saved: {result.get('final_saved', 0)}")
        
        if result.get('top_keywords'):
            print(f"  Top keywords: {result['top_keywords'][:3]}")
        
        if result['status'] == 'success' and result.get('final_saved', 0) > 0:
            print("\n✅ Keyword research completed successfully!")
            return True
        else:
            print(f"\n❌ Keyword research failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error running keyword research: {e}")
        return False


async def main():
    """Main function to fix the job."""
    print("🔧 Fixing Keyword Research Job Issue")
    print("=" * 50)
    
    # Step 1: Check current status and try to fix
    job_fixed = update_job_status()
    
    if not job_fixed:
        print("\n🔄 Job needs to be rerun - attempting now...")
        
        # Step 2: Rerun the keyword research
        success = await rerun_keyword_research()
        
        if success:
            print("\n🎉 Job fixed! Keywords should now appear in frontend")
            print("\n📱 Next steps:")
            print("1. Refresh the frontend page")
            print("2. Navigate to: /brands/f44fcde5-d3c6-4250-a6ec-86b2a06a63a7/keywords")
            print("3. You should see 'cloud computing' related keywords")
            print("4. Try clicking 'Start SERP Analysis' button for Pipeline 2")
        else:
            print("\n❌ Failed to fix job - check logs for errors")
            
    else:
        print("\n✅ Job status fixed - keywords should appear in frontend")
        print("Refresh the frontend page to see results")


if __name__ == "__main__":
    asyncio.run(main())