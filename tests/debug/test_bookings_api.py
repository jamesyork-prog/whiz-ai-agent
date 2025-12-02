"""
Test ParkWhiz bookings API with OAuth2 authentication.

Run with: docker-compose exec parlant python tests/debug/test_bookings_api.py
"""

import asyncio
import os
import httpx
from datetime import datetime, timedelta


async def test_bookings_api():
    """Test the /v4/bookings endpoint with OAuth2."""
    
    print("=" * 60)
    print("ParkWhiz Bookings API Test")
    print("=" * 60)
    
    # Get credentials
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    scope = os.getenv("PARKWHIZ_SCOPE", "partner")
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    print(f"\n📋 Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Scope: {scope}")
    
    # Step 1: Get OAuth2 token
    print(f"\n🔑 Step 1: Getting OAuth2 token...")
    token_url = f"{base_url.rstrip('/')}/oauth/token"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )
        
        if token_response.status_code != 200:
            print(f"❌ Token request failed: {token_response.status_code}")
            print(f"   Response: {token_response.text}")
            return
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        print(f"✅ Token obtained: {access_token[:30]}...")
        print(f"   Expires in: {token_data.get('expires_in')} seconds")
        
        # Step 2: Test bookings endpoint
        print(f"\n🔍 Step 2: Testing /v4/bookings endpoint...")
        
        # Try different query formats
        test_cases = [
            {
                "name": "Query by email (q parameter)",
                "params": {
                    "q": "customer_email:test@example.com",
                },
            },
            {
                "name": "Query by email (email parameter)",
                "params": {
                    "email": "test@example.com",
                },
            },
            {
                "name": "No filters (list all)",
                "params": {},
            },
        ]
        
        for test_case in test_cases:
            print(f"\n  Testing: {test_case['name']}")
            print(f"  Params: {test_case['params']}")
            
            try:
                bookings_response = await client.get(
                    f"{base_url.rstrip('/')}/bookings",
                    params=test_case['params'],
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    }
                )
                
                print(f"  Status: {bookings_response.status_code}")
                
                if bookings_response.status_code == 200:
                    data = bookings_response.json()
                    print(f"  ✅ Success!")
                    
                    # Response might be a list or a dict
                    if isinstance(data, list):
                        bookings = data
                        print(f"  Response is a list")
                    elif isinstance(data, dict):
                        print(f"  Response keys: {list(data.keys())}")
                        bookings = data.get("bookings", data.get("results", []))
                    else:
                        print(f"  Unexpected response type: {type(data)}")
                        bookings = []
                    
                    print(f"  Found {len(bookings)} bookings")
                    
                    if bookings:
                        print(f"\n  📦 Sample booking:")
                        booking = bookings[0]
                        print(f"    Keys: {list(booking.keys())}")
                        print(f"    ID: {booking.get('id')}")
                        print(f"    Status: {booking.get('status')}")
                        print(f"    Customer: {booking.get('customer_email')}")
                        print(f"    Location: {booking.get('location_name')}")
                        print(f"    Start: {booking.get('start_time')}")
                    
                    # If this worked, we're done
                    if bookings_response.status_code == 200:
                        print(f"\n✅ Bookings API is working!")
                        return
                        
                else:
                    print(f"  ❌ Failed: {bookings_response.status_code}")
                    print(f"  Response: {bookings_response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"  ⏱️  Request timed out (30s)")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\n❌ All test cases failed or timed out")


if __name__ == "__main__":
    asyncio.run(test_bookings_api())
