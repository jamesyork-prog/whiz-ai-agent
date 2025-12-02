#!/usr/bin/env python3
"""
Quick test script to verify pattern extraction is working.
"""

import asyncio
import os
import sys

# Add app_tools to path
sys.path.insert(0, '/app')

from app_tools.tools.booking_extractor import BookingExtractor


async def test_pattern_extraction():
    """Test pattern extraction with structured and unstructured text."""
    
    # Set API key
    os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'test-key')
    
    extractor = BookingExtractor(use_pattern_fallback=True)
    
    print("\n" + "="*60)
    print("TEST 1: Structured text (should use pattern extraction)")
    print("="*60)
    
    structured_text = """
    Booking ID: PW-12345
    Amount: $45.00
    Event Date: 2025-11-15
    Location: Downtown Parking Garage
    Email: customer@example.com
    """
    
    result = await extractor.extract_booking_info(structured_text)
    print(f"\nExtraction Method: {result['extraction_method']}")
    print(f"Found: {result['found']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Booking Info: {result['booking_info']}")
    
    print("\n" + "="*60)
    print("TEST 2: Unstructured text (should fall back to LLM)")
    print("="*60)
    
    unstructured_text = """
    I made a parking reservation last week for the downtown area.
    It cost me around forty-five dollars. Can I get a refund?
    """
    
    result2 = await extractor.extract_booking_info(unstructured_text)
    print(f"\nExtraction Method: {result2['extraction_method']}")
    print(f"Found: {result2['found']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"Booking Info: {result2['booking_info']}")
    
    print("\n" + "="*60)
    print("✅ Pattern extraction test complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_pattern_extraction())
