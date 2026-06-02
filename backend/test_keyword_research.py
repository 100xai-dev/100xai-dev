#!/usr/bin/env python3
"""
Test script for Pipeline 1: Keyword Research

This script demonstrates different ways to test the keyword research pipeline.
"""

import asyncio
import sys
import os
from uuid import uuid4

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.db import get_db
from app.models.onboarding import Brand, Job
from app.models.keyword import Keyword
from app.services.seo_research import run_keyword_research
from app.services.job_dispatcher import JobDispatcher


def test_direct_function():
    """Test the keyword research function directly (fastest way to test)."""
    print("🧪 Testing keyword research function directly...")
    
    # Create test data
    job_id = str(uuid4())
    brand_id = str(uuid4())
    primary_keyword = "artificial intelligence"
    brand_context = "AI software company focused on business automation"
    business_description = "We build AI tools for enterprise automation and workflow optimization"
    
    print(f"Job ID: {job_id}")
    print(f"Brand ID: {brand_id}")
    print(f"Primary keyword: {primary_keyword}")
    print()
    
    async def run_test():
        result = await run_keyword_research(
            job_id=job_id,
            brand_id=brand_id,
            primary_keyword=primary_keyword,
            brand_context=brand_context,
            business_description=business_description
        )
        return result
    
    # Run the test
    result = asyncio.run(run_test())
    
    print("📊 Results:")
    print(f"Status: {result.get('status')}")
    print(f"Total collected: {result.get('total_collected', 0)}")
    print(f"After deduplication: {result.get('after_deduplication', 0)}")
    print(f"After AI filtering: {result.get('after_ai_filtering', 0)}")
    print(f"Final saved: {result.get('final_saved', 0)}")
    
    if result.get('top_keywords'):
        print("\n🏆 Top 10 keywords:")
        for i, keyword in enumerate(result['top_keywords'][:10], 1):
            print(f"  {i}. {keyword}")
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    
    return result


def test_with_database():
    """Test with actual database records (creates brand and job)."""
    print("\n🗄️  Testing with database records...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test brand
        brand = Brand(
            name="TestAI Corp",
            website_url="https://testai.com",
            status="APPROVED"  # Set to approved so we can use it
        )
        db.add(brand)
        db.flush()  # Get the ID
        
        # Create test job
        job = Job(
            brand_id=brand.id,
            job_type="keyword_research",
            status="NEW",
            stage="NEW"
        )
        db.add(job)
        db.flush()  # Get the ID
        
        db.commit()
        
        print(f"Created brand: {brand.id} ({brand.name})")
        print(f"Created job: {job.id}")
        
        # Run keyword research
        result = asyncio.run(run_keyword_research(
            job_id=job.id,
            brand_id=brand.id,
            primary_keyword="machine learning",
            brand_context="AI/ML consulting company",
            business_description="Machine learning consulting and model development services"
        ))
        
        print("\n📊 Database Test Results:")
        print(f"Status: {result.get('status')}")
        print(f"Keywords saved: {result.get('final_saved', 0)}")
        
        # Check database for saved keywords
        keyword_count = db.query(Keyword).filter(Keyword.job_id == job.id).count()
        print(f"Keywords in database: {keyword_count}")
        
        # Show some sample keywords
        sample_keywords = db.query(Keyword).filter(Keyword.job_id == job.id).order_by(Keyword.score.desc()).limit(5).all()
        if sample_keywords:
            print("\n🔍 Sample saved keywords:")
            for kw in sample_keywords:
                print(f"  • {kw.related_keyword} (score: {kw.score}, volume: {kw.search_volume})")
        
        # Check job status
        db.refresh(job)
        print(f"\nJob stage updated to: {job.stage}")
        
        return {
            "brand_id": brand.id,
            "job_id": job.id,
            "result": result,
            "keyword_count": keyword_count
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database test failed: {e}")
        raise
    finally:
        db.close()


def test_queue_dispatch():
    """Test via the queue dispatcher (most realistic test)."""
    print("\n🔄 Testing via queue dispatcher...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test brand and job
        brand = Brand(
            name="QueueTest AI",
            website_url="https://queuetest.ai",
            status="APPROVED"
        )
        db.add(brand)
        db.flush()
        
        job = Job(
            brand_id=brand.id,
            job_type="keyword_research",
            status="NEW",
            stage="NEW"
        )
        db.add(job)
        db.flush()
        
        db.commit()
        
        print(f"Created brand: {brand.id} ({brand.name})")
        print(f"Created job: {job.id}")
        
        # Dispatch to queue
        dispatcher = JobDispatcher()
        dispatcher.enqueue_keyword_research(
            job_id=job.id,
            brand_id=brand.id,
            primary_keyword="natural language processing",
            brand_context="NLP technology company",
            business_description="Natural language processing tools and APIs"
        )
        
        print("✅ Job dispatched to keyword research queue")
        print("🔍 To check if it processed, run:")
        print(f"   psql -h localhost -p 5432 -U 100xai -d 100xai -c \"SELECT COUNT(*) FROM keywords WHERE job_id = '{job.id}';\"")
        print("   (You need to run the worker to process the job)")
        
        return {
            "brand_id": brand.id,
            "job_id": job.id,
            "message": "Job queued successfully"
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Queue test failed: {e}")
        raise
    finally:
        db.close()


def check_prerequisites():
    """Check if all prerequisites are met for testing."""
    print("🔧 Checking prerequisites...")
    
    # Check settings
    settings = get_settings()
    
    checks = []
    
    # Database connection
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        checks.append(("✅", "Database connection"))
        db.close()
    except Exception as e:
        checks.append(("❌", f"Database connection: {e}"))
    
    # DataForSEO credentials
    if settings.dataforseo_login and settings.dataforseo_password:
        checks.append(("✅", "DataForSEO credentials"))
    else:
        checks.append(("❌", "DataForSEO credentials not set"))
    
    # Redis connection
    try:
        from app.queue import get_redis
        redis = get_redis()
        redis.ping()
        checks.append(("✅", "Redis connection"))
    except Exception as e:
        checks.append(("❌", f"Redis connection: {e}"))
    
    for status, message in checks:
        print(f"  {status} {message}")
    
    return all(check[0] == "✅" for check in checks)


if __name__ == "__main__":
    print("🚀 Pipeline 1: Keyword Research Testing")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    print("\nChoose a test method:")
    print("1. Direct function test (fastest)")
    print("2. Database test (with brand/job records)")
    print("3. Queue dispatch test (most realistic)")
    print("4. Run all tests")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            test_direct_function()
        elif choice == "2":
            test_with_database()
        elif choice == "3":
            test_queue_dispatch()
        elif choice == "4":
            print("\n" + "="*50)
            test_direct_function()
            print("\n" + "="*50)
            test_with_database()
            print("\n" + "="*50)
            test_queue_dispatch()
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
            
        print("\n✅ Testing completed!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Testing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)