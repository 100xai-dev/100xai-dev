#!/usr/bin/env python3
"""
WordPress Connection Test Script
Usage: python test_wordpress_connection.py <site_url> [username] [app_password]
"""

import asyncio
import sys
from urllib.parse import urlparse
import httpx
import socket


async def test_wordpress_connection(site_url: str, username: str = "", app_password: str = ""):
    """Test WordPress connection with detailed diagnostics."""
    
    print(f"🔍 Testing WordPress connection to: {site_url}")
    print("=" * 60)
    
    # Normalize URL
    if not site_url.startswith(('http://', 'https://')):
        site_url = f"https://{site_url}"
    
    parsed = urlparse(site_url)
    domain = parsed.netloc.split(':')[0]
    
    # 1. DNS Test
    print("1️⃣ DNS Resolution Test...")
    try:
        ip = socket.gethostbyname(domain)
        print(f"✅ DNS: {domain} → {ip}")
    except socket.gaierror as e:
        print(f"❌ DNS Failed: {e}")
        print("💡 Check domain spelling and existence")
        return False
    
    # 2. HTTP Connectivity  
    print("\n2️⃣ HTTP Connectivity Test...")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(site_url)
            print(f"✅ HTTP: {resp.status_code} - Site accessible")
    except Exception as e:
        print(f"❌ HTTP Failed: {e}")
        return False
    
    # 3. WordPress REST API
    print("\n3️⃣ WordPress REST API Test...")
    rest_url = f"{site_url.rstrip('/')}/wp-json/"
    
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(rest_url)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ REST API: {data.get('description', 'Found')}")
            else:
                print(f"❌ REST API: HTTP {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ REST API Failed: {e}")
        return False
    
    # 4. Authentication (if provided)
    if username and app_password:
        print("\n4️⃣ Authentication Test...")
        auth_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
        
        try:
            auth = (username, app_password)
            async with httpx.AsyncClient(timeout=10, auth=auth, follow_redirects=True) as client:
                resp = await client.get(auth_url)
                
                if resp.status_code == 200:
                    user = resp.json()
                    print(f"✅ Auth: {user.get('name', 'Success')}")
                    print(f"🎭 Roles: {', '.join(user.get('roles', []))}")
                    return True
                else:
                    print(f"❌ Auth Failed: HTTP {resp.status_code}")
                    if resp.status_code == 401:
                        print("💡 Check username and regenerate application password")
                    return False
        except Exception as e:
            print(f"❌ Auth Error: {e}")
            return False
    else:
        print("\n✅ Basic connectivity successful (no auth test)")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_wordpress_connection.py <site_url> [username] [app_password]")
        print("Example: python test_wordpress_connection.py mysite.com admin xxxx-xxxx-xxxx-xxxx")
        sys.exit(1)
    
    site_url = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else ""
    app_password = sys.argv[3] if len(sys.argv) > 3 else ""
    
    success = asyncio.run(test_wordpress_connection(site_url, username, app_password))
    
    if not success:
        print("\n🚨 CONNECTION FAILED")
        print("\n🔧 TROUBLESHOOTING TIPS:")
        print("• Verify domain exists and is accessible")
        print("• Ensure WordPress site has REST API enabled")  
        print("• Check username spelling exactly")
        print("• Regenerate application password in WordPress admin")
        print("• Verify user has admin/editor permissions")
        print("• Check firewall/security plugins aren't blocking API")
        sys.exit(1)
    else:
        print("\n✅ CONNECTION SUCCESSFUL")