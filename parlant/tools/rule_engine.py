"""
RuleEngine component for applying deterministic business rules to refund decisions.

This module provides a RuleEngine class that applies clear-cut business rules
to make refund decisions with high confidence, reducing the need for LLM analysis
in straightforward cases.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from .vehicle_classifier import VehicleClassifier

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
        self.vehicle_classifier = VehicleClassifier()
    
    async def apply_rules(
        self,
        booking_info: Dict,
        ticket_data: Dict,
        ticket_notes: str = ""
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
        event_date_raw = booking_info.get("event_date")
        cancellation_date_raw = booking_info.get("cancellation_date")
        
        logger.info(f"Date calculation inputs: event_date='{event_date_raw}', cancellation_date='{cancellation_date_raw}'")
        
        days_before_event = self._calculate_days_before_event(
            cancellation_date_raw,
            event_date_raw
        )
        
        if days_before_event is None:
            logger.error(f"Failed to calculate days before event - invalid date format. event_date='{event_date_raw}', cancellation_date='{cancellation_date_raw}'")
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
        
        # PRIORITY RULE 1: Check for missing attendant / operational failure
        # These are service delivery failures that require LLM analysis to determine
        # if the customer made a good faith effort vs. just changed their mind
        if self._check_for_operational_failure(ticket_description, ticket_notes):
            logger.info("Operational failure detected (missing attendant/amenity), escalating to LLM for nuanced analysis")
            return {
                "decision": "Uncertain",
                "reasoning": (
                    "Customer reports operational failure (missing attendant, closed facility, etc.). "
                    "This requires LLM analysis to determine if customer made good faith effort to use service "
                    "or if this is a legitimate service delivery failure warranting refund."
                ),
                "policy_rule": "Operational Failure - Requires LLM Analysis",
                "confidence": "low",
                "method_used": "rules"  # Will trigger LLM in decision_maker
            }
        
        # PRIORITY RULE 2: Check for vehicle restriction issues using LLM classification
        # Only triggers if customer EXPLICITLY mentions being turned away due to vehicle type
        # This prevents unnecessary LLM calls for unrelated issues
        if self._check_for_vehicle_restriction_issue(ticket_description):
            logger.info("Customer explicitly mentions vehicle-based rejection, using LLM classifier")
            
            # Extract vehicle and location restrictions from ticket notes
            logger.debug(f"Ticket notes length: {len(ticket_notes) if ticket_notes else 0} chars")
            vehicle = self.vehicle_classifier.extract_vehicle_from_ticket(ticket_notes)
            location_restrictions = self.vehicle_classifier.extract_location_restrictions(ticket_notes)
            
            logger.info(f"Extraction results: vehicle='{vehicle}', restrictions_found={location_restrictions is not None}")
            
            if vehicle and location_restrictions:
                logger.info(f"Classifying vehicle: {vehicle} against restrictions: {location_restrictions[:100]}...")
                
                # Use LLM to classify and compare
                classification = await self.vehicle_classifier.check_vehicle_restriction_mismatch(
                    vehicle_make_model=vehicle,
                    location_restrictions=location_restrictions,
                    ticket_description=ticket_description
                )
                
                # If there's a mismatch (vehicle was incorrectly rejected), approve
                if classification.get("is_mismatch") and classification.get("confidence") in ["high", "medium"]:
                    logger.info(f"Vehicle restriction mismatch confirmed: {classification.get('reasoning')}")
                    
                    # Format restricted categories for display
                    restricted_display = ', '.join(classification.get('restricted_categories', []))
                    
                    return {
                        "decision": "Approved",
                        "reasoning": (
                            f"Customer was turned away due to vehicle restrictions that do not apply to their vehicle.<br><br>"
                            f"<strong>Vehicle:</strong> {vehicle}<br>"
                            f"<strong>Classified as:</strong> {classification.get('vehicle_category').replace('_', ' ').title()}<br>"
                            f"<strong>Location restricts:</strong> {restricted_display}<br><br>"
                            f"<strong>Analysis:</strong> {classification.get('reasoning')}<br><br>"
                            f"<strong>Action required:</strong> Contact location to clarify vehicle restriction policy."
                        ),
                        "policy_rule": "Vehicle Restriction Mismatch",
                        "confidence": classification.get("confidence", "medium"),
                        "method_used": "llm"  # Mark that LLM was used for classification
                    }
                else:
                    logger.info(f"No vehicle restriction mismatch found: {classification.get('reasoning')}")
            else:
                logger.warning(f"Could not extract vehicle ({vehicle}) or restrictions ({location_restrictions is not None})")
                
                # Fallback to simple keyword matching
                logger.info("Falling back to keyword-based vehicle restriction check")
                return {
                    "decision": "Approved",
                    "reasoning": (
                        "Customer reports being turned away due to vehicle restrictions. "
                        "Unable to verify against location's restriction list, but customer's description "
                        "suggests the restriction was not clearly disclosed in the booking.<br><br>"
                        "<strong>Action required:</strong> Manually verify vehicle type against location restrictions."
                    ),
                    "policy_rule": "Undisclosed Vehicle Restriction (Unverified)",
                    "confidence": "medium"
                }
        
        # PRIORITY RULE 2: Check for extra charge claims (need proof verification)
        # Customer claims they had to pay additional money - needs human review to:
        # - Verify proof of payment
        # - Check if entry/exit were within booking window (legitimate) or outside (deny)
        if self._check_for_extra_charge_claim(ticket_description):
            logger.info("Rule matched: Extra Charge Claim. Decision: Needs Human Review (proof verification required)")
            return {
                "decision": "Needs Human Review",
                "reasoning": (
                    "Customer reports having to pay additional charges. Human review required to:<br>"
                    "<ol>"
                    "<li>Verify customer's arrival/entry time against booking start time</li>"
                    "<li>Verify customer's exit time against booking end time</li>"
                    "<li>Request proof of payment if needed</li>"
                    "</ol><br>"
                    "<strong>Decision guidance:</strong>"
                    "<ul>"
                    "<li>If entry and exit were both within booking window → May be legitimate extra charge (approve)</li>"
                    "<li>If entry was before booking start or exit exceeded booking end → Early arrival or overstay (customer responsibility - deny)</li>"
                    "</ul>"
                ),
                "policy_rule": "Extra Charge Claim - Requires Proof Verification",
                "confidence": "high"
            }
        
        # PRIORITY RULE 3: Check for retroactive booking (booked after start time)
        # This is suspicious and needs human review to clarify customer intent
        if self._check_for_retroactive_booking(ticket_description):
            logger.info("Rule matched: Retroactive Booking. Decision: Needs Human Review (timing clarification needed)")
            return {
                "decision": "Needs Human Review",
                "reasoning": (
                    "Customer reports booking wrong time or date. Human review required to:<br>"
                    "<ol>"
                    "<li>Verify if booking was created after the booking start time (retroactive - suspicious)</li>"
                    "<li>Clarify if customer intended to book for a different date/time</li>"
                    "<li>Check if customer's actual arrival/exit times align with their claimed intent</li>"
                    "</ol><br>"
                    "<strong>Decision guidance:</strong>"
                    "<ul>"
                    "<li>May warrant refund if customer can demonstrate they intended different booking time</li>"
                    "<li>May be non-refundable if this was customer error after using the pass</li>"
                    "</ul>"
                ),
                "policy_rule": "Retroactive/Wrong Time Booking - Requires Clarification",
                "confidence": "high"
            }
        
        # PRIORITY RULE 4: Check for duplicate claims (must escalate regardless of timing)
        # This overrides all other rules because we cannot auto-detect duplicates
        if self._check_for_duplicate_claim(ticket_data):
            logger.info("Rule matched: Duplicate Claim. Decision: Needs Human Review (API limitation)")
            return {
                "decision": "Needs Human Review",
                "reasoning": (
                    "Customer reports duplicate booking or being charged twice.<br><br>"
                    "Duplicate detection requires manual review because the ParkWhiz API "
                    "does not support searching bookings by customer email.<br><br>"
                    "<strong>Action required:</strong> A specialist will review the customer's account to locate both bookings."
                ),
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
        
        Uses date-only comparison (ignoring time) to avoid timezone issues
        with same-day bookings.
        
        Args:
            cancellation_date: ISO format date string (YYYY-MM-DD) or None (uses current date)
            event_date: ISO format date string (YYYY-MM-DD)
        
        Returns:
            Number of days before event (positive) or after event (negative),
            or None if date parsing fails
        """
        try:
            # Parse event date (extract date only, ignore time)
            event_dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            event_date_only = event_dt.date()
            
            # Parse or use current date for cancellation (date only)
            if cancellation_date:
                cancel_dt = datetime.fromisoformat(cancellation_date.replace('Z', '+00:00'))
                if cancel_dt.tzinfo is None:
                    cancel_dt = cancel_dt.replace(tzinfo=timezone.utc)
                cancel_date_only = cancel_dt.date()
            else:
                cancel_date_only = datetime.now(timezone.utc).date()
            
            # Log parsed dates for debugging
            logger.debug(f"Parsed dates: event={event_date_only}, cancellation={cancel_date_only}")
            
            # Calculate difference in days (using date objects, not datetime)
            delta = (event_date_only - cancel_date_only).days
            return delta
        
        except (ValueError, AttributeError) as e:
            # Invalid date format
            logger.error(f"Date parsing error: {type(e).__name__}: {e}")
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
    
    def _check_for_retroactive_booking(self, ticket_description: str) -> bool:
        """
        Check if booking was created AFTER the booking start time (retroactive).
        
        This is suspicious because you cannot book for a time that has already passed.
        Common scenarios:
        - Customer books at 8:21 PM for a pass starting at 8:00 PM (21 min retroactive)
        - May indicate customer confusion about booking times
        - Needs human review to clarify customer intent
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if retroactive booking indicators found
        """
        # Look for patterns in Zapier notes that show booking created after start time
        # The Zapier note includes both "Booking Created" and "Parking Pass Start Time"
        # This is a simple heuristic - if customer mentions booking "wrong time" or "mistake"
        # combined with timing issues, flag for review
        
        retroactive_indicators = [
            "wrong time", "booked wrong", "wrong date", "mistake",
            "meant to book", "supposed to book", "intended to book",
            "booked for wrong", "incorrect time", "incorrect date"
        ]
        
        return any(indicator in ticket_description for indicator in retroactive_indicators)
    
    def _check_for_operational_failure(self, ticket_description: str, ticket_notes: str = "") -> bool:
        """
        Check if customer reports an operational/service delivery failure.
        
        This is a GATEKEEPER function for LLM analysis of edge cases where:
        - The location failed to provide the service (missing attendant, closed, etc.)
        - The customer made a good faith effort to use the service
        - It's unclear if this warrants a refund without understanding context
        
        Common scenarios:
        - "no attendant after 10 mins wait"
        - "facility was closed"
        - "gate wouldn't open"
        - "no one to help me"
        - "missing amenity" (EV charger, handicap access, etc.)
        
        Args:
            ticket_description: Ticket description text (lowercase)
            ticket_notes: Full ticket notes including Zapier data (lowercase)
        
        Returns:
            True if customer reports operational failure requiring LLM analysis
        """
        # Combine description and notes for checking
        full_text = f"{ticket_description} {ticket_notes}".lower()
        
        # Keywords indicating operational/service failures
        operational_failure_keywords = [
            "no attendant", "missing attendant", "attendant not there", "no one there",
            "facility closed", "location closed", "gate closed", "lot closed",
            "gate wouldn't open", "gate didn't open", "couldn't get in",
            "no one to help", "nobody there", "no staff",
            "missing amenity", "no ev charger", "no handicap", "no elevator",
            "waited", "wait", "after.*min"  # "waited 10 mins", "after 10 mins wait"
        ]
        
        # Check if any operational failure keywords are present
        has_operational_issue = any(
            re.search(keyword, full_text) 
            for keyword in operational_failure_keywords
        )
        
        # Also check the Zapier "Reason" field specifically
        reason_match = re.search(r'Reason:\s*([^\n]+)', ticket_notes, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).lower()
            # Check if reason mentions missing attendant/amenity
            if any(keyword in reason for keyword in [
                'missing attendant', 'missing amenity', 'handicap', 'ev charger',
                'closed', 'no attendant', 'no one'
            ]):
                logger.info(f"Operational failure detected in Reason field: {reason}")
                return True
        
        if has_operational_issue:
            logger.info(f"Operational failure keywords detected in ticket text")
        
        return has_operational_issue
    
    def _check_for_vehicle_restriction_issue(self, ticket_description: str) -> bool:
        """
        Check if customer explicitly claims they were turned away due to vehicle restrictions.
        
        This is a GATEKEEPER function - only returns True if customer clearly states
        they were rejected because of their vehicle type. This prevents unnecessary
        LLM calls for unrelated issues.
        
        Common scenarios that should trigger this:
        - "didn't allow crossover vehicles"
        - "turned away because of my SUV"
        - "said they don't accept trucks"
        - "attendant told me my vehicle type wasn't allowed"
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True ONLY if customer explicitly mentions vehicle-based rejection
        """
        # MUST have at least one "rejection" keyword
        rejection_keywords = [
            "didn't allow", "don't allow", "not allow", "wouldn't allow",
            "didn't accept", "don't accept", "not accept", "wouldn't accept",
            "turned away", "turned me away", "rejected", "denied entry",
            "wouldn't let", "didn't let", "refused"
        ]
        
        has_rejection = any(re.search(keyword, ticket_description) for keyword in rejection_keywords)
        
        if not has_rejection:
            return False
        
        # MUST also mention vehicle-related terms
        vehicle_keywords = [
            "vehicle", "car", "suv", "crossover", "truck", "van",
            "tesla", "sedan", "make and model", "vehicle type"
        ]
        
        has_vehicle_mention = any(re.search(keyword, ticket_description) for keyword in vehicle_keywords)
        
        # Only return True if BOTH rejection AND vehicle are mentioned
        # This ensures we only call the LLM classifier when it's actually a vehicle issue
        return has_rejection and has_vehicle_mention
    
    def _check_for_extra_charge_claim(self, ticket_description: str) -> bool:
        """
        Check if customer claims they had to pay additional charges.
        
        These claims require human review to:
        1. Verify proof of payment
        2. Check if entry time was within booking window
        3. Check if exit time was within booking window
        4. Determine if charge was legitimate or overstay
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if customer claims extra charges (needs human verification)
        """
        extra_charge_keywords = [
            "had to pay", "charged additional", "charged extra", "pay more",
            "additional.*due", "told.*due", "pay.*leave", "pay.*exit",
            "pay.*retrieve", "before they would release"
        ]
        
        return any(keyword in ticket_description for keyword in extra_charge_keywords)
    
    def _check_for_paid_again(self, ticket_description: str) -> bool:
        """
        Check if customer had to pay again on-site for a DUPLICATE booking.
        
        This distinguishes between:
        - Paid again for duplicate booking (approve) 
        - Paid additional overstay/exit charges (deny - not a refund case)
        
        Args:
            ticket_description: Ticket description text (lowercase)
        
        Returns:
            True if paid-again indicators found AND not an overstay scenario, False otherwise
        """
        # Exclusion keywords that indicate overstay/exit charges (NOT duplicate bookings)
        overstay_keywords = [
            "additional", "overstay", "over stay", "exceeded", "extra time",
            "stayed longer", "exit", "release", "retrieve", "pick up",
            "attendant", "gate", "before they would release", "additional.*due",
            "told.*due", "had to pay.*leave", "pay.*exit", "pay.*retrieve",
            "more time", "longer", "late", "overtime"
        ]
        
        # Check if this is an overstay scenario first
        if any(keyword in ticket_description for keyword in overstay_keywords):
            # If overstay keywords present, NOT a duplicate booking scenario
            return False
        
        # Keywords that indicate duplicate booking payment (not overstay)
        paid_again_keywords = [
            "paid again", "charged at gate", "paid onsite", "paid on-site",
            "paid twice", "charged extra", "had to pay", "wouldn't let me park",
            "said i didn't have", "no reservation", "not in system"
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
