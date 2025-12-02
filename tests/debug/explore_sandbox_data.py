"""
Explore ParkWhiz sandbox data to find the most recent bookings.

Run with: docker-compose exec parlant python tests/debug/explore_sandbox_data.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/app')

from app_tools.tools.parkwhiz_client import ParkWhizOAuth2Client


async def explore_sandbox():
    """Explore sandbox data to find date ranges and patterns."""
    
    print("=" * 80)
    print("ParkWhiz Sandbox Data Explorer")
    print("=" * 80)
    
    async with ParkWhizOAuth2Client() as client:
        # Query a wide date range to see what's available
        print("\n📅 Querying bookings from 2000 to 2030...")
        
        try:
            bookings = await client.get_customer_bookings(
                customer_email="test@example.com",
                start_date="2000-01-01",
                end_date="2030-12-31",
            )
            
            print(f"\n✅ Found {len(bookings)} total bookings")
            
            if not bookings:
                print("\n❌ No bookings found in sandbox")
                return
            
            # Analyze dates
            dates = []
            years = defaultdict(int)
            locations = defaultdict(int)
            statuses = defaultdict(int)
            
            for booking in bookings:
                start_time = booking.get("start_time", "")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        dates.append(dt)
                        years[dt.year] += 1
                    except:
                        pass
                
                # Track locations
                if "_embedded" in booking and "pw:location" in booking["_embedded"]:
                    loc_name = booking["_embedded"]["pw:location"].get("name", "Unknown")
                    locations[loc_name] += 1
                
                # Track pass status
                if "_embedded" in booking and "pw:parking_pass" in booking["_embedded"]:
                    status = booking["_embedded"]["pw:parking_pass"].get("status", "unknown")
                    statuses[status] += 1
            
            # Print date analysis
            if dates:
                dates.sort()
                print(f"\n📊 Date Range Analysis:")
                print(f"  Oldest booking: {dates[0].strftime('%Y-%m-%d')}")
                print(f"  Newest booking: {dates[-1].strftime('%Y-%m-%d')}")
                
                print(f"\n📈 Bookings by Year:")
                for year in sorted(years.keys()):
                    print(f"  {year}: {years[year]} bookings")
                
                print(f"\n📍 Top Locations:")
                for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {loc}: {count} bookings")
                
                print(f"\n🎫 Pass Statuses:")
                for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {status}: {count} bookings")
            
            # Show sample recent booking
            if dates:
                print(f"\n📦 Sample Recent Booking:")
                # Find booking with most recent date
                recent_bookings = [b for b in bookings if b.get("start_time")]
                if recent_bookings:
                    recent = max(
                        recent_bookings,
                        key=lambda b: datetime.fromisoformat(b["start_time"].replace("Z", "+00:00"))
                    )
                    
                    print(f"  ID: {recent.get('id')}")
                    print(f"  Start: {recent.get('start_time')}")
                    print(f"  End: {recent.get('end_time')}")
                    
                    if "_embedded" in recent and "pw:location" in recent["_embedded"]:
                        loc = recent["_embedded"]["pw:location"]
                        print(f"  Location: {loc.get('name')}")
                        print(f"  Address: {loc.get('address1')}, {loc.get('city')}, {loc.get('state')}")
                    
                    if "_embedded" in recent and "pw:parking_pass" in recent["_embedded"]:
                        pass_info = recent["_embedded"]["pw:parking_pass"]
                        print(f"  Pass Status: {pass_info.get('status')}")
                        print(f"  Pass Type: {pass_info.get('pass_type')}")
            
            # Recommendations
            print(f"\n💡 Recommendations:")
            if dates and dates[-1].year < 2020:
                print(f"  ⚠️  Sandbox data is very old (newest: {dates[-1].year})")
                print(f"  ⚠️  For testing with real tickets, you need production credentials")
                print(f"  ✅  Sandbox is good for testing the integration, not real data")
            else:
                print(f"  ✅  Sandbox has relatively recent data")
                print(f"  ✅  You can test with dates around {dates[-1].strftime('%Y-%m')}")
        
        except Exception as e:
            print(f"\n❌ Error querying sandbox: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(explore_sandbox())
