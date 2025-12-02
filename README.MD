# Parlant-Pipecat Voice Assistant 🎙️

A voice-enabled customer support system combining Parlant's AI agent framework with Pipecat's real-time voice pipeline.

## Features

- 🗣️ **Voice Interface** - WebRTC-based voice chat with STT/TTS
- 🤖 **AI Agent** - Structured conversation journeys with Parlant
- 🧠 **Hybrid Decision Engine** - Rule-based + LLM-powered refund decisions
- 📋 **Policy-Driven** - Refund rules loaded from JSON/Markdown configuration
- 🗄️ **Database Integration** - PostgreSQL for audit logs and metrics
- 🐳 **Docker Compose** - One-command deployment
- 📞 **Automated Refund Processing** - Complete ticket-to-decision workflow
- 🔗 **Webhook Automation** - Freshdesk webhook integration for real-time ticket processing

## Architecture

```
Architecture Overview
Three main components:

Parlant (Port 8800) - The AI agent backend

Manages conversation journeys (structured dialogue flows)
Implements a refund request workflow with conditional logic
Connects to PostgreSQL for product data
Provides tools: check_refund_eligibility, process_refund, find_products


Pipecat (Port 7860) - The voice interface layer

Handles WebRTC audio streaming from browser
Speech-to-text using OpenAI Whisper
Text-to-speech using OpenAI TTS
Voice Activity Detection (VAD) using Silero
ParlantBridge: Custom processor that connects voice pipeline to Parlant


PostgreSQL (Port 5432) - Database

Product catalog with sample electronics/accessories
Order history structure
```

```
Browser (WebRTC) ←→ Pipecat (Voice I/O) ←→ Parlant (AI Logic) ←→ PostgreSQL
```

## Key Flow

### Voice Interaction
```
User speaks → Pipecat (STT) → ParlantBridge → Parlant Agent → Response
                                                    ↓
                                              PostgreSQL
                                                    ↓
Response ← Pipecat (TTS) ← ParlantBridge ← Agent decides action
```

### Refund Decision Flow
```
Freshdesk Ticket → Extract Booking Info (LLM) → Apply Rules (Python) →
  ├─ High Confidence → Approve/Deny (< 2s)
  └─ Low Confidence → LLM Analysis (< 10s) → Approve/Deny/Escalate
    → Document Decision in Freshdesk → Tag Ticket
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/parlant-pipecat-voice.git
   cd parlant-pipecat-voice
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Parlant UI: http://localhost:8800
   - Voice Client: http://localhost:7860/client
   - Database: localhost:5432

### First Use

1. Open http://localhost:7860/client in your browser
2. Click "Connect" and allow microphone access
3. Say "Hello" to start chatting with the assistant
4. Try: "I'd like to get a refund" or "Show me your products"

## Services

### Parlant (Port 8800)
The AI agent backend with:
- **Hybrid Decision Engine**: Combines rule-based logic with LLM analysis
- **Policy-Based Decisions**: Loads refund rules from JSON/Markdown files
- **Automated Ticket Processing**: Freshdesk integration for ticket ingestion
- **Booking Extraction**: Pattern-based + LLM extraction of booking information
- **Security Scanning**: Lakera API integration for content safety
- **Audit Logging**: PostgreSQL tracking of all decisions and actions
- **Session Management**: Stateful conversation handling

### Pipecat (Port 7860)
The voice interface providing:
- Real-time speech-to-text (OpenAI Whisper)
- Text-to-speech (OpenAI TTS)
- WebRTC audio streaming
- Event-driven integration with Parlant

### PostgreSQL (Port 5432)
Database containing:
- Product catalog
- Customer data
- Order history

## Webhook Automation

The system supports **two distinct processing modes** for ticket handling: automated webhook-triggered processing and interactive chat-based processing.

### Processing Modes

#### 1. Automated Processing (Webhook-Triggered)

When Freshdesk sends a webhook notification for ticket creation or updates, the system automatically processes the ticket in the background without human interaction.

**Flow:**
```
Freshdesk Ticket Created/Updated
  ↓
Webhook POST → /webhook/freshdesk
  ↓
Signature Validation (HMAC-SHA256)
  ↓
Journey Router → Automated Processing Journey
  ↓
Silent Background Processing (no chat states)
  ↓
Decision Made → Ticket Updated in Freshdesk
  ↓
HTTP 200 Response to Freshdesk
```

**Characteristics:**
- **No user interaction**: Runs completely in the background
- **Fast processing**: Target < 15 seconds end-to-end
- **Secure**: HMAC-SHA256 signature verification
- **Filtered**: Only processes refund-related events
- **Logged**: Complete audit trail of all actions

#### 2. Interactive Processing (Chat-Triggered)

When a support agent types a message in the Parlant chat interface, the system provides step-by-step feedback during processing.

**Flow:**
```
Agent: "Process ticket 12345"
  ↓
Journey Router → Interactive Processing Journey
  ↓
Chat State: "Fetching ticket data..."
  ↓
Chat State: "Running security scan..."
  ↓
Chat State: "Making decision..."
  ↓
Chat State: "Decision: Approved - Adding note..."
  ↓
Final Summary Presented to Agent
```

**Characteristics:**
- **User feedback**: Shows progress at each step
- **Interactive**: Agent can see what's happening
- **Flexible**: Agent can intervene if needed
- **Educational**: Helps agents understand the process

### Journey Routing

The system automatically routes requests to the appropriate journey based on the trigger source:

| Trigger Source | Journey Type | Chat States | Use Case |
|----------------|--------------|-------------|----------|
| Webhook | Automated Processing | No | Background automation |
| Chat Message | Interactive Processing | Yes | Agent-initiated processing |

**Routing Logic:**
```python
def route_to_journey(trigger_source: str) -> str:
    if trigger_source == "webhook":
        return "Automated Ticket Processing"
    else:
        return "Interactive Ticket Processing"
```

### Webhook Configuration

#### Prerequisites

- Publicly accessible webhook endpoint (or ngrok for testing)
- Webhook secret for signature verification
- Freshdesk admin access

#### Quick Setup

1. **Configure environment variables** in `.env`:
   ```bash
   WEBHOOK_SECRET=your-secure-random-secret
   WEBHOOK_ENABLED=true
   WEBHOOK_PORT=8801
   WEBHOOK_PATH=/webhook/freshdesk
   WEBHOOK_EVENTS=ticket_created,ticket_updated
   ```

2. **Expose webhook port** in `docker-compose.yml`:
   ```yaml
   services:
     parlant:
       ports:
         - "8800:8800"  # Parlant UI
         - "8801:8801"  # Webhook endpoint
   ```

3. **Configure Freshdesk webhook**:
   - URL: `https://your-domain.com:8801/webhook/freshdesk`
   - Events: Ticket Created, Ticket Updated
   - Secret: Same as `WEBHOOK_SECRET` in `.env`
   - Custom Header: `X-Freshdesk-Signature` = `{{webhook.signature}}`

4. **Restart services**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

#### Verification

Test the webhook endpoint:
```bash
# Health check
curl http://localhost:8801/webhook/health

# Expected response:
# {"status":"healthy","timestamp":"2025-11-17T10:30:00Z"}
```

Monitor webhook events:
```bash
docker-compose logs -f parlant | grep -E "webhook|journey"
```

### Security Features

#### 1. Signature Verification

All webhooks must include a valid HMAC-SHA256 signature:
- Header: `X-Freshdesk-Signature`
- Algorithm: HMAC-SHA256
- Secret: Configured in `WEBHOOK_SECRET`

Invalid signatures are rejected with HTTP 401.

#### 2. Event Filtering

Only configured event types are processed:
- `ticket_created`: New refund requests
- `ticket_updated`: Updates to existing tickets (refund-related only)

Other events are logged and ignored.

#### 3. Rate Limiting

Protects against abuse:
- Default: 100 requests per minute
- Configurable via `WEBHOOK_RATE_LIMIT`
- Exceeding limit returns HTTP 429

