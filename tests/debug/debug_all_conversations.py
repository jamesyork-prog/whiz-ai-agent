#!/usr/bin/env python3
"""
Debug script to see ALL conversations from Freshdesk API.
"""

import asyncio
import os
import httpx

async def debug_all_conversations():
    """Debug all conversations from Freshdesk."""
    
    print("=" * 80)
    print("DEBUG: ALL FRESHDESK CONVERSATIONS")
    print("=" * 80)
    print()
    
    ticket_id = "1206331"
    domain = os.getenv("FRESHDESK_DOMAIN")
    api_key = os.getenv("FRESHDESK_API_KEY")
    
    url = f"https://{domain}/api/v2/tickets/{ticket_id}/conversations"
    auth = (api_key, "X")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=auth)
        response.raise_for_status()
        conversations = response.json()
        
        print(f"Total conversations returned: {len(conversations)}")
        print()
        
        for i, conv in enumerate(conversations):
            print(f"{'=' * 80}")
            print(f"CONVERSATION {i+1}")
            print(f"{'=' * 80}")
            print(f"ID: {conv.get('id')}")
            print(f"Private: {conv.get('private')}")
            print(f"Incoming: {conv.get('incoming')}")
            print(f"Created: {conv.get('created_at')}")
            print(f"User ID: {conv.get('user_id')}")
            print()
            
            body_text = conv.get('body_text', '')
            print(f"Body Text Length: {len(body_text)} chars")
            print()
            print("Body Text:")
            print(body_text)
            print()
            
            # Check for booking keywords
            keywords = ['booking id', 'booking_id', 'booking created', 'booking base price', 
                       'parking pass', 'user id', 'user email', 'location name', '509266779']
            found = [kw for kw in keywords if kw.lower() in body_text.lower()]
            if found:
                print(f"✓ BOOKING INFO FOUND! Keywords: {found}")
            print()

if __name__ == "__main__":
    asyncio.run(debug_all_conversations())
