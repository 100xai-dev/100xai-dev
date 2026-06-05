#!/usr/bin/env python3
import asyncio
import base64
import httpx
from app.config import get_settings

async def test_dataforseo_auth():
    login = 'shubhamrathod1619@gmail.com'
    password = 'uavXu7tE6mr8zgb'
    
    print('Testing DataForSEO Authentication with login:password...')
    
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