#### 4. Deduplication

Prevents duplicate processing:
- Tracks last 100 events
- Ignores duplicates within 60 seconds
- Logs duplicate detection

### Monitoring

#### Key Metrics

Track webhook performance:
- **Delivery Rate**: Webhooks received per minute
- **Success Rate**: Percentage of successfully processed webhooks
- **Processing Time**: Average time to process (target: < 15s)
- **Error Rate**: Percentage of failed processing
- **Signature Failures**: Potential security issues

#### Logging

All webhook events are logged with structured JSON:
```json
{
  "timestamp": "2025-11-17T10:30:00Z",
  "level": "INFO",
  "component": "webhook_endpoint",
  "event": "webhook_received",
  "ticket_id": "12345",
  "event_type": "ticket_created",
  "processing_time_ms": 1247,
  "journey": "Automated Ticket Processing",
  "decision": "Approved"
}
```

View webhook logs:
```bash
# All webhook activity
docker-compose logs parlant | grep webhook

# Journey activations
docker-compose logs parlant | grep journey_activated

# Decisions made
docker-compose logs parlant | grep decision_made
```

### Documentation

Comprehensive guides are available in `.kiro/specs/webhook-automation/`:

- **[WEBHOOK_SETUP_GUIDE.md](.kiro/specs/webhook-automation/WEBHOOK_SETUP_GUIDE.md)**: Complete setup instructions
  - Environment configuration
  - Freshdesk webhook setup
  - Security best practices
  - Production deployment guide

- **[TROUBLESHOOTING_GUIDE.md](.kiro/specs/webhook-automation/TROUBLESHOOTING_GUIDE.md)**: Common issues and solutions
  - Webhook not receiving events
  - Signature validation failures
  - Journey activation issues
  - Network connectivity problems
  - Diagnostic commands

- **[TESTING_GUIDE.md](.kiro/specs/webhook-automation/TESTING_GUIDE.md)**: Testing procedures
  - Manual testing with curl
  - Freshdesk test webhook
  - Automated test suite
  - End-to-end testing scenarios
  - Performance testing

### Testing

Test webhook functionality:

```bash
# Run webhook tests
docker-compose exec parlant pytest tests/test_webhook_event_handling.py -v
docker-compose exec parlant pytest tests/test_webhook_routing_integration.py -v
docker-compose exec parlant pytest tests/test_journey_router.py -v

# Test webhook validator
docker-compose exec parlant pytest tests/tools/test_webhook_validator.py -v

# Test webhook configuration
docker-compose exec parlant pytest tests/tools/test_webhook_config.py -v
```

Manual testing with curl:
```bash
# Generate signature
SECRET="your-webhook-secret"
PAYLOAD='{"ticket_id":"12345","event":"ticket_created"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send test webhook
curl -X POST http://localhost:8801/webhook/freshdesk \
  -H "Content-Type: application/json" \
  -H "X-Freshdesk-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

### Implementation Status

**Phase 1-9: Core Implementation** ✅ COMPLETE
- Webhook endpoint with FastAPI
- Signature validation and security
- Automated and interactive journeys
- Journey routing logic
- Event filtering and deduplication
- Comprehensive logging
- Metrics tracking
- Configuration management

**Phase 10: Documentation** ✅ COMPLETE
- Setup guide
- Troubleshooting guide
- Testing guide
- README integration

**Phase 11-14: Testing & Deployment** 🚧 PENDING
- Unit tests
- Integration tests
- Performance testing
- Production deployment

## Policy-Based Decision Making

The system uses a **hybrid approach** combining rule-based logic with LLM-powered analysis to make intelligent refund decisions based on configurable policy documents.

### Decision Flow

1. **Extract Booking Info**: Uses pattern matching + Gemini LLM to extract structured booking data from ticket text
2. **Apply Rules**: Deterministic Python logic for clear-cut cases (7+ days before event → Approve, etc.)
3. **LLM Analysis**: For uncertain cases, Gemini analyzes with full policy context
4. **Map Cancellation Reason**: Approved decisions get appropriate ParkWhiz cancellation reason
5. **Document Decision**: Private note added to Freshdesk with reasoning and confidence

### Components

All core components are **fully implemented and integrated**:

- **PolicyLoader** ✅: Loads refund rules from `parlant/context/processed/` (JSON/MD files)
- **BookingExtractor** ✅: Extracts booking info using pattern matching + LLM fallback
- **RuleEngine** ✅: Applies deterministic business rules (< 2s execution)
- **LLMAnalyzer** ✅: Uses Gemini for complex case analysis (< 10s execution)
- **CancellationReasonMapper** ✅: Maps decisions to ParkWhiz cancellation reasons
- **DecisionMaker** ✅: Orchestrates the complete hybrid workflow
- **extract_booking_info_from_note** ✅: Parlant tool for booking extraction
- **triage_ticket** ✅: Parlant tool for decision-making
- **document_decision** ✅: Parlant tool for documenting decisions in Freshdesk

### Decision Outcomes

The system produces one of three decision types:

- **Approved**: Clear policy support, includes refund amount and ParkWhiz cancellation reason
- **Denied**: Policy violation with specific reasoning and customer-friendly explanation
- **Needs Human Review**: Missing critical data, ambiguous case, or low confidence score

### Confidence Levels

Each decision includes a confidence score that determines whether LLM analysis is needed:

- **High Confidence (>= 0.8)**: Clear-cut case matching deterministic rules
  - Example: Cancellation 7+ days before event with confirmed booking
  - Processing: Rule-based only, no LLM call needed
  - Decision time: < 2 seconds

- **Medium Confidence (0.5 - 0.8)**: Some ambiguity or missing context
  - Example: Cancellation 4 days before event with unclear booking type
  - Processing: Rule-based result + LLM analysis for validation
  - Decision time: < 10 seconds

- **Low Confidence (< 0.5)**: Significant uncertainty or edge case
  - Example: Multiple bookings mentioned, conflicting dates, or missing event date
  - Processing: LLM analysis with full policy context
  - Decision time: < 10 seconds
  - Escalation: May result in "Needs Human Review" if LLM confidence is also low

### Escalation Criteria

Cases are escalated to "Needs Human Review" when:

1. **Missing Critical Data**:
   - No booking ID found in ticket
   - Event date cannot be determined
   - Cancellation date is missing or invalid

2. **Ambiguous Scenarios**:
   - Multiple bookings mentioned without clear indication of which is disputed
   - Conflicting information between ticket description and notes
   - Booking type cannot be determined (confirmed vs on-demand vs third-party)

3. **Low Confidence**:
   - Rule engine produces low confidence (< 0.5)
   - LLM analysis also produces low confidence (< 0.5)
   - LLM explicitly recommends human review

4. **Edge Cases**:
   - Partial refund requests (system only handles full refunds in MVP)
   - Special circumstances mentioned (medical emergency, natural disaster, etc.)
   - Policy exceptions or goodwill requests

5. **System Errors**:
   - LLM API failures or timeouts
   - Policy files cannot be loaded
   - Booking extraction fails completely

### Decision Documentation

The `document_decision` tool automatically documents all decisions in Freshdesk:

**Private Note Format:**
```
**AGENT DECISION: Approved**

**Reasoning:**
Cancellation made 8 days before event start. Customer has confirmed booking 
(PW-12345) for $45.00. Per policy, cancellations 7+ days in advance qualify 
for full refund.

**Policy Applied:**
pre_arrival_7_days (Rule-based decision)

**ParkWhiz Cancellation Reason:** Pre-arrival

**Confidence Level:** high
**Method Used:** rules
**Processing Time:** 1247ms

---
This decision was made by the Whiz Agent. Please review before processing the refund.
```

**Ticket Updates:**
- Adds private note visible only to agents
- Tags ticket with "Processed by Whiz Agent"
- Preserves all existing ticket data and conversations
- Graceful error handling with partial success states

### Complete Workflow

The end-to-end refund processing workflow:

```
1. Ticket Created in Freshdesk
   ↓
