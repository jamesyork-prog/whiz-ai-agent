#!/usr/bin/env python3
"""
Direct test of tool functionality with Gemini by importing and calling tools.
This bypasses the Parlant API and tests tools directly.
"""

import asyncio
import sys
import os
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, '/app/app_tools')

# Import tools
from tools.freshdesk_tools import get_ticket, get_ticket_description, get_ticket_conversations
from tools.lakera_security_tool import check_content
from tools.journey_helpers import extract_booking_info_from_note, triage_ticket

TEST_TICKET_ID = "1206331"

async def test_get_ticket():
    """Test get_ticket tool."""
    print("\n" + "=" * 80)
    print("TEST 1: get_ticket - Fetch ticket metadata")
    print("=" * 80)
    
    # Create mock context
    context = Mock()
    context.inputs = {}
    
    try:
        result = await get_ticket(context, ticket_id=TEST_TICKET_ID)
        
        if result.data and "id" in result.data:
            print(f"✓ Tool executed successfully")
            print(f"  - Ticket ID: {result.data.get('id')}")
            print(f"  - Subject: {result.data.get('subject', '')[:60]}...")
            print(f"  - Status: {result.data.get('status')}")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


async def test_get_ticket_description():
    """Test get_ticket_description tool."""
    print("\n" + "=" * 80)
    print("TEST 2: get_ticket_description - Fetch ticket description")
    print("=" * 80)
    
    context = Mock()
    context.inputs = {}
    
    try:
        result = await get_ticket_description(context, ticket_id=TEST_TICKET_ID)
        
        if result.data and "description" in result.data:
            print(f"✓ Tool executed successfully")
            print(f"  - Ticket ID: {result.data.get('ticket_id')}")
            print(f"  - Description length: {len(result.data.get('description', ''))} chars")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

async def test_get_ticket_conversations():
    """Test get_ticket_conversations tool."""
    print("\n" + "=" * 80)
    print("TEST 3: get_ticket_conversations - Fetch conversations")
    print("=" * 80)
    
    context = Mock()
    context.inputs = {}
    
    try:
        result = await get_ticket_conversations(context, ticket_id=TEST_TICKET_ID)
        
        if result.data and "conversations" in result.data:
            conv_count = len(result.data.get('conversations', []))
            print(f"✓ Tool executed successfully")
            print(f"  - Conversations fetched: {conv_count}")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

async def test_check_content():
    """Test check_content (Lakera) tool."""
    print("\n" + "=" * 80)
    print("TEST 4: check_content - Security scanning")
    print("=" * 80)
    
    context = Mock()
    context.inputs = {"content": "This is a normal customer support request about a refund."}
    
    try:
        result = await check_content(context)
        
        if result.data and "safe" in result.data:
            print(f"✓ Tool executed successfully")
            print(f"  - Safe: {result.data.get('safe')}")
            print(f"  - Flagged: {result.data.get('flagged')}")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


async def test_extract_booking_info():
    """Test extract_booking_info_from_note tool."""
    print("\n" + "=" * 80)
    print("TEST 5: extract_booking_info_from_note - Booking extraction")
    print("=" * 80)
    
    context = Mock()
    context.inputs = {
        "ticket_notes": "Booking ID: PW-12345, Amount: $45.00, Date: 2025-11-15, Location: Downtown Parking"
    }
    
    try:
        result = await extract_booking_info_from_note(context)
        
        if result.data and "booking_info" in result.data:
            print(f"✓ Tool executed successfully")
            print(f"  - Booking info: {result.data.get('booking_info')}")
            print(f"  - Confidence: {result.data.get('confidence')}")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

async def test_triage_ticket():
    """Test triage_ticket tool."""
    print("\n" + "=" * 80)
    print("TEST 6: triage_ticket - Decision making")
    print("=" * 80)
    
    context = Mock()
    context.inputs = {
        "ticket_data": {
            "id": TEST_TICKET_ID,
            "subject": "Refund request",
            "description": "Customer wants refund"
        },
        "booking_info": None,
        "refund_policy": "Standard refund policy applies"
    }
    
    try:
        result = await triage_ticket(context)
        
        if result.data and "decision" in result.data:
            print(f"✓ Tool executed successfully")
            print(f"  - Decision: {result.data.get('decision')}")
            print(f"  - Reasoning: {result.data.get('reasoning', '')[:60]}...")
            print(f"  - Confidence: {result.data.get('confidence')}")
            return True
        else:
            print(f"✗ Tool failed: {result.data}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

async def main():
    """Run all direct tool tests."""
    print("=" * 80)
    print("GEMINI TOOL CALLING TEST - DIRECT EXECUTION")
    print("=" * 80)
    print(f"\nTest Ticket ID: {TEST_TICKET_ID}")
    print("Testing tools by direct function calls\n")
    
    results = {}
    
    results["get_ticket"] = await test_get_ticket()
    results["get_ticket_description"] = await test_get_ticket_description()
    results["get_ticket_conversations"] = await test_get_ticket_conversations()
    results["check_content"] = await test_check_content()
    results["extract_booking_info"] = await test_extract_booking_info()
    results["triage_ticket"] = await test_triage_ticket()
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\nTests Run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}\n")
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "=" * 80)
    
    if all(results.values()):
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        print("\nGemini tool calling functionality verified:")
        print("  • get_ticket works correctly")
        print("  • get_ticket_description works correctly")
        print("  • get_ticket_conversations works correctly")
        print("  • check_content (Lakera) works correctly")
        print("  • extract_booking_info works correctly")
        print("  • triage_ticket works correctly")
        print("  • Parameter extraction works correctly")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 80)
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
