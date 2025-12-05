"""
BookingExtractor component for extracting structured booking information from ticket text.

This module uses a hybrid approach: first attempting fast pattern-based extraction,
then falling back to Gemini LLM for complex or unstructured ticket notes.
"""

import os
import json
import logging
from typing import Dict, Optional
from google import genai
from google.genai import types
from .booking_patterns import PatternExtractor

# Configure logger
logger = logging.getLogger(__name__)


class BookingExtractor:
    """
    Extracts structured booking information from ticket text using hybrid approach.
    
    This class first attempts fast pattern-based extraction using regex and HTML parsing.
    If pattern extraction fails or has low confidence, it falls back to Gemini LLM
    for more sophisticated analysis.
    """
    
    def __init__(self, model_name: Optional[str] = None, use_pattern_fallback: bool = True):
        """
        Initialize the BookingExtractor with Gemini model and pattern extractor.
        
        Args:
            model_name: Gemini model to use (defaults to GEMINI_MODEL env var or gemini-2.5-flash)
            use_pattern_fallback: Whether to try pattern-based extraction first (default: True)
        """
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Please add it to your .env file."
            )
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)
        
        # Use provided model or fall back to environment variable or default
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Initialize pattern extractor for performance optimization
        self.use_pattern_fallback = use_pattern_fallback
        self.pattern_extractor = PatternExtractor() if use_pattern_fallback else None
    
    async def extract_booking_info(self, ticket_notes: str) -> Dict:
        """
        Extract booking information from ticket text using hybrid approach.
        
        First attempts fast pattern-based extraction. If that fails or has low
        confidence, falls back to Gemini LLM for more sophisticated analysis.
        
        Args:
            ticket_notes: Raw text from ticket notes/conversations
            
        Returns:
            Dict containing:
                - booking_info: Dict with extracted fields (booking_id, amount, dates, etc.)
                - confidence: "high" | "medium" | "low"
                - found: bool indicating if booking info was found
                - extraction_method: "pattern" | "llm"
        """
        logger.info("Starting booking information extraction")
        
        if not ticket_notes or not ticket_notes.strip():
            logger.warning("Empty ticket notes provided for extraction")
            return {
                "booking_info": {},
                "confidence": "low",
                "found": False,
                "extraction_method": "none"
            }
        
        logger.debug(f"Ticket notes length: {len(ticket_notes)} characters")
        
        # Try pattern-based extraction first (performance optimization)
        if self.use_pattern_fallback and self.pattern_extractor:
            logger.info("Attempting pattern-based extraction")
            pattern_result = self._try_pattern_extraction(ticket_notes)
            
            # If pattern extraction succeeded with medium or high confidence, use it
            if pattern_result["found"] and pattern_result["confidence"] in ["medium", "high"]:
                logger.info(f"Pattern extraction succeeded with {pattern_result['confidence']} confidence. "
                           f"Found: {list(pattern_result['booking_info'].keys())}")
                return pattern_result
            
            # If pattern extraction found some data but low confidence, we'll still try LLM
            # but can use the pattern result as a fallback if LLM fails
            logger.info(f"Pattern extraction had {pattern_result['confidence']} confidence, falling back to LLM")
        
        # Fall back to LLM extraction
        logger.info("Using LLM extraction")
        return await self._extract_with_llm(ticket_notes)
    
    def _try_pattern_extraction(self, ticket_notes: str) -> Dict:
        """
        Attempt pattern-based extraction from ticket text.
        
        Args:
            ticket_notes: Raw text from ticket notes
            
        Returns:
            Dict with extraction results
        """
        try:
            # Check if content looks like HTML
            if '<' in ticket_notes and '>' in ticket_notes:
                logger.debug("Detected HTML content, using HTML extraction")
                return self.pattern_extractor.extract_from_html(ticket_notes)
            else:
                logger.debug("Detected plain text content, using text extraction")
                return self.pattern_extractor.extract_from_text(ticket_notes)
        except Exception as e:
            logger.error(f"Pattern extraction error: {type(e).__name__}: {e}")
            return {
                "booking_info": {},
                "confidence": "low",
                "found": False,
                "extraction_method": "pattern"
            }
    
    async def _extract_with_llm(self, ticket_notes: str) -> Dict:
        """
        Extract booking information using Gemini LLM with timeout and error handling.
        
        Args:
            ticket_notes: Raw text from ticket notes
            
        Returns:
            Dict with extraction results
        """
        import asyncio
        
        # Create structured prompt for extraction
        prompt = self._create_extraction_prompt(ticket_notes)
        
        logger.debug(f"Calling Gemini API with model: {self.model_name}")
        
        try:
            # Make Gemini API call with JSON schema and 10-second timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Low temperature for consistent extraction
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "booking_id": {"type": "string"},
                                "amount": {"type": "number"},
                                "reservation_date": {"type": "string"},
                                "event_date": {"type": "string"},
                                "location": {"type": "string"},
                                "booking_type": {"type": "string"},
                                "customer_email": {"type": "string"},
                                "cancellation_date": {"type": "string"},
                                "found": {"type": "boolean"},
                                "multiple_bookings": {"type": "boolean"}
                            },
                            "required": ["found"]
                        }
                    )
                ),
                timeout=10.0  # 10-second timeout
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Calculate confidence based on completeness
            confidence = self._calculate_confidence(result)
            
            # Extract booking info (remove metadata fields)
            booking_info = {
                k: v for k, v in result.items() 
                if k not in ["found", "multiple_bookings"] and v is not None
            }
            
            logger.info(f"LLM extraction completed. Found: {result.get('found', False)}, "
                       f"Confidence: {confidence}, Fields: {list(booking_info.keys())}")
            
            if result.get("multiple_bookings"):
                logger.warning("Multiple bookings detected in ticket")
            
            return {
                "booking_info": booking_info,
                "confidence": confidence,
                "found": result.get("found", False),
                "extraction_method": "llm",
                "multiple_bookings": result.get("multiple_bookings", False)
            }
            
        except asyncio.TimeoutError:
            # Handle timeout - log and return empty result
            logger.error("LLM extraction timeout after 10 seconds")
            return {
                "booking_info": {},
                "confidence": "low",
                "found": False,
                "extraction_method": "llm",
                "error": "Timeout after 10 seconds"
            }
        
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            logger.error(f"Error parsing LLM response: {e}")
            return {
                "booking_info": {},
                "confidence": "low",
                "found": False,
                "extraction_method": "llm",
                "error": f"JSON parsing error: {str(e)}"
            }
        
        except Exception as e:
            # Handle all other errors (API failures, network issues, etc.)
            error_type = type(e).__name__
            logger.error(f"Error extracting booking info ({error_type}): {e}")
            return {
                "booking_info": {},
                "confidence": "low",
                "found": False,
                "extraction_method": "llm",
                "error": f"{error_type}: {str(e)}"
            }
    
    def _create_extraction_prompt(self, ticket_notes: str) -> str:
        """
        Create a structured prompt for booking information extraction.
        
        Args:
            ticket_notes: Raw ticket text
            
        Returns:
            Formatted prompt string
        """
        return f"""Extract booking information from the following ticket notes. Look for:

1. **Booking ID**: Any reference number like "PW-12345", "509266779", "Booking #123", etc.
2. **Amount**: Dollar amounts like "$45.00", "45 dollars", etc.
3. **Reservation Date**: When the booking was made
4. **Event Date**: When the parking was scheduled for (start date/time) - THIS IS THE MOST CRITICAL FIELD
5. **Location**: Parking facility name or address
6. **Booking Type**: "confirmed", "on-demand", "third-party", or "unknown"
7. **Customer Email**: Email address of the customer
8. **Cancellation Date**: When the cancellation was requested (if mentioned)

**CRITICAL DATE EXTRACTION RULES:**
- Look for "Parking Pass Start Time" - this is the event_date
- Look for "Booking Created" - this is the reservation_date
- ALWAYS use 4-digit years (e.g., 2025, not 25)
- Convert dates to ISO format: YYYY-MM-DD (e.g., "Thursday Dec 04, 2025, 12:00 PM" → "2025-12-04")
- Pay careful attention to the year - if you see "2025", use 2025, NOT 2020
- If a date includes time (e.g., "12:00 PM"), ignore the time and extract only the date

**Important Instructions:**
- If multiple bookings are mentioned, extract information for the PRIMARY booking being disputed
- Set "found" to true if you find at least a booking ID or event date
- Set "multiple_bookings" to true if more than one booking is referenced
- Use ISO format (YYYY-MM-DD) for dates - ALWAYS include the full 4-digit year
- If a field is not found, omit it from the response (don't include null values)
- For booking_type, infer from context: "confirmed" for advance bookings, "on-demand" for same-day, "third-party" if booked through another platform

**Ticket Notes:**
{ticket_notes}

Extract the booking information as JSON."""
    
    def _calculate_confidence(self, result: Dict) -> str:
        """
        Calculate confidence level based on completeness of extracted data.
        
        Args:
            result: Extracted booking information
            
        Returns:
            "high" | "medium" | "low"
        """
        if not result.get("found", False):
            return "low"
        
        # Count critical fields present
        critical_fields = ["booking_id", "event_date"]
        critical_count = sum(1 for field in critical_fields if result.get(field))
        
        # Count optional fields present
        optional_fields = ["amount", "reservation_date", "location", "booking_type", "customer_email"]
        optional_count = sum(1 for field in optional_fields if result.get(field))
        
        # High confidence: both critical fields + at least 3 optional fields
        if critical_count == 2 and optional_count >= 3:
            return "high"
        
        # Medium confidence: both critical fields (even without optional fields)
        elif critical_count == 2:
            return "medium"
        
        # Medium confidence: 1 critical field + at least 3 optional fields
        elif critical_count == 1 and optional_count >= 3:
            return "medium"
        
        # Low confidence: missing critical fields or very incomplete
        else:
            return "low"
