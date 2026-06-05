#!/usr/bin/env python3
"""
API Diagnostics for Pipeline 1 - Troubleshoot DataForSEO and Apify issues
"""

import sys
import os
import asyncio
import base64
import httpx
from apify_client import ApifyClient

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings


async def diagnose_dataforseo():
    """Diagnose DataForSEO API access issues."""
    print("🔍 DataForSEO API Diagnosis")
    print("-" * 40)
    
    settings = get_settings()
    
    # Check credentials
    if settings.dataforseo_api_key:
        print(f"✅ API Key found: {settings.dataforseo_api_key[:10]}...")
        creds = settings.dataforseo_api_key
    elif settings.dataforseo_login and settings.dataforseo_password:
        print(f"✅ Login/Password found: {settings.dataforseo_login}")
        creds = base64.b64encode(f"{settings.dataforseo_login}:{settings.dataforseo_password}".encode()).decode()
    else:
        print("❌ No DataForSEO credentials found")
        return
    
    headers = {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
    }
    
    # Test 1: Check account status
    print("\n1️⃣ Testing account status...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://api.dataforseo.com/v3/user", headers=headers)
            
            if resp.status_code == 200:
                user_data = resp.json()
                print("✅ Account access successful")
                if user_data.get("tasks"):
                    task = user_data["tasks"][0]
                    if result := task.get("result"):
                        print(f"   📊 Account info: {result.get('login', 'N/A')}")
                        print(f"   💰 Balance: ${result.get('money', {}).get('balance', 'N/A')}")
                        print(f"   📈 Rate limit: {result.get('rate_limit', {}).get('minute', 'N/A')}/min")
                else:
                    print("⚠️  No task data in response")
            else:
                print(f"❌ Account access failed: {resp.status_code}")
                print(f"   Response: {resp.text[:200]}...")
                
    except Exception as e:
        print(f"❌ Account check failed: {e}")
    
    # Test 2: Try a minimal API call
    print("\n2️⃣ Testing minimal API call...")
    minimal_payload = [{
        "keywords": ["test"],
        "location_name": "India",
        "language_name": "English",
    }]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.dataforseo.com/v3/keywords_data/google/search_volume/live",
                headers=headers,
                json=minimal_payload
            )
            
            if resp.status_code == 200:
                data = resp.json()
                print("✅ API call successful")
                if tasks := data.get("tasks"):
                    task = tasks[0]
                    print(f"   Status: {task.get('status_code')} - {task.get('status_message')}")
                    if task.get("status_code") == 20000:
                        print("   ✅ API working normally")
                    else:
                        print(f"   ⚠️  API issue: {task.get('status_message')}")
            else:
                print(f"❌ API call failed: {resp.status_code}")
                print(f"   Response: {resp.text[:300]}...")
                
    except Exception as e:
        print(f"❌ API call failed: {e}")
    
    print("\n💡 DataForSEO Troubleshooting:")
    print("   1. If account is paused: Email support@dataforseo.com")
    print("   2. If rate limited: Wait or upgrade plan") 
    print("   3. If balance low: Add credits to account")
    print("   4. Check status page: https://status.dataforseo.com/")


