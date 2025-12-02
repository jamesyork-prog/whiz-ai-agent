# Freshdesk Webhook Setup Guide

## Quick Start

Run the configuration generator:
```bash
python3 scripts/generate_webhook_config.py
```

This will generate:
- A secure webhook secret
- Complete configuration details
- A saved copy in `scripts/webhook_config_output.txt`

---

## Step-by-Step Configuration

### 1. Generate Configuration

```bash
python3 scripts/generate_webhook_config.py
```

Copy the `FRESHDESK_WEBHOOK_SECRET` value to your `.env` file.

### 2. Update Environment Variables

Add to your `.env` file:
```bash
FRESHDESK_WEBHOOK_SECRET=your-generated-secret-here
```

### 3. Make Your Webhook Publicly Accessible

**Option A: Production (Recommended)**
- Deploy your application to a server with a public IP or domain
- Use HTTPS (required by most webhook providers)
- Update the URL in Freshdesk to: `https://your-domain.com/webhook/freshdesk`

**Option B: Development/Testing with ngrok**
```bash
# Install ngrok: https://ngrok.com/download
# Start your webhook server
docker-compose up -d

# In another terminal, expose it publicly
ngrok http 8000

# Use the ngrok URL in Freshdesk
# Example: https://abc123.ngrok.io/webhook/freshdesk
```

**Option C: Development/Testing with localtunnel**
```bash
# Install localtunnel
npm install -g localtunnel

# Expose your local server
lt --port 8000

# Use the provided URL in Freshdesk
```

### 4. Configure Webhook in Freshdesk

1. **Login to Freshdesk** as an admin

2. **Navigate to Automations**
   - Go to: Admin → Workflows → Automations

3. **Create New Webhook**
   - Click "New Automation" or "New Webhook"

4. **Fill in the form** (based on your screenshot):

   **Request Type:**
   ```
   POST
   ```

   **URL:**
   ```
   https://your-domain.com/webhook/freshdesk
   ```
   (or your ngrok/localtunnel URL for testing)

   **Requires Authentication:**
   - Toggle OFF (we use webhook secret instead)

   **Add Custom Headers:**
   - Toggle ON
   - Add header:
     - Name: `X-Webhook-Secret`
     - Value: `your-generated-secret-here`

   **Encoding:**
   - Select the fields you want to send:
     - ✓ Ticket ID (`{{ticket.id}}`)
     - ✓ Subject (`{{ticket.subject}}`)
     - ✓ Description (`{{ticket.description}}`)
     - ✓ Ticket URL (`{{ticket.url}}`)
     - ✓ Product Specific Ticket URL (`{{ticket.portal_url}}`)
     - ✓ Status (`{{ticket.status}}`)
     - ✓ Priority (`{{ticket.priority}}`)
     - ✓ Requester Email (`{{ticket.requester.email}}`)
     - ✓ Requester Name (`{{ticket.requester.name}}`)

5. **Select Trigger Events**
   - ✓ Ticket is created
   - ✓ Ticket is updated
   - ✓ Note is added
   - ✓ Ticket priority is changed
   - ✓ Ticket status is changed

6. **Add Conditions (Optional)**
   - You can filter which tickets trigger the webhook
   - Example: Only tickets with specific tags or from specific groups

7. **Save the Webhook**

### 5. Restart Your Application

```bash
docker-compose up -d --force-recreate parlant
```

### 6. Test the Webhook

**Method 1: Freshdesk Test Button**
- In the webhook configuration, click "Test Webhook"
- Check your logs: `docker-compose logs -f parlant`

**Method 2: Create a Test Ticket**
- Create a new ticket in Freshdesk
- Monitor your logs for incoming webhook events

**Method 3: Manual Test with curl**
```bash
curl -X POST http://localhost:8000/webhook/freshdesk \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-secret-here" \
  -d '{
    "ticket_id": "12345",
    "ticket_subject": "Test Ticket",
    "ticket_description": "This is a test"
  }'
```

---

## Webhook Payload Format

Your system expects this JSON structure:

```json
{
  "ticket_id": "1234567",
  "ticket_subject": "Refund Request",
  "ticket_description": "Customer wants refund for booking #ABC123",
  "ticket_url": "https://yourdomain.freshdesk.com/a/tickets/1234567",
  "ticket_status": "Open",
  "ticket_priority": "High",
  "requester_email": "customer@example.com",
  "requester_name": "John Doe"
}
```

---

## Security Features

Your webhook implementation includes:

1. **Signature Verification**: Validates HMAC-SHA256 signatures
2. **Secret Validation**: Checks X-Webhook-Secret header
3. **Payload Validation**: Ensures required fields are present
4. **Rate Limiting**: Prevents abuse (if configured)
5. **Logging**: All webhook events are logged for audit

---

## Troubleshooting

### Webhook Not Receiving Events

**Check 1: Is the URL accessible?**
```bash
curl https://your-domain.com/webhook/freshdesk
```

**Check 2: Are containers running?**
```bash
docker-compose ps
```

**Check 3: Check logs**
```bash
docker-compose logs -f parlant
```

**Check 4: Verify environment variables**
```bash
docker-compose exec parlant env | grep FRESHDESK
```

### Authentication Failures

**Error: "Invalid webhook secret"**
- Verify the secret in `.env` matches what you configured in Freshdesk
- Restart containers after updating `.env`

**Error: "Missing X-Webhook-Secret header"**
- Ensure custom headers are enabled in Freshdesk
- Check the header name is exactly `X-Webhook-Secret`

### Payload Issues

**Error: "Missing required field"**
- Check the encoding section in Freshdesk includes all required fields
- Verify field names match what your code expects

---

## Monitoring

### View Webhook Logs
```bash
# Real-time logs
docker-compose logs -f parlant

# Last 100 lines
docker-compose logs --tail=100 parlant

# Search for webhook events
docker-compose logs parlant | grep "webhook"
```

### Database Audit Trail
```bash
# Connect to database
docker-compose exec postgres psql -U whizuser -d whizdb

# View recent webhook events
SELECT * FROM audit_logs WHERE action LIKE '%webhook%' ORDER BY timestamp DESC LIMIT 10;

# View webhook metrics
SELECT * FROM metrics WHERE metric_name LIKE '%webhook%' ORDER BY timestamp DESC LIMIT 10;
```

---

## Production Checklist

Before going live:

- [ ] Use HTTPS for webhook URL
- [ ] Set strong webhook secret (32+ characters)
- [ ] Configure firewall to allow Freshdesk IPs
- [ ] Enable webhook signature verification
- [ ] Set up monitoring and alerting
- [ ] Test with real tickets
- [ ] Document the configuration
- [ ] Set up log rotation
- [ ] Configure backup webhook URL (if supported)
- [ ] Test failure scenarios

---

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f parlant`
2. Verify configuration: `python3 scripts/generate_webhook_config.py`
3. Test locally: Use curl to send test payloads
4. Review Freshdesk webhook logs in their admin panel

For more details, see:
- `parlant/webhook_server.py` - Main webhook handler
- `parlant/tools/webhook_validator.py` - Validation logic
- `tests/test_webhook_server.py` - Test examples
