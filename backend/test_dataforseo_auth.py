#!/usr/bin/env python3
import asyncio
import base64
import httpx
import os
from app.config import get_settings

async def test_dataforseo_auth():
    login = os.getenv('DATAFORSEO_LOGIN')
    password = os.getenv('DATAFORSEO_PASSWORD')
    
    if not login or not password:
        print('❌ Missing DataForSEO credentials. Please set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables.')
        return
    
    print(f'Testing DataForSEO Authentication with login: {login[:10]}...')
    
    # Create Basic Auth credentials
    creds = base64.b64encode(f'{login}:{password}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {creds}',
        'Content-Type': 'application/json'
    }
    
    test_payload = [{
        'keyword': 'test',
        'location_name': 'United States', 
        'language_name': 'English',
        'depth': 3
    }]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                'https://api.dataforseo.com/v3/serp/google/organic/live/advanced',
                headers=headers,
                json=test_payload
            )
            print(f'Status: {resp.status_code}')
            if resp.status_code != 200:
                print(f'Error: {resp.text[:500]}')
            else:
                print('✅ Authentication successful!')
                print('Response preview:', str(resp.json())[:200])
                
    except Exception as e:
        print(f'❌ Request failed: {e}')

if __name__ == "__main__":
    asyncio.run(test_dataforseo_auth())