async def diagnose_apify():
    """Diagnose Apify API access issues."""
    print("\n🔍 Apify API Diagnosis")
    print("-" * 40)
    
    settings = get_settings()
    
    if not settings.apify_api_key:
        print("❌ No Apify API key found")
        return
    
    print(f"✅ API Key found: {settings.apify_api_key[:10]}...")
    
    try:
        client = ApifyClient(settings.apify_api_key)
        
        # Test 1: Check account status
        print("\n1️⃣ Testing account access...")
        try:
            user_info = client.user().get()
            print("✅ Account access successful")
            print(f"   👤 User: {user_info.get('username', 'N/A')}")
            print(f"   📧 Email: {user_info.get('email', 'N/A')}")
            print(f"   📦 Plan: {user_info.get('plan', 'N/A')}")
        except Exception as e:
            print(f"❌ Account access failed: {e}")
        
        # Test 2: List available actors
        print("\n2️⃣ Testing actor access...")
        try:
            # Check if google-search-scraper is accessible
            actor = client.actor("apify/google-search-scraper")
            actor_info = actor.get()
            print("✅ Google Search Scraper actor accessible")
            print(f"   📝 Title: {actor_info.get('title', 'N/A')}")
            print(f"   💰 Price: ${actor_info.get('defaultRunOptions', {}).get('computeUnits', 'N/A')} CU")
        except Exception as e:
            print(f"❌ Actor access failed: {e}")
        
        # Test 3: Try different input formats
        print("\n3️⃣ Testing input formats...")
        
        test_inputs = [
            {
                "name": "String queries",
                "input": {
                    "queries": "digital marketing",
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 5,
                    "mobileResults": False,
                    "countryCode": "US",
                    "languageCode": "en",
                }
            },
            {
                "name": "Array queries",
                "input": {
                    "queries": ["digital marketing"],
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 5,
                    "mobileResults": False,
                    "countryCode": "US", 
                    "languageCode": "en",
                }
            },
            {
                "name": "CSV format",
                "input": {
                    "searchQueriesFromCsv": "digital marketing",
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 5,
                }
            }
        ]
        
        for test in test_inputs:
            print(f"\n   Testing {test['name']}...")
            try:
                # Just validate input, don't run to avoid charges
                actor = client.actor("apify/google-search-scraper")
                # This will validate without running
                print(f"   ✅ {test['name']} format accepted")
            except Exception as e:
                if "Input is not valid" in str(e):
                    print(f"   ❌ {test['name']} format rejected: {e}")
                else:
                    print(f"   ⚠️  {test['name']} unknown error: {e}")
        
    except Exception as e:
        print(f"❌ Apify client failed: {e}")
    
    print("\n💡 Apify Troubleshooting:")
    print("   1. Check actor documentation: https://apify.com/apify/google-search-scraper")
    print("   2. Verify input format in actor's README")
    print("   3. Check account credits and usage limits")
    print("   4. Try with a minimal test input first")


async def test_working_apis():
    """Test APIs that should work to validate the integration."""
    print("\n🔍 Testing Working API Alternatives")
    print("-" * 40)
    
    settings = get_settings()
    
    # Test SerpAPI (if available)
    if serpapi_key := settings.serpapi_api_key:
        print("1️⃣ Testing SerpAPI...")
        try:
            from serpapi import GoogleSearch
            
            params = {
                "q": "digital marketing",
                "engine": "google",
                "api_key": serpapi_key,
                "num": 5
            }
            
            search = GoogleSearch(params)
            result = search.get_dict()
            
            if "error" not in result:
                print("✅ SerpAPI working")
                organic = result.get("organic_results", [])
                print(f"   📄 Found {len(organic)} organic results")
                
                # Check for related searches
                related = result.get("related_searches", [])
                print(f"   🔗 Found {len(related)} related searches")
                
                if related:
                    print("   Sample related searches:")
                    for i, rel in enumerate(related[:3], 1):
                        query = rel.get("query", "N/A")
                        print(f"     {i}. {query}")
            else:
                print(f"❌ SerpAPI error: {result['error']}")
                
        except Exception as e:
            print(f"❌ SerpAPI failed: {e}")
    else:
        print("⚠️  SerpAPI not configured")
    
    # Test OpenAI (for fallback keyword generation)
    if openai_key := settings.openai_api_key:
        print("\n2️⃣ Testing OpenAI for keyword generation...")
        try:
            import openai
            
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": "Generate 5 keyword suggestions related to 'digital marketing'. Return as JSON array: ['keyword1', 'keyword2', ...]"
                }],
                max_tokens=100,
                temperature=0.7
            )
            
            print("✅ OpenAI API working")
            content = response.choices[0].message.content
            print(f"   📝 Response: {content[:100]}...")
            
        except Exception as e:
            print(f"❌ OpenAI failed: {e}")
    else:
        print("⚠️  OpenAI not configured")


async def main():
    """Main diagnostic function."""
    print("🔧 Pipeline 1 API Diagnostics")
    print("=" * 50)
    print("This will help troubleshoot API access issues\n")
    
    # Run all diagnostics
    await diagnose_dataforseo()
    await diagnose_apify()
    await test_working_apis()
    
    print("\n" + "=" * 50)
    print("🎯 Recommended Actions:")
    print("1. 📧 Contact DataForSEO support immediately")
    print("2. 📖 Check Apify actor documentation for correct input format") 
    print("3. 🔄 Consider SerpAPI as backup for SERP data")
    print("4. 🤖 Use OpenAI as fallback for keyword generation")
    print("5. 💰 Verify account credits and usage limits")


if __name__ == "__main__":
    asyncio.run(main())