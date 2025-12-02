"""
Zapier Failure Detector module for identifying when Zapier failed to find booking information.

This module detects two types of failures:
1. Explicit Zapier failure messages in ticket descriptions
2. Invalid booking ID patterns (0000, N/A, empty, etc.)
"""

import re
import logging
from typing import Optional

# Configure logger
logger = logging.getLogger(__name__)


class ZapierFailureDetector:
    """
    Detects when Zapier failed to find booking information.
    
    This class identifies two failure scenarios:
    1. Explicit failure message: "Booking information not found for provided Booking Number"
    2. Invalid booking ID patterns: "0000", "N/A", empty strings, etc.
    """
    
    # Zapier failure message pattern
    ZAPIER_FAILURE_MESSAGE = "Booking information not found for provided Booking Number"
    
    # Invalid booking ID patterns
    INVALID_BOOKING_PATTERNS = [
        r'^0+$',           # All zeros: 0, 00, 0000, etc.
        r'^N/?A$',         # N/A or NA (case insensitive)
        r'^none$',         # "none" (case insensitive)
        r'^null$',         # "null" (case insensitive)
        r'^undefined$',    # "undefined" (case insensitive)
        r'^\s*$',          # Empty or whitespace only
    ]
    
    def __init__(self):
        """Initialize the ZapierFailureDetector."""
        # Compile regex patterns for performance
        self.invalid_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.INVALID_BOOKING_PATTERNS
        ]
        logger.debug("ZapierFailureDetector initialized")
    
    def is_zapier_failure(self, ticket_description: str) -> bool:
        """
        Check if ticket indicates Zapier booking lookup failure.
        
        Detects the specific message: "Booking information not found for provided Booking Number"
        
        Args:
            ticket_description: Full ticket description text
            
        Returns:
            True if Zapier failure detected, False otherwise
        """
        if not ticket_description:
            logger.debug("Empty ticket description provided")
            return False
        
        # Check for exact failure message (case insensitive)
        is_failure = self.ZAPIER_FAILURE_MESSAGE.lower() in ticket_description.lower()
        
        if is_failure:
            logger.info("Zapier failure message detected in ticket")
        else:
            logger.debug("No Zapier failure message found")
        
        return is_failure
    
    def is_invalid_booking_id(self, booking_id: Optional[str]) -> bool:
        """
        Check if booking ID appears invalid (0000, N/A, empty, etc).
        
        Invalid patterns include:
        - All zeros: "0", "00", "0000", etc.
        - N/A variants: "N/A", "NA"
        - Placeholder values: "none", "null", "undefined"
        - Empty or whitespace-only strings
        - None values
        
        Args:
            booking_id: Booking ID to validate
            
        Returns:
            True if booking ID is invalid, False otherwise
        """
        # None is considered invalid
        if booking_id is None:
            logger.debug("Booking ID is None - considered invalid")
            return True
        
        # Convert to string for pattern matching
        booking_id_str = str(booking_id).strip()
        
        # Check against all invalid patterns
        for pattern in self.invalid_patterns:
            if pattern.match(booking_id_str):
                logger.info(f"Invalid booking ID detected: '{booking_id}' matches pattern {pattern.pattern}")
                return True
        
        logger.debug(f"Booking ID '{booking_id}' is valid")
        return False
    
    def detect_failure(self, ticket_description: str, booking_id: Optional[str] = None) -> dict:
        """
        Comprehensive failure detection combining message and booking ID checks.
        
        Args:
            ticket_description: Full ticket description text
            booking_id: Optional booking ID to validate
            
        Returns:
            Dict containing:
                - is_failure: bool indicating if any failure detected
                - zapier_message_failure: bool for message-based detection
                - invalid_booking_id: bool for ID-based detection
                - reason: str explaining the failure
        """
        zapier_msg_failure = self.is_zapier_failure(ticket_description)
        invalid_id = self.is_invalid_booking_id(booking_id) if booking_id is not None else False
        
        is_failure = zapier_msg_failure or invalid_id
        
        # Build reason string
        reasons = []
        if zapier_msg_failure:
            reasons.append("Zapier failure message detected")
        if invalid_id:
            reasons.append(f"Invalid booking ID: '{booking_id}'")
        
        reason = "; ".join(reasons) if reasons else "No failure detected"
        
        result = {
            "is_failure": is_failure,
            "zapier_message_failure": zapier_msg_failure,
            "invalid_booking_id": invalid_id,
            "reason": reason
        }
        
        logger.info(f"Failure detection result: {result}")
        return result
