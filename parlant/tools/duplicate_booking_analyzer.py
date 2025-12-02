"""
Duplicate Booking Analyzer

Analyzes customer bookings to detect duplicates based on location and time overlap.
Identifies which booking was used and which should be refunded.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class DuplicateDetectionResult:
    """
    Result of duplicate booking detection analysis.
    
    Attributes:
        has_duplicates: Whether duplicate bookings were found
        duplicate_count: Number of duplicate bookings found
        used_booking_id: ID of the booking that was actually used (if applicable)
        unused_booking_id: ID of the unused booking to refund (if applicable)
        action: Action to take - "refund_duplicate", "escalate", or "deny"
        explanation: Human-readable explanation of the detection result
        all_booking_ids: List of all booking IDs analyzed
    """
    has_duplicates: bool
    duplicate_count: int
    used_booking_id: Optional[int]
    unused_booking_id: Optional[int]
    action: str  # "refund_duplicate", "escalate", "deny"
    explanation: str
    all_booking_ids: List[int]


class DuplicateBookingAnalyzer:
    """
    Analyzes bookings to detect duplicates and determine refund actions.
    
    Duplicate detection logic:
    - Bookings are duplicates if they have the same location_id
    - AND their time windows overlap by at least 50%
    
    Decision logic:
    - 0-1 bookings: No duplicates → deny claim
    - 2 bookings: Identify used/unused → refund unused
    - 3+ bookings: Too complex → escalate to human
    """
    
    # Status values indicating a booking was used
    USED_STATUSES = {"completed", "checked_in", "checked_out"}
    
    # Status values indicating a booking was not used
    UNUSED_STATUSES = {"confirmed", "pending", "reserved"}
    
    # Minimum time overlap percentage to consider bookings as duplicates
    MIN_OVERLAP_PERCENTAGE = 50.0
    
    def analyze(self, bookings: List[Dict[str, Any]]) -> DuplicateDetectionResult:
        """
        Analyze bookings to detect duplicates and determine action.
        
        Args:
            bookings: List of booking dictionaries from ParkWhiz API
            
        Returns:
            DuplicateDetectionResult with detection outcome and recommended action
        """
        logger.info(
            f"Starting duplicate booking analysis for {len(bookings)} bookings",
            extra={
                "booking_count": len(bookings),
                "operation": "analyze_duplicates",
            }
        )
        
        # Extract all booking IDs (handle malformed bookings)
        all_booking_ids = []
        for b in bookings:
            if isinstance(b, dict) and b.get("id"):
                all_booking_ids.append(b.get("id"))
        
        # Handle 0-1 bookings case
        if len(bookings) <= 1:
            logger.info(
                "No duplicates possible with 0-1 bookings",
                extra={
                    "booking_count": len(bookings),
                    "action": "deny",
                }
            )
            return DuplicateDetectionResult(
                has_duplicates=False,
                duplicate_count=len(bookings),
                used_booking_id=None,
                unused_booking_id=None,
                action="deny",
                explanation=f"Found {len(bookings)} booking(s). No duplicates detected.",
                all_booking_ids=all_booking_ids
            )
        
        # Find duplicate sets
        duplicate_sets = self._find_duplicates(bookings)
        
        # If no duplicates found
        if not duplicate_sets:
            logger.info(
                "No duplicate bookings found",
                extra={
                    "booking_count": len(bookings),
                    "duplicate_sets": 0,
                    "action": "deny",
                }
            )
            return DuplicateDetectionResult(
                has_duplicates=False,
                duplicate_count=len(bookings),
                used_booking_id=None,
                unused_booking_id=None,
                action="deny",
                explanation=f"Found {len(bookings)} bookings but no duplicates (different locations or times).",
                all_booking_ids=all_booking_ids
            )
        
        # Get the first (and should be only) duplicate set
        duplicates = duplicate_sets[0]
        duplicate_ids = [b.get("id") for b in duplicates]
        
        # Log duplicate booking IDs when detected (Requirement 11.3)
        logger.info(
            f"Detected {len(duplicates)} duplicate bookings",
            extra={
                "duplicate_count": len(duplicates),
                "duplicate_booking_ids": duplicate_ids,
                "all_booking_ids": all_booking_ids,
            }
        )
        
        # Handle 3+ duplicates - escalate
        if len(duplicates) >= 3:
            logger.warning(
                f"Found {len(duplicates)} duplicate bookings - escalating to human review",
                extra={
                    "duplicate_count": len(duplicates),
                    "duplicate_booking_ids": duplicate_ids,
                    "action": "escalate",
                }
            )
            return DuplicateDetectionResult(
                has_duplicates=True,
                duplicate_count=len(duplicates),
                used_booking_id=None,
                unused_booking_id=None,
                action="escalate",
                explanation=f"Found {len(duplicates)} duplicate bookings (IDs: {duplicate_ids}). Too complex for automatic processing - escalate to human review.",
                all_booking_ids=all_booking_ids
            )
        
        # Handle exactly 2 duplicates
        if len(duplicates) == 2:
            logger.info(
                "Found 2 duplicate bookings - identifying used vs unused",
                extra={
                    "duplicate_booking_ids": duplicate_ids,
                }
            )
            used_booking = self._identify_used_booking(duplicates)
            
            if used_booking:
                # Found a used booking - refund the other one
                unused_booking = duplicates[0] if duplicates[1].get("id") == used_booking.get("id") else duplicates[1]
                
                # Log which booking will be refunded and which will be kept (Requirement 11.3)
                logger.info(
                    f"Identified used and unused bookings",
                    extra={
                        "used_booking_id": used_booking.get("id"),
                        "used_booking_status": used_booking.get("status"),
                        "unused_booking_id": unused_booking.get("id"),
                        "unused_booking_status": unused_booking.get("status"),
                        "action": "refund_duplicate",
                        "will_refund": unused_booking.get("id"),
                        "will_keep": used_booking.get("id"),
                    }
                )
                
                return DuplicateDetectionResult(
                    has_duplicates=True,
                    duplicate_count=2,
                    used_booking_id=used_booking.get("id"),
                    unused_booking_id=unused_booking.get("id"),
                    action="refund_duplicate",
                    explanation=f"Found 2 duplicate bookings. Booking {used_booking.get('id')} was used (status: {used_booking.get('status')}), booking {unused_booking.get('id')} was unused (status: {unused_booking.get('status')}). Recommend refunding unused booking.",
                    all_booking_ids=all_booking_ids
                )
            else:
                # Could not determine which was used - escalate
                logger.warning(
                    "Could not determine which booking was used - escalating",
                    extra={
                        "duplicate_booking_ids": duplicate_ids,
                        "action": "escalate",
                    }
                )
                return DuplicateDetectionResult(
                    has_duplicates=True,
                    duplicate_count=2,
                    used_booking_id=None,
                    unused_booking_id=None,
                    action="escalate",
                    explanation=f"Found 2 duplicate bookings (IDs: {duplicate_ids}) but could not determine which was used. Escalate to human review.",
                    all_booking_ids=all_booking_ids
                )
        
        # Shouldn't reach here, but handle gracefully
        logger.warning(
            f"Unexpected duplicate count: {len(duplicates)}",
            extra={
                "duplicate_count": len(duplicates),
                "duplicate_booking_ids": duplicate_ids,
            }
        )
        return DuplicateDetectionResult(
            has_duplicates=False,
            duplicate_count=len(bookings),
            used_booking_id=None,
            unused_booking_id=None,
            action="deny",
            explanation="Unexpected analysis result. No action taken.",
            all_booking_ids=all_booking_ids
        )
    
    def _find_duplicates(self, bookings: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group bookings into duplicate sets based on location and time overlap.
        
        Two bookings are considered duplicates if:
        1. They have the same location_id
        2. Their time windows overlap by at least 50%
        
        Args:
            bookings: List of booking dictionaries
            
        Returns:
            List of duplicate sets (each set is a list of duplicate bookings)
        """
        duplicate_sets = []
        processed = set()
        
        for i, booking1 in enumerate(bookings):
            if i in processed:
                continue
            
            # Validate booking1 has required fields
            if not self._validate_booking_structure(booking1):
                logger.warning(f"Skipping malformed booking at index {i}")
                continue
            
            duplicate_set = [booking1]
            
            for j, booking2 in enumerate(bookings):
                if i == j or j in processed:
                    continue
                
                # Validate booking2 has required fields
                if not self._validate_booking_structure(booking2):
                    logger.warning(f"Skipping malformed booking at index {j}")
                    continue
                
                # Check if same location
                try:
                    loc1_id = booking1.get("location", {}).get("id")
                    loc2_id = booking2.get("location", {}).get("id")
                    
                    if loc1_id is None or loc2_id is None:
                        continue
                    
                    if loc1_id != loc2_id:
                        continue
                    
                    # Check time overlap
                    overlap_pct = self._calculate_time_overlap(booking1, booking2)
                    
                    if overlap_pct >= self.MIN_OVERLAP_PERCENTAGE:
                        duplicate_set.append(booking2)
                        processed.add(j)
                        
                except Exception as e:
                    # Log full error details with stack trace (Requirement 11.5)
                    logger.error(
                        f"Error comparing bookings {i} and {j}: {e}",
                        extra={
                            "booking1_id": booking1.get("id"),
                            "booking2_id": booking2.get("id"),
                            "error_type": type(e).__name__,
                        },
                        exc_info=True
                    )
                    continue
            
            # Only add if we found duplicates (more than 1 booking in set)
            if len(duplicate_set) > 1:
                duplicate_sets.append(duplicate_set)
                processed.add(i)
        
        return duplicate_sets
    
    def _validate_booking_structure(self, booking: Dict[str, Any]) -> bool:
        """
        Validate that a booking has the required structure for duplicate detection.
        
        Args:
            booking: Booking dictionary to validate
            
        Returns:
            True if booking has required fields, False otherwise
        """
        if not isinstance(booking, dict):
            return False
        
        # Check for required fields
        required_fields = ["id", "start_time", "end_time", "location"]
        for field in required_fields:
            if field not in booking:
                return False
        
        # Validate location structure
        location = booking.get("location")
        if not isinstance(location, dict) or "id" not in location:
            return False
        
        return True
    
    def _identify_used_booking(self, duplicates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Determine which booking was actually used based on status.
        
        Logic:
        - If one booking has a "used" status and the other has "unused" status, return the used one
        - If both have "used" status, return None (escalate)
        - If both have "unused" status, return the most recent one (keep most recent)
        
        Args:
            duplicates: List of duplicate bookings (should be exactly 2)
            
        Returns:
            The booking that was used, or None if cannot determine
        """
        if len(duplicates) != 2:
            logger.warning(f"Expected 2 duplicates, got {len(duplicates)}")
            return None
        
        booking1, booking2 = duplicates[0], duplicates[1]
        status1 = booking1.get("status", "").lower()
        status2 = booking2.get("status", "").lower()
        
        is_used1 = status1 in self.USED_STATUSES
        is_used2 = status2 in self.USED_STATUSES
        
        # One used, one unused - return the used one
        if is_used1 and not is_used2:
            logger.info(f"Booking {booking1.get('id')} is used, {booking2.get('id')} is unused")
            return booking1
        
        if is_used2 and not is_used1:
            logger.info(f"Booking {booking2.get('id')} is used, {booking1.get('id')} is unused")
            return booking2
        
        # Both used - cannot determine, escalate
        if is_used1 and is_used2:
            logger.warning("Both bookings appear to be used - cannot determine which to refund")
            return None
        
        # Both unused - keep the most recent one (by start_time)
        try:
            start1 = datetime.fromisoformat(booking1.get("start_time", "").replace("Z", "+00:00"))
            start2 = datetime.fromisoformat(booking2.get("start_time", "").replace("Z", "+00:00"))
            
            if start1 > start2:
                logger.info(f"Both unused - keeping more recent booking {booking1.get('id')}")
                return booking1
            else:
                logger.info(f"Both unused - keeping more recent booking {booking2.get('id')}")
                return booking2
        except (ValueError, AttributeError) as e:
            # Log full error details with stack trace (Requirement 11.5)
            logger.error(
                f"Error parsing start times: {e}",
                extra={
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            return None
    
    def _calculate_time_overlap(self, booking1: Dict[str, Any], booking2: Dict[str, Any]) -> float:
        """
        Calculate the percentage of time overlap between two bookings.
        
        Overlap percentage is calculated as:
        (overlap_duration / shorter_booking_duration) * 100
        
        Args:
            booking1: First booking dictionary
            booking2: Second booking dictionary
            
        Returns:
            Overlap percentage (0-100)
        """
        try:
            # Parse start and end times
            start1 = datetime.fromisoformat(booking1.get("start_time", "").replace("Z", "+00:00"))
            end1 = datetime.fromisoformat(booking1.get("end_time", "").replace("Z", "+00:00"))
            start2 = datetime.fromisoformat(booking2.get("start_time", "").replace("Z", "+00:00"))
            end2 = datetime.fromisoformat(booking2.get("end_time", "").replace("Z", "+00:00"))
            
            # Calculate overlap
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            # No overlap if overlap_end <= overlap_start
            if overlap_end <= overlap_start:
                return 0.0
            
            # Calculate durations in seconds
            overlap_duration = (overlap_end - overlap_start).total_seconds()
            duration1 = (end1 - start1).total_seconds()
            duration2 = (end2 - start2).total_seconds()
            
            # Use the shorter duration as the denominator
            shorter_duration = min(duration1, duration2)
            
            if shorter_duration <= 0:
                return 0.0
            
            overlap_pct = (overlap_duration / shorter_duration) * 100.0
            
            logger.debug(f"Time overlap: {overlap_pct:.1f}%")
            
            return overlap_pct
            
        except (ValueError, AttributeError) as e:
            # Log full error details with stack trace (Requirement 11.5)
            logger.error(
                f"Error calculating time overlap: {e}",
                extra={
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            return 0.0