2. Security Scan (Lakera API)
   ↓ (if safe)
3. Extract Booking Info
   ├─ Pattern matching (regex + HTML parsing)
   └─ LLM extraction (if patterns fail)
   ↓
4. Apply Business Rules
   ├─ Calculate days_before_event
   ├─ Check booking type
   └─ Match against rule conditions
   ↓
5. Decision Logic
   ├─ High Confidence → Return decision
   └─ Low Confidence → LLM Analysis
       ├─ Load full policy context
       ├─ Gemini analyzes case
       └─ Return decision with reasoning
   ↓
6. Map Cancellation Reason (if Approved)
   ├─ Keyword matching on reasoning
   └─ Select ParkWhiz dropdown value
   ↓
7. Document Decision
   ├─ Format private note
   ├─ Add note to Freshdesk
   └─ Tag ticket "Processed by Whiz Agent"
   ↓
8. Human Review (MVP)
   ├─ Agent reviews decision
   ├─ Agent processes refund manually
   └─ Agent provides feedback
```

**Integration Points:**

- **Freshdesk API**: Ticket retrieval, note creation, tag updates
- **Gemini API**: Booking extraction, complex case analysis
- **Lakera API**: Content security scanning
- **PostgreSQL**: Audit logging and metrics (future)
- **ParkWhiz API**: Booking data retrieval (fallback), refund processing (post-MVP)

### Policy Files

The system loads refund policies from configuration files in `parlant/context/processed/`. This allows policy updates without code changes.

#### File Locations

```
parlant/context/processed/
├── refund_rules.json              # Structured business rules
├── refund_guide.json              # Policy guidance text
├── refund_scenario_decision_chart.md  # Decision tree logic
├── refund_policy_condensed.md     # Human-readable policy summary
└── ai_vs_human_refund_scenarios.md    # Escalation criteria
```

#### Policy File Formats

**refund_rules.json** - Deterministic business rules:
```json
{
  "rules": [
    {
      "id": "pre_arrival_7_days",
      "condition": "days_before_event >= 7",
      "decision": "Approved",
      "reasoning": "Cancellation made 7+ days before event qualifies for full refund",
      "confidence": 0.95,
      "priority": 1
    },
    {
      "id": "post_event",
      "condition": "days_before_event < 0",
      "decision": "Denied",
      "reasoning": "Event has already occurred, no refund available",
      "confidence": 0.95,
      "priority": 2
    }
  ]
}
```

**refund_guide.json** - Policy guidance for LLM:
```json
{
  "general_policy": "Full refunds available for cancellations 7+ days before event...",
  "special_cases": {
    "oversold_location": "Approve refund regardless of timing",
    "duplicate_booking": "Approve refund for duplicate pass",
    "third_party": "Escalate to human review"
  }
}
```

**Markdown files** - Human-readable policy documentation that gets included in LLM context for complex case analysis.

#### Adding New Rules

To add a new business rule:

1. **Edit refund_rules.json**:
   ```json
   {
     "id": "new_rule_id",
     "condition": "booking_type == 'monthly' AND days_before_event >= 3",
     "decision": "Approved",
     "reasoning": "Monthly passes can be cancelled 3+ days in advance",
     "confidence": 0.9,
     "priority": 5
   }
   ```

2. **Update rule_engine.py** (if new condition logic needed):
   ```python
   # In RuleEngine.apply_rules()
   if booking_info.get("booking_type") == "monthly" and days_before_event >= 3:
       return {
           "decision": "Approved",
           "reasoning": "Monthly passes can be cancelled 3+ days in advance",
           "policy_rule": "new_rule_id",
           "confidence": "high"
       }
   ```

3. **Restart the service**:
   ```bash
   docker-compose restart parlant
   ```

4. **Test the new rule**:
   ```bash
   docker-compose exec parlant pytest tests/tools/test_rule_engine.py -v
   ```

#### Updating Policy Guidance

To update LLM policy context:

1. **Edit markdown files** in `parlant/context/processed/`:
   - `refund_policy_condensed.md` - Main policy text
   - `ai_vs_human_refund_scenarios.md` - Escalation guidelines

2. **Update refund_guide.json** for structured guidance:
   ```json
   {
     "special_cases": {
       "new_scenario": "Policy guidance for this scenario"
     }
   }
   ```

3. **Restart to reload policies**:
   ```bash
   docker-compose restart parlant
   ```

The PolicyLoader caches files at startup, so changes require a service restart.

#### Policy Validation

The system validates policy files on startup:

- **JSON files**: Must be valid JSON with expected structure
- **Required fields**: Each rule must have id, condition, decision, reasoning
- **Confidence values**: Must be between 0.0 and 1.0
- **Priority values**: Must be positive integers (lower = higher priority)

If validation fails, the system logs errors and falls back to minimal default rules.

### Performance

- **Rule-based decisions**: < 2 seconds
- **LLM-based decisions**: < 10 seconds
- **Policy caching**: Loaded once at startup
- **Pattern extraction**: Reduces LLM API calls by ~60%

### Implementation Status

**Phase 1: Core Components** ✅ COMPLETE (November 14, 2025)
- All 7 core components implemented and integrated
- Hybrid decision-making workflow fully operational
- Pattern-based extraction with LLM fallback working
- Rule engine applying deterministic business logic
- LLM analyzer handling complex edge cases
- Cancellation reason mapping for approved refunds
- Decision orchestration via DecisionMaker

**Phase 2: Tool Integration** ✅ COMPLETE (November 14, 2025)
- `extract_booking_info_from_note` tool updated with BookingExtractor
- `triage_ticket` tool updated with DecisionMaker
- Both tools tested and passing all test cases (11/11 each)
- Graceful error handling and escalation logic implemented

**Phase 3: MVP Documentation** ✅ COMPLETE (November 14, 2025)
- `document_decision` tool implemented and integrated
- Adds private notes to Freshdesk with decision details
- Tags tickets with "Processed by Whiz Agent"
- Includes ParkWhiz cancellation reason for approved refunds
- Graceful error handling with partial success states

**Phase 4: Testing & Monitoring** 🚧 IN PROGRESS
- Add comprehensive logging and monitoring
- Create unit tests for remaining components
- Complete integration testing with real tickets

### MVP Scope

The current implementation **documents decisions** in Freshdesk but does NOT automatically process refunds via ParkWhiz API. This confidence-building phase allows the team to:

1. **Verify Decision Accuracy**: Review agent decisions against human judgment
2. **Tune Policies**: Adjust rules and thresholds based on real cases
3. **Build Trust**: Demonstrate consistent, policy-compliant decisions
4. **Identify Edge Cases**: Discover scenarios that need additional rules

#### What Works Now (MVP Phase)

**✅ Complete Decision-Making Pipeline:**
- Booking information extraction from ticket notes (pattern + LLM)
- Rule-based decision making for clear-cut cases (< 2s)
- LLM-powered analysis for complex scenarios (< 10s)
- Cancellation reason mapping for approved refunds
- Confidence scoring and method tracking
- Error handling with escalation to human review

**✅ Freshdesk Integration:**
- Decision documentation in private notes
- Ticket tagging with "Processed by Whiz Agent"
- Structured note format with decision, reasoning, policy, confidence
- ParkWhiz cancellation reason included for approved decisions
- Graceful error handling with partial success states

**✅ Monitoring & Observability:**
- Processing time tracking (rule vs LLM vs hybrid)
- Confidence level reporting
- Method used tracking (pattern extraction vs LLM)
- Error logging for failed extractions or API issues

#### What's NOT Included (MVP Limitations)

**❌ Automatic Refund Processing:**
- No ParkWhiz API calls to process refunds
- No automatic booking cancellations
- No payment processing or refund transactions
- Human agents must manually process approved refunds

**❌ Advanced Features:**
- No partial refund calculations (only full refunds)
- No multi-booking handling (escalates to human)
- No automatic customer notifications
- No refund status tracking

#### Next Steps (Post-MVP)

**Phase 1: Validation & Tuning (Current)**
- Review 50-100 agent decisions against human judgment
- Measure accuracy, precision, and recall
- Identify policy gaps and edge cases
- Tune confidence thresholds

**Phase 2: ParkWhiz Integration**
- Implement ParkWhiz refund API calls
- Add booking cancellation logic
- Implement refund transaction processing
- Add rollback handling for failed refunds

**Phase 3: Advanced Features**
- Partial refund calculations
- Multi-booking support
- Automatic customer notifications
- Refund status tracking and reporting

**Phase 4: Full Automation**
- Remove human review requirement for high-confidence decisions
- Implement automatic processing for Approved decisions
- Add real-time monitoring and alerting
- Deploy to production with full automation

#### How to Use MVP

**For Customer Service Agents:**

1. **Ticket arrives** in Freshdesk with refund request
2. **Agent triggers** the Whiz Agent (manual or automatic)
3. **Agent reviews** the private note with decision and reasoning
4. **Agent validates** the decision against their judgment
5. **Agent processes** the refund manually in ParkWhiz (if approved)
6. **Agent provides feedback** on decision accuracy

**For System Administrators:**

1. **Monitor** decision distribution (Approved/Denied/Escalated)
2. **Review** escalated cases to identify policy gaps
3. **Tune** confidence thresholds based on accuracy metrics
4. **Update** policy files to handle new scenarios
5. **Track** processing times and API usage

**For Developers:**

1. **Run tests** to verify decision accuracy: `docker-compose exec parlant pytest`
2. **Review logs** for errors or unexpected behavior
3. **Update rules** in `parlant/context/processed/refund_rules.json`
4. **Add test cases** for new scenarios
5. **Monitor** Gemini API usage and costs

## ParkWhiz Duplicate Booking Detection

The system integrates with the ParkWhiz API to automatically detect and resolve duplicate booking issues. When customers claim they were "charged twice" or "paid again," the system queries ParkWhiz to find duplicate bookings for the same event, identifies which booking was used, and automatically refunds the unused duplicate booking.

### Overview

**Problem:** Customers sometimes accidentally create duplicate bookings for the same parking event, resulting in double charges. Manual verification is time-consuming and error-prone.

**Solution:** Automated duplicate detection that:
- Queries ParkWhiz API for customer bookings around the event date
- Identifies duplicates by matching location and time overlap
- Determines which booking was actually used (checked in/out)
- Automatically refunds the unused duplicate booking
- Documents the entire process in Freshdesk

### How It Works

#### Detection Flow

```
Customer Claims "Paid Again"
  ↓
