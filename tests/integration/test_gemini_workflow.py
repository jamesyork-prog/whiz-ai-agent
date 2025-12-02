#!/usr/bin/env python3
"""
Test script to verify Gemini integration with ticket processing workflow.
Tests ticket 1206331 through the complete workflow.
"""

import asyncio
import httpx
import json
import sys

PARLANT_BASE_URL = "http://localhost:8800"
TEST_TICKET_ID = "1206331"

async def test_ticket_processing():
    """Test the complete ticket processing workflow with Gemini."""
    
    print("=" * 80)
    print("GEMINI INTEGRATION TEST - TICKET PROCESSING WORKFLOW")
    print("=" * 80)
    print(f"\nTest Ticket ID: {TEST_TICKET_ID}")
    print(f"Parlant Server: {PARLANT_BASE_URL}")
    print()
    
    # Read agent ID
    try:
        with open("data/agent_id.txt", "r") as f:
            agent_id = f.read().strip()
        print(f"✓ Agent ID: {agent_id}")
    except FileNotFoundError:
        print("✗ Error: Agent ID file not found. Is the server running?")
        return False
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Create a session
        print("\n" + "-" * 80)
        print("STEP 1: Creating session")
        print("-" * 80)
        
        try:
            response = await client.post(
                f"{PARLANT_BASE_URL}/agents/{agent_id}/customers/test_customer/sessions",
                json={}
            )
            response.raise_for_status()
            session_data = response.json()
            session_id = session_data["id"]
            print(f"✓ Session created: {session_id}")
        except Exception as e:
            print(f"✗ Failed to create session: {e}")
            return False
        
        # Step 2: Send message to process ticket
        print("\n" + "-" * 80)
        print("STEP 2: Sending ticket processing request")
        print("-" * 80)
        
        message = f"Process ticket {TEST_TICKET_ID}"
        print(f"Message: '{message}'")
        
        try:
            response = await client.post(
                f"{PARLANT_BASE_URL}/agents/{agent_id}/customers/test_customer/sessions/{session_id}/events",
                json={
                    "kind": "message",
                    "source": "customer",
                    "message": message
                }
            )
            response.raise_for_status()
            print("✓ Message sent successfully")
        except Exception as e:
            print(f"✗ Failed to send message: {e}")
            return False
        
        # Step 3: Poll for events and tool calls
        print("\n" + "-" * 80)
        print("STEP 3: Monitoring workflow execution")
        print("-" * 80)
        
        max_polls = 30
        poll_count = 0
        workflow_complete = False
        tool_calls = []
        agent_messages = []
        
        while poll_count < max_polls and not workflow_complete:
            poll_count += 1
            await asyncio.sleep(2)  # Wait between polls
            
            try:
                response = await client.get(
                    f"{PARLANT_BASE_URL}/agents/{agent_id}/customers/test_customer/sessions/{session_id}/events"
                )
                response.raise_for_status()
                events = response.json()
                
                # Process events
                for event in events:
                    event_kind = event.get("kind")
                    
                    if event_kind == "tool_call":
                        tool_name = event.get("tool_name", "unknown")
                        tool_id = event.get("id", "")
                        
                        # Avoid duplicates
                        if tool_id not in [t.get("id") for t in tool_calls]:
                            tool_calls.append(event)
                            print(f"  → Tool called: {tool_name}")
                            
                            # Check for specific workflow tools
                            if tool_name == "process_ticket_end_to_end":
                                print(f"    ✓ End-to-end workflow tool invoked")
                            elif tool_name == "get_ticket":
                                print(f"    ✓ Fetching ticket metadata")
                            elif tool_name == "get_ticket_description":
                                print(f"    ✓ Fetching ticket description")
                            elif tool_name == "get_ticket_conversations":
                                print(f"    ✓ Fetching ticket conversations")
                            elif tool_name == "check_content":
                                print(f"    ✓ Running security scan")
                            elif tool_name == "extract_booking_info_from_note":
                                print(f"    ✓ Extracting booking information")
                            elif tool_name == "triage_ticket":
                                print(f"    ✓ Making triage decision")
                            elif tool_name == "add_note":
                                print(f"    ✓ Adding note to ticket")
                            elif tool_name == "update_ticket":
                                print(f"    ✓ Updating ticket tags")
                    
                    elif event_kind == "message" and event.get("source") == "agent":
                        message_text = event.get("message", "")
                        if message_text and message_text not in agent_messages:
                            agent_messages.append(message_text)
                            print(f"  💬 Agent: {message_text[:100]}...")
                            
                            # Check for completion indicators
                            if any(word in message_text.lower() for word in ["complete", "finished", "done", "processed"]):
                                workflow_complete = True
                
                # Check if we have all expected tool calls
                tool_names = [t.get("tool_name") for t in tool_calls]
                expected_tools = ["get_ticket", "check_content", "add_note", "update_ticket"]
                
                if all(tool in tool_names for tool in expected_tools):
                    print(f"\n  ✓ All core workflow steps detected")
                    workflow_complete = True
                    
            except Exception as e:
                print(f"  ⚠ Poll error: {e}")
        
        # Step 4: Verify results
        print("\n" + "-" * 80)
        print("STEP 4: Verification Results")
        print("-" * 80)
        
        success = True
        
        # Check tool calls
        tool_names = [t.get("tool_name") for t in tool_calls]
        print(f"\nTool Calls Detected ({len(tool_calls)} total):")
        for tool_name in set(tool_names):
            count = tool_names.count(tool_name)
            print(f"  • {tool_name}: {count}x")
        
        # Verify critical steps
        print("\nCritical Workflow Steps:")
        
        checks = {
            "Fetch ticket data": "get_ticket" in tool_names,
            "Security scan": "check_content" in tool_names,
            "Add note to ticket": "add_note" in tool_names,
            "Update ticket tags": "update_ticket" in tool_names,
        }
        
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            if not passed:
                success = False
        
        # Check for agent responses
        print(f"\nAgent Messages: {len(agent_messages)}")
        if agent_messages:
            print(f"  ✓ Agent provided responses")
        else:
            print(f"  ⚠ No agent messages detected")
        
        # Final verdict
        print("\n" + "=" * 80)
        if success and len(tool_calls) >= 4:
            print("✓ TEST PASSED: Gemini successfully processed ticket through workflow")
            print("=" * 80)
            return True
        else:
            print("✗ TEST FAILED: Workflow incomplete or missing steps")
            print("=" * 80)
            return False

if __name__ == "__main__":
    result = asyncio.run(test_ticket_processing())
    sys.exit(0 if result else 1)
