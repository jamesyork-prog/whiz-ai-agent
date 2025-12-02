"""
Generate curl commands showing the actual ParkWhiz API requests.

Run with: docker-compose exec parlant python tests/debug/generate_curl.py
"""

import os
import base64


def generate_token_curl():
    """Generate curl for OAuth2 token request."""
    client_id = os.getenv("PARKWHIZ_CLIENT_ID")
    client_secret = os.getenv("PARKWHIZ_CLIENT_SECRET")
    scope = os.getenv("PARKWHIZ_SCOPE", "partner")
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    token_url = f"{base_url.rstrip('/')}/oauth/token"
    
    print("=" * 80)
    print("1. OAuth2 Token Request")
    print("=" * 80)
    print()
    print(f"curl -X POST '{token_url}' \\")
    print(f"  -H 'Content-Type: application/x-www-form-urlencoded' \\")
    print(f"  -H 'Accept: application/json' \\")
    print(f"  -d 'grant_type=client_credentials' \\")
    print(f"  -d 'client_id={client_id}' \\")
    print(f"  -d 'client_secret={client_secret}' \\")
    print(f"  -d 'scope={scope}'")
    print()
    print("Response time: ~1-2 seconds")
    print()


def generate_bookings_curl():
    """Generate curl for bookings query."""
    base_url = os.getenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    
    bookings_url = f"{base_url.rstrip('/')}/bookings"
    
    print("=" * 80)
    print("2. Bookings Query Request (the slow one)")
    print("=" * 80)
    print()
    print(f"# First, get a token from step 1, then:")
    print()
    print(f"curl -X GET '{bookings_url}?q=customer_email:test@example.com' \\")
    print(f"  -H 'Authorization: Bearer <access_token_from_step_1>' \\")
    print(f"  -H 'Accept: application/json'")
    print()
    print("Response time: 15-25 seconds (!)")
    print()
    print("Alternative query formats that also work:")
    print(f"  - {bookings_url}?email=test@example.com")
    print(f"  - {bookings_url}  (no filter, returns all)")
    print()


def generate_use_case():
    """Explain the actual use case."""
    print("=" * 80)
    print("3. Actual Use Case")
    print("=" * 80)
    print()
    print("When a refund ticket comes in, we need to:")
    print()
    print("1. Extract customer email from ticket (e.g., 'customer@example.com')")
    print("2. Query ParkWhiz API for their bookings in a date range:")
    print("   GET /v4/bookings?q=customer_email:customer@example.com")
    print("   (or with start_date/end_date filters if needed)")
    print()
    print("3. Check if they have duplicate bookings for the same location/time")
    print("4. If duplicates found, automatically approve refund for one of them")
    print()
    print("Expected frequency: ~10-50 queries per day")
    print("Current sandbox performance: 20+ seconds per query")
    print()
    print("Question: Is this query pattern reasonable, or should we optimize it?")
    print("(e.g., add more filters, use different endpoint, etc.)")
    print()


if __name__ == "__main__":
    generate_token_curl()
    generate_bookings_curl()
    generate_use_case()