Extract Booking Info (email, event_date, location)
  ↓
Query ParkWhiz API (GET /v4/bookings)
  ├─ Search window: event_date ± 1 day
  └─ Filter by customer email
  ↓
Analyze Bookings for Duplicates
  ├─ Match by location_id
  ├─ Check time overlap (>= 50%)
  └─ Group duplicate sets
  ↓
Determine Action
  ├─ 0-1 bookings → DENY (no duplicates)
  ├─ 2 bookings → Identify used vs unused
  │   ├─ Check status: completed/checked_in = used
  │   ├─ Check status: confirmed/pending = unused
  │   └─ Refund unused booking (DELETE /v4/bookings/{id})
  └─ 3+ bookings → ESCALATE (too complex)
  ↓
Document Decision in Freshdesk
  ├─ Add private note with details
  ├─ Tag ticket "Processed by Whiz Agent"
  └─ Tag ticket "Refunded" (if applicable)
```

#### Integration with Decision Workflow

The duplicate detection is seamlessly integrated into the existing refund processing workflow:

```python
# In process_ticket_workflow.py
if _is_paid_again_claim(ticket_text):
    # Trigger duplicate detection
    detection = await detect_duplicate_bookings(
        context=context,
        customer_email=booking_info.get("customer_email"),
        event_date=booking_info.get("event_date"),
        location_name=booking_info.get("location")
    )
    
    # Use detection result to make decision
    if detection.data.get("action_taken") == "refunded":
        decision = "Approved"
        reasoning = f"Duplicate booking detected and refunded. {detection.data.get('explanation')}"
    elif detection.data.get("action_taken") == "escalate":
        decision = "Needs Human Review"
        reasoning = f"Multiple duplicates found. {detection.data.get('explanation')}"
    else:
        decision = "Denied"
        reasoning = f"No duplicate bookings found. {detection.data.get('explanation')}"
```

### Components

#### 1. ParkWhiz API Client (`parkwhiz_client.py`)

Low-level HTTP client for ParkWhiz API v4 with OAuth2 authentication.

**Status:** ✅ Tested and working with sandbox credentials (December 2025)

**Key Features:**
- OAuth2 Client Credentials flow for authentication
- Automatic token refresh before expiration (tokens last ~1 year)
- Response caching (2 minutes default, configurable)
- Connection pooling and timeout configuration
- Exponential backoff retry logic for network errors
- Custom exceptions for different error types

**Performance Notes:**
- Sandbox API: 15-25 seconds per request (requires 30s timeout)
- Production API: Expected to be significantly faster
- Token generation: ~1-2 seconds

**Methods:**
```python
class ParkWhizClient:
    async def get_customer_bookings(
        customer_email: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]
    
    async def delete_booking(booking_id: int) -> Dict[str, Any]
```

#### 2. Duplicate Booking Analyzer (`duplicate_booking_analyzer.py`)

Analyzes bookings to detect duplicates and determine which to refund.

**Detection Logic:**
- **Location Matching**: Bookings must be at exact same location (location_id)
- **Time Overlap**: Bookings must overlap by >= 50% of their time windows
- **Usage Detection**: Checks status field to determine which booking was used
  - Used: "completed", "checked_in", "checked_out"
  - Unused: "confirmed", "pending", "reserved"

**Decision Logic:**
- 0-1 bookings: No duplicates → DENY claim
- 2 bookings: Refund unused → APPROVE
- 3+ bookings: Too complex → ESCALATE

#### 3. Duplicate Detection Tool (`detect_duplicate_bookings_tool.py`)

Parlant tool that orchestrates the complete duplicate detection workflow.

**Parameters:**
- `customer_email`: Customer's email from Freshdesk ticket
- `event_date`: Event date from booking info (ISO format)
- `location_name`: Parking location name

**Returns:**
```python
{
    "has_duplicates": true,
    "action_taken": "refunded",
    "refunded_booking_id": 12346,
    "kept_booking_id": 12345,
    "refund_amount": 15.00,
    "explanation": "Found 2 duplicate bookings. Booking 12345 was used, booking 12346 was unused. Refunded unused booking."
}
```

### Authentication

The ParkWhiz API uses OAuth2 Client Credentials flow for authentication.

#### Obtaining Credentials

**Prerequisites:**
- ParkWhiz admin account
- Contact: `dev-admin@parkwhiz.com` or `partner-support@parkwhiz.com`

**Request Information:**
```
Subject: API Credentials Request for Customer Support Automation

We need API credentials for automated duplicate booking detection and refunds.

Required access:
- GET /v4/bookings (query customer bookings by email)
- DELETE /v4/bookings/{id} (cancel/refund bookings)
- Scope: "internal" or "partner"

