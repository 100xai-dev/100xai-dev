#!/usr/bin/env python3
"""
WordPress Connection Test Script
Debug WordPress integration issues for: assuring-cod-3ba97e.instawp.site
"""
import asyncio
import httpx
import json

async def test_wordpress_connection():
    site_url = "https://assuring-cod-3ba97e.instawp.site"
    username = "xuyagonete8147"
    # Note: You'll need to provide the actual application password
    app_password = "GFrz zTOC 4ClR jvoB 4FFM 7ad0"
    
    print(f"🔗 Testing WordPress connection to: {site_url}")
    print(f"👤 Username: {username}")
    print("=" * 60)
    
    auth = (username, app_password)
    
    async with httpx.AsyncClient(timeout=15, auth=auth, follow_redirects=True) as client:
        
        # Step 1: Test basic connectivity
        print("1️⃣ Testing basic connectivity...")
        try:
            resp = await client.get(f"{site_url}")
            print(f"   ✅ Site reachable (HTTP {resp.status_code})")
            print(f"   📍 Final URL: {resp.url}")
        except httpx.RequestError as e:
            print(f"   ❌ Site not reachable: {e}")
            return
        
        # Step 2: Test WordPress REST API discovery
        print("\n2️⃣ Testing WordPress REST API...")
        try:
            resp = await client.get(f"{site_url}/wp-json/")
            print(f"   📊 REST API Status: {resp.status_code}")
            
            if resp.status_code == 200:
                site_info = resp.json()
                print(f"   ✅ REST API accessible")
                print(f"   📝 Site Name: {site_info.get('name', 'Unknown')}")
                print(f"   📝 WP Version: {site_info.get('wp_version', 'Unknown')}")
                print(f"   📝 API Version: {site_info.get('api_version', 'Unknown')}")
            else:
                print(f"   ❌ REST API not accessible")
                print(f"   📄 Response: {resp.text[:200]}")
                return
                
        except httpx.RequestError as e:
            print(f"   ❌ REST API error: {e}")
            return
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON response: {e}")
            return
        
        # Step 3: Test authentication
        print("\n3️⃣ Testing authentication...")
        try:
            resp = await client.get(f"{site_url}/wp-json/wp/v2/users/me")
            print(f"   🔐 Auth Status: {resp.status_code}")
            
            if resp.status_code == 401:
                print(f"   ❌ Authentication failed")
                print(f"   💡 Check username and application password")
                print(f"   📄 Response: {resp.text[:200]}")
                return
            elif resp.status_code == 200:
                user_info = resp.json()
                print(f"   ✅ Authentication successful")
                print(f"   👤 Display Name: {user_info.get('name', 'Unknown')}")
                print(f"   📧 Email: {user_info.get('email', 'Unknown')}")
                print(f"   🎭 Roles: {user_info.get('roles', [])}")
            else:
                print(f"   ❌ Auth check failed (HTTP {resp.status_code})")
                print(f"   📄 Response: {resp.text[:200]}")
                return
                
        except httpx.RequestError as e:
            print(f"   ❌ Auth test error: {e}")
            return
        
        # Step 4: Check capabilities
        print("\n4️⃣ Checking user capabilities...")
        caps = user_info.get("capabilities", {})
        print(f"   📋 Total capabilities: {len(caps)}")
        
        required_caps = ["publish_posts", "edit_posts"]
        for cap in required_caps:
            has_cap = caps.get(cap, False)
            status = "✅" if has_cap else "❌"
            print(f"   {status} {cap}: {has_cap}")
        
        has_required_caps = caps.get("publish_posts") or caps.get("edit_posts")
        
        # InstaWP Workaround: Test actual post creation if capabilities are missing
        if not has_required_caps and len(caps) == 0:
            print(f"   🔧 Capabilities empty (InstaWP issue) - testing actual permissions...")
            
            # Test with draft post creation
            test_post = {
                "title": "Connection Test (Auto-Delete)",
                "content": "Temporary test post for integration verification.",
                "status": "draft"
            }
            
            try:
                test_resp = await client.post(f"{site_url}/wp-json/wp/v2/posts", json=test_post)
                if test_resp.status_code == 201:
                    post_data = test_resp.json()
                    post_id = post_data.get("id")
                    print(f"   ✅ Test post created successfully (ID: {post_id}) - User CAN publish!")
                    
                    # Clean up test post
                    if post_id:
                        delete_resp = await client.delete(f"{site_url}/wp-json/wp/v2/posts/{post_id}?force=true")
                        if delete_resp.status_code in [200, 410]:
                            print(f"   🗑️ Test post cleaned up")
                    
                    has_required_caps = True  # Override capability check
                    
                elif test_resp.status_code == 403:
                    print(f"   ❌ Post creation failed (HTTP 403) - User lacks permissions")
                    return
                else:
                    print(f"   ⚠️ Post creation test inconclusive (HTTP {test_resp.status_code})")
                    
            except httpx.RequestError as e:
                print(f"   ⚠️ Post creation test failed: {e}")
        
        if not has_required_caps:
            print(f"   ❌ User lacks required publishing capabilities")
            return
            
        # Step 5: Test post creation (dry run)
        print("\n5️⃣ Testing post creation capability...")
        test_post = {
            "title": "Connection Test (Draft)",
            "content": "This is a test post to verify WordPress integration.",
            "status": "draft",
            "type": "post"
        }
        
        try:
            resp = await client.post(
                f"{site_url}/wp-json/wp/v2/posts",
                json=test_post
            )
            print(f"   📝 Post Creation Status: {resp.status_code}")
            
            if resp.status_code == 201:
                post_info = resp.json()
                post_id = post_info.get("id")
                print(f"   ✅ Test post created successfully (ID: {post_id})")
                
                # Clean up test post
                delete_resp = await client.delete(f"{site_url}/wp-json/wp/v2/posts/{post_id}?force=true")
                if delete_resp.status_code in [200, 410]:
                    print(f"   🗑️ Test post cleaned up")
                
            else:
                print(f"   ❌ Post creation failed")
                print(f"   📄 Response: {resp.text[:300]}")
                
        except httpx.RequestError as e:
            print(f"   ❌ Post creation test error: {e}")
            return
    
    print(f"\n🎉 WordPress connection test completed!")
    print(f"💡 If all steps passed, the integration should work properly.")

if __name__ == "__main__":
    print("WordPress Connection Diagnostic Tool")
    print("Note: Replace 'YOUR_APPLICATION_PASSWORD_HERE' with your actual WordPress application password")
    print("=" * 60)
    asyncio.run(test_wordpress_connection())