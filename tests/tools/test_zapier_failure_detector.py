"""
Tests for ZapierFailureDetector component.

Tests cover:
- Property-based tests for Zapier failure detection consistency
- Property-based tests for invalid booking ID detection
- Unit tests for specific edge cases
- Comprehensive failure detection
"""

import pytest
from hypothesis import given, strategies as st, settings
from app_tools.tools.zapier_failure_detector import ZapierFailureDetector


@pytest.fixture
def detector():
    """Create ZapierFailureDetector instance."""
    return ZapierFailureDetector()


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================

# Feature: booking-verification-enhancement, Property 1: Zapier failure detection is consistent
# Validates: Requirements 1.1
@given(
    prefix=st.text(min_size=0, max_size=100),
    suffix=st.text(min_size=0, max_size=100),
    case_variant=st.sampled_from([
        "Booking information not found for provided Booking Number",
        "BOOKING INFORMATION NOT FOUND FOR PROVIDED BOOKING NUMBER",
        "booking information not found for provided booking number",
        "BoOkInG iNfOrMaTiOn NoT fOuNd FoR pRoViDeD bOoKiNg NuMbEr"
    ])
)
@settings(max_examples=100)
def test_property_zapier_failure_detection_consistent(prefix, suffix, case_variant):
    """
    Property 1: Zapier failure detection is consistent.
    
    For any ticket description containing "Booking information not found for provided Booking Number"
    (in any case variation), the detector should always identify it as a Zapier failure case.
    
    This property tests that:
    - Detection works regardless of surrounding text
    - Detection is case-insensitive
    - Detection is consistent across all variations
    """
    # Create detector instance
    detector = ZapierFailureDetector()
    
    # Construct ticket with failure message embedded
    ticket_description = f"{prefix}{case_variant}{suffix}"
    
    # Property: Should always detect Zapier failure
    result = detector.is_zapier_failure(ticket_description)
    
    assert result is True, (
        f"Failed to detect Zapier failure message in ticket. "
        f"Prefix: '{prefix[:20]}...', Suffix: '{suffix[:20]}...', "
        f"Case variant: '{case_variant}'"
    )


# Feature: booking-verification-enhancement, Property 2: Invalid booking IDs are detected
# Validates: Requirements 1.5
@given(
    invalid_id=st.sampled_from([
        # All zeros patterns
        "0", "00", "000", "0000", "00000",
        # N/A variants
        "N/A", "NA", "n/a", "na", "N/a", "n/A",
        # Placeholder values
        "none", "None", "NONE", "NoNe",
        "null", "Null", "NULL", "NuLl",
        "undefined", "Undefined", "UNDEFINED", "UnDeFiNeD",
        # Empty/whitespace
        "", "   ", "\t", "\n", "  \t\n  ",
        # None value (will be passed as None, not string)
    ])
)
@settings(max_examples=100)
def test_property_invalid_booking_ids_detected(invalid_id):
    """
    Property 2: Invalid booking IDs are detected.
    
    For any booking ID matching invalid patterns (0000, N/A, empty, null, etc.),
    the system should treat it as a Zapier failure case.
    
    This property tests that:
    - All zero patterns are detected
    - N/A variants are detected (case insensitive)
    - Placeholder values are detected (case insensitive)
    - Empty and whitespace-only strings are detected
    """
    # Create detector instance
    detector = ZapierFailureDetector()
    
    # Handle None case separately
    if invalid_id == "":
        # Test both empty string and None
        assert detector.is_invalid_booking_id("") is True, "Empty string should be invalid"
        assert detector.is_invalid_booking_id(None) is True, "None should be invalid"
    else:
        result = detector.is_invalid_booking_id(invalid_id)
        
        assert result is True, (
            f"Failed to detect invalid booking ID: '{invalid_id}'. "
            f"This pattern should be recognized as invalid."
        )


# Additional property test: Valid booking IDs should NOT be detected as invalid
@given(
    valid_id=st.text(
        alphabet=st.characters(blacklist_categories=('Cs', 'Cc')),
        min_size=1,
        max_size=50
    ).filter(
        lambda x: (
            x.strip() != "" and  # Not empty/whitespace
            (not x.strip().isdigit() or int(x.strip()) > 0) and  # Not all zeros
            x.strip().upper() not in ["N/A", "NA", "NONE", "NULL", "UNDEFINED"]  # Not placeholders
        )
    )
)
@settings(max_examples=100)
def test_property_valid_booking_ids_not_flagged(valid_id):
    """
    Property: Valid booking IDs should not be flagged as invalid.
    
    For any booking ID that doesn't match invalid patterns, the system should
    recognize it as valid.
    
    This ensures we don't have false positives.
    """
    # Create detector instance
    detector = ZapierFailureDetector()
    
    result = detector.is_invalid_booking_id(valid_id)
    
    # Valid IDs should NOT be detected as invalid
    assert result is False, (
        f"Valid booking ID '{valid_id}' was incorrectly flagged as invalid"
    )


# ============================================================================
# UNIT TESTS - Specific Examples and Edge Cases
# ============================================================================

def test_zapier_failure_exact_message(detector):
    """Test detection of exact Zapier failure message."""
    ticket = "Booking information not found for provided Booking Number"
    assert detector.is_zapier_failure(ticket) is True


def test_zapier_failure_message_in_context(detector):
    """Test detection when failure message is embedded in larger text."""
    ticket = """
    Customer requested refund for booking.
    
    Booking information not found for provided Booking Number
    
    Please review manually.
    """
    assert detector.is_zapier_failure(ticket) is True


