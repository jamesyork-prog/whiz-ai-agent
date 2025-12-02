# ParkWhiz API Quick Reference

## Authentication (OAuth2)

### Get Token
```bash
curl -X POST 'https://api-sandbox.parkwhiz.com/v4/oauth/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=YOUR_CLIENT_ID' \
  -d 'client_secret=YOUR_CLIENT_SECRET' \
  -d 'scope=partner'
```

### Use Token
```bash
curl -X GET 'https://api-sandbox.parkwhiz.com/v4/bookings?q=customer_email:test@example.com' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

## Python Usage

```python
from app_tools.tools.parkwhiz_client import ParkWhizOAuth2Client

async with ParkWhizOAuth2Client() as client:
    # Search bookings
    bookings = await client.get_customer_bookings(
        customer_email="customer@example.com",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
    
    # Delete booking (refund)
    result = await client.delete_booking(booking_id=12345)
```

## Environment Variables

```bash
PARKWHIZ_CLIENT_ID=your_client_id
PARKWHIZ_CLIENT_SECRET=your_client_secret
PARKWHIZ_SCOPE=partner
PARKWHIZ_ENV=sandbox  # or production
PARKWHIZ_TIMEOUT=30   # seconds
```

## Testing

```bash
# Test OAuth2 authentication
docker-compose exec parlant python tests/debug/test_oauth2_auth.py

# Test bookings API
docker-compose exec parlant python tests/debug/test_bookings_api.py

# Generate curl commands
docker-compose exec parlant python tests/debug/generate_curl.py
```

## Performance

| Environment | Token Gen | Booking Query | Timeout |
|-------------|-----------|---------------|---------|
| Sandbox     | 1-2s      | 15-25s        | 30s     |
| Production  | TBD       | TBD           | TBD     |

## Common Issues

### 401 Unauthorized
- Check credentials in `.env`
- Ensure credentials in request body (not Basic Auth)
- Recreate container: `docker-compose up -d --force-recreate parlant`

### Timeout
- Increase `PARKWHIZ_TIMEOUT` to 30s
- Sandbox is slow, production should be faster

### Container not picking up changes
```bash
docker-compose up -d --force-recreate parlant
```

## Documentation

- **Setup Guide:** `planning/docs/PARKWHIZ_OAUTH2_SETUP.md`
- **Implementation Summary:** `planning/docs/OAUTH2_IMPLEMENTATION_SUMMARY.md`
- **Migration Guide:** `.kiro/specs/parkwhiz-api-integration/OAUTH2_UPDATE.md`
- **ParkWhiz Docs:** https://developer.parkwhiz.com/v4/#authentication