Use case: Detect and refund duplicate bookings when customers claim "charged twice"
```

**You will receive:**
- `client_id`: Your application identifier
- `client_secret`: Your application secret (keep secure!)
- `scope`: Typically "internal" or "partner" for support operations

#### OAuth2 Flow

**Step 1: Request Access Token**

```bash
POST https://api.parkwhiz.com/v4/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&scope=internal
```

**Step 2: Receive Token Response**

```json
{
  "access_token": "a84823535f04030bdcbfcc713c2c4d84871d0f70d5214bc942f0d6eca7cdd09bb",
  "token_type": "bearer",
  "expires_in": 31557600,
  "scope": "internal",
  "created_at": 1499797873
}
```

**Step 3: Use Token in API Requests**

```bash
GET https://api.parkwhiz.com/v4/bookings?q=customer_email:user@example.com
Authorization: Bearer a84823535f04030bdcbfcc713c2c4d84871d0f70d5214bc942f0d6eca7cdd09bb
```

#### Token Management

**Token Lifecycle:**
- **Expires in**: ~1 year (31,557,600 seconds)
- **Refresh strategy**: Generate new token before expiration
- **Storage**: Store in environment variables, never commit to code

The ParkWhizClient automatically handles token refresh:
- Checks token expiration before each request
- Refreshes token if it expires within 24 hours
- Logs token refresh events for monitoring

### Configuration

#### Environment Variables

Add these to your `.env` file:

```bash
# ParkWhiz OAuth2 Credentials
PARKWHIZ_CLIENT_ID=your_client_id_here
PARKWHIZ_CLIENT_SECRET=your_client_secret_here
PARKWHIZ_SCOPE=internal

# ParkWhiz API Configuration
PARKWHIZ_BASE_URL=https://api.parkwhiz.com/v4
PARKWHIZ_TIMEOUT=5
PARKWHIZ_MAX_RETRIES=3
PARKWHIZ_CACHE_TTL=120  # 2 minutes

