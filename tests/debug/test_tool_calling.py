#!/usr/bin/env python3
"""
Test script to verify Gemini integration with individual tool calling.
Tests each tool independently to verify parameter extraction and execution.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

PARLANT_BASE_URL = "http://localhost:8800"
TEST_TICKET_ID = "1206331"

class ToolCallTester:
    def __init__(self):
        self.agent_id = None
        self.session_id = None
        self.client = None
        self.test_results = {}
        
    async def setup(self):
        """Initialize test environment."""
        print("=" * 80)
        print("GEMINI TOOL CALLING TEST")
        print("=" * 80)
        print(f"\nParlant Server: {PARLANT_BASE_URL}")
        print(f"Test Ticket ID: {TEST_TICKET_ID}\n")
        
        # Read agent ID
        try:
            with open("data/agent_id.txt", "r") as f:
                self.agent_id = f.read().strip()
            print(f"✓ Agent ID: {self.agent_id}")
        except FileNotFoundError:
            print("✗ Error: Agent ID file not found. Is the server running?")
            return False
        
        # Create HTTP client
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Create session
        try:
            response = await self.client.post(
                f"{PARLANT_BASE_URL}/agents/{self.agent_id}/customers/test_customer/sessions",
                json={}
            )
            response.raise_for_status()
            session_data = response.json()
            self.session_id = session_data["id"]
            print(f"✓ Session created: {self.session_id}\n")
            return True
        except Exception as e:
            print(f"✗ Failed to create session: {e}")
            return False
    
    async def send_message_and_wait(self, message: str, expected_tool: str, timeout: int = 30) -> Dict[str, Any]:
        """Send a message and wait for tool execution."""
        print(f"  📤 Sending: '{message}'")
        
        try:
            # Send message
            response = await self.client.post(
                f"{PARLANT_BASE_URL}/agents/{self.agent_id}/customers/test_customer/sessions/{self.session_id}/events",
                json={
                    "kind": "message",
                    "source": "customer",
                    "message": message
                }
            )
            response.raise_for_status()
            
            # Poll for tool execution
            max_polls = timeout
            poll_count = 0
            tool_result = None
            
            while poll_count < max_polls:
                poll_count += 1
                await asyncio.sleep(1)
                
                response = await self.client.get(
                    f"{PARLANT_BASE_URL}/agents/{self.agent_id}/customers/test_customer/sessions/{self.session_id}/events"
                )
                response.raise_for_status()
                events = response.json()
                
                # Look for the expected tool call
                for event in events:
                    if event.get("kind") == "tool_call" and event.get("tool_name") == expected_tool:
                        tool_result = event
                        break
                
                if tool_result:
                    break
            
            if tool_result:
                print(f"  ✓ Tool '{expected_tool}' executed")
                return {
                    "success": True,
                    "tool_name": tool_result.get("tool_name"),
                    "arguments": tool_result.get("arguments", {}),
                    "result": tool_result.get("result", {})
                }
            else:
                print(f"  ✗ Tool '{expected_tool}' not executed within {timeout}s")
                return {"success": False, "error": "Timeout waiting for tool execution"}
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_get_ticket(self):
        """Test get_ticket tool with parameter extraction."""
        print("\n" + "-" * 80)
        print("TEST 1: get_ticket - Fetch ticket metadata")
        print("-" * 80)
        
        result = await self.send_message_and_wait(
            f"Get ticket {TEST_TICKET_ID}",
            "get_ticket"
        )
        
        if result["success"]:
            # Verify parameter extraction
            args = result.get("arguments", {})
            ticket_id = args.get("ticket_id")
            
            if ticket_id == TEST_TICKET_ID:
                print(f"  ✓ Parameter extracted correctly: ticket_id={ticket_id}")
            else:
                print(f"  ✗ Parameter extraction failed: expected {TEST_TICKET_ID}, got {ticket_id}")
                result["success"] = False
            
            # Verify result structure
            tool_result = result.get("result", {})
            if "id" in tool_result and "subject" in tool_result:
                print(f"  ✓ Result contains expected fields")
                print(f"    - Ticket ID: {tool_result.get('id')}")
                print(f"    - Subject: {tool_result.get('subject', '')[:50]}...")
            else:
                print(f"  ✗ Result missing expected fields")
                result["success"] = False
        
        self.test_results["get_ticket"] = result["success"]
        return result["success"]
    
    async def test_check_content(self):
        """Test check_content (Lakera) tool."""
        print("\n" + "-" * 80)
        print("TEST 2: check_content - Security scanning")
        print("-" * 80)
        
        test_content = "This is a normal customer support request about a refund."
        result = await self.send_message_and_wait(
            f"Check if this content is safe: '{test_content}'",
            "check_content"
        )
        
        if result["success"]:
            # Verify result structure
            tool_result = result.get("result", {})
            if "safe" in tool_result and "flagged" in tool_result:
                print(f"  ✓ Result contains expected fields")
                print(f"    - Safe: {tool_result.get('safe')}")
                print(f"    - Flagged: {tool_result.get('flagged')}")
            else:
                print(f"  ✗ Result missing expected fields")
                result["success"] = False
        
        self.test_results["check_content"] = result["success"]
        return result["success"]
    
    async def test_extract_booking_info(self):
        """Test extract_booking_info_from_note tool."""
        print("\n" + "-" * 80)
        print("TEST 3: extract_booking_info_from_note - Booking extraction")
        print("-" * 80)
        
        test_notes = "Booking ID: PW-12345, Amount: $45.00, Date: 2025-11-15"
        result = await self.send_message_and_wait(
            f"Extract booking information from these notes: '{test_notes}'",
            "extract_booking_info_from_note"
        )
        
        if result["success"]:
            # Verify parameter extraction
            args = result.get("arguments", {})
            if "ticket_notes" in args:
                print(f"  ✓ Parameter extracted: ticket_notes provided")
            else:
                print(f"  ✗ Parameter extraction failed: ticket_notes missing")
                result["success"] = False
            
            # Verify result structure
            tool_result = result.get("result", {})
            if "booking_info" in tool_result:
                print(f"  ✓ Result contains expected fields")
                print(f"    - Booking info: {tool_result.get('booking_info')}")
            else:
                print(f"  ✗ Result missing expected fields")
                result["success"] = False
        
        self.test_results["extract_booking_info"] = result["success"]
        return result["success"]
    
    async def test_triage_ticket(self):
        """Test triage_ticket tool."""
        print("\n" + "-" * 80)
        print("TEST 4: triage_ticket - Decision making")
        print("-" * 80)
        
        result = await self.send_message_and_wait(
            f"Triage ticket {TEST_TICKET_ID} and make a refund decision",
            "triage_ticket"
        )
        
        if result["success"]:
            # Verify result structure
            tool_result = result.get("result", {})
            expected_fields = ["decision", "reasoning", "confidence"]
            
            missing_fields = [f for f in expected_fields if f not in tool_result]
            if not missing_fields:
                print(f"  ✓ Result contains expected fields")
                print(f"    - Decision: {tool_result.get('decision')}")
                print(f"    - Reasoning: {tool_result.get('reasoning', '')[:50]}...")
                print(f"    - Confidence: {tool_result.get('confidence')}")
            else:
                print(f"  ✗ Result missing fields: {missing_fields}")
                result["success"] = False
        
        self.test_results["triage_ticket"] = result["success"]
        return result["success"]
    
    async def test_parameter_extraction_complex(self):
        """Test parameter extraction with multiple parameters."""
        print("\n" + "-" * 80)
        print("TEST 5: Parameter Extraction - Multiple parameters")
        print("-" * 80)
        
        result = await self.send_message_and_wait(
            f"Add a note to ticket {TEST_TICKET_ID} saying 'Test note from automated testing'",
            "add_note",
            timeout=20
        )
        
        if result["success"]:
            # Verify both parameters extracted
            args = result.get("arguments", {})
            ticket_id = args.get("ticket_id")
            note = args.get("note")
            
            if ticket_id == TEST_TICKET_ID:
                print(f"  ✓ ticket_id extracted correctly: {ticket_id}")
            else:
                print(f"  ✗ ticket_id extraction failed: expected {TEST_TICKET_ID}, got {ticket_id}")
                result["success"] = False
            
            if note and "test" in note.lower():
                print(f"  ✓ note parameter extracted: '{note[:50]}...'")
            else:
                print(f"  ✗ note parameter extraction failed")
                result["success"] = False
        
        self.test_results["parameter_extraction"] = result["success"]
        return result["success"]
    
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()
    
    async def run_all_tests(self):
        """Run all tool calling tests."""
        if not await self.setup():
            return False
        
        try:
            # Run individual tests
            await self.test_get_ticket()
            await asyncio.sleep(2)  # Brief pause between tests
            
            await self.test_check_content()
            await asyncio.sleep(2)
            
            await self.test_extract_booking_info()
            await asyncio.sleep(2)
            
            await self.test_triage_ticket()
            await asyncio.sleep(2)
            
            await self.test_parameter_extraction_complex()
            
            # Print summary
            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            
            total_tests = len(self.test_results)
            passed_tests = sum(1 for result in self.test_results.values() if result)
            
            print(f"\nTests Run: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {total_tests - passed_tests}")
            print()
            
            for test_name, passed in self.test_results.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {status}: {test_name}")
            
            print("\n" + "=" * 80)
            
            all_passed = all(self.test_results.values())
            if all_passed:
                print("✓ ALL TESTS PASSED")
                print("=" * 80)
                print("\nGemini tool calling functionality verified:")
                print("  • get_ticket works correctly")
                print("  • check_content (Lakera) works correctly")
                print("  • extract_booking_info works correctly")
                print("  • triage_ticket works correctly")
                print("  • Parameter extraction works correctly")
            else:
                print("✗ SOME TESTS FAILED")
                print("=" * 80)
            
            return all_passed
            
        finally:
            await self.cleanup()

async def main():
    tester = ToolCallTester()
    result = await tester.run_all_tests()
    return result

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
