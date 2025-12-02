"""
Duplicate Booking Detection Tool

Parlant tool that detects and resolves duplicate booking issues by:
1. Querying ParkWhiz API for customer bookings
2. Analyzing bookings for duplicates
3. Automatically refunding unused duplicate bookings

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import parlant.sdk as p

from app_tools.tools.parkwhiz_client import (
    ParkWhizOAuth2Client,
    ParkWhizAuthenticationError,
    ParkWhizNotFoundError,
    ParkWhizTimeoutError,
    ParkWhizError,
)
from app_tools.tools.duplicate_booking_analyzer import (
    DuplicateBookingAnalyzer,
    DuplicateDetectionResult,
)


logger = logging.getLogger(__name__)


@p.tool
async def detect_duplicate_bookings(
    context: p.ToolContext,
    customer_email: str,
    event_date: str,
    location_name: Optional[str] = None,
) -> p.ToolResult:
    """
    Detect and resolve duplicate bookings for a customer.
    
    This tool queries the ParkWhiz API to find all bookings for a customer
    around a specific event date, analyzes them for duplicates, and automatically
    refunds unused duplicate bookings when detected.
    
    Args:
        customer_email (str): Customer's email address from Freshdesk ticket
        event_date (str): Event date from booking info (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        location_name (str, optional): Parking location name (for logging/context)
    
    Returns:
        ToolResult with duplicate detection outcome:
        - has_duplicates: Whether duplicates were found
        - action_taken: "refunded", "escalate", or "deny"
        - refunded_booking_id: ID of refunded booking (if applicable)
        - kept_booking_id: ID of kept booking (if applicable)
        - refund_amount: Amount refunded (if applicable)
        - explanation: Human-readable explanation
    """
    logger.info(
        f"Starting duplicate detection for {customer_email}",
        extra={
            "customer_email": customer_email,
            "event_date": event_date,
            "location_name": location_name,
        }
    )
    
    try:
        # Initialize ParkWhiz OAuth2 client
        client = ParkWhizOAuth2Client()
        
        # Parse event date and calculate date range (+/- 1 day)
        try:
            # Handle both date and datetime formats
            if "T" in event_date:
                event_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            else:
                event_dt = datetime.fromisoformat(event_date)
        except ValueError as e:
            logger.error(f"Invalid event_date format: {event_date}", extra={"error": str(e)})
            return p.ToolResult(
                data={
                    "error": "invalid_date_format",
                    "message": f"Invalid date format: {event_date}. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                },
                metadata={"summary": f"Invalid date format: {event_date}"}
            )
        
        # Calculate date range
        start_date = (event_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (event_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(
            f"Querying bookings from {start_date} to {end_date}",
            extra={"start_date": start_date, "end_date": end_date}
        )
        
        # Query customer bookings
        bookings = await client.get_customer_bookings(
            customer_email=customer_email,
            start_date=start_date,
            end_date=end_date,
        )
        
        logger.info(
            f"Retrieved {len(bookings)} bookings for analysis",
            extra={"booking_count": len(bookings)}
        )
        
        # Analyze for duplicates
        try:
            analyzer = DuplicateBookingAnalyzer()
            result: DuplicateDetectionResult = analyzer.analyze(bookings)
            
            logger.info(
                f"Analysis complete: action={result.action}, duplicates={result.has_duplicates}",
                extra={
                    "action": result.action,
                    "has_duplicates": result.has_duplicates,
                    "duplicate_count": result.duplicate_count,
                }
            )
        except Exception as e:
            logger.error(
                f"Duplicate analysis failed: {e}",
                extra={"error": str(e), "booking_count": len(bookings)},
                exc_info=True
            )
            return p.ToolResult(
                data={
                    "error": "analysis_failed",
                    "message": f"Failed to analyze bookings: {str(e)}",
                    "action_taken": "escalate",
                },
                metadata={
                    "summary": "Duplicate analysis failed - escalate to human review"
                }
            )
        
        # If action is refund_duplicate, process the refund
        # SAFETY CHECK: Only refund if we have clear duplicate detection with used/unused identification
        if result.action == "refund_duplicate" and result.unused_booking_id and result.used_booking_id:
            logger.info(
                f"Processing refund for booking {result.unused_booking_id}",
                extra={
                    "unused_booking_id": result.unused_booking_id,
                    "used_booking_id": result.used_booking_id,
                    "duplicate_count": result.duplicate_count
                }
            )
            
            # Additional safety check: Ensure we have exactly 2 duplicates
            if result.duplicate_count != 2:
                logger.error(
                    f"Safety check failed: Expected 2 duplicates, got {result.duplicate_count}",
                    extra={"duplicate_count": result.duplicate_count}
                )
                return p.ToolResult(
                    data={
                        "error": "safety_check_failed",
                        "message": f"Cannot refund: Expected 2 duplicates, got {result.duplicate_count}",
                        "action_taken": "escalate",
                        "explanation": "Safety check failed - escalate to human review",
                    },
                    metadata={
                        "summary": "Safety check failed - escalate to human review"
                    }
                )
            
            try:
                refund_result = await client.delete_booking(str(result.unused_booking_id))
                
                # Extract refund amount from response
                refund_amount = None
                if isinstance(refund_result, dict):
                    # Try different possible field names
                    refund_amount = (
                        refund_result.get("refund_amount") or
                        refund_result.get("amount") or
                        refund_result.get("price_paid")
                    )
                
                # Log refund confirmation when deletion succeeds (Requirement 11.4)
                logger.info(
                    f"Refund completed successfully for booking {result.unused_booking_id}",
                    extra={
                        "refunded_booking_id": result.unused_booking_id,
                        "kept_booking_id": result.used_booking_id,
                        "refund_amount": refund_amount,
                        "customer_email": customer_email,
                        "operation": "refund_duplicate",
                        "refund_status": "success",
                    }
                )
                
                return p.ToolResult(
                    data={
                        "has_duplicates": True,
                        "action_taken": "refunded",
                        "refunded_booking_id": result.unused_booking_id,
                        "kept_booking_id": result.used_booking_id,
                        "refund_amount": refund_amount,
                        "explanation": result.explanation,
                        "all_booking_ids": result.all_booking_ids,
                    },
                    metadata={
                        "summary": f"Refunded duplicate booking {result.unused_booking_id}. {result.explanation}"
                    }
                )
            
            except ParkWhizNotFoundError as e:
                # Log full error details with stack trace (Requirement 11.5)
                logger.error(
                    f"Booking {result.unused_booking_id} not found for refund",
                    extra={
                        "booking_id": result.unused_booking_id,
                        "error_type": "booking_not_found",
                        "customer_email": customer_email,
                    },
                    exc_info=True
                )
                return p.ToolResult(
                    data={
                        "error": "booking_not_found",
                        "message": f"Booking {result.unused_booking_id} not found",
                        "action_taken": "escalate",
                        "explanation": f"Duplicate detected but booking {result.unused_booking_id} not found. Escalate to human review.",
                    },
                    metadata={
                        "summary": f"Booking {result.unused_booking_id} not found - escalate to human review"
                    }
                )
            
            except ParkWhizError as e:
                # Log full error details with stack trace (Requirement 11.5)
                logger.error(
                    f"Failed to refund booking {result.unused_booking_id}: {e}",
                    extra={
                        "booking_id": result.unused_booking_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "customer_email": customer_email,
                    },
                    exc_info=True
                )
                return p.ToolResult(
                    data={
                        "error": "refund_failed",
                        "message": str(e),
                        "action_taken": "escalate",
                        "explanation": f"Duplicate detected but refund failed: {str(e)}. Escalate to human review.",
                    },
                    metadata={
                        "summary": f"Refund failed for booking {result.unused_booking_id} - escalate to human review"
                    }
                )
        
        # Safety check: If action is refund but we're missing required IDs, escalate
        elif result.action == "refund_duplicate" and (not result.unused_booking_id or not result.used_booking_id):
            logger.error(
                "Safety check failed: refund_duplicate action but missing booking IDs",
                extra={
                    "unused_booking_id": result.unused_booking_id,
                    "used_booking_id": result.used_booking_id,
                    "action": result.action
                }
            )
            return p.ToolResult(
                data={
                    "error": "missing_booking_ids",
                    "message": "Cannot refund: Missing used or unused booking ID",
                    "action_taken": "escalate",
                    "explanation": "Duplicate detected but cannot identify which booking to refund. Escalate to human review.",
                },
                metadata={
                    "summary": "Missing booking IDs - escalate to human review"
                }
            )
        
        # Return result without refund action (escalate or deny)
        return p.ToolResult(
            data={
                "has_duplicates": result.has_duplicates,
                "action_taken": result.action,
                "duplicate_count": result.duplicate_count,
                "explanation": result.explanation,
                "all_booking_ids": result.all_booking_ids,
                "used_booking_id": result.used_booking_id,
                "unused_booking_id": result.unused_booking_id,
            },
            metadata={
                "summary": result.explanation
            }
        )
    
    except ParkWhizAuthenticationError as e:
        # Log full error details with stack trace (Requirement 11.5)
        logger.critical(
            "ParkWhiz API authentication failed",
            extra={
                "error": str(e),
                "error_type": "authentication_failed",
                "customer_email": customer_email,
            },
            exc_info=True
        )
        return p.ToolResult(
            data={
                "error": "authentication_failed",
                "message": "ParkWhiz API authentication failed. Check credentials.",
                "action_taken": "escalate",
            },
            metadata={
                "summary": "ParkWhiz authentication failed - escalate to human review"
            }
        )
    
    except ParkWhizTimeoutError as e:
        # Log full error details with stack trace (Requirement 11.5)
        logger.error(
            "ParkWhiz API timeout",
            extra={
                "error": str(e),
                "error_type": "api_timeout",
                "customer_email": customer_email,
            },
            exc_info=True
        )
        return p.ToolResult(
            data={
                "error": "api_timeout",
                "message": "ParkWhiz API request timed out. Please retry.",
                "action_taken": "escalate",
            },
            metadata={
                "summary": "ParkWhiz API timeout - escalate to human review"
            }
        )
    
    except ParkWhizError as e:
        # Log full error details with stack trace (Requirement 11.5)
        logger.error(
            f"ParkWhiz API error: {e}",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "customer_email": customer_email,
            },
            exc_info=True
        )
        return p.ToolResult(
            data={
                "error": "api_error",
                "message": str(e),
                "action_taken": "escalate",
            },
            metadata={
                "summary": f"ParkWhiz API error - escalate to human review"
            }
        )
    
    except Exception as e:
        logger.error(
            f"Unexpected error during duplicate detection: {e}",
            extra={"error": str(e)},
            exc_info=True
        )
        return p.ToolResult(
            data={
                "error": "detection_failed",
                "message": f"Unexpected error: {str(e)}",
                "action_taken": "escalate",
            },
            metadata={
                "summary": f"Detection failed: {str(e)} - escalate to human review"
            }
        )
    
    finally:
        # Clean up client connection
        try:
            await client.close()
        except Exception as e:
            logger.warning(f"Error closing ParkWhiz client: {e}")
