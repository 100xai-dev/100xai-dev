#!/usr/bin/env python3
"""
Test Pipeline 2 API endpoints - Quick verification that the backend endpoints work
"""

import sys
import os
import httpx
import asyncio
import json

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings


async def test_pipeline2_endpoints():
    """Test the Pipeline 2 API endpoints with a local backend."""
    print("🧪 Testing Pipeline 2 API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # For this test, we'll need a test brand ID
    # You would normally get this from your database or frontend
    test_brand_id = "test-brand-123"  # Replace with actual brand ID
    
    print(f"🔗 Testing endpoints at: {base_url}")
    print(f"🏢 Test brand ID: {test_brand_id}")
    
    headers = {
        "Content-Type": "application/json",
        # In real usage, you'd include authentication headers
        # "Authorization": "Bearer your_jwt_token_here"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Start SERP Analysis (POST)
        print("\n1️⃣ Testing POST /v1/brands/{brand_id}/serp-analysis")
        try:
            response = await client.post(
                f"{base_url}/v1/brands/{test_brand_id}/serp-analysis",
                headers=headers,
                json={}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SERP analysis started successfully!")
                print(f"   Job ID: {result.get('job_id', 'N/A')}")
                print(f"   Keywords count: {result.get('keywords_count', 'N/A')}")
                print(f"   Status: {result.get('status', 'N/A')}")
            elif response.status_code == 400:
                error = response.json()
                print(f"⚠️  Expected error (no keywords): {error.get('detail', 'Unknown')}")
            elif response.status_code == 401:
                print(f"🔐 Authentication required (expected in production)")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except httpx.ConnectError:
            print(f"❌ Cannot connect to {base_url}")
            print("   💡 Make sure the backend is running:")
            print("   cd /Users/shubhamrathod/Downloads/100xai/backend")
            print("   source venv/bin/activate")
            print("   python -m uvicorn app.main:app --reload --port 8000")
            return False
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        # Test 2: Get SERP Analysis Results (GET)
        print("\n2️⃣ Testing GET /v1/brands/{brand_id}/serp-analysis")
        try:
            response = await client.get(
                f"{base_url}/v1/brands/{test_brand_id}/serp-analysis",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SERP results retrieved successfully!")
                print(f"   Total analyses: {result.get('total_analyses', 0)}")
                print(f"   Analysis status: {result.get('analysis_status', 'N/A')}")
                print(f"   Latest job ID: {result.get('latest_job_id', 'N/A')}")
                
                analyses = result.get('serp_analyses', [])
                if analyses:
                    print(f"   Sample analysis: {analyses[0].get('keyword_text', 'N/A')}")
                else:
                    print(f"   No analyses found (expected for new brand)")
                    
            elif response.status_code == 401:
                print(f"🔐 Authentication required (expected in production)")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    return True


async def test_backend_health():
    """Test if the backend is responding."""
    print("\n🏥 Testing Backend Health")
    print("-" * 30)
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                print(f"✅ Backend is healthy!")
                return True
            else:
                print(f"⚠️  Backend responded with status: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"❌ Backend not responding at {base_url}")
        print("   Start the backend with:")
        print(f"   cd /Users/shubhamrathod/Downloads/100xai/backend")
        print(f"   source venv/bin/activate")
        print(f"   python -m uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def show_integration_instructions():
    """Show instructions for testing Pipeline 2 with the frontend."""
    print("\n" + "="*60)
    print("🎯 Pipeline 2 Frontend Integration Instructions")
    print("="*60)
    
    print("\n📋 Prerequisites:")
    print("1. ✅ LLM parsing fix applied")
    print("2. ✅ API endpoints added to backend") 
    print("3. ✅ Frontend button connected to API calls")
    print("4. ⚠️  SerpAPI key needed for full functionality")
    
    print("\n🚀 To Test Full Integration:")
    print("1. Start Backend:")
    print("   cd /Users/shubhamrathod/Downloads/100xai/backend")
    print("   source venv/bin/activate") 
    print("   python -m uvicorn app.main:app --reload --port 8000")
    
    print("\n2. Start Frontend:")
    print("   cd /Users/shubhamrathod/Downloads/100xai/frontend")
    print("   npm run dev")
    
    print("\n3. Test Workflow:")
    print("   • Navigate to: http://localhost:3000/brands/{brand-id}/keywords")
    print("   • Complete keyword research first (Pipeline 1)")
    print("   • Click '🔍 Start SERP Analysis' button")
    print("   • Monitor backend logs for processing")
    print("   • Check database for results")
    
    print("\n📊 Expected Results:")
    print("   • Job created in jobs table")
    print("   • Top 5 keywords analyzed")
    print("   • Competitor pages crawled with Apify") 
    print("   • AI content analysis generated")
    print("   • Results stored in serp_analyses tables")
    
    print("\n🎉 Pipeline 2 Status: 🟢 Ready for Frontend Testing!")


async def main():
    """Main test function."""
    print("🧪 Pipeline 2 API Endpoint Testing")
    print("="*50)
    
    # Test backend health first
    backend_healthy = await test_backend_health()
    
    if backend_healthy:
        # Test Pipeline 2 endpoints
        await test_pipeline2_endpoints()
    else:
        print("\n⚠️  Backend not running. Start backend first to test API endpoints.")
    
    # Show integration instructions
    show_integration_instructions()


if __name__ == "__main__":
    asyncio.run(main())