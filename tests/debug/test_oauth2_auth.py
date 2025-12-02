"""
Quick test script to verify ParkWhiz OAuth2 authentication.

Run with: docker-compose exec parlant python tests/debug/test_oauth2_auth.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from app_tools.tools.parkwhiz_client import ParkWhizOAuth2Client


async def test_oauth2_auth():
    """Test OAuth2 token generation and basic API call."""
    
    print("=" * 60)
    print("ParkWhiz OAuth2 Authentication Test")
    print("=" * 60)
    
    # Display configuration
    print("\n📋 Configuration:")
    print(f"  Environment: {os.getenv('PARKWHIZ_ENV', 'sandbox')}")
    print(f"  Client ID: {os.getenv('PARKWHIZ_CLIENT_ID', 'NOT SET')[:20]}...")
    print(f"  Client Secret: {'SET' if os.getenv('PARKWHIZ_CLIENT_SECRET') else 'NOT SET'}")
    print(f"  Scope: {os.getenv('PARKWHIZ_SCOPE', 'partner')}")
    print(f"  Base URL: {os.getenv('PARKWHIZ_SANDBOX_URL', 'NOT SET')}")
    
    # Initialize client
    print("\n🔧 Initializing OAuth2 client...")
    try:
        client = ParkWhizOAuth2Client()
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Test token generation
    print("\n🔑 Testing OAuth2 token generation...")
    try:
        await client._ensure_valid_token()
        print(f"✅ Token generated successfully")
        print(f"  Token: {client._token[:30]}..." if client._token else "  Token: None")
        print(f"  Expires: {client._token_expires_at}")
    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        await client.close()
        return
    
    # Test API call - search for bookings
    print("\n🔍 Testing API call: get_customer_bookings...")
    try:
        # Use a test email and date range
        test_email = "test@example.com"
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"  Email: {test_email}")
        print(f"  Date range: {start_date} to {end_date}")
        
        bookings = await client.get_customer_bookings(
            customer_email=test_email,
            start_date=start_date,
            end_date=end_date,
        )
        
        print(f"✅ API call successful")
        print(f"  Found {len(bookings)} bookings")
        
        if bookings:
            print("\n📦 Sample booking:")
            booking = bookings[0]
            print(f"  ID: {booking.get('id')}")
            print(f"  Status: {booking.get('status')}")
            print(f"  Location: {booking.get('location_name')}")
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    await client.close()
    print("✅ Test complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_oauth2_auth())
