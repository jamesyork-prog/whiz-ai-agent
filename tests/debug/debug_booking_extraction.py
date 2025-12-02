#!/usr/bin/env python3
"""
Debug script to see what notes are being passed to booking extraction.
"""

import asyncio
import os
import sys

sys.path.insert(0, '/app')

from app_tools.tools.freshdesk_tools import get_ticket_conversations
from unittest.mock import Mock

async def debug_booking_extraction():
    """Debug what notes are being extracted."""
    
    print("=" * 80)
    print("DEBUG: BOOKING EXTRACTION")
    print("=" * 80)
    print()
    
    ticket_id = "1206331"
    
    # Create mock context
    context = Mock()
    context.agent_id = "test_agent"
    context.customer_id = "test_customer"
    context.session_id = "test_session"
    
    # Get conversations
    conv_result = await get_ticket_conversations(context, ticket_id)
    conversations = conv_result.data.get('conversations', [])
    
    print(f"Total conversations: {len(conversations)}")
    print()
    
    # Build notes text like the workflow does
    notes_text = "Private Notes:\n"
    for i, conv in enumerate(conversations):
        body_text = conv.get('body_text', '')
        print(f"--- Conversation {i+1} ---")
        print(f"Length: {len(body_text)} chars")
        print(f"Preview: {body_text[:200]}")
        print()
        
        # Check for booking info keywords
        keywords = ['booking id', 'booking_id', 'booking created', 'booking base price', 
                   'parking pass', 'user id', 'user email', 'location name']
        found_keywords = [kw for kw in keywords if kw.lower() in body_text.lower()]
        
        if found_keywords:
            print(f"✓ Found keywords: {found_keywords}")
            print()
            print("Full text:")
            print(body_text)
            print()
        
        notes_text += f"\n{body_text}\n"
    
    print("=" * 80)
    print(f"Total notes text length: {len(notes_text)} chars")
    print()
    
    # Check if booking info is present
    if 'booking id' in notes_text.lower() or 'booking_id' in notes_text.lower():
        print("✓ Booking ID found in notes")
    else:
        print("✗ Booking ID NOT found in notes")
    
    if 'booking base price' in notes_text.lower():
        print("✓ Booking price found in notes")
    else:
        print("✗ Booking price NOT found in notes")

if __name__ == "__main__":
    asyncio.run(debug_booking_extraction())
