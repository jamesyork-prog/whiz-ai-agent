"""
Verification Note Generator Module

Generates detailed HTML notes with verified booking information for Freshdesk tickets.
Handles both successful verification and failure cases, highlighting discrepancies
between customer-provided and verified data.
"""

import logging
from typing import List, Optional
from html import escape

from app_tools.tools.decision_guard import VerifiedBooking
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
        
        # Build shadcn-style HTML note
        # Determine badge based on pass usage
        if verified_booking.pass_used:
            badge_bg = "#fee2e2"
            badge_color = "#991b1b"
            badge_text = "PASS USED"
        else:
            badge_bg = "#dcfce7"
            badge_color = "#166534"
            badge_text = "PASS NOT USED"
        
        html_parts = [
            # Card container with soft blue glow (reduced width + margin for glow visibility)
            "<div style='background-color: #ffffff; border: 1px solid #bae6fd; border-radius: 8px; "
            "box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(32, 185, 226, 0.1); overflow: hidden; "
            "font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; max-width: 580px; margin: 10px;'>",
            
            # Header
            "<div style='padding: 24px 24px 10px 24px; display: flex; align-items: flex-start; justify-content: space-between;'>",
            "<div>",
            "<h3 style='margin: 0; font-size: 18px; font-weight: 700; color: #0f172a;'>",
            "✅ Booking Verification</h3>",
            "<p style='margin: 4px 0 0 0; font-size: 13px; color: #64748b;'>Verified via ParkWhiz API</p>",
            "</div>",
            # Badge for pass usage
            f"<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
            f"padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
            f"color: {badge_color}; background-color: {badge_bg};'>{badge_text}</span>",
            "</div>",
            
            # Content
            "<div style='padding: 0 24px 24px 24px;'>",
        ]
        
        # Booking details in grid
        html_parts.append(
            "<div style='background-color: #f8fafc; padding: 16px; border-radius: 6px; margin-top: 8px;'>"
        )
        
        # Booking ID (prominent)
        html_parts.append(
            f"<div style='margin-bottom: 12px;'>"
            f"<div style='font-size: 12px; font-weight: 500; color: #64748b; margin-bottom: 4px;'>Booking ID</div>"
            f"<div style='font-size: 16px; font-weight: 600; color: #0f172a; font-family: monospace; "
            f"background-color: #ffffff; padding: 6px 10px; border-radius: 4px; display: inline-block;'>"
            f"{escape(verified_booking.booking_id)}</div>"
            f"</div>"
        )
        
        # Key details in clean rows
        html_parts.append(
            f"<div style='margin-bottom: 10px;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 3px;'>Customer Email</div>"
            f"<div style='font-size: 14px; font-weight: 600; color: #0f172a;'>{escape(verified_booking.customer_email)}</div>"
            f"</div>"
        )
        
        # Dates in two-column
        html_parts.append("<div style='display: flex; gap: 12px; margin-bottom: 10px;'>")
        html_parts.append(
            f"<div style='flex: 1;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 3px;'>Arrival</div>"
            f"<div style='font-size: 14px; font-weight: 600; color: #0f172a;'>{escape(verified_booking.arrival_date.split('T')[0])}</div>"
            f"</div>"
        )
        html_parts.append(
            f"<div style='flex: 1;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 3px;'>Exit</div>"
            f"<div style='font-size: 14px; font-weight: 600; color: #0f172a;'>{escape(verified_booking.exit_date.split('T')[0])}</div>"
            f"</div>"
        )
        html_parts.append("</div>")
        
        # Location and Amount in two-column
        html_parts.append("<div style='display: flex; gap: 12px; margin-bottom: 10px;'>")
        if verified_booking.location:
            html_parts.append(
                f"<div style='flex: 1;'>"
                f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 3px;'>Location</div>"
                f"<div style='font-size: 13px; font-weight: 600; color: #0f172a;'>{escape(verified_booking.location)}</div>"
                f"</div>"
            )
        html_parts.append(
            f"<div style='flex: 1;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 3px;'>Amount Paid</div>"
            f"<div style='font-size: 14px; font-weight: 600; color: #0f172a;'>${verified_booking.amount_paid:.2f}</div>"
            f"</div>"
        )
        html_parts.append("</div>")
        
        # Pass status and confidence as pills
        html_parts.append(
            "<div style='display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0;'>"
        )
        
        # Pass status pill
        if verified_booking.pass_used:
            pass_bg = "#fee2e2"
            pass_color = "#991b1b"
            pass_icon = "✗"
        else:
            pass_bg = "#dcfce7"
            pass_color = "#166534"
            pass_icon = "✓"
        
        html_parts.append(
            f"<div style='background-color: {pass_bg}; color: {pass_color}; "
            f"padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;'>"
            f"{pass_icon} {escape(verified_booking.pass_usage_status)}</div>"
        )
        
        # Match confidence pill
        confidence_styles = {
            "exact": {"bg": "#dcfce7", "color": "#166534"},
            "partial": {"bg": "#fef3c7", "color": "#92400e"},
            "weak": {"bg": "#fee2e2", "color": "#991b1b"}
        }
        conf_style = confidence_styles.get(verified_booking.match_confidence, {"bg": "#f1f5f9", "color": "#475569"})
        
        html_parts.append(
            f"<div style='background-color: {conf_style['bg']}; color: {conf_style['color']}; "
            f"padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;'>"
            f"{escape(verified_booking.match_confidence.capitalize())} Match</div>"
        )
        
        html_parts.append("</div>")  # End pills
        
        html_parts.append("</div>")  # End details box
        
        # Add discrepancies alert if any found
        if discrepancies:
            html_parts.append(
                "<div style='border: 1px solid #fca5a5; background-color: #fef2f2; color: #991b1b; "
                "border-radius: 6px; padding: 12px 16px; margin-top: 16px; font-size: 13px;'>"
                "<div style='margin-bottom: 4px; font-weight: 600; display: flex; align-items: center; gap: 8px;'>"
                "⚠️ Discrepancies Detected</div>"
                "<ul style='margin: 4px 0 0 24px; padding: 0; line-height: 1.5; color: #7f1d1d;'>"
            )
            for discrepancy in discrepancies:
                html_parts.append(f"<li>{escape(discrepancy)}</li>")
            html_parts.append("</ul></div>")
        
        html_parts.append("</div>")  # End content
        
        # Footer
        html_parts.append(
            "<div style='border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 24px;'>"
            f"<div style='font-size: 12px; color: #64748b;'>Verified booking data from ParkWhiz API</div>"
            "</div>"
        )
        
        html_parts.append("</div>")  # End card
        
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
            # Card container with soft blue glow (reduced width + margin for glow visibility)
            "<div style='background-color: #ffffff; border: 1px solid #bae6fd; border-radius: 8px; "
            "box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(32, 185, 226, 0.1); overflow: hidden; "
            "font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; max-width: 580px; margin: 10px;'>",
            
            # Header
            "<div style='padding: 24px 24px 10px 24px; display: flex; align-items: flex-start; justify-content: space-between;'>",
            "<div>",
            "<h3 style='margin: 0; font-size: 18px; font-weight: 700; color: #0f172a;'>",
            "❌ Verification Failed</h3>",
            "<p style='margin: 4px 0 0 0; font-size: 13px; color: #64748b;'>Unable to verify booking</p>",
            "</div>",
            # Badge - red to match NEEDS REVIEW styling
            "<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
            "padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
            "border: 1px solid #fca5a5; color: #991b1b; background-color: #fee2e2;'>MANUAL REVIEW</span>",
            "</div>",
            
            # Content
            "<div style='padding: 0 24px 24px 24px;'>",
        ]
        
        # Failure reason alert
        html_parts.append(
            "<div style='border: 1px solid #fca5a5; background-color: #fef2f2; color: #991b1b; "
            "border-radius: 6px; padding: 12px 16px; margin-top: 8px; font-size: 13px;'>"
            f"<div style='font-weight: 600; margin-bottom: 4px;'>Reason</div>"
            f"<div style='font-weight: 600;'>{escape(failure_reason)}</div>"
            "</div>"
        )
        
        # Customer information attempted
        html_parts.append(
            "<div style='background-color: #f8fafc; padding: 16px; border-radius: 6px; margin-top: 16px;'>"
            "<div style='font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 12px;'>Customer Information Attempted</div>"
        )
        
        if customer_info.email:
            html_parts.append(
                f"<div style='margin-bottom: 8px;'>"
                f"<div style='font-size: 12px; font-weight: 500; color: #64748b;'>Email</div>"
                f"<div style='font-size: 14px; color: #0f172a;'>{escape(customer_info.email)}</div>"
                f"</div>"
            )
        
        if customer_info.name:
            html_parts.append(
                f"<div style='margin-bottom: 8px;'>"
                f"<div style='font-size: 12px; font-weight: 500; color: #64748b;'>Name</div>"
                f"<div style='font-size: 14px; color: #0f172a;'>{escape(customer_info.name)}</div>"
                f"</div>"
            )
        
        # Dates in two-column layout
        if customer_info.arrival_date or customer_info.exit_date:
            html_parts.append("<div style='display: flex; gap: 16px; margin-bottom: 8px;'>")
            if customer_info.arrival_date:
                html_parts.append(
                    f"<div style='flex: 1;'>"
                    f"<div style='font-size: 12px; font-weight: 500; color: #64748b;'>Arrival Date</div>"
                    f"<div style='font-size: 14px; color: #0f172a;'>{escape(customer_info.arrival_date)}</div>"
                    f"</div>"
                )
            if customer_info.exit_date:
                html_parts.append(
                    f"<div style='flex: 1;'>"
                    f"<div style='font-size: 12px; font-weight: 500; color: #64748b;'>Exit Date</div>"
                    f"<div style='font-size: 14px; color: #0f172a;'>{escape(customer_info.exit_date)}</div>"
                    f"</div>"
                )
            html_parts.append("</div>")
        
        if customer_info.location:
            html_parts.append(
                f"<div>"
                f"<div style='font-size: 12px; font-weight: 500; color: #64748b;'>Location</div>"
                f"<div style='font-size: 14px; color: #0f172a;'>{escape(customer_info.location)}</div>"
                f"</div>"
            )
        
        html_parts.append("</div>")  # End customer info box
        
        # Next steps
        html_parts.append(
            "<div style='background-color: #fffaf0; border: 1px solid #fed7aa; border-radius: 6px; "
            "padding: 12px 16px; margin-top: 16px; font-size: 13px;'>"
            "<div style='font-weight: 600; color: #92400e; margin-bottom: 8px;'>📋 Next Steps</div>"
            "<ol style='margin: 0; padding-left: 20px; color: #78350f; line-height: 1.6;'>"
            "<li>Verify customer information directly with ParkWhiz system</li>"
            "<li>Check for alternate email addresses or booking methods</li>"
            "<li>Contact customer if information is unclear or missing</li>"
            "</ol>"
            "</div>"
        )
        
        html_parts.append("</div>")  # End content
        
        # Footer
        html_parts.append(
            "<div style='border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 24px;'>"
            "<div style='font-size: 12px; color: #64748b;'>Manual verification required</div>"
            "</div>"
        )
        
        html_parts.append("</div>")  # End card
        
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
            # Card container with soft blue glow (reduced width + margin for glow visibility)
            "<div style='background-color: #ffffff; border: 1px solid #bae6fd; border-radius: 8px; "
            "box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(32, 185, 226, 0.1); overflow: hidden; "
            "font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; max-width: 580px; margin: 10px;'>",
            
            # Header
            "<div style='padding: 24px 24px 10px 24px; display: flex; align-items: flex-start; justify-content: space-between;'>",
            "<div>",
            "<h3 style='margin: 0; font-size: 18px; font-weight: 700; color: #0f172a;'>",
            f"🔍 Multiple Bookings Found</h3>",
            "<p style='margin: 4px 0 0 0; font-size: 13px; color: #64748b;'>Review and select correct booking</p>",
            "</div>",
            # Badge with count - red to match NEEDS REVIEW styling
            f"<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
            f"padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
            f"border: 1px solid #fca5a5; color: #991b1b; background-color: #fee2e2;'>{len(bookings)} MATCHES</span>",
            "</div>",
            
            # Content
            "<div style='padding: 0 24px 24px 24px;'>",
            
            # Warning message
            "<div style='background-color: #fffaf0; border: 1px solid #fed7aa; border-radius: 6px; "
            "padding: 12px 16px; margin-top: 8px; font-size: 13px; color: #78350f;'>"
            "Multiple bookings match the customer's information. Please review all options below.</div>",
        ]
        
        # List each booking in compact cards
        for i, booking in enumerate(bookings, 1):
            # Determine accent color based on confidence
            accent_color = {
                "exact": "#16a34a",
                "partial": "#d97706",
                "weak": "#dc2626"
            }.get(booking.match_confidence, "#64748b")
            
            html_parts.append(
                f"<div style='background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid {accent_color}; "
                f"border-radius: 6px; padding: 12px; margin-top: 12px;'>"
            )
            
            # Booking header with ID and confidence
            html_parts.append(
                f"<div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;'>"
                f"<div style='font-size: 12px; font-weight: 600; color: #64748b;'>BOOKING #{i}</div>"
                f"<div style='font-size: 11px; font-weight: 600; color: {accent_color};'>"
                f"{escape(booking.match_confidence.capitalize())} Match</div>"
                f"</div>"
            )
            
            # Booking ID (prominent)
            html_parts.append(
                f"<div style='font-size: 15px; font-weight: 600; color: #0f172a; font-family: monospace; "
                f"margin-bottom: 8px;'>{escape(booking.booking_id)}</div>"
            )
            
            # Pass usage with icon
            usage_icon = (
                '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" '
                'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle>'
                '<line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
                if booking.pass_used else
                '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" '
                'stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>'
                '<polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
            )
            usage_color = "#dc2626" if booking.pass_used else "#16a34a"
            usage_text = "Pass Used" if booking.pass_used else "Pass Not Used"
            
            html_parts.append(
                f"<div style='display: flex; align-items: center; gap: 6px; margin-bottom: 8px;'>"
                f"{usage_icon}"
                f"<span style='font-size: 13px; font-weight: 600; color: {usage_color};'>{usage_text}</span>"
                f"</div>"
            )
            
            # Compact details grid
            html_parts.append("<div style='font-size: 12px; color: #64748b; line-height: 1.6;'>")
            html_parts.append(
                f"<div><strong>Dates:</strong> {escape(booking.arrival_date.split('T')[0])} to "
                f"{escape(booking.exit_date.split('T')[0])}</div>"
            )
            if booking.location:
                html_parts.append(f"<div><strong>Location:</strong> {escape(booking.location)}</div>")
            html_parts.append(f"<div><strong>Amount:</strong> ${booking.amount_paid:.2f}</div>")
            html_parts.append("</div>")
            
            html_parts.append("</div>")  # End booking card
        
        html_parts.append("</div>")  # End content
        
        # Footer
        html_parts.append(
            "<div style='border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 24px;'>"
            f"<div style='font-size: 12px; color: #64748b;'>Found {len(bookings)} matching bookings via ParkWhiz API</div>"
            "</div>"
        )
        
        html_parts.append("</div>")  # End card
        
        note = "".join(html_parts)
        
        logger.debug(f"Generated multiple bookings note with {len(bookings)} bookings")
        
        return note
