# Debug and Development Test Scripts

This directory contains debug scripts and development tests used during implementation.

## Debug Scripts

### debug_all_conversations.py
**Purpose:** Debug script to fetch and display all conversations from a Freshdesk ticket.

**Use case:** Troubleshooting conversation retrieval and note visibility

### debug_booking_extraction.py
**Purpose:** Debug script to test booking information extraction from ticket notes.

**Use case:** Troubleshooting the booking extraction logic and LLM analysis

### debug_ticket_full.py
**Purpose:** Debug script to fetch complete ticket information (metadata, description, conversations).

**Use case:** Inspecting full ticket structure and data availability

## Development Test Scripts

### test_tool_calling.py
**Purpose:** Tests individual tool calling through Parlant's API with parameter extraction.

**What it tests:**
- Tool triggering via natural language
- Parameter extraction from user messages
- Tool execution and response handling

**Note:** This was used during development but may not work due to Parlant API session issues.

### test_parameter_extraction.py
**Purpose:** Verifies that Gemini correctly extracts parameters for all tools.

**What it tests:**
- Single parameter extraction (ticket_id)
- Multiple parameter extraction (ticket_id + note, ticket_id + tags)
- Complex parameter extraction (ticket_data, booking_info, refund_policy)

**Status:** Verification complete - all parameter extraction working

### test_tools_direct.py
**Purpose:** Tests tools by calling them directly as Python functions (bypassing Parlant).

**What it tests:**
- Direct tool execution
- Tool functionality without Parlant orchestration
- API integrations (Freshdesk, Lakera)

**Status:** 5/6 tools passed (Lakera API endpoint issue)

### verify_private_notes.py
**Purpose:** Verifies that notes added to Freshdesk are marked as private.

**What it tests:**
- Note privacy settings
- Freshdesk API response structure
- Internal vs. customer visibility

**Status:** Verification complete - notes are private

## Usage

These scripts are primarily for debugging and development. They can be run individually:

```bash
# Run a debug script
docker-compose exec parlant python /app/app_tools/debug_booking_extraction.py

# Run a test script
docker-compose exec parlant python /app/app_tools/test_tools_direct.py
```

## Note

Most of these scripts were created during development and testing. For production testing, use the scripts in `tests/integration/` instead.

## Cleanup Candidates

Some of these scripts may be candidates for removal once the policy-based decision making is implemented and verified:
- `debug_all_conversations.py` - Can be removed if no longer needed
- `debug_ticket_full.py` - Can be removed if no longer needed
- `test_tool_calling.py` - May not work due to API issues

Keep:
- `test_tools_direct.py` - Useful for direct tool testing
- `test_parameter_extraction.py` - Useful for verification
- `debug_booking_extraction.py` - Useful until booking extraction is fixed
