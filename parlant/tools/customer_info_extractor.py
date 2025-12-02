"""
Customer Information Extractor module for extracting customer details from ticket text.

This module uses Gemini LLM to extract customer information (email, name, dates, location)
from ticket descriptions when Zapier fails to find booking information.
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Optional
from google import genai
from google.genai import types

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class CustomerInfo:
    """Extracted customer information for ParkWhiz search."""
    email: str
    name: Optional[str] = None
    arrival_date: str = ""  # ISO format YYYY-MM-DD
    exit_date: str = ""     # ISO format YYYY-MM-DD
    location: Optional[str] = None
    
    def is_complete(self) -> bool:
        """
        Check if required fields are present.
        
        Required fields for ParkWhiz API search:
        - email: Customer email address
        - arrival_date: Parking start date
        - exit_date: Parking end date
        
        Returns:
            True if all required fields are present and non-empty, False otherwise
        """
        return bool(
            self.email and 
            self.email.strip() and
            self.arrival_date and 
            self.arrival_date.strip() and
            self.exit_date and 
            self.exit_date.strip()
        )


class CustomerInfoExtractor:
    """Extracts customer details from ticket description using LLM."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the CustomerInfoExtractor with Gemini model.
        
        Args:
            model_name: Gemini model to use (defaults to GEMINI_MODEL env var or gemini-2.5-flash)
            
        Raises:
            ValueError: If GEMINI_API_KEY environment variable is not set
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
        
        logger.debug(f"CustomerInfoExtractor initialized with model: {self.model_name}")
    
    async def extract(self, ticket_description: str) -> CustomerInfo:
        """
        Extract customer information using LLM.
        
        Extracts:
        - email: Customer email address (required)
        - name: Customer name (optional)
        - arrival_date: Parking start date in ISO format YYYY-MM-DD (required)
        - exit_date: Parking end date in ISO format YYYY-MM-DD (required)
        - location: Parking location/facility name (optional)
        
        Args:
            ticket_description: Full ticket text
            
        Returns:
            CustomerInfo object with extracted information
        """
        import asyncio
        
        logger.info("Starting customer information extraction")
        
        if not ticket_description or not ticket_description.strip():
            logger.warning("Empty ticket description provided for extraction")
            return CustomerInfo(email="")
        
        logger.debug(f"Ticket description length: {len(ticket_description)} characters")
        
        # Create structured prompt for extraction
        prompt = self._create_extraction_prompt(ticket_description)
        
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
                                "email": {"type": "string"},
                                "name": {"type": "string"},
                                "arrival_date": {"type": "string"},
                                "exit_date": {"type": "string"},
                                "location": {"type": "string"}
                            },
                            "required": []  # All fields optional in response, we validate with is_complete()
                        }
                    )
                ),
                timeout=10.0  # 10-second timeout
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Create CustomerInfo object
            customer_info = CustomerInfo(
                email=result.get("email", ""),
                name=result.get("name"),
                arrival_date=result.get("arrival_date", ""),
                exit_date=result.get("exit_date", ""),
                location=result.get("location")
            )
            
            logger.info(
                f"Customer info extraction completed. "
                f"Email: {'present' if customer_info.email else 'missing'}, "
                f"Dates: {'present' if customer_info.arrival_date and customer_info.exit_date else 'missing'}, "
                f"Complete: {customer_info.is_complete()}"
            )
            
            return customer_info
            
        except asyncio.TimeoutError:
            # Handle timeout - log and return empty result
            logger.error("Customer info extraction timeout after 10 seconds")
            return CustomerInfo(email="")
        
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            logger.error(f"Error parsing LLM response: {e}")
            return CustomerInfo(email="")
        
        except Exception as e:
            # Handle all other errors (API failures, network issues, etc.)
            error_type = type(e).__name__
            logger.error(f"Error extracting customer info ({error_type}): {e}")
            return CustomerInfo(email="")
    
    def _create_extraction_prompt(self, ticket_description: str) -> str:
        """
        Create a structured prompt for customer information extraction.
        
        Args:
            ticket_description: Raw ticket text
            
        Returns:
            Formatted prompt string
        """
        return f"""Extract customer information from the following ticket description. Look for:

1. **Email**: Customer email address (e.g., customer@example.com)
2. **Name**: Customer name (first and last name if available)
3. **Arrival Date**: When the parking starts (start date/time)
4. **Exit Date**: When the parking ends (end date/time)
5. **Location**: Parking facility name or address

**Important Instructions:**
- Use ISO format (YYYY-MM-DD) for dates
- If a date includes time, extract just the date portion
- If only one date is mentioned, it might be the arrival date (event date)
- If a date range is mentioned (e.g., "Nov 15-17"), extract start as arrival_date and end as exit_date
- If a field is not found, omit it from the response or return empty string
- Email is the most critical field - search carefully for email addresses
- Look for dates in various formats: "11/15/2025", "November 15, 2025", "Nov 15", etc.

**Ticket Description:**
{ticket_description}

Extract the customer information as JSON."""