def test_zapier_failure_case_insensitive(detector):
    """Test that detection is case insensitive."""
    tickets = [
        "BOOKING INFORMATION NOT FOUND FOR PROVIDED BOOKING NUMBER",
        "booking information not found for provided booking number",
        "Booking Information Not Found For Provided Booking Number"
    ]
    
    for ticket in tickets:
        assert detector.is_zapier_failure(ticket) is True


def test_no_zapier_failure(detector):
    """Test that normal tickets are not flagged."""
    ticket = "Customer wants refund for booking PW-123456789"
    assert detector.is_zapier_failure(ticket) is False


def test_empty_ticket_description(detector):
    """Test handling of empty ticket description."""
    assert detector.is_zapier_failure("") is False
    assert detector.is_zapier_failure(None) is False


def test_invalid_booking_id_all_zeros(detector):
    """Test detection of all-zero booking IDs."""
    invalid_ids = ["0", "00", "000", "0000", "00000000"]
    
    for booking_id in invalid_ids:
        assert detector.is_invalid_booking_id(booking_id) is True


def test_invalid_booking_id_na_variants(detector):
    """Test detection of N/A variants."""
    invalid_ids = ["N/A", "NA", "n/a", "na", "N/a", "n/A"]
    
    for booking_id in invalid_ids:
        assert detector.is_invalid_booking_id(booking_id) is True


def test_invalid_booking_id_placeholders(detector):
    """Test detection of placeholder values."""
    invalid_ids = [
        "none", "None", "NONE",
        "null", "Null", "NULL",
        "undefined", "Undefined", "UNDEFINED"
    ]
    
    for booking_id in invalid_ids:
        assert detector.is_invalid_booking_id(booking_id) is True


def test_invalid_booking_id_empty_whitespace(detector):
    """Test detection of empty and whitespace-only strings."""
    invalid_ids = ["", "   ", "\t", "\n", "  \t\n  "]
    
    for booking_id in invalid_ids:
        assert detector.is_invalid_booking_id(booking_id) is True


def test_invalid_booking_id_none(detector):
    """Test that None is considered invalid."""
    assert detector.is_invalid_booking_id(None) is True


def test_valid_booking_ids(detector):
    """Test that valid booking IDs are not flagged."""
    valid_ids = [
        "PW-123456789",
        "509266779",
        "ABC-123",
        "12345",
        "booking-001",
        "1"  # Single non-zero digit
    ]
    
    for booking_id in valid_ids:
        assert detector.is_invalid_booking_id(booking_id) is False


def test_valid_booking_id_with_zeros(detector):
    """Test that booking IDs containing zeros but not all zeros are valid."""
    valid_ids = [
        "PW-1000",
        "20250101",
        "100",
        "1001"
    ]
    
    for booking_id in valid_ids:
        assert detector.is_invalid_booking_id(booking_id) is False


def test_detect_failure_comprehensive_zapier_message(detector):
    """Test comprehensive failure detection with Zapier message."""
    ticket = "Booking information not found for provided Booking Number"
    result = detector.detect_failure(ticket)
    
    assert result["is_failure"] is True
    assert result["zapier_message_failure"] is True
    assert result["invalid_booking_id"] is False
    assert "Zapier failure message detected" in result["reason"]


def test_detect_failure_comprehensive_invalid_id(detector):
    """Test comprehensive failure detection with invalid booking ID."""
    ticket = "Customer wants refund"
    result = detector.detect_failure(ticket, booking_id="0000")
    
    assert result["is_failure"] is True
    assert result["zapier_message_failure"] is False
    assert result["invalid_booking_id"] is True
    assert "Invalid booking ID" in result["reason"]


def test_detect_failure_comprehensive_both(detector):
    """Test comprehensive failure detection with both failures."""
    ticket = "Booking information not found for provided Booking Number"
    result = detector.detect_failure(ticket, booking_id="N/A")
    
    assert result["is_failure"] is True
    assert result["zapier_message_failure"] is True
    assert result["invalid_booking_id"] is True
    assert "Zapier failure message detected" in result["reason"]
    assert "Invalid booking ID" in result["reason"]


def test_detect_failure_comprehensive_no_failure(detector):
    """Test comprehensive failure detection with no failures."""
    ticket = "Customer wants refund for booking"
    result = detector.detect_failure(ticket, booking_id="PW-123456789")
    
    assert result["is_failure"] is False
    assert result["zapier_message_failure"] is False
    assert result["invalid_booking_id"] is False
    assert result["reason"] == "No failure detected"


def test_detect_failure_no_booking_id_provided(detector):
    """Test comprehensive failure detection when no booking ID provided."""
    ticket = "Customer wants refund"
    result = detector.detect_failure(ticket)
    
    assert result["is_failure"] is False
    assert result["zapier_message_failure"] is False
    assert result["invalid_booking_id"] is False


def test_booking_id_with_leading_trailing_whitespace(detector):
    """Test that whitespace is trimmed before validation."""
    # Valid ID with whitespace should be valid
    assert detector.is_invalid_booking_id("  PW-123  ") is False
    
    # Invalid ID with whitespace should still be invalid
    assert detector.is_invalid_booking_id("  0000  ") is True
    assert detector.is_invalid_booking_id("  N/A  ") is True


def test_partial_zapier_message_not_detected(detector):
    """Test that partial matches of the failure message are not detected."""
    tickets = [
        "Booking information not found",
        "Information not found for provided Booking Number",
        "Booking not found"
    ]
    
    for ticket in tickets:
        assert detector.is_zapier_failure(ticket) is False


def test_similar_but_different_message_not_detected(detector):
    """Test that similar but different messages are not detected."""
    tickets = [
        "Booking details not found for provided Booking Number",
        "Booking information unavailable for provided Booking Number",
        "Booking information not found for Booking Number"
    ]
    
    for ticket in tickets:
        assert detector.is_zapier_failure(ticket) is False
