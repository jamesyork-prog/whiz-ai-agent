"""
Verification Note Generator Module

Generates detailed HTML notes with verified booking information for Freshdesk tickets.
Handles both successful verification and failure cases, highlighting discrepancies
between customer-provided and verified data.
"""

import logging
from typing import List, Optional
from html import escape

from app_tools.tools.booking_verifier import VerifiedBooking
from app_tools.tools.customer_info_extractor import CustomerInfo


# Configure logging
logger = logging.getLogger(__name__)


class VerificationNoteGenerator:
    """Generates detailed notes with verified booking information."""
    
    def generate_verified_note(
        self,
        verified_booking: VerifiedBooking,
        customer_provided: CustomerInfo
    ) -> str:
        """
        Generate HTML note with verified booking details.
        
        Creates a formatted note containing:
        - Verified booking ID
        - Pass usage status
        - Booking dates and location
        - Amount paid
        - Match confidence level
        - Highlighted discrepancies (if any)
        
        Args:
            verified_booking: Verified booking from ParkWhiz
            customer_provided: Customer-provided information
            
        Returns:
            HTML formatted note for Freshdesk
        """
        logger.info(
            f"Generating verified note for booking {verified_booking.booking_id}",
            extra={"booking_id": verified_booking.booking_id}
        )
        
        # Find discrepancies
        discrepancies = self.highlight_discrepancies(verified_booking, customer_provided)
        
        # Build HTML note
        html_parts = [
            "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>",
            "<h3 style='color: #2c5282; margin-bottom: 10px;'>✅ Booking Verification Results</h3>",
            "<div style='background-color: #f7fafc; padding: 15px; border-left: 4px solid #48bb78; margin-bottom: 15px;'>",
        ]
        
        # Booking ID
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Booking ID:</strong> "
            f"<span style='font-family: monospace; background-color: #edf2f7; padding: 2px 6px; border-radius: 3px;'>"
            f"{escape(verified_booking.booking_id)}</span></p>"
        )
        
        # Pass Usage Status (highlighted)
        usage_color = "#48bb78" if verified_booking.pass_used else "#f56565"
        usage_text = "USED ✓" if verified_booking.pass_used else "NOT USED ✗"
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Pass Usage:</strong> "
            f"<span style='color: {usage_color}; font-weight: bold;'>{usage_text}</span> "
            f"({escape(verified_booking.pass_usage_status)})</p>"
        )
        
        # Customer Email
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Customer Email:</strong> "
            f"{escape(verified_booking.customer_email)}</p>"
        )
        
        # Dates
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Arrival Date:</strong> "
            f"{escape(verified_booking.arrival_date)}</p>"
        )
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Exit Date:</strong> "
            f"{escape(verified_booking.exit_date)}</p>"
        )
        
        # Location
        if verified_booking.location:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Location:</strong> "
                f"{escape(verified_booking.location)}</p>"
            )
        
        # Amount Paid
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Amount Paid:</strong> "
            f"${verified_booking.amount_paid:.2f}</p>"
        )
        
        # Match Confidence
        confidence_color = {
            "exact": "#48bb78",
            "partial": "#ed8936",
            "weak": "#f56565"
        }.get(verified_booking.match_confidence, "#718096")
        
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Match Confidence:</strong> "
            f"<span style='color: {confidence_color}; font-weight: bold;'>"
            f"{escape(verified_booking.match_confidence.upper())}</span></p>"
        )
        
        html_parts.append("</div>")
        
        # Add discrepancies section if any found
        if discrepancies:
            html_parts.append(
                "<div style='background-color: #fff5f5; padding: 15px; border-left: 4px solid #f56565; margin-bottom: 15px;'>"
            )
            html_parts.append(
                "<h4 style='color: #c53030; margin-top: 0; margin-bottom: 10px;'>⚠️ Discrepancies Found</h4>"
            )
            html_parts.append("<ul style='margin: 5px 0; padding-left: 20px;'>")
            for discrepancy in discrepancies:
                html_parts.append(f"<li style='margin: 3px 0;'>{escape(discrepancy)}</li>")
            html_parts.append("</ul>")
            html_parts.append("</div>")
        
        html_parts.append("</div>")
        
        note = "".join(html_parts)
        
        logger.debug(
            f"Generated verified note with {len(discrepancies)} discrepancies",
            extra={
                "booking_id": verified_booking.booking_id,
                "discrepancy_count": len(discrepancies)
            }
        )
        
        return note
    
    def generate_verification_failed_note(
        self,
        customer_info: CustomerInfo,
        failure_reason: str
    ) -> str:
        """
        Generate note explaining why verification failed.
        
        Creates a formatted note containing:
        - Failure reason
        - Customer information that was attempted
        - Next steps for manual review
        
        Args:
            customer_info: Customer information attempted
            failure_reason: Reason verification failed
            
        Returns:
            HTML formatted note
        """
        logger.info(
            "Generating verification failed note",
            extra={"failure_reason": failure_reason}
        )
        
        html_parts = [
            "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>",
            "<h3 style='color: #c53030; margin-bottom: 10px;'>❌ Booking Verification Failed</h3>",
            "<div style='background-color: #fff5f5; padding: 15px; border-left: 4px solid #f56565; margin-bottom: 15px;'>",
        ]
        
        # Failure reason
        html_parts.append(
            f"<p style='margin: 5px 0;'><strong>Reason:</strong> {escape(failure_reason)}</p>"
        )
        
        html_parts.append("</div>")
        
        # Customer information attempted
        html_parts.append(
            "<div style='background-color: #f7fafc; padding: 15px; border-left: 4px solid #718096; margin-bottom: 15px;'>"
        )
        html_parts.append(
            "<h4 style='color: #2d3748; margin-top: 0; margin-bottom: 10px;'>Customer Information Attempted</h4>"
        )
        
        if customer_info.email:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Email:</strong> {escape(customer_info.email)}</p>"
            )
        
        if customer_info.name:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Name:</strong> {escape(customer_info.name)}</p>"
            )
        
        if customer_info.arrival_date:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Arrival Date:</strong> {escape(customer_info.arrival_date)}</p>"
            )
        
        if customer_info.exit_date:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Exit Date:</strong> {escape(customer_info.exit_date)}</p>"
            )
        
        if customer_info.location:
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Location:</strong> {escape(customer_info.location)}</p>"
            )
        
        html_parts.append("</div>")
        
        # Next steps
        html_parts.append(
            "<div style='background-color: #fffaf0; padding: 15px; border-left: 4px solid #ed8936;'>"
        )
        html_parts.append(
            "<h4 style='color: #7c2d12; margin-top: 0; margin-bottom: 10px;'>📋 Next Steps</h4>"
        )
        html_parts.append(
            "<p style='margin: 5px 0;'>This ticket requires manual review. Please:</p>"
        )
        html_parts.append("<ol style='margin: 5px 0; padding-left: 20px;'>")
        html_parts.append("<li>Verify customer information directly with ParkWhiz system</li>")
        html_parts.append("<li>Check for alternate email addresses or booking methods</li>")
        html_parts.append("<li>Contact customer if information is unclear or missing</li>")
        html_parts.append("</ol>")
        html_parts.append("</div>")
        
        html_parts.append("</div>")
        
        note = "".join(html_parts)
        
        logger.debug("Generated verification failed note")
        
        return note
    
    def highlight_discrepancies(
        self,
        verified: VerifiedBooking,
        customer_provided: CustomerInfo
    ) -> List[str]:
        """
        Identify discrepancies between verified and customer data.
        
        Compares:
        - Arrival dates
        - Exit dates
        - Location names
        
        Args:
            verified: Verified booking data
            customer_provided: Customer-provided data
            
        Returns:
            List of discrepancy descriptions
        """
        from datetime import datetime
        
        discrepancies = []
        
        logger.debug(
            "Checking for discrepancies",
            extra={
                "booking_id": verified.booking_id,
                "customer_email": customer_provided.email
            }
        )
        
        # Compare arrival dates
        if customer_provided.arrival_date:
            try:
                # Parse verified date (may include time)
                verified_arrival_str = verified.arrival_date.replace('Z', '+00:00').split('T')[0]
                verified_arrival = datetime.fromisoformat(verified_arrival_str)
                customer_arrival = datetime.fromisoformat(customer_provided.arrival_date)
                
                if verified_arrival.date() != customer_arrival.date():
                    discrepancies.append(
                        f"Arrival date mismatch: customer said {customer_provided.arrival_date}, "
                        f"booking shows {verified_arrival.date()}"
                    )
                    logger.debug(
                        f"Arrival date discrepancy found: {customer_provided.arrival_date} vs {verified_arrival.date()}"
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error comparing arrival dates: {e}")
        
        # Compare exit dates
        if customer_provided.exit_date:
            try:
                # Parse verified date (may include time)
                verified_exit_str = verified.exit_date.replace('Z', '+00:00').split('T')[0]
                verified_exit = datetime.fromisoformat(verified_exit_str)
                customer_exit = datetime.fromisoformat(customer_provided.exit_date)
                
                if verified_exit.date() != customer_exit.date():
                    discrepancies.append(
                        f"Exit date mismatch: customer said {customer_provided.exit_date}, "
                        f"booking shows {verified_exit.date()}"
                    )
                    logger.debug(
                        f"Exit date discrepancy found: {customer_provided.exit_date} vs {verified_exit.date()}"
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error comparing exit dates: {e}")
        
        # Compare location if provided by customer
        if customer_provided.location and verified.location:
            # Case-insensitive substring match
            customer_loc_lower = customer_provided.location.lower()
            verified_loc_lower = verified.location.lower()
            
            # Check if either location contains the other (partial match is okay)
            if (customer_loc_lower not in verified_loc_lower and 
                verified_loc_lower not in customer_loc_lower):
                discrepancies.append(
                    f"Location mismatch: customer said '{customer_provided.location}', "
                    f"booking shows '{verified.location}'"
                )
                logger.debug(
                    f"Location discrepancy found: {customer_provided.location} vs {verified.location}"
                )
        
        logger.info(
            f"Found {len(discrepancies)} discrepancies",
            extra={
                "booking_id": verified.booking_id,
                "discrepancy_count": len(discrepancies)
            }
        )
        
        return discrepancies
    
    def generate_multiple_bookings_note(
        self,
        bookings: List[VerifiedBooking],
        customer_provided: CustomerInfo
    ) -> str:
        """
        Generate note listing multiple matching bookings.
        
        Used when multiple bookings are found and need to be presented
        for manual review or selection.
        
        Args:
            bookings: List of verified bookings
            customer_provided: Customer-provided information
            
        Returns:
            HTML formatted note listing all bookings
        """
        logger.info(
            f"Generating multiple bookings note for {len(bookings)} bookings",
            extra={"booking_count": len(bookings)}
        )
        
        html_parts = [
            "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>",
            f"<h3 style='color: #2c5282; margin-bottom: 10px;'>🔍 Multiple Bookings Found ({len(bookings)})</h3>",
            "<div style='background-color: #fffaf0; padding: 15px; border-left: 4px solid #ed8936; margin-bottom: 15px;'>",
            "<p style='margin: 5px 0;'>Multiple bookings match the customer's information. "
            "Please review all bookings below and select the correct one.</p>",
            "</div>",
        ]
        
        # List each booking
        for i, booking in enumerate(bookings, 1):
            # Determine border color based on confidence
            border_color = {
                "exact": "#48bb78",
                "partial": "#ed8936",
                "weak": "#f56565"
            }.get(booking.match_confidence, "#718096")
            
            html_parts.append(
                f"<div style='background-color: #f7fafc; padding: 15px; border-left: 4px solid {border_color}; margin-bottom: 10px;'>"
            )
            html_parts.append(
                f"<h4 style='color: #2d3748; margin-top: 0; margin-bottom: 10px;'>Booking #{i}</h4>"
            )
            
            # Booking details
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Booking ID:</strong> "
                f"<span style='font-family: monospace; background-color: #edf2f7; padding: 2px 6px; border-radius: 3px;'>"
                f"{escape(booking.booking_id)}</span></p>"
            )
            
            # Pass usage
            usage_color = "#48bb78" if booking.pass_used else "#f56565"
            usage_text = "USED ✓" if booking.pass_used else "NOT USED ✗"
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Pass Usage:</strong> "
                f"<span style='color: {usage_color}; font-weight: bold;'>{usage_text}</span></p>"
            )
            
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Dates:</strong> "
                f"{escape(booking.arrival_date)} to {escape(booking.exit_date)}</p>"
            )
            
            if booking.location:
                html_parts.append(
                    f"<p style='margin: 5px 0;'><strong>Location:</strong> {escape(booking.location)}</p>"
                )
            
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Amount:</strong> ${booking.amount_paid:.2f}</p>"
            )
            
            # Match confidence
            confidence_color = {
                "exact": "#48bb78",
                "partial": "#ed8936",
                "weak": "#f56565"
            }.get(booking.match_confidence, "#718096")
            
            html_parts.append(
                f"<p style='margin: 5px 0;'><strong>Match:</strong> "
                f"<span style='color: {confidence_color}; font-weight: bold;'>"
                f"{escape(booking.match_confidence.upper())}</span></p>"
            )
            
            html_parts.append("</div>")
        
        html_parts.append("</div>")
        
        note = "".join(html_parts)
        
        logger.debug(f"Generated multiple bookings note with {len(bookings)} bookings")
        
        return note
