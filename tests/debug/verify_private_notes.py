#!/usr/bin/env python3
"""
Verify that notes added to Freshdesk tickets are private.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
TEST_TICKET_ID = "1206331"

async def check_note_privacy():
    """Check if the notes on the test ticket are private."""
    
    print("=" * 80)
    print("FRESHDESK PRIVATE NOTE VERIFICATION")
    print("=" * 80)
    print(f"\nTicket ID: {TEST_TICKET_ID}")
    print(f"Freshdesk Domain: {FRESHDESK_DOMAIN}\n")
    
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{TEST_TICKET_ID}/conversations"
    auth = (FRESHDESK_API_KEY, "X")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, auth=auth)
            response.raise_for_status()
            conversations = response.json()
            
            print(f"Total conversations found: {len(conversations)}\n")
            
            # Check recent notes added by our automation
            automation_notes = []
            for conv in conversations:
                body = conv.get("body_text", "")
                if "Automated by Whiz AI Agent" in body or "automated_analysis" in body.lower():
                    automation_notes.append(conv)
            
            print(f"Automation notes found: {len(automation_notes)}\n")
            
            if not automation_notes:
                print("⚠️  No automation notes found on this ticket")
                print("   This might mean the workflow hasn't run yet")
                return
            
            # Check privacy status
            print("Privacy Status of Automation Notes:")
            print("-" * 80)
            
            all_private = True
            for i, note in enumerate(automation_notes[:5], 1):  # Check last 5
                is_private = note.get("private", False)
                status = "✓ PRIVATE" if is_private else "✗ PUBLIC"
                created_at = note.get("created_at", "unknown")
                
                print(f"\nNote {i}:")
                print(f"  Status: {status}")
                print(f"  Created: {created_at}")
                print(f"  Preview: {note.get('body_text', '')[:80]}...")
                
                if not is_private:
                    all_private = False
            
            print("\n" + "=" * 80)
            if all_private:
                print("✓ SUCCESS: All automation notes are PRIVATE")
                print("=" * 80)
                print("\nThe add_note function is correctly configured with 'private': True")
                print("Notes are only visible to internal team members.")
            else:
                print("✗ ISSUE: Some automation notes are PUBLIC")
                print("=" * 80)
                print("\nThe add_note function may need to be updated.")
                print("Check the payload in freshdesk_tools.py")
                
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_note_privacy())
