"""
Booking Verification Module

Verifies bookings using ParkWhiz API when Zapier fails to find booking information.
Searches for bookings using customer details, selects best match, and verifies pass usage.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from app_tools.tools.parkwhiz_client import (
    ParkWhizOAuth2Client,
    ParkWhizTimeoutError,
    ParkWhizAuthenticationError,
    ParkWhizError,
)
from app_tools.tools.customer_info_extractor import CustomerInfo


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class VerifiedBooking:
    """Verified booking information from ParkWhiz API."""
    booking_id: str
    customer_email: str
    arrival_date: str
    exit_date: str
    location: str
    pass_used: bool
    pass_usage_status: str  # "used", "not_used", "unknown"
    amount_paid: float
    match_confidence: str  # "exact", "partial", "weak"


@dataclass
class BookingVerificationResult:
    """Complete result of booking verification process."""
    success: bool
    verified_booking: Optional[VerifiedBooking]
    customer_info: CustomerInfo
    failure_reason: Optional[str]
    discrepancies: List[str]
    should_escalate: bool
    escalation_reason: Optional[str]
    api_calls_made: int
    processing_time_ms: int


class ParkWhizBookingVerifier:
    """Verifies bookings using ParkWhiz API."""
    
    def __init__(self, client: Optional[ParkWhizOAuth2Client] = None):
        """
        Initialize booking verifier.
        
        Args:
            client: ParkWhiz OAuth2 client (creates new one if not provided)
        """
        try:
            self.client = client or ParkWhizOAuth2Client()
            self.client_available = True
            logger.info("ParkWhiz booking verifier initialized with OAuth2 authentication")
        except ParkWhizAuthenticationError as e:
            logger.warning(
                f"ParkWhiz credentials not configured: {e}. "
                "Booking verification will be disabled."
            )
            self.client = None
            self.client_available = False
    
    async def search_bookings(
        self,
        customer_info: CustomerInfo
    ) -> List[Dict[str, Any]]:
        """
        Search for bookings using customer details.
        
        Args:
            customer_info: Customer information to search with
            
        Returns:
            List of matching bookings from ParkWhiz API
            
        Raises:
            ParkWhizAuthenticationError: If credentials invalid
            ParkWhizTimeoutError: If request times out (after retry)
        """
        logger.info(
            f"Searching bookings for customer: {customer_info.email}",
            extra={
                "customer_email": customer_info.email,
                "arrival_date": customer_info.arrival_date,
                "exit_date": customer_info.exit_date,
            }
        )
        
        try:
            # Call ParkWhiz API with retry logic built into the client
            bookings = await self.client.get_customer_bookings(
                customer_email=customer_info.email,
                start_date=customer_info.arrival_date,
                end_date=customer_info.exit_date,
            )
            
            logger.info(
                f"Found {len(bookings)} bookings for {customer_info.email}",
                extra={
                    "booking_count": len(bookings),
                    "customer_email": customer_info.email,
                }
            )
            
            return bookings
            
        except ParkWhizTimeoutError:
            # Timeout already includes retry logic in the client
            logger.error(
                f"ParkWhiz API timeout searching for {customer_info.email}",
                extra={"customer_email": customer_info.email}
            )
            raise
        
        except ParkWhizAuthenticationError:
            logger.critical(
                "ParkWhiz authentication failed during booking search",
                extra={"customer_email": customer_info.email}
            )
            raise
        
        except Exception as e:
            logger.error(
                f"Error searching bookings: {e}",
                extra={"customer_email": customer_info.email, "error": str(e)},
                exc_info=True
            )
            raise ParkWhizError(f"Booking search failed: {e}")
    
    def select_best_match(
        self,
        bookings: List[Dict[str, Any]],
        customer_info: CustomerInfo
    ) -> Optional[VerifiedBooking]:
        """
        Select booking that best matches customer-provided dates.
        
        Matching logic:
        - Exact match: arrival and exit dates match exactly
        - Partial match: dates overlap or are within a few days
        - Weak match: same month/year but different days
        
        Args:
            bookings: List of bookings from API
            customer_info: Customer-provided information
            
        Returns:
            Best matching booking or None if no good match
        """
        if not bookings:
            logger.info("No bookings to match")
            return None
        
        logger.info(
            f"Selecting best match from {len(bookings)} bookings",
            extra={
                "booking_count": len(bookings),
                "target_arrival": customer_info.arrival_date,
                "target_exit": customer_info.exit_date,
            }
        )
        
        # Parse target dates
        try:
            target_arrival = datetime.fromisoformat(customer_info.arrival_date)
            target_exit = datetime.fromisoformat(customer_info.exit_date)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid date format in customer info: {e}")
            return None
        
        best_booking = None
        best_score = float('inf')
        best_confidence = "weak"
        
        for booking in bookings:
            # Extract booking dates
            try:
                booking_start = booking.get("start_time") or booking.get("arrival_date")
                booking_end = booking.get("end_time") or booking.get("exit_date")
                
                if not booking_start or not booking_end:
                    logger.debug(f"Booking {booking.get('id')} missing dates, skipping")
                    continue
                
                # Parse booking dates (handle both datetime and date strings)
                if 'T' in str(booking_start):
                    booking_arrival = datetime.fromisoformat(booking_start.replace('Z', '+00:00'))
                else:
                    booking_arrival = datetime.fromisoformat(booking_start)
                
                if 'T' in str(booking_end):
                    booking_exit = datetime.fromisoformat(booking_end.replace('Z', '+00:00'))
                else:
                    booking_exit = datetime.fromisoformat(booking_end)
                
                # Calculate date difference (in days)
                arrival_diff = abs((booking_arrival.date() - target_arrival.date()).days)
                exit_diff = abs((booking_exit.date() - target_exit.date()).days)
                total_diff = arrival_diff + exit_diff
                
                # Determine confidence level (strict matching)
                if arrival_diff == 0 and exit_diff == 0:
                    confidence = "exact"
                elif total_diff <= 1:  # Within 1 day total (same day or next day)
                    confidence = "partial"
                elif total_diff <= 3:  # Within 3 days total
                    confidence = "weak"
                else:
                    # More than 3 days off - skip this booking entirely
                    logger.debug(
                        f"Booking {booking.get('id')}: {total_diff} days difference - skipping"
                    )
                    continue
                
                logger.debug(
                    f"Booking {booking.get('id')}: arrival_diff={arrival_diff}, "
                    f"exit_diff={exit_diff}, confidence={confidence}"
                )
                
                # Update best match if this is better
                if total_diff < best_score:
                    best_score = total_diff
                    best_booking = booking
                    best_confidence = confidence
                    
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(
                    f"Error processing booking {booking.get('id')}: {e}",
                    extra={"booking_id": booking.get('id'), "error": str(e)}
                )
                continue
        
        if not best_booking:
            logger.info("No valid bookings found after matching")
            return None
        
        # Reject matches that are too far off (more than 7 days total difference)
        MAX_DATE_DIFF_DAYS = 7
        if best_score > MAX_DATE_DIFF_DAYS:
            logger.warning(
                f"Best match (booking {best_booking.get('id')}) has {best_score} days difference - "
                f"exceeds threshold of {MAX_DATE_DIFF_DAYS} days. Rejecting as no match.",
                extra={
                    "booking_id": best_booking.get('id'),
                    "date_diff_days": best_score,
                    "threshold_days": MAX_DATE_DIFF_DAYS,
                }
            )
            return None
        
        # Extract pass usage information
        pass_usage_status = self._extract_pass_usage(best_booking)
        pass_used = pass_usage_status == "used"
        
        # Create VerifiedBooking object
        # Extract price_paid - it's a dict like {"USD": 15.00}
        price_paid = best_booking.get("price_paid", {})
        if isinstance(price_paid, dict):
            # Get the first currency value (usually USD)
            amount_paid = float(list(price_paid.values())[0]) if price_paid else 0.0
        else:
            amount_paid = float(price_paid)
        
        # Extract location name from embedded data
        location_name = customer_info.location or ""
        if "_embedded" in best_booking and "pw:location" in best_booking["_embedded"]:
            location_name = best_booking["_embedded"]["pw:location"].get("name", location_name)
        
        verified = VerifiedBooking(
            booking_id=str(best_booking.get("id", "")),
            customer_email=best_booking.get("customer_email", customer_info.email),
            arrival_date=str(best_booking.get("start_time", customer_info.arrival_date)),
            exit_date=str(best_booking.get("end_time", customer_info.exit_date)),
            location=location_name,
            pass_used=pass_used,
            pass_usage_status=pass_usage_status,
            amount_paid=amount_paid,
            match_confidence=best_confidence,
        )
        
        logger.info(
            f"Selected booking {verified.booking_id} with {best_confidence} confidence",
            extra={
                "booking_id": verified.booking_id,
                "confidence": best_confidence,
                "date_diff_days": best_score,
                "pass_usage": pass_usage_status,
            }
        )
        
        return verified
    
    def _extract_pass_usage(self, booking: Dict[str, Any]) -> str:
        """
        Extract pass usage status from booking data.
        
        Args:
            booking: Booking dictionary from API
            
        Returns:
            "used", "not_used", or "unknown"
        """
        # Check various possible fields for pass usage
        usage_fields = [
            "pass_used",
            "pass_usage",
            "usage_status",
            "scanned",
            "checked_in",
        ]
        
        for field in usage_fields:
            value = booking.get(field)
            if value is not None:
                # Handle boolean values
                if isinstance(value, bool):
                    return "used" if value else "not_used"
                # Handle string values
                if isinstance(value, str):
                    value_lower = value.lower()
                    if value_lower in ("used", "scanned", "checked_in", "true", "yes"):
                        return "used"
                    elif value_lower in ("not_used", "not_scanned", "false", "no"):
                        return "not_used"
        
        # If no usage information found
        logger.warning(
            f"Pass usage status not found in booking {booking.get('id')}",
            extra={"booking_id": booking.get('id')}
        )
        return "unknown"
    
    async def verify_booking(
        self,
        customer_info: CustomerInfo
    ) -> BookingVerificationResult:
        """
        Complete verification workflow: search + select + verify usage.
        
        This is the main entry point for booking verification.
        Handles all errors gracefully and returns a result object.
        
        Args:
            customer_info: Customer information
            
        Returns:
            BookingVerificationResult with verification outcome
        """
        start_time = time.time()
        api_calls = 0
        
        logger.info(
            f"Starting booking verification for {customer_info.email}",
            extra={"customer_email": customer_info.email}
        )
        
        # Check if client is available
        if not self.client_available:
            logger.warning(
                "Booking verification skipped - ParkWhiz credentials not configured"
            )
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return BookingVerificationResult(
                success=False,
                verified_booking=None,
                customer_info=customer_info,
                failure_reason="ParkWhiz API credentials not configured.",
                discrepancies=[],
                should_escalate=True,
                escalation_reason="Booking verification unavailable - API credentials required",
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
        
        # Validate customer info is complete
        if not customer_info.is_complete():
            logger.warning(
                "Customer info incomplete - missing required fields",
                extra={
                    "has_email": bool(customer_info.email),
                    "has_arrival": bool(customer_info.arrival_date),
                    "has_exit": bool(customer_info.exit_date),
                }
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return BookingVerificationResult(
                success=False,
                verified_booking=None,
                customer_info=customer_info,
                failure_reason="Missing required customer information (email, arrival date, or exit date)",
                discrepancies=[],
                should_escalate=True,
                escalation_reason="Cannot verify booking without complete customer information",
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
        
        try:
            # Search for bookings
            bookings = await self.search_bookings(customer_info)
            api_calls += 1
            
            # No bookings found
            if not bookings:
                logger.info(
                    f"No bookings found for {customer_info.email}",
                    extra={"customer_email": customer_info.email}
                )
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return BookingVerificationResult(
                    success=False,
                    verified_booking=None,
                    customer_info=customer_info,
                    failure_reason="No matching bookings found in ParkWhiz system",
                    discrepancies=[],
                    should_escalate=True,
                    escalation_reason="No bookings found for customer email and dates",
                    api_calls_made=api_calls,
                    processing_time_ms=processing_time_ms,
                )
            
            # Select best match
            verified_booking = self.select_best_match(bookings, customer_info)
            
            if not verified_booking:
                logger.info(
                    f"No good match found among {len(bookings)} bookings",
                    extra={
                        "customer_email": customer_info.email,
                        "booking_count": len(bookings),
                    }
                )
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return BookingVerificationResult(
                    success=False,
                    verified_booking=None,
                    customer_info=customer_info,
                    failure_reason=f"Found {len(bookings)} bookings but none matched customer dates well",
                    discrepancies=[],
                    should_escalate=True,
                    escalation_reason="Bookings found but dates don't match customer claim",
                    api_calls_made=api_calls,
                    processing_time_ms=processing_time_ms,
                )
            
            # Check for escalation conditions
            should_escalate, escalation_reason = self._check_escalation(
                verified_booking, customer_info
            )
            
            # Calculate discrepancies
            discrepancies = self._find_discrepancies(verified_booking, customer_info)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Booking verification completed successfully for {customer_info.email}",
                extra={
                    "customer_email": customer_info.email,
                    "booking_id": verified_booking.booking_id,
                    "should_escalate": should_escalate,
                    "processing_time_ms": processing_time_ms,
                }
            )
            
            return BookingVerificationResult(
                success=True,
                verified_booking=verified_booking,
                customer_info=customer_info,
                failure_reason=None,
                discrepancies=discrepancies,
                should_escalate=should_escalate,
                escalation_reason=escalation_reason,
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
            
        except ParkWhizAuthenticationError as e:
            logger.critical(
                f"ParkWhiz authentication failed: {e}",
                extra={"customer_email": customer_info.email}
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return BookingVerificationResult(
                success=False,
                verified_booking=None,
                customer_info=customer_info,
                failure_reason=f"Authentication error: {e}",
                discrepancies=[],
                should_escalate=True,
                escalation_reason="ParkWhiz API authentication failed - check credentials",
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
        
        except ParkWhizTimeoutError as e:
            logger.error(
                f"ParkWhiz API timeout: {e}",
                extra={"customer_email": customer_info.email}
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return BookingVerificationResult(
                success=False,
                verified_booking=None,
                customer_info=customer_info,
                failure_reason="API timeout after retry",
                discrepancies=[],
                should_escalate=True,
                escalation_reason="ParkWhiz API timed out - try again later",
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error during verification: {e}",
                extra={"customer_email": customer_info.email},
                exc_info=True
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return BookingVerificationResult(
                success=False,
                verified_booking=None,
                customer_info=customer_info,
                failure_reason=f"Unexpected error: {e}",
                discrepancies=[],
                should_escalate=True,
                escalation_reason=f"System error during verification: {type(e).__name__}",
                api_calls_made=api_calls,
                processing_time_ms=processing_time_ms,
            )
    
    def _check_escalation(
        self,
        verified_booking: VerifiedBooking,
        customer_info: CustomerInfo
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if ticket should be escalated to human review.
        
        Args:
            verified_booking: Verified booking data
            customer_info: Customer-provided information
            
        Returns:
            (should_escalate, reason)
        """
        # Escalate if pass usage is unknown
        if verified_booking.pass_usage_status == "unknown":
            return (
                True,
                "Pass usage status unavailable - cannot determine if pass was used"
            )
        
        # Escalate if match confidence is weak
        if verified_booking.match_confidence == "weak":
            return (
                True,
                "Booking dates don't match customer claim closely - needs human review"
            )
        
        # No escalation needed
        return (False, None)
    
    def _find_discrepancies(
        self,
        verified_booking: VerifiedBooking,
        customer_info: CustomerInfo
    ) -> List[str]:
        """
        Identify discrepancies between verified and customer data.
        
        Args:
            verified_booking: Verified booking data
            customer_info: Customer-provided data
            
        Returns:
            List of discrepancy descriptions
        """
        discrepancies = []
        
        # Compare dates
        try:
            verified_arrival = datetime.fromisoformat(
                verified_booking.arrival_date.replace('Z', '+00:00').split('T')[0]
            )
            customer_arrival = datetime.fromisoformat(customer_info.arrival_date)
            
            if verified_arrival.date() != customer_arrival.date():
                discrepancies.append(
                    f"Arrival date mismatch: customer said {customer_info.arrival_date}, "
                    f"booking shows {verified_arrival.date()}"
                )
        except (ValueError, TypeError):
            pass
        
        try:
            verified_exit = datetime.fromisoformat(
                verified_booking.exit_date.replace('Z', '+00:00').split('T')[0]
            )
            customer_exit = datetime.fromisoformat(customer_info.exit_date)
            
            if verified_exit.date() != customer_exit.date():
                discrepancies.append(
                    f"Exit date mismatch: customer said {customer_info.exit_date}, "
                    f"booking shows {verified_exit.date()}"
                )
        except (ValueError, TypeError):
            pass
        
        # Compare location if provided
        if customer_info.location and verified_booking.location:
            if customer_info.location.lower() not in verified_booking.location.lower():
                discrepancies.append(
                    f"Location mismatch: customer said '{customer_info.location}', "
                    f"booking shows '{verified_booking.location}'"
                )
        
        return discrepancies
