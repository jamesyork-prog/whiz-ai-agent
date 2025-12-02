"""
Tests for DuplicateBookingAnalyzer

Tests duplicate detection logic including:
- Location matching
- Time overlap calculation
- Edge cases (0-1 bookings, 3+ duplicates)
- Used vs unused identification
"""

import pytest
from datetime import datetime, timedelta
from app_tools.tools.duplicate_booking_analyzer import (
    DuplicateBookingAnalyzer,
    DuplicateDetectionResult
)


class TestDuplicateBookingAnalyzer:
    """Test suite for DuplicateBookingAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = DuplicateBookingAnalyzer()
    
    def test_no_bookings(self):
        """Test with 0 bookings - should deny"""
        result = self.analyzer.analyze([])
        
        assert result.has_duplicates is False
        assert result.duplicate_count == 0
        assert result.action == "deny"
        assert "0 booking" in result.explanation
    
    def test_single_booking(self):
        """Test with 1 booking - should deny"""
        booking = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed"
        }
        
        result = self.analyzer.analyze([booking])
        
        assert result.has_duplicates is False
        assert result.duplicate_count == 1
        assert result.action == "deny"
        assert "1 booking" in result.explanation
    
    def test_two_duplicates_same_location_full_overlap(self):
        """Test 2 bookings with same location and 100% time overlap"""
        booking1 = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed"
        }
        booking2 = {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "confirmed"
        }
        
        result = self.analyzer.analyze([booking1, booking2])
        
        assert result.has_duplicates is True
        assert result.duplicate_count == 2
        assert result.action == "refund_duplicate"
        assert result.used_booking_id == 12345
        assert result.unused_booking_id == 12346
    
    def test_two_bookings_different_locations(self):
        """Test 2 bookings at different locations - should deny"""
        booking1 = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed"
        }
        booking2 = {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 790, "name": "Airport Parking"},
            "status": "confirmed"
        }
        
        result = self.analyzer.analyze([booking1, booking2])
        
        assert result.has_duplicates is False
        assert result.action == "deny"
        assert "different locations" in result.explanation
    
    def test_two_bookings_no_time_overlap(self):
        """Test 2 bookings at same location but different times - should deny"""
        booking1 = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T12:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed"
        }
        booking2 = {
            "id": 12346,
            "start_time": "2024-01-15T14:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "confirmed"
        }
        
        result = self.analyzer.analyze([booking1, booking2])
        
        assert result.has_duplicates is False
        assert result.action == "deny"
    
    def test_three_or_more_duplicates_escalate(self):
        """Test 3+ duplicate bookings - should escalate"""
        booking1 = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed"
        }
        booking2 = {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "confirmed"
        }
        booking3 = {
            "id": 12347,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "pending"
        }
        
        result = self.analyzer.analyze([booking1, booking2, booking3])
        
        assert result.has_duplicates is True
        assert result.duplicate_count == 3
        assert result.action == "escalate"
        assert "Too complex" in result.explanation
    
    def test_calculate_time_overlap_full(self):
        """Test time overlap calculation with 100% overlap"""
        booking1 = {
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z"
        }
        booking2 = {
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z"
        }
        
        overlap = self.analyzer._calculate_time_overlap(booking1, booking2)
        
        assert overlap == 100.0
    
    def test_calculate_time_overlap_partial(self):
        """Test time overlap calculation with 50% overlap"""
        booking1 = {
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T14:00:00Z"  # 4 hours
        }
        booking2 = {
            "start_time": "2024-01-15T12:00:00Z",  # 2 hour overlap
            "end_time": "2024-01-15T16:00:00Z"  # 4 hours
        }
        
        overlap = self.analyzer._calculate_time_overlap(booking1, booking2)
        
        # 2 hours overlap / 4 hours shorter duration = 50%
        assert overlap == 50.0
    
    def test_calculate_time_overlap_none(self):
        """Test time overlap calculation with no overlap"""
        booking1 = {
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T12:00:00Z"
        }
        booking2 = {
            "start_time": "2024-01-15T14:00:00Z",
            "end_time": "2024-01-15T16:00:00Z"
        }
        
        overlap = self.analyzer._calculate_time_overlap(booking1, booking2)
        
        assert overlap == 0.0
    
    def test_identify_used_booking_one_used_one_unused(self):
        """Test identifying used booking when one is used and one is unused"""
        booking1 = {
            "id": 12345,
            "status": "completed",
            "start_time": "2024-01-15T10:00:00Z"
        }
        booking2 = {
            "id": 12346,
            "status": "confirmed",
            "start_time": "2024-01-15T10:00:00Z"
        }
        
        used = self.analyzer._identify_used_booking([booking1, booking2])
        
        assert used is not None
        assert used["id"] == 12345
    
    def test_identify_used_booking_both_used_escalate(self):
        """Test that both used bookings returns None (escalate)"""
        booking1 = {
            "id": 12345,
            "status": "completed",
            "start_time": "2024-01-15T10:00:00Z"
        }
        booking2 = {
            "id": 12346,
            "status": "checked_out",
            "start_time": "2024-01-15T10:00:00Z"
        }
        
        used = self.analyzer._identify_used_booking([booking1, booking2])
        
        assert used is None
    
    def test_identify_used_booking_both_unused_keep_recent(self):
        """Test that both unused bookings keeps the most recent one"""
        booking1 = {
            "id": 12345,
            "status": "confirmed",
            "start_time": "2024-01-15T10:00:00Z"
        }
        booking2 = {
            "id": 12346,
            "status": "pending",
            "start_time": "2024-01-15T12:00:00Z"  # More recent
        }
        
        used = self.analyzer._identify_used_booking([booking1, booking2])
        
        assert used is not None
        assert used["id"] == 12346  # More recent one
    
    def test_find_duplicates_groups_correctly(self):
        """Test that _find_duplicates correctly groups duplicate bookings"""
        booking1 = {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789}
        }
        booking2 = {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789}
        }
        booking3 = {
            "id": 12347,
            "start_time": "2024-01-16T10:00:00Z",
            "end_time": "2024-01-16T18:00:00Z",
            "location": {"id": 790}  # Different location
        }
        
        duplicate_sets = self.analyzer._find_duplicates([booking1, booking2, booking3])
        
        assert len(duplicate_sets) == 1
        assert len(duplicate_sets[0]) == 2
        assert booking1 in duplicate_sets[0]
        assert booking2 in duplicate_sets[0]


    def test_malformed_booking_objects(self):
        """Test handling of malformed booking objects."""
        bookings = [
            {
                "id": 12345,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"id": 789, "name": "Downtown Garage"},
                "status": "completed",
            },
            "not a dict",  # Invalid booking
            {
                "id": 12346,
                # Missing required fields
                "status": "confirmed",
            },
            {
                "id": 12347,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": "not a dict",  # Invalid location
                "status": "confirmed",
            },
        ]
        
        analyzer = DuplicateBookingAnalyzer()
        result = analyzer.analyze(bookings)
        
        # Should handle malformed data gracefully and return deny (no valid duplicates)
        assert result.action == "deny"
        assert not result.has_duplicates
    
    def test_missing_location_id(self):
        """Test handling bookings with missing location ID."""
        bookings = [
            {
                "id": 12345,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"name": "Downtown Garage"},  # Missing id
                "status": "completed",
            },
            {
                "id": 12346,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"name": "Downtown Garage"},  # Missing id
                "status": "confirmed",
            },
        ]
        
        analyzer = DuplicateBookingAnalyzer()
        result = analyzer.analyze(bookings)
        
        # Should not detect duplicates without location IDs
        assert not result.has_duplicates
        assert result.action == "deny"
    
    def test_invalid_time_format(self):
        """Test handling bookings with invalid time formats."""
        bookings = [
            {
                "id": 12345,
                "start_time": "invalid date",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"id": 789, "name": "Downtown Garage"},
                "status": "completed",
            },
            {
                "id": 12346,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "also invalid",
                "location": {"id": 789, "name": "Downtown Garage"},
                "status": "confirmed",
            },
        ]
        
        analyzer = DuplicateBookingAnalyzer()
        result = analyzer.analyze(bookings)
        
        # Should handle invalid dates gracefully (time overlap calculation returns 0)
        assert not result.has_duplicates
        assert result.action == "deny"