# Feature Flags
PARKWHIZ_DUPLICATE_DETECTION_ENABLED=true
```

#### Docker Compose

Ensure environment variables are passed to the container in `docker-compose.yml`:

```yaml
services:
  parlant:
    environment:
      # ParkWhiz OAuth2 Credentials
      PARKWHIZ_CLIENT_ID: ${PARKWHIZ_CLIENT_ID}
      PARKWHIZ_CLIENT_SECRET: ${PARKWHIZ_CLIENT_SECRET}
      PARKWHIZ_SCOPE: ${PARKWHIZ_SCOPE:-internal}
      
      # ParkWhiz API Configuration
      PARKWHIZ_BASE_URL: ${PARKWHIZ_BASE_URL:-https://api.parkwhiz.com/v4}
      PARKWHIZ_TIMEOUT: ${PARKWHIZ_TIMEOUT:-5}
      PARKWHIZ_MAX_RETRIES: ${PARKWHIZ_MAX_RETRIES:-3}
      PARKWHIZ_DUPLICATE_DETECTION_ENABLED: ${PARKWHIZ_DUPLICATE_DETECTION_ENABLED:-true}
```

After updating configuration:
```bash
docker-compose down
docker-compose up -d
```

### Examples

#### Example 1: Successful Duplicate Detection and Refund

**Customer Claim:**
> "I was charged twice for parking at Downtown Garage on January 15th. My email is customer@example.com."

**System Processing:**
1. Extracts: email=customer@example.com, event_date=2024-01-15, location="Downtown Garage"
2. Queries ParkWhiz API for bookings from 2024-01-14 to 2024-01-16
3. Finds 2 bookings:
   - Booking 12345: status="completed" (used)
   - Booking 12346: status="confirmed" (unused)
4. Identifies duplicate (same location, overlapping time)
5. Deletes booking 12346 (triggers automatic refund)
6. Documents decision in Freshdesk

**Decision Note:**
```
👾 Automated Analysis Complete

Decision: Approved

Analysis: Duplicate booking detected and refunded. Found 2 duplicate bookings 
for Downtown Garage on 2024-01-15. Booking 12345 was used (status: completed), 
booking 12346 was unused (status: confirmed). Refunded unused booking 12346 
for $15.00.

Security Status: ✅ Safe

Booking Info: ✅ Found

Policy Applied: Duplicate Booking Detection

Confidence: high

Refunded: Yes

Automated by Whiz AI Agent
```

#### Example 2: No Duplicates Found

**Customer Claim:**
> "I think I was charged twice for parking."

**System Processing:**
1. Extracts booking info from ticket
2. Queries ParkWhiz API
3. Finds only 1 booking for the customer
4. No duplicates detected

**Decision Note:**
```
👾 Automated Analysis Complete

Decision: Denied

Analysis: No duplicate bookings found. Customer has only 1 booking for the 
specified event date and location. The charge appears to be legitimate.

Security Status: ✅ Safe

Booking Info: ✅ Found

Policy Applied: Duplicate Booking Detection

Confidence: high

Refunded: No

Automated by Whiz AI Agent
```

#### Example 3: Multiple Duplicates (Escalation)

**Customer Claim:**
> "I have multiple charges for the same parking event."

**System Processing:**
1. Extracts booking info
2. Queries ParkWhiz API
3. Finds 4 bookings for the same event
4. Too complex for automatic resolution

**Decision Note:**
```
👾 Automated Analysis Complete

Decision: Needs Human Review

Analysis: Multiple duplicates found (4 bookings). Found 4 bookings for the 
same location and time period. This scenario is too complex for automatic 
resolution and requires human review to determine which bookings are legitimate 
and which should be refunded.

Security Status: ✅ Safe

Booking Info: ✅ Found

Policy Applied: Duplicate Booking Detection

Confidence: medium

Refunded: No

Automated by Whiz AI Agent
```

### Performance

- **Cached requests**: < 100ms (when booking data is cached)
- **Uncached requests**: < 5 seconds (API query + analysis)
- **Cache TTL**: 2 minutes (reduces redundant API calls)
- **Cache hit rate**: > 40% (some tickets reference same customer/date)

**Performance Optimization:**
- Connection pooling for HTTP requests
- TTL cache for booking queries (2 minute expiration)
- Exponential backoff retry logic
- Timeout configuration (5 seconds default)

### Error Handling

The system handles various error scenarios gracefully:

| Error Type | Handling | Action |
|------------|----------|--------|
| Authentication failure | Log critical error | Escalate to human review |
| Customer not found | Log warning | Return empty booking list |
| API timeout | Retry 3 times with backoff | Escalate if all retries fail |
| Malformed response | Log error | Escalate to human review |
| Network error | Retry with backoff | Escalate if all retries fail |
| Missing credentials | Log critical error | Disable duplicate detection |

**Error Response Example:**
```python
{
    "error": "authentication_failed",
    "summary": "ParkWhiz authentication failed - escalate to human review"
}
```

### Troubleshooting

#### Authentication Issues

**Symptom:** `ParkWhizAuthenticationError: Invalid or expired token`

**Solutions:**
1. Verify credentials in `.env`:
   ```bash
   echo $PARKWHIZ_CLIENT_ID
   echo $PARKWHIZ_CLIENT_SECRET
   ```

2. Test OAuth2 flow manually:
   ```bash
   curl -X POST https://api.parkwhiz.com/v4/oauth/token \
     -d "grant_type=client_credentials" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "scope=internal"
   ```

3. Check token expiration in logs:
   ```bash
   docker-compose logs parlant | grep "token refresh"
   ```

4. Restart service to force token refresh:
   ```bash
   docker-compose restart parlant
   ```

#### No Bookings Found

**Symptom:** System returns "No duplicate bookings found" but customer insists they have duplicates

**Solutions:**
1. Verify customer email matches ParkWhiz records exactly
2. Check date range (system searches ± 1 day from event_date)
3. Verify location name matches ParkWhiz location
4. Check ParkWhiz API directly:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://api.parkwhiz.com/v4/bookings?q=customer_email:customer@example.com"
   ```

5. Review extraction logs:
   ```bash
   docker-compose logs parlant | grep BookingExtractor
   ```

#### Token Expiration

**Symptom:** Duplicate detection works initially but fails after ~1 year

**Solutions:**
1. The system automatically refreshes tokens before expiration
2. If manual refresh needed:
   ```bash
   docker-compose restart parlant
   ```

3. Monitor token refresh in logs:
   ```bash
   docker-compose logs parlant | grep "OAuth2 token refreshed"
   ```

4. If automatic refresh fails, request new credentials from ParkWhiz

#### API Rate Limiting

**Symptom:** `429 Too Many Requests` errors

**Solutions:**
1. Check rate limit in ParkWhiz API documentation
2. Implement request throttling if needed
3. Increase cache TTL to reduce API calls:
   ```bash
   PARKWHIZ_CACHE_TTL=300  # 5 minutes
   ```

4. Contact ParkWhiz to increase rate limits for your application

#### Duplicate Detection Not Triggering

**Symptom:** System doesn't detect "paid again" claims

**Solutions:**
1. Verify feature flag is enabled:
   ```bash
   echo $PARKWHIZ_DUPLICATE_DETECTION_ENABLED
   ```

2. Check keyword detection in logs:
   ```bash
   docker-compose logs parlant | grep "paid again"
   ```

3. Review ticket text for trigger keywords:
   - "paid again"
   - "charged twice"
   - "double charged"
   - "charged multiple times"
   - "billed twice"
   - "duplicate charge"

4. Test keyword detection:
   ```python
   # In process_ticket_workflow.py
   keywords = ["paid again", "charged twice", ...]
   ticket_text = "I was charged twice for parking"
   detected = any(keyword in ticket_text.lower() for keyword in keywords)
   ```

### Testing

Run duplicate detection tests:

```bash
# All duplicate detection tests
docker-compose exec parlant pytest tests/tools/test_parkwhiz_client.py -v
docker-compose exec parlant pytest tests/tools/test_duplicate_booking_analyzer.py -v
docker-compose exec parlant pytest tests/tools/test_detect_duplicate_bookings_tool.py -v

# Integration tests
docker-compose exec parlant pytest tests/integration/test_duplicate_detection_flow.py -v

# Specific test
docker-compose exec parlant pytest tests/tools/test_parkwhiz_client.py::test_get_customer_bookings_success -v
```

**Test Coverage:**
- ParkWhiz Client: OAuth2 flow, booking queries, deletion, error handling
- Duplicate Analyzer: Detection logic, usage identification, edge cases
- Detection Tool: Integration with ToolContext, result formatting
- End-to-End: Full workflow from ticket to refund

### Security Best Practices

1. **Never commit credentials to code**:
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Rotate credentials periodically**:
   - Request new credentials every 6-12 months
   - Update environment variables

3. **Monitor token usage**:
   - Log authentication failures
   - Alert on repeated auth errors

4. **Secure storage**:
   - Use secrets management in production (AWS Secrets Manager, etc.)
   - Encrypt credentials at rest

5. **HTTPS only**:
   - All API requests use HTTPS
   - Verify SSL certificates

6. **Input validation**:
   - Validate email format before API calls
   - Validate date formats (ISO 8601)
   - Sanitize all user inputs

### Implementation Status

**Phase 1-17: Core Implementation** ✅ COMPLETE
- ParkWhiz API client with OAuth2 authentication
- Customer booking query functionality
- Booking deletion/refund processing
- Duplicate booking analyzer
- Duplicate detection logic
- Used vs unused booking identification
- Detection result generation
- Parlant tool integration
- Decision workflow integration
- Error handling and fallback logic
- Configuration and environment variables
- Caching for performance
- Logging and observability
- Comprehensive test suite

**Phase 18: Documentation** ✅ COMPLETE
- README integration
- Environment variable documentation
- OAuth2 flow documentation
- Example scenarios
- Troubleshooting guide

### Future Enhancements

1. **Smart Duplicate Detection:**
   - Use ML to detect "similar" bookings (slightly different times/locations)
   - Detect patterns of accidental duplicate bookings by user

2. **Partial Refund Support:**
   - If ParkWhiz adds partial refund API, integrate it
   - Handle cases where customer used one booking partially

3. **Proactive Duplicate Prevention:**
   - Detect duplicates at booking time
   - Alert customer before they complete second booking

4. **Analytics Dashboard:**
   - Track duplicate booking trends
   - Identify locations with high duplicate rates
   - Monitor refund processing success rates

## Booking Verification Enhancement

The system includes automated booking verification to handle cases where Zapier fails to find booking information. When a booking ID is invalid or missing, the system uses ParkWhiz OAuth2 API to search for bookings using customer email and dates, verify pass usage, and make informed refund decisions.

### Overview

**Problem:** Zapier sometimes fails to find booking information, leaving tickets with "Booking information not found" messages. Without verified booking data, the system cannot safely make automated refund decisions.

**Solution:** Automated booking verification that:
- Detects Zapier failures and invalid booking IDs
- Extracts customer email, name, and dates from ticket text
- Queries ParkWhiz API to find matching bookings
- Verifies pass usage status (used vs unused)
- Makes decisions only on verified data
- Documents all findings in Freshdesk private notes

### How It Works

```
Zapier Failure Detected
  ↓
Extract Customer Info (email, dates, location)
  ↓
Search ParkWhiz API
  ├─ Found booking → Verify pass usage
  │   ├─ Pass used → Include in decision context
  │   ├─ Pass not used → Include in decision context
  │   └─ Usage unknown → Escalate to human
  └─ No booking found → Escalate to human
  ↓
Add Verified Note to Freshdesk
  ↓
Make Decision (using verified data only)
```

### OAuth2 Authentication Setup

The booking verification feature requires ParkWhiz OAuth2 credentials.

#### Obtaining Credentials

**Prerequisites:**
- ParkWhiz partner account
- Contact: `dev-admin@parkwhiz.com` or `partner-support@parkwhiz.com`

**Request Template:**
```
Subject: OAuth2 API Credentials for Booking Verification

We need OAuth2 credentials for automated booking verification in our customer support system.

Required access:
- GET /v4/bookings (search customer bookings by email and date range)
- Scope: "internal" or "partner"

Use case: When Zapier fails to find booking information, automatically search 
ParkWhiz API using customer email and dates to verify booking details and pass 
usage before making refund decisions.
```

**You will receive:**
- `PARKWHIZ_CLIENT_ID`: Your OAuth2 client identifier
- `PARKWHIZ_CLIENT_SECRET`: Your OAuth2 client secret (keep secure!)
- `PARKWHIZ_SCOPE`: Typically "internal" for support operations

#### Configuration

Add these environment variables to your `.env` file:

```bash
# ParkWhiz OAuth2 Configuration
PARKWHIZ_CLIENT_ID=your-client-id-here
PARKWHIZ_CLIENT_SECRET=your-client-secret-here
PARKWHIZ_SCOPE=internal
PARKWHIZ_BASE_URL=https://api.parkwhiz.com/v4
PARKWHIZ_TIMEOUT=5
PARKWHIZ_MAX_RETRIES=3
PARKWHIZ_CACHE_TTL=120
```

**Important:** After updating `.env`, restart the service:
```bash
docker-compose down
docker-compose up -d
```

#### Credential Validation

The system validates OAuth2 credentials at startup. If credentials are missing or invalid, you'll see:

```
CRITICAL - ParkWhiz OAuth2 credentials not configured. 
Set PARKWHIZ_CLIENT_ID and PARKWHIZ_CLIENT_SECRET environment variables.
Contact dev-admin@parkwhiz.com to obtain credentials.
```

**To verify credentials are configured:**
```bash
# Check environment variables
docker-compose exec parlant env | grep PARKWHIZ

# Check startup logs
docker-compose logs parlant | grep "OAuth2 credentials validated"
```

### Features

**Zapier Failure Detection:**
- Detects "Booking information not found" messages
- Identifies invalid booking IDs (0000, N/A, empty)
- Triggers automatic verification workflow

**Customer Information Extraction:**
- Extracts email, name, arrival date, exit date from ticket text
- Uses LLM to parse unstructured ticket descriptions
- Validates required fields before API calls

**Booking Search:**
- Queries ParkWhiz API with customer email and date range
- Handles multiple matching bookings
- Selects best match based on date proximity
- Includes retry logic for network errors

**Pass Usage Verification:**
- Retrieves pass usage status from booking data
- Determines if pass was actually used/scanned
- Escalates if usage status is unclear

**Decision Safety:**
- Makes decisions only on verified booking data
- Never uses unverified customer claims
- Escalates contradictions to human review
- Documents all verification details in private notes

### Error Handling

The system handles various error scenarios gracefully:

| Error Type | Handling | Action |
|------------|----------|--------|
| Missing credentials | Log critical error at startup | System starts but verification disabled |
| Authentication failure | Log critical error | Escalate ticket to human review |
| API timeout | Retry once with backoff | Escalate if retry fails |
| No booking found | Log info | Escalate with "no booking found" reason |
| Multiple bookings | Select best match | Use closest date match |
| Missing customer info | Log warning | Escalate with "incomplete info" reason |
| Usage status unknown | Log warning | Escalate with "unclear usage" reason |

### Troubleshooting

#### Credentials Not Configured

**Symptom:** System logs "ParkWhiz OAuth2 credentials not configured" at startup

**Solutions:**
1. Verify `.env` file contains `PARKWHIZ_CLIENT_ID` and `PARKWHIZ_CLIENT_SECRET`
2. Check docker-compose.yml passes environment variables to container
3. Restart service: `docker-compose down && docker-compose up -d`
4. If credentials missing, contact `dev-admin@parkwhiz.com`

#### Authentication Failures

**Symptom:** "ParkWhiz authentication failed" errors in logs

**Solutions:**
1. Verify credentials are correct in `.env`
2. Test OAuth2 flow manually:
   ```bash
   curl -X POST https://api.parkwhiz.com/v4/oauth/token \
     -d "grant_type=client_credentials" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "scope=internal"
   ```
3. Check if credentials expired (contact ParkWhiz for new ones)
4. Review logs: `docker-compose logs parlant | grep "OAuth2"`

#### Verification Not Triggering

**Symptom:** Zapier failures not triggering verification workflow

**Solutions:**
1. Check ticket contains "Booking information not found" message
2. Verify booking ID is invalid (0000, N/A, empty)
3. Review logs: `docker-compose logs parlant | grep "Zapier failure"`
4. Test detection: `docker-compose exec parlant pytest tests/tools/test_zapier_failure_detector.py -v`

#### No Bookings Found

**Symptom:** System reports "No matching bookings found" but customer has booking

**Solutions:**
1. Verify customer email matches ParkWhiz records exactly
2. Check date range is correct (system searches ± 1 day)
3. Review extraction logs: `docker-compose logs parlant | grep "CustomerInfoExtractor"`
4. Test API directly with customer email

### Testing

Run booking verification tests:

```bash
# All booking verification tests
docker-compose exec parlant pytest tests/tools/test_zapier_failure_detector.py -v
docker-compose exec parlant pytest tests/tools/test_customer_info_extractor.py -v
docker-compose exec parlant pytest tests/tools/test_booking_verifier.py -v
docker-compose exec parlant pytest tests/tools/test_decision_guard.py -v
docker-compose exec parlant pytest tests/tools/test_verification_note_generator.py -v

# Integration tests
docker-compose exec parlant pytest tests/integration/test_booking_verification_integration.py -v

# Specific test
docker-compose exec parlant pytest tests/tools/test_booking_verifier.py::test_verify_booking_success -v
```

### Performance

- **Cached requests**: < 100ms (when booking data is cached)
- **Uncached requests**: < 5 seconds (API query + verification)
- **Cache TTL**: 2 minutes (reduces redundant API calls)
- **Retry logic**: 1 retry on timeout (max 10 seconds total)

### Security

1. **Credentials stored in environment variables** - Never committed to code
2. **HTTPS only** - All API requests use HTTPS
3. **OAuth2 token auto-refresh** - Tokens refreshed before expiration
4. **Input validation** - Email and date formats validated before API calls
5. **Private notes only** - Verified data added to private notes (not public)

## Monitoring & Observability

### Decision Metrics

The system tracks key metrics for each decision:

**Performance Metrics:**
- Processing time (ms) - Total time from ticket to decision
- Method used - `rules`, `llm`, or `hybrid`
- Extraction method - `pattern`, `llm`, or `none`
- API calls made - Number of Gemini API requests

**Quality Metrics:**
- Confidence level - `high`, `medium`, or `low`
- Decision distribution - Approved/Denied/Escalated percentages
- Escalation rate - Percentage of cases needing human review
- Rule match rate - Percentage handled by rules alone

**Error Metrics:**
- Extraction failures - Booking info not found
- LLM timeouts - API calls exceeding 10s
- Policy load errors - Missing or invalid policy files
- API errors - Gemini or Freshdesk failures

### Logging

The system logs all decision-making activities:

**View decision logs:**
```bash
# All decision-making logs
docker-compose logs parlant | grep -E "BookingExtractor|RuleEngine|LLMAnalyzer|DecisionMaker"

# Booking extraction logs
docker-compose logs parlant | grep BookingExtractor

# Rule application logs
docker-compose logs parlant | grep RuleEngine

# LLM analysis logs
docker-compose logs parlant | grep LLMAnalyzer

# Decision outcomes
docker-compose logs parlant | grep "Decision:"
```

**Log levels:**
- `INFO`: Normal operations (decision made, booking extracted)
- `WARNING`: Low confidence, fallback to LLM, missing data
- `ERROR`: API failures, policy load errors, extraction failures

### Audit Trail (Future)

PostgreSQL audit logging will track:
- All decisions with full context
- Booking information extracted
- Rules applied and confidence scores
- LLM prompts and responses
- Processing times and API usage
- Human review outcomes and feedback

**Query decision history:**
```sql
-- Future implementation
SELECT ticket_id, decision, confidence, method_used, processing_time_ms
FROM decision_audit
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# LLM Provider Configuration
LLM_PROVIDER=gemini  # or 'openai'

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Gemini Configuration (if using Gemini)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash

# Freshdesk Integration
FRESHDESK_DOMAIN=your-domain.freshdesk.com
FRESHDESK_API_KEY=your-freshdesk-api-key

# ParkWhiz Integration (Legacy API Key)
PARKWHIZ_API_KEY=your-parkwhiz-api-key

# ParkWhiz OAuth2 Configuration (for Booking Verification)
# Required for automated booking verification when Zapier fails
# Contact: dev-admin@parkwhiz.com or partner-support@parkwhiz.com
PARKWHIZ_CLIENT_ID=your-oauth2-client-id
PARKWHIZ_CLIENT_SECRET=your-oauth2-client-secret
PARKWHIZ_SCOPE=internal
PARKWHIZ_BASE_URL=https://api.parkwhiz.com/v4
PARKWHIZ_TIMEOUT=5
PARKWHIZ_MAX_RETRIES=3
PARKWHIZ_CACHE_TTL=120  # Cache booking queries for 2 minutes

# Lakera Security
LAKERA_API_KEY=your-lakera-api-key

# Webhook Configuration
WEBHOOK_SECRET=your-secure-random-secret
WEBHOOK_ENABLED=true
WEBHOOK_PORT=8801
WEBHOOK_PATH=/webhook/freshdesk
WEBHOOK_EVENTS=ticket_created,ticket_updated
WEBHOOK_RATE_LIMIT=100  # requests per minute

# Parlant Configuration
PARLANT_BASE_URL=http://parlant:8800

# Database Configuration
POSTGRES_DB=ranjayDB
POSTGRES_USER=ranjay.kumar
POSTGRES_PASSWORD=ranjay
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Voice Bridge Tuning
TURN_TIMEOUT_SECS=30
POLL_WAIT_SECS=10
MAX_EMPTY_POLLS=3
```

## Testing

**IMPORTANT: All tests MUST be run inside the Docker container.**

```bash
# Run all tests
docker-compose exec parlant pytest

# Run specific test file
docker-compose exec parlant pytest tests/tools/test_booking_extractor.py -v

# Run specific test
docker-compose exec parlant pytest tests/tools/test_llm_analyzer.py::test_analyze_case_approved -v

# Run with coverage
docker-compose exec parlant pytest --cov=app_tools --cov-report=html
```

**Import Pattern for Tests:**
Test files must use `app_tools.tools.*` imports (not `parlant.tools.*`) because the Docker container mounts `./parlant` as `/app/app_tools`:

```python
# ✅ Correct - use in test files
from app_tools.tools.booking_extractor import BookingExtractor
from app_tools.tools.journey_helpers import extract_booking_info_from_note

# ❌ Wrong - will fail in Docker
from parlant.tools.booking_extractor import BookingExtractor
```

### Test Coverage

- **BookingExtractor**: 15 tests passing ✅ (pattern + LLM extraction)
- **LLMAnalyzer**: 13 tests passing ✅ (all decision paths + error handling)
- **JourneyHelpers**: 11 tests passing ✅ (extract_booking_info + triage_ticket)
- **RuleEngine**: Unit tests pending
- **DecisionMaker**: Integration tests pending
- **CancellationReasonMapper**: Unit tests pending
- **Freshdesk Tools**: API mocking with pytest-httpx

## Development

### Running Locally (without Docker)

1. **Start PostgreSQL**
   ```bash
   docker run -d -p 5432:5432 \
     -e POSTGRES_DB=ranjayDB \
     -e POSTGRES_USER=ranjay.kumar \
     -e POSTGRES_PASSWORD=ranjay \
     postgres:15
   ```

2. **Run Parlant**
   ```bash
   cd parlant
   pip install -r requirements.txt
   python main.py
   ```

3. **Run Pipecat**
   ```bash
   cd voice
   pip install -r requirements.txt
   python app.py
   ```

### Logs

View logs for specific services:
```bash
docker-compose logs -f parlant
docker-compose logs -f pipecat
docker-compose logs -f postgres
```

## Project Structure

```
.
├── README.md
├── docker-compose.yml
├── .env
├── .gitignore
├── parlant/                    # Main application code
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # Agent creation and journey definitions
│   ├── webhook_server.py       # FastAPI webhook endpoint ✅
│   ├── journey_router.py       # Journey routing logic ✅
│   ├── tools/                  # Parlant tools (@p.tool decorated)
│   │   ├── freshdesk_tools.py  # Ticket operations
│   │   ├── parkwhiz_tools.py   # Booking data retrieval
│   │   ├── lakera_security_tool.py  # Security scanning
│   │   ├── webhook_validator.py  # Webhook signature validation ✅
│   │   ├── webhook_config.py   # Webhook configuration management ✅
│   │   ├── structured_logger.py  # Structured JSON logging ✅
│   │   ├── metrics_tracker.py  # Metrics collection ✅
│   │   ├── policy_loader.py    # Policy document loader ✅
│   │   ├── booking_extractor.py  # Booking info extraction ✅
│   │   ├── booking_patterns.py # Pattern-based extraction ✅
│   │   ├── rule_engine.py      # Deterministic business rules ✅
│   │   ├── llm_analyzer.py     # LLM-powered case analysis ✅
│   │   ├── decision_maker.py   # Hybrid decision orchestrator ✅
│   │   ├── cancellation_reason_mapper.py  # ParkWhiz reason mapping ✅
│   │   ├── journey_helpers.py  # AI reasoning tools (extract_booking_info, triage_ticket, document_decision) ✅
│   │   └── process_ticket_workflow.py  # End-to-end workflow
│   ├── retrievers/             # Parlant retrievers
│   │   └── refund_retrievers.py
│   └── context/                # Policy documents
│       ├── processed/          # Structured policy files (JSON, MD)
│       └── raw/                # Original policy documents
├── tests/                      # Test suite
│   ├── tools/                  # Tool tests
│   ├── retrievers/             # Retriever tests
│   ├── integration/            # Integration tests
│   └── debug/                  # Debug scripts
├── voice/                      # Voice interface
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── postgres/                   # Database
│   └── init.sql
└── planning/                   # Documentation
    ├── docs/                   # Architecture docs
    └── testing/                # Test results
```

## Troubleshooting

### Voice not working
- Ensure microphone permissions are granted
- Check browser console for WebRTC errors
- Verify OPENAI_API_KEY is set correctly

### Database connection errors
- Wait 10-20 seconds after `docker-compose up` for PostgreSQL to initialize
- Check logs: `docker-compose logs postgres`

### Agent not responding
- Verify Parlant is running: `curl http://localhost:8800`
- Check agent_id.txt was created
- Review logs: `docker-compose logs parlant pipecat`

### Gemini API errors
- **404 Model Not Found**: Update GEMINI_MODEL to `gemini-2.5-flash` (not `gemini-1.5-flash`)
- **401 Authentication**: Verify GEMINI_API_KEY is correct
- **429 Rate Limit**: Free tier has 15 RPM limit, consider upgrading
- See `parlant/PATCH_README.md` for Gemini model patching details

### Decision making issues

**"Needs Human Review" for all tickets:**
- Check policy files exist in `parlant/context/processed/`
- Verify JSON files are valid: `cat parlant/context/processed/refund_rules.json | python -m json.tool`
- Check PolicyLoader logs: `docker-compose logs parlant | grep PolicyLoader`
- Restart service to reload policies: `docker-compose restart parlant`

**Booking extraction failing:**
- Review ticket format - ensure booking info is in notes or description
- Check Gemini API logs: `docker-compose logs parlant | grep BookingExtractor`
- Verify GEMINI_API_KEY is set correctly in `.env`
- Test pattern extraction: `docker-compose exec parlant python -m app_tools.test_pattern_extraction`

**Rule engine not matching:**
- Verify date formats are ISO 8601 (YYYY-MM-DD)
- Check days_before_event calculation in logs
- Review rule conditions in `refund_rules.json`
- Test specific rule: `docker-compose exec parlant pytest tests/tools/test_rule_engine.py::test_specific_rule -v`

**Wrong cancellation reason selected:**
- Review reasoning text in decision output
- Check keyword matching in `cancellation_reason_mapper.py`
- Add new keywords for specific scenarios
- Test mapper: `docker-compose exec parlant pytest tests/tools/test_cancellation_reason_mapper.py -v`

**Low confidence scores:**
- Review policy completeness in markdown files
- Add more specific rules to `refund_rules.json`
- Tune confidence thresholds in `rule_engine.py`
- Check LLM prompt quality in `llm_analyzer.py`

**Slow decision times:**
- Check if pattern extraction is enabled (should reduce LLM calls)
- Review Gemini API latency in logs
- Consider caching common booking patterns
- Monitor API rate limits (15 RPM on free tier)

### Test failures
- **Import errors**: Always run tests in Docker: `docker-compose exec parlant pytest`
- **API mocking issues**: Check pytest-httpx fixtures in test files
- **Environment variables**: Ensure .env is loaded in docker-compose.yml

## Documentation

Detailed documentation is available in the `.kiro/specs/` directory:

- **webhook-automation/**: Complete spec for webhook integration
  - `requirements.md`: Functional requirements
  - `design.md`: Architecture and component design
  - `tasks.md`: Implementation task list
  - `WEBHOOK_SETUP_GUIDE.md`: Complete setup instructions
  - `TROUBLESHOOTING_GUIDE.md`: Common issues and solutions
  - `TESTING_GUIDE.md`: Testing procedures and examples

- **policy-based-decisions/**: Complete spec for the hybrid decision-making system
  - `README.md`: Overview and problem statement
  - `requirements.md`: Functional requirements
  - `design.md`: Architecture and component design
  - `tasks.md`: Implementation task list
  - `CHANGELOG.md`: Implementation progress tracker

Additional documentation:
- `planning/docs/`: Architecture clarifications and integration guides
- `planning/testing/`: Test results and verification reports
- `tests/*/README.md`: Test suite documentation

## License

MIT

## Contributing

Pull requests welcome! Please open an issue first to discuss changes.
```