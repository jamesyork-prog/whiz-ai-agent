"""
RuleEngine component for applying deterministic business rules to refund decisions.

This module provides a RuleEngine class that applies clear-cut business rules
to make refund decisions with high confidence, reducing the need for LLM analysis
in straightforward cases.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

# Configure logger
logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Applies deterministic business rules for refund decisions.
    
    The RuleEngine evaluates booking information against predefined business rules
    to make quick, consistent decisions for clear-cut cases. When rules produce
    uncertain results, the decision is escalated to LLM analysis.
    """
    
    def __init__(self, rules: Dict):
        """
        Initialize the RuleEngine with policy rules.
        
        Args:
            rules: Dictionary containing refund policy rules from PolicyLoader
        """
        self.rules = rules
    
    def apply_rules(
        self,
        booking_info: Dict,
        ticket_data: Dict
    ) -> Dict:
        """
        Apply business rules to make a refund decision.
        
        This method evaluates the booking information against deterministic rules
        in priority order:
        1. 7+ days before event → Approve (high confidence)
        2. After event start → Deny (high confidence)
        3. 3-7 days + confirmed booking → Approve (medium confidence)
        4. <3 days + on-demand → Deny (high confidence)
        5. Oversold location → Approve (high confidence)
        6. Duplicate pass → Approve (high confidence)
        7. Edge cases → Uncertain (triggers LLM)
        
        Args:
            booking_info: Dictionary containing booking details:
                - booking_id (str): Booking identifier
                - event_date (str): ISO format date of the event
                - booking_type (str): Type of booking (confirmed, on-demand, etc.)
                - amount (float): Booking amount
                - cancellation_date (str, optional): ISO format cancellation date
            ticket_data: Dictionary containing ticket information:
                - ticket_id (str): Freshdesk ticket ID
                - subject (str): Ticket subject
                - description (str): Ticket description
        
        Returns:
            Dictionary containing:
                - decision (str): "Approved", "Denied", or "Uncertain"
                - reasoning (str): Human-readable explanation
                - policy_rule (str): Specific policy rule applied
                - confidence (str): "high", "medium", or "low"
        """
        logger.info("Applying rule-based decision logic")
        logger.debug(f"Booking info: booking_id={booking_info.get('booking_id')}, "
                    f"event_date={booking_info.get('event_date')}, "
                    f"booking_type={booking_info.get('booking_type')}")
        
        # Validate required fields
        if not booking_info.get("event_date"):
            logger.warning("Missing event date - cannot apply rules")
            return {
                "decision": "Uncertain",
                "reasoning": "Missing event date - cannot calculate days before event",
                "policy_rule": "Data Validation",
                "confidence": "low"
            }
        
        # Calculate days before event
        days_before_event = self._calculate_days_before_event(
            booking_info.get("cancellation_date"),
            booking_info.get("event_date")
        )
        
        if days_before_event is None:
            logger.error("Failed to calculate days before event - invalid date format")
            return {
                "decision": "Uncertain",
                "reasoning": "Unable to calculate days before event - invalid date format",
                "policy_rule": "Data Validation",
                "confidence": "low"
            }
        
        logger.info(f"Days before event: {days_before_event}")
        
        # Extract booking details
        booking_type = booking_info.get("booking_type", "").lower()
        amount = booking_info.get("amount", 0)
        ticket_description = ticket_data.get("description", "").lower()
        
        # PRIORITY RULE: Check for duplicate claims FIRST (must escalate regardless of timing)
        # This overrides all other rules because we cannot auto-detect duplicates
        if self._check_for_duplicate_claim(ticket_data):
            logger.info("Rule matched: Duplicate Claim. Decision: Needs Human Review (API limitation)")
            return {
                "decision": "Needs Human Review",
                "reasoning": "Customer reports duplicate booking or being charged twice. "
                            "Duplicate detection requires manual review because the ParkWhiz API "
                            "does not support searching bookings by customer email. "
                            "A specialist will review the account to locate both bookings.",
                "policy_rule": "Duplicate Booking Claim - Requires Manual Review",
                "confidence": "high"
            }
        
        # Rule 1: 7+ days before event → Approve (Pre-Arrival)
        if days_before_event >= 7:
            logger.info(f"Rule matched: Pre-Arrival (7+ days). Decision: Approved")
            return {
                "decision": "Approved",
                "reasoning": f"Cancellation requested {days_before_event} days before event start. "
                            f"Pre-arrival cancellations (7+ days) are automatically approved per policy.",
                "policy_rule": "Pre-Arrival (7+ days before event)",
                "confidence": "high"
            }
        
        # Rule 2: After event start → Deny (unless special circumstances)
        if days_before_event < 0:
            logger.info(f"Post-event cancellation detected ({abs(days_before_event)} days after)")
            
            # Check for special circumstances that override post-event denial
            if self._check_for_oversold(ticket_description):
                logger.info("Rule matched: Oversold Location (post-event exception). Decision: Approved")
                return {
                    "decision": "Approved",
                    "reasoning": "Location was oversold/full. Customer was unable to park despite valid booking.",
                    "policy_rule": "Oversold Location",
                    "confidence": "high"
                }
            
            # Check for duplicate claims - escalate even post-event
            if self._check_for_duplicate_claim(ticket_data):
                logger.info("Rule matched: Duplicate Claim (post-event). Decision: Needs Human Review")
                return {
                    "decision": "Needs Human Review",
                    "reasoning": "Customer reports duplicate booking or being charged twice. "
                                "Duplicate detection requires manual review because the ParkWhiz API "
                                "does not support searching bookings by customer email. "
                                "A specialist will review the account to locate both bookings.",
                    "policy_rule": "Duplicate Booking Claim - Requires Manual Review",
                    "confidence": "high"
                }
            
            if self._check_for_paid_again(ticket_description):
                logger.info("Rule matched: Paid Again (post-event exception). Decision: Approved")
                return {
                    "decision": "Approved",
                    "reasoning": "Customer had to pay again on-site despite having a valid booking.",
                    "policy_rule": "Paid Again",
                    "confidence": "high"
                }
            
            if self._check_for_closed(ticket_description):
                logger.info("Rule matched: Closed Location (post-event exception). Decision: Approved")
                return {
                    "decision": "Approved",
                    "reasoning": "Location was closed or inaccessible due to circumstances beyond customer control (gate down, flooded, power out, etc.).",
                    "policy_rule": "Closed Location",
                    "confidence": "high"
                }
            
            if self._check_for_accessibility(ticket_description):
                logger.info("Rule matched: Accessibility Issue (post-event exception). Decision: Approved")
                return {
                    "decision": "Approved",
                    "reasoning": "Customer was unable to access location due to road closures, police blockades, or other access restrictions.",
                    "policy_rule": "Accessibility Issue",
                    "confidence": "high"
                }
            
            # Default post-event denial - keep message vague to prevent gaming
            logger.info("Rule matched: Post-Event Cancellation. Decision: Denied")
            return {
                "decision": "Denied",
                "reasoning": f"Cancellation requested {abs(days_before_event)} days after event start. "
                            f"Post-event refunds are not permitted per policy.",
                "policy_rule": "Post-Event Cancellation",
                "confidence": "high"
            }
        
        # Rule 3: <3 days + on-demand → Deny
        if days_before_event < 3 and "on-demand" in booking_type:
            logger.info("Rule matched: On-Demand Cancellation (<3 days). Decision: Denied")
            return {
                "decision": "Denied",
                "reasoning": f"On-demand booking with only {days_before_event} days notice. "
                            f"On-demand bookings require 3+ days notice for cancellation.",
                "policy_rule": "On-Demand Cancellation Policy (<3 days)",
                "confidence": "high"
            }
        
        # Rule 4: 3-7 days + confirmed booking → Approve (medium confidence)
        if 3 <= days_before_event < 7 and "confirmed" in booking_type:
            logger.info("Rule matched: Confirmed Booking (3-7 days). Decision: Approved")
            return {
                "decision": "Approved",
                "reasoning": f"Confirmed booking with {days_before_event} days notice. "
                            f"Meets minimum cancellation window for confirmed bookings.",
                "policy_rule": "Confirmed Booking (3-7 days notice)",
                "confidence": "medium"
            }
        
        # Rule 5: Check for special scenarios that always approve
        if self._check_for_oversold(ticket_description):
            logger.info("Rule matched: Oversold Location. Decision: Approved")
            return {
                "decision": "Approved",
                "reasoning": "Location was oversold/full. Customer was unable to park despite valid booking.",
                "policy_rule": "Oversold Location",
                "confidence": "high"
            }
        
        if self._check_for_paid_again(ticket_description):
            logger.info("Rule matched: Paid Again. Decision: Approved")
            return {
                "decision": "Approved",
                "reasoning": "Customer had to pay again on-site despite having a valid booking.",
                "policy_rule": "Paid Again",
                "confidence": "high"
            }
        
        # Rule 6: 3-7 days with unclear booking type → Uncertain (needs LLM)
        if 3 <= days_before_event < 7:
            logger.info("Rule matched: Ambiguous Booking Type (3-7 days). Decision: Uncertain (needs LLM)")
            return {
                "decision": "Uncertain",
                "reasoning": f"Cancellation with {days_before_event} days notice, but booking type is unclear. "
                            f"Requires LLM analysis to determine if refund should be approved.",
                "policy_rule": "Ambiguous Booking Type (3-7 days)",
                "confidence": "low"
            }
        
        # Rule 7: <3 days with non-on-demand booking → Uncertain (needs LLM)
        if days_before_event < 3:
            logger.info("Rule matched: Short Notice Cancellation (<3 days). Decision: Uncertain (needs LLM)")
            return {
                "decision": "Uncertain",
                "reasoning": f"Short notice cancellation ({days_before_event} days) with booking type '{booking_type}'. "
                            f"Requires LLM analysis to evaluate special circumstances.",
                "policy_rule": "Short Notice Cancellation (<3 days)",
                "confidence": "low"
            }
        
        # Default: Uncertain (edge case)
        logger.warning(f"No rule matched - edge case. Days: {days_before_event}, Type: {booking_type}")
        return {
            "decision": "Uncertain",
            "reasoning": f"Edge case: {days_before_event} days before event, booking type '{booking_type}'. "
                        f"Requires LLM analysis for proper evaluation.",
            "policy_rule": "Edge Case - Requires LLM Analysis",
            "confidence": "low"
        }
    
    def _calculate_days_before_event(
        self,
        cancellation_date: Optional[str],
        event_date: str
    ) -> Optional[int]:
        """
        Calculate the number of days between cancellation and event start.
        
        Args:
            cancellation_date: ISO format date string (YYYY-MM-DD) or None (uses current date)
            event_date: ISO format date string (YYYY-MM-DD)
        
        Returns:
            Number of days before event (positive) or after event (negative),
            or None if date parsing fails
        """
        try:
            # Parse event date
            event_dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            
            # Parse or use current date for cancellation
            if cancellation_date:
                cancel_dt = datetime.fromisoformat(cancellation_date.replace('Z', '+00:00'))
                if cancel_dt.tzinfo is None:
                    cancel_dt = cancel_dt.replace(tzinfo=timezone.utc)
            else:
                cancel_dt = datetime.now(timezone.utc)
            
            # Calculate difference in days
            delta = event_dt - cancel_dt
            return delta.days
        
        except (ValueError, AttributeError) as e:
            # Invalid date format
            return None
    
    def _check_for_oversold(self, ticket_description: str) -> bool:
        """
        Check if ticket mentions oversold/full location.
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if oversold indicators found, False otherwise
        """
        oversold_keywords = [
            "oversold", "full", "no space", "no spots", "at capacity",
            "turned away", "garage full", "lot full", "sold out"
        ]
        return any(keyword in ticket_description for keyword in oversold_keywords)
    
    def _check_for_duplicate_claim(self, ticket_data: Dict) -> bool:
        """
        Check if customer is claiming a duplicate booking.
        
        NOTE: This method only DETECTS duplicate claims for escalation purposes.
        Actual duplicate detection and resolution is NON-FUNCTIONAL due to 
        ParkWhiz API limitations (cannot search bookings by customer email).
        
        All duplicate claims must be escalated to human review.
        
        Args:
            ticket_data: Ticket data dictionary
        
        Returns:
            True if duplicate claim detected (triggers escalation), False otherwise
        """
        ticket_description = ticket_data.get("description", "").lower()
        ticket_subject = ticket_data.get("subject", "").lower()
        
        duplicate_keywords = [
            "duplicate", "charged twice", "double charge", "two passes",
            "bought twice", "multiple passes", "same time", "two bookings",
            "charged 2 times", "billed twice", "double booking"
        ]
        
        # Check both subject and description
        full_text = f"{ticket_subject} {ticket_description}"
        return any(keyword in full_text for keyword in duplicate_keywords)
    
    def _check_for_paid_again(self, ticket_description: str) -> bool:
        """
        Check if customer had to pay again on-site.
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if paid-again indicators found, False otherwise
        """
        paid_again_keywords = [
            "paid again", "charged at gate", "paid onsite", "paid on-site",
            "paid twice", "charged extra", "had to pay"
        ]
        return any(keyword in ticket_description for keyword in paid_again_keywords)
    
    def _check_for_closed(self, ticket_description: str) -> bool:
        """
        Check if location was closed or inaccessible.
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if closed/inaccessible indicators found, False otherwise
        """
        closed_keywords = [
            "closed", "gate down", "flooded", "power out", "no power",
            "elevator broken", "lift broken", "no lights", "lights off",
            "no attendant", "nobody there", "shut down", "not open"
        ]
        return any(keyword in ticket_description for keyword in closed_keywords)
    
    def _check_for_accessibility(self, ticket_description: str) -> bool:
        """
        Check if customer couldn't access location due to external factors.
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if accessibility issue indicators found, False otherwise
        """
        accessibility_keywords = [
            "road closed", "street closed", "blocked", "police block",
            "construction", "parade", "barricade", "can't access",
            "couldn't access", "unable to access", "no access", "blocked off",
            "road closure", "detour", "emergency"
        ]
        return any(keyword in ticket_description for keyword in accessibility_keywords)
