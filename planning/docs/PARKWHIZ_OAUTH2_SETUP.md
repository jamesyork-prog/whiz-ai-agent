# ParkWhiz OAuth2 Authentication Setup

## Summary

Successfully configured OAuth2 Bearer token authentication for the ParkWhiz API. The previous HMAC-based authentication was incorrect - ParkWhiz uses OAuth2 Client Credentials flow.

## Key Findings

### Authentication Method

- **Correct**: OAuth2 Client Credentials flow with Bearer tokens
- **Incorrect**: HMAC-SHA256 signatures (not supported by ParkWhiz)

### Token Endpoint

- **URL**: `https://api-sandbox.parkwhiz.com/v4/oauth/token` (sandbox)
- **URL**: `https://api.parkwhiz.com/v4/oauth/token` (production)
- **Method**: POST
- **Content-Type**: `application/x-www-form-urlencoded`

### Request Format

Credentials must be sent in the **request body**, not as Basic Auth header:

```
POST /v4/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=<your_client_id>
&client_secret=<your_client_secret>
&scope=partner
```

### Response Format

```json
{
  "access_token": "861326c1969910644a4dd42842f2f1a536627cc57e2de3ca334a0c96850b0d65",
  "token_type": "Bearer",
  "expires_in": 31556952,
  "scope": "partner",
  "created_at": 1764611359
}
```

Token expires in ~1 year (31556952 seconds).

### API Requests

Use the Bearer token in the Authorization header:

```
GET /v4/bookings?q=customer_email:test@example.com
Authorization: Bearer <access_token>
Accept: application/json
```

### Response Format

The `/v4/bookings` endpoint returns a **list directly**, not wrapped in a dict:

```json
[
  {
    "id": 3,
    "customer_id": 123,
    "start_time": "2007-08-16T06:00:00.000-05:00",
    "end_time": "2007-08-16T18:00:00.000-05:00",
    "price_paid": 15.00,
    "full_price": 20.00,
    "purchased_at": "2007-08-15T10:30:00.000-05:00",
    "type": "reservation",
    "on_demand": false,
    "cancellable": true,
    "_embedded": { ... },
    "_links": { ... }
  },
  ...
]
```

## Configuration

### Environment Variables

```bash
# OAuth2 Credentials (same for sandbox and production)
PARKWHIZ_CLIENT_ID=da1d8a94234b9cf058f57dd579ed548b0dbe152cbd613bb690752e8f3bd6cccf
PARKWHIZ_CLIENT_SECRET=bff63429dcdabf0977b8b3020944cd5381e2a6af887d36c57e0e4ac22b0521a1
PARKWHIZ_SCOPE=partner

# Environment Selection
PARKWHIZ_ENV=sandbox  # or "production"

# API URLs
PARKWHIZ_SANDBOX_URL=https://api-sandbox.parkwhiz.com/v4
PARKWHIZ_PRODUCTION_URL=https://api.parkwhiz.com/v4

# Timeouts (sandbox is slow, needs 30s)
PARKWHIZ_TIMEOUT=30
PARKWHIZ_MAX_RETRIES=3

# Feature Flags
PARKWHIZ_DUPLICATE_DETECTION_ENABLED=true
```

### Docker Compose

All environment variables are already configured in `docker-compose.yml` under the `parlant` service.

## Implementation

### Client Class

Use `ParkWhizOAuth2Client` from `parlant/tools/parkwhiz_client.py`:

```python
from app_tools.tools.parkwhiz_client import ParkWhizOAuth2Client

async with ParkWhizOAuth2Client() as client:
    # Automatically handles token generation and refresh
    bookings = await client.get_customer_bookings(
        customer_email="customer@example.com",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
```

### Features

- **Automatic token management**: Generates and refreshes tokens automatically
- **Token caching**: Reuses tokens until they expire (within 24 hours of expiration)
- **Response caching**: Caches booking queries for 2 minutes (configurable via `PARKWHIZ_CACHE_TTL`)
- **Retry logic**: Automatically retries on timeout/network errors (3 attempts with exponential backoff)
- **Connection pooling**: Reuses HTTP connections for better performance
- **Comprehensive logging**: Logs all requests, responses, and errors

## Performance Notes

### Sandbox Performance

The sandbox API is **very slow**:
- Token generation: ~1-2 seconds
- Booking queries: **15-25 seconds** (!)
- Requires 30-second timeout to avoid failures

### Production Performance

Production API should be faster (not yet tested with these credentials).

## Testing

### Quick Test

```bash
docker-compose exec parlant python tests/debug/test_oauth2_auth.py
```

### Test Different Auth Methods

```bash
docker-compose exec parlant python tests/debug/test_oauth_methods.py
```

### Test Bookings API

```bash
docker-compose exec parlant python tests/debug/test_bookings_api.py
```

## Migration Notes

### Old HMAC Client (Deprecated)

The `ParkWhizClient` class using HMAC authentication is **deprecated** and should not be used. It was based on incorrect assumptions about the API.

### New OAuth2 Client (Current)

Use `ParkWhizOAuth2Client` for all ParkWhiz API interactions.

## Troubleshooting

### 401 Unauthorized

- Verify `PARKWHIZ_CLIENT_ID` and `PARKWHIZ_CLIENT_SECRET` are set correctly
- Ensure credentials are in request body, not Basic Auth header
- Check that scope is set to `partner`

### Timeout Errors

- Increase `PARKWHIZ_TIMEOUT` to 30 seconds (sandbox is slow)
- Check network connectivity
- Verify the API endpoint URL is correct

### Container Not Picking Up Env Changes

After changing `.env`, recreate the container:

```bash
docker-compose up -d --force-recreate parlant
```

## References

- ParkWhiz API Documentation: https://developer.parkwhiz.com/v4/#authentication
- OAuth2 Client Credentials: https://www.rfc-editor.org/rfc/rfc6749#section-4.4
