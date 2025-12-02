#!/usr/bin/env python3
"""
Debug script to see the FULL ticket data including all fields.
"""

import asyncio
import os
import httpx
import json

async def debug_full_ticket():
    """Debug full ticket data from Freshdesk."""
    
    print("=" * 80)
    print("DEBUG: FULL TICKET DATA")
    print("=" * 80)
    print()
    
    ticket_id = "1206331"
    domain = os.getenv("FRESHDESK_DOMAIN")
    api_key = os.getenv("FRESHDESK_API_KEY")
    
    url = f"https://{domain}/api/v2/tickets/{ticket_id}"
    auth = (api_key, "X")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=auth)
        response.raise_for_status()
        ticket = response.json()
        
        print("TICKET FIELDS:")
        print(json.dumps(ticket, indent=2))
        print()
        print("=" * 80)
        
        # Check description
        description = ticket.get('description', '')
        description_text = ticket.get('description_text', '')
        
        print()
        print("DESCRIPTION (HTML):")
        print(description[:1000] if description else "None")
        print()
        
        print("DESCRIPTION (TEXT):")
        print(description_text[:1000] if description_text else "None")
        print()
        
        # Check custom fields
        print("CUSTOM FIELDS:")
        custom_fields = ticket.get('custom_fields', {})
        print(json.dumps(custom_fields, indent=2))
        print()
        
        # Search for booking info
        all_text = f"{description} {description_text} {json.dumps(custom_fields)}"
        keywords = ['booking id', 'booking_id', '509266779', 'bridget vesel']
        found = [kw for kw in keywords if kw.lower() in all_text.lower()]
        
        if found:
            print(f"✓ BOOKING INFO FOUND IN TICKET! Keywords: {found}")
        else:
            print("✗ No booking info found in ticket fields")

if __name__ == "__main__":
    asyncio.run(debug_full_ticket())
