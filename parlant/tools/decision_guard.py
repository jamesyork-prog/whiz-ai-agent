"""
Decision Guard Module

Ensures refund decisions only use verified booking data from ParkWhiz API.
Provides safety checks to prevent automated decisions based on unverified customer claims.
"""

import logging
from typing import Optional, Tuple, Any
from dataclasses import dataclass

from app_tools.tools.customer_info_extractor import CustomerInfo


# Stub classes for backward compatibility
# These are no longer used since booking verification happens upstream in Zapier
@dataclass
class VerifiedBooking:
    """Stub for backward compatibility - no longer used."""
    booking_id: str
    customer_email: str
    arrival_date: str
    exit_date: str
    location: str
    pass_used: bool
    pass_usage_status: str
    amount_paid: float
    match_confidence: str


@dataclass
class BookingVerificationResult:
    """Stub for backward compatibility - no longer used."""
    success: bool
    verified_booking: Optional[VerifiedBooking]
    customer_info: CustomerInfo
    failure_reason: Optional[str] = None


# Configure logging
logger = logging.getLogger(__name__)


class DecisionGuard:
    """Ensures decisions only use verified booking data."""
    
    def can_make_automated_decision(
        self,
        verified_booking: Optional[VerifiedBooking]
    ) -> bool:
        """
        Check if automated decision is safe to make.
        
        An automated decision is only safe when:
        - Booking verification succeeded (verified_booking is not None)
        - Pass usage status is known (not "unknown")
        - Match confidence is not weak
        
        Args:
            verified_booking: Verified booking or None
            
        Returns:
            True if automated decision is allowed, False otherwise
        """
        if verified_booking is None:
            logger.info("Cannot make automated decision: no verified booking")
            return False
        
        # Check pass usage status
        if verified_booking.pass_usage_status == "unknown":
            logger.info(
                "Cannot make automated decision: pass usage status unknown",
                extra={"booking_id": verified_booking.booking_id}
            )
            return False
        
        # Check match confidence
        if verified_booking.match_confidence == "weak":
            logger.info(
                "Cannot make automated decision: weak match confidence",
                extra={
                    "booking_id": verified_booking.booking_id,
                    "confidence": verified_booking.match_confidence
                }
            )
            return False
        
        logger.info(
            "Automated decision allowed",
            extra={
                "booking_id": verified_booking.booking_id,
                "pass_usage": verified_booking.pass_usage_status,
                "confidence": verified_booking.match_confidence
            }
        )
        return True
    
    def should_escalate(
        self,
        verified_booking: Optional[VerifiedBooking],
        customer_info: CustomerInfo,
        failure_reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determine if ticket should be escalated to human review.
        
        Escalation occurs when:
        - Booking verification failed (verified_booking is None)
        - Pass usage status is unknown or unclear
        - Verified data contradicts customer claim
        - Match confidence is weak
        
        Args:
            verified_booking: Verified booking or None
            customer_info: Customer-provided information
            failure_reason: Reason verification failed (if applicable)
            
        Returns:
            (should_escalate, reason) tuple
        """
        # Case 1: Verification failed completely
        if verified_booking is None:
            reason = failure_reason or "Booking verification failed"
            logger.info(
                f"Escalating: {reason}",
                extra={"customer_email": customer_info.email}
            )
            return (True, reason)
        
        # Case 2: Pass usage status is unknown
        if verified_booking.pass_usage_status == "unknown":
            reason = "Pass usage status unavailable - cannot determine if pass was used"
            logger.info(
                f"Escalating: {reason}",
                extra={
                    "booking_id": verified_booking.booking_id,
                    "customer_email": customer_info.email
                }
            )
            return (True, reason)
        
        # Case 3: Weak match confidence (dates don't match well)
        if verified_booking.match_confidence == "weak":
            reason = "Booking dates don't match customer claim closely - needs human review"
            logger.info(
                f"Escalating: {reason}",
                extra={
                    "booking_id": verified_booking.booking_id,
                    "confidence": verified_booking.match_confidence,
                    "customer_email": customer_info.email
                }
            )
            return (True, reason)
        
        # No escalation needed
        logger.info(
            "No escalation needed - verification successful",
            extra={
                "booking_id": verified_booking.booking_id,
                "pass_usage": verified_booking.pass_usage_status,
                "confidence": verified_booking.match_confidence
            }
        )
        return (False, "")
    
    def _detect_usage_contradiction(
        self,
        verified_booking: VerifiedBooking,
        customer_info: CustomerInfo
    ) -> Tuple[bool, str]:
        """
        Detect if verified pass usage contradicts customer claim.
        
        Note: Currently returns (False, "") as we don't extract customer usage claims
        from ticket text yet. This is infrastructure for future enhancement.
        
        Args:
            verified_booking: Verified booking with pass usage status
            customer_info: Customer information (may contain usage claim in future)
            
        Returns:
            (contradiction_detected, reason) tuple
        """
        # TODO: Extract customer usage claim from ticket text
        # For now, return no contradiction as we don't have claim extraction
        return (False, "")
    
    def detect_usage_contradiction(
        self,
        verified_booking: VerifiedBooking,
        customer_claim: str
    ) -> bool:
        """
        Detect if verified pass usage contradicts customer claim.
        
        Args:
            verified_booking: Verified booking with pass usage status
            customer_claim: Customer's claim about pass usage (e.g., "didn't use", "used")
            
        Returns:
            True if contradiction detected, False otherwise
        """
        if not customer_claim:
            return False
        
        claim_lower = customer_claim.lower()
        
        # Customer claims they didn't use the pass
        if any(phrase in claim_lower for phrase in [
            "didn't use", "did not use", "never used", "not used",
            "couldn't use", "could not use", "unable to use"
        ]):
            if verified_booking.pass_used:
                logger.warning(
                    "Usage contradiction detected: customer claims not used, but pass was scanned",
                    extra={
                        "booking_id": verified_booking.booking_id,
                        "verified_status": verified_booking.pass_usage_status,
                        "customer_claim": customer_claim
                    }
                )
                return True
        
        # Customer claims they did use the pass
        if any(phrase in claim_lower for phrase in [
            "used the pass", "scanned", "checked in", "did use"
        ]):
            if not verified_booking.pass_used:
                logger.warning(
                    "Usage contradiction detected: customer claims used, but pass was not scanned",
                    extra={
                        "booking_id": verified_booking.booking_id,
                        "verified_status": verified_booking.pass_usage_status,
                        "customer_claim": customer_claim
                    }
                )
                return True
        
        return False
    
    def validate_decision_data(
        self,
        verified_booking: Optional[VerifiedBooking],
        customer_info: CustomerInfo
    ) -> Tuple[bool, str]:
        """
        Validate that decision data is safe to use for automated decisions.
        
        This checks that:
        - Booking has been verified (not None)
        - Pass usage status is known
        - Match confidence is acceptable
        
        Args:
            verified_booking: Verified booking or None
            customer_info: Customer-provided information
            
        Returns:
            (is_valid, reason) tuple where:
            - is_valid: True if data is valid for automated decisions
            - reason: Explanation if not valid
        """
        # Must have verified booking
        if verified_booking is None:
            return (False, "No verified booking - cannot use customer data without verification")
        
        # Pass usage must be known
        if verified_booking.pass_usage_status == "unknown":
            return (False, "Pass usage status unknown - cannot make automated decision")
        
        # Match confidence must not be weak
        if verified_booking.match_confidence == "weak":
            return (False, "Booking match confidence too low - dates don't match well")
        
        # All checks passed
        logger.info(
            "Decision data validated successfully",
            extra={
                "booking_id": verified_booking.booking_id,
                "pass_usage": verified_booking.pass_usage_status,
                "confidence": verified_booking.match_confidence
            }
        )
        return (True, "Decision data is valid")
    
    def validate_verification_result(
        self,
        result: BookingVerificationResult
    ) -> Tuple[bool, str]:
        """
        Validate a complete booking verification result.
        
        This is a convenience method that combines all safety checks.
        
        Args:
            result: Complete booking verification result
            
        Returns:
            (can_proceed, reason) tuple where:
            - can_proceed: True if automated decision is safe
            - reason: Explanation if cannot proceed
        """
        # Check if verification succeeded
        if not result.success:
            return (False, result.failure_reason or "Verification failed")
        
        # Check if we can make automated decision
        if not self.can_make_automated_decision(result.verified_booking):
            # Determine specific reason
            if result.verified_booking is None:
                return (False, "No verified booking found")
            elif result.verified_booking.pass_usage_status == "unknown":
                return (False, "Pass usage status unknown")
            elif result.verified_booking.match_confidence == "weak":
                return (False, "Booking match confidence too low")
            else:
                return (False, "Cannot make automated decision")
        
        # Check if escalation is needed
        should_escalate, escalation_reason = self.should_escalate(
            result.verified_booking,
            result.customer_info,
            result.failure_reason
        )
        
        if should_escalate:
            return (False, escalation_reason)
        
        # All checks passed
        return (True, "Verification successful - automated decision allowed")
