#!/usr/bin/env python3
"""
WordPress Connection Debugging Script
Helps diagnose WordPress integration connection issues
"""

import asyncio
import sys
from urllib.parse import urlparse
import httpx
import socket


async def debug_wordpress_connection(site_url: str, username: str = "", app_password: str = ""):
    """Debug WordPress connection step by step."""
    
    print("🔍 WordPress Connection Debugging")
    print("=" * 50)
    
    # Parse URL
    try:
        parsed = urlparse(site_url)
        if not parsed.scheme:
            site_url = f"https://{site_url}"
            parsed = urlparse(site_url)
        
        print(f"📍 Site URL: {site_url}")
        print(f"📍 Domain: {parsed.netloc}")
        print(f"📍 Scheme: {parsed.scheme}")
        print()
    except Exception as e:
        print(f"❌ URL parsing error: {e}")
        return
    
    # 1. DNS Resolution Test
    print("1️⃣ Testing DNS Resolution...")
    try:
        domain = parsed.netloc.split(':')[0]  # Remove port if present
        ip = socket.gethostbyname(domain)
        print(f"✅ DNS resolved: {domain} → {ip}")
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        print("💡 Check if the domain exists and is spelled correctly")
        return
    except Exception as e:
        print(f"❌ DNS error: {e}")
        return
    
    print()
    
    # 2. Basic HTTP Connectivity
    print("2️⃣ Testing Basic HTTP Connectivity...")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(site_url)
            print(f"✅ Site accessible: HTTP {resp.status_code}")
            print(f"📄 Content-Type: {resp.headers.get('content-type', 'unknown')}")
    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Site may be down or blocking connections")
        return
    except httpx.TimeoutException:
        print("❌ Connection timeout")
        print("💡 Site is slow to respond or unreachable")
        return
    except Exception as e:
        print(f"❌ HTTP error: {e}")
        return
    
    print()
    
    # 3. WordPress REST API Discovery
    print("3️⃣ Testing WordPress REST API...")
    rest_url = f"{site_url.rstrip('/')}/wp-json/"
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(rest_url)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    wp_version = data.get('description', 'Unknown')
                    print(f"✅ WordPress REST API found: {wp_version}")
                    
                    # Check if routes include posts endpoint
                    routes = data.get('routes', {})
                    if '/wp/v2/posts' in routes or any('/wp/v2/posts' in route for route in routes.keys()):
                        print("✅ Posts endpoint available")
                    else:
                        print("⚠️ Posts endpoint not found in routes")
                        
                except Exception as json_error:
                    print(f"✅ REST API accessible but JSON parsing failed: {json_error}")
            else:
                print(f"❌ REST API not accessible: HTTP {resp.status_code}")
                print("💡 WordPress may not have REST API enabled or URL is incorrect")
                
    except Exception as e:
        print(f"❌ REST API test failed: {e}")
        print("💡 WordPress REST API may be disabled or site structure is different")
    
    print()
    
    # 4. Authentication Test (if credentials provided)
    if username and app_password:
        print("4️⃣ Testing Authentication...")
        auth_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
        
        try:
            auth = (username, app_password)
            async with httpx.AsyncClient(timeout=15, auth=auth, follow_redirects=True) as client:
                resp = await client.get(auth_url)
                
                if resp.status_code == 200:
                    user_data = resp.json()
                    print(f"✅ Authentication successful")
                    print(f"👤 User: {user_data.get('name', 'Unknown')}")
                    print(f"🎭 Roles: {', '.join(user_data.get('roles', []))}")
                    
                    # Check capabilities
                    caps = user_data.get('capabilities', {})
                    if caps:
                        important_caps = ['edit_posts', 'publish_posts', 'upload_files']
                        print("🔑 Key capabilities:")
                        for cap in important_caps:
                            status = "✅" if caps.get(cap) else "❌"
                            print(f"   {status} {cap}")
                    else:
                        print("⚠️ No capabilities data (may be InstaWP/managed hosting)")
                        
                elif resp.status_code == 401:
                    print("❌ Authentication failed: Invalid username or application password")
                    print("💡 Double-check username and regenerate application password")
                elif resp.status_code == 403:
                    print("❌ Authentication forbidden: User lacks API access")
                else:
                    print(f"❌ Auth test failed: HTTP {resp.status_code}")
                    
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
    else:
        print("4️⃣ Skipping authentication test (no credentials provided)")
    
    print()
    print("🔧 COMMON SOLUTIONS:")
    print("• Verify WordPress site URL is correct and accessible")
    print("• Ensure WordPress REST API is enabled")
    print("• Check username spelling and application password")
    print("• Try regenerating application password in WordPress admin")
    print("• Verify user has 'edit_posts' and 'publish_posts' capabilities")
    print("• Check if firewall/security plugin is blocking API requests")


async def main():
    """Interactive debugging."""
    print("WordPress Connection Debugger")
    print("Enter your WordPress site details for testing:")
    print()
    
    site_url = input("WordPress Site URL (e.g., https://example.com): ").strip()
    if not site_url:
        print("Site URL is required!")
        return
        
    username = input("Username (optional for basic tests): ").strip()
    app_password = input("Application Password (optional): ").strip()
    
    print()
    await debug_wordpress_connection(site_url, username, app_password)


if __name__ == "__main__":
    asyncio.run(main())