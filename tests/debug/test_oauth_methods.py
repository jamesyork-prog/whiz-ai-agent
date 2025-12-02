"""
Test different OAuth2 authentication methods for ParkWhiz API.

Run with: docker-compose exec parlant python tests/debug/test_oauth_methods.py
"""

import asyncio
import os
import base64
import httpx


async def test_method_1_basic_auth():
    """Method 1: Basic Authentication (RFC 6749 standard)"""
    print("\n" + "="*60)
    print("Method 1: Basic Authentication")
    print("="*60)
    
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    scope = os.getenv("PARKWHIZ_SCOPE", "partner")
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    token_url = f"{base_url.rstrip('/')}/oauth/token"
    
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    print(f"URL: {token_url}")
    print(f"Scope: {scope}")
    print(f"Auth: Basic {credentials[:20]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Authorization": f"Basic {credentials}",
                }
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                return response.json()
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return None


async def test_method_2_body_params():
    """Method 2: Credentials in request body"""
    print("\n" + "="*60)
    print("Method 2: Credentials in Body")
    print("="*60)
    
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    scope = os.getenv("PARKWHIZ_SCOPE", "partner")
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    token_url = f"{base_url.rstrip('/')}/oauth/token"
    
    print(f"URL: {token_url}")
    print(f"Scope: {scope}")
    print(f"Client ID: {client_id[:20]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
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
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                return response.json()
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return None


async def test_method_3_no_scope():
    """Method 3: Basic Auth without scope parameter"""
    print("\n" + "="*60)
    print("Method 3: Basic Auth (No Scope)")
    print("="*60)
    
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    token_url = f"{base_url.rstrip('/')}/oauth/token"
    
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    print(f"URL: {token_url}")
    print(f"Auth: Basic {credentials[:20]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Authorization": f"Basic {credentials}",
                }
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                return response.json()
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return None


async def test_method_4_production_url():
    """Method 4: Try production URL instead of sandbox"""
    print("\n" + "="*60)
    print("Method 4: Production URL")
    print("="*60)
    
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    scope = os.getenv("PARKWHIZ_SCOPE", "partner")
    
    # Try production URL
    token_url = "https://api.parkwhiz.com/v4/oauth/token"
    
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    print(f"URL: {token_url}")
    print(f"Scope: {scope}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Authorization": f"Basic {credentials}",
                }
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                return response.json()
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return None


async def main():
    print("\n" + "="*60)
    print("ParkWhiz OAuth2 Authentication Method Testing")
    print("="*60)
    
    # Test all methods
    result = await test_method_1_basic_auth()
    if result:
        print(f"\n🎉 Method 1 worked! Token: {result.get('access_token', '')[:30]}...")
        return
    
    result = await test_method_2_body_params()
    if result:
        print(f"\n🎉 Method 2 worked! Token: {result.get('access_token', '')[:30]}...")
        return
    
    result = await test_method_3_no_scope()
    if result:
        print(f"\n🎉 Method 3 worked! Token: {result.get('access_token', '')[:30]}...")
        return
    
    result = await test_method_4_production_url()
    if result:
        print(f"\n🎉 Method 4 worked! Token: {result.get('access_token', '')[:30]}...")
        return
    
    print("\n❌ All methods failed. Check credentials or contact ParkWhiz support.")


if __name__ == "__main__":
    asyncio.run(main())
