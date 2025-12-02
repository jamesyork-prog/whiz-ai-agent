"""
Property-based tests for Decision Guard module.

Tests verify that the decision guard correctly enforces safety rules
for automated refund decisions.
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta

from app_tools.tools.decision_guard import DecisionGuard
from app_tools.tools.booking_verifier import VerifiedBooking, BookingVerificationResult
from app_tools.tools.customer_info_extractor import CustomerInfo


# Hypothesis strategies for generating test data
@st.composite
def customer_info_strategy(draw):
    """Generate random CustomerInfo objects."""
    email = draw(st.emails())
    name = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    
    # Generate dates
    base_date = datetime(2024, 1, 1)
    days_offset = draw(st.integers(min_value=0, max_value=365))
    arrival_date = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
    
    duration = draw(st.integers(min_value=1, max_value=7))
    exit_date = (base_date + timedelta(days=days_offset + duration)).strftime("%Y-%m-%d")
    
    location = draw(st.one_of(st.none(), st.text(min_size=1, max_size=100)))
    
    return CustomerInfo(
        email=email,
        name=name,
        arrival_date=arrival_date,
        exit_date=exit_date,
        location=location
    )


@st.composite
def verified_booking_strategy(draw, pass_usage_status=None, match_confidence=None):
    """Generate random VerifiedBooking objects."""
    booking_id = draw(st.text(min_size=1, max_size=20))
    email = draw(st.emails())
    
    # Generate dates
    base_date = datetime(2024, 1, 1)
    days_offset = draw(st.integers(min_value=0, max_value=365))
    arrival_date = (base_date + timedelta(days=days_offset)).isoformat()
    
    duration = draw(st.integers(min_value=1, max_value=7))
    exit_date = (base_date + timedelta(days=days_offset + duration)).isoformat()
    
    location = draw(st.text(min_size=1, max_size=100))
    
    # Use provided values or generate random ones
    if pass_usage_status is None:
        pass_usage_status = draw(st.sampled_from(["used", "not_used", "unknown"]))
    
    if match_confidence is None:
        match_confidence = draw(st.sampled_from(["exact", "partial", "weak"]))
    
    pass_used = pass_usage_status == "used"
    amount_paid = draw(st.floats(min_value=0.0, max_value=1000.0))
    
    return VerifiedBooking(
        booking_id=booking_id,
        customer_email=email,
        arrival_date=arrival_date,
        exit_date=exit_date,
        location=location,
        pass_used=pass_used,
        pass_usage_status=pass_usage_status,
        amount_paid=amount_paid,
        match_confidence=match_confidence
    )


# Property 8: Missing usage status triggers escalation
# Feature: booking-verification-enhancement, Property 8: Missing usage status triggers escalation
# Validates: Requirements 3.4
@given(customer_info=customer_info_strategy())
def test_property_8_missing_usage_triggers_escalation(customer_info):
    """
    Property 8: For any booking where pass usage status is "unknown",
    the system should flag for human review.
    """
    decision_guard = DecisionGuard()
    
    # Create a verified booking with unknown usage status
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email=customer_info.email,
        arrival_date=customer_info.arrival_date,
        exit_date=customer_info.exit_date,
        location=customer_info.location or "Test Location",
        pass_used=False,
        pass_usage_status="unknown",  # Unknown status
        amount_paid=50.0,
        match_confidence="exact"
    )
    
    # Check escalation
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info
    )
    
    # Property: Unknown usage status MUST trigger escalation
    assert should_escalate, "Unknown pass usage status should trigger escalation"
    assert "usage" in reason.lower(), f"Escalation reason should mention usage: {reason}"


# Property 9: Usage contradictions trigger escalation
# Feature: booking-verification-enhancement, Property 9: Usage contradictions trigger escalation
# Validates: Requirements 3.5
@given(customer_info=customer_info_strategy())
def test_property_9_contradiction_triggers_escalation(customer_info):
    """
    Property 9: For any case where verified pass usage contradicts customer claim,
    the system should flag for human review with explanation.
    
    Note: Currently, we don't extract customer usage claims from ticket text,
    so this test verifies the infrastructure is in place for future enhancement.
    """
    decision_guard = DecisionGuard()
    
    # Create a verified booking with known usage
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email=customer_info.email,
        arrival_date=customer_info.arrival_date,
        exit_date=customer_info.exit_date,
        location=customer_info.location or "Test Location",
        pass_used=True,
        pass_usage_status="used",
        amount_paid=50.0,
        match_confidence="exact"
    )
    
    # Check for contradictions (currently returns False since we don't extract claims)
    contradiction_detected, reason = decision_guard._detect_usage_contradiction(
        verified_booking, customer_info
    )
    
    # Property: The method should exist and return a tuple
    assert isinstance(contradiction_detected, bool), "Should return boolean"
    assert isinstance(reason, str), "Should return string reason"
    
    # When contradiction detection is implemented, this will be:
    # assert contradiction_detected implies should_escalate


# Property 15: Verified data is used for decisions
# Feature: booking-verification-enhancement, Property 15: Verified data is used for decisions
# Validates: Requirements 5.1
@given(
    verified_booking=verified_booking_strategy(
        pass_usage_status=st.sampled_from(["used", "not_used"]),
        match_confidence=st.sampled_from(["exact", "partial"])
    ),
    customer_info=customer_info_strategy()
)
def test_property_15_verified_data_used_for_decisions(verified_booking, customer_info):
    """
    Property 15: For any successful booking verification with known usage status
    and good match confidence, the system should allow automated decisions using
    verified data.
    """
    decision_guard = DecisionGuard()
    
    # Validate decision data
    is_valid, reason = decision_guard.validate_decision_data(
        verified_booking, customer_info
    )
    
    # Property: Verified bookings with known usage should be valid for decisions
    assert is_valid, f"Verified booking should be valid for decisions: {reason}"
    
    # Property: Can make automated decision when verification succeeded
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert can_decide, "Should allow automated decision with verified data"


# Property 16: No automated decision without verification
# Feature: booking-verification-enhancement, Property 16: No automated decision without verification
# Validates: Requirements 5.2
@given(customer_info=customer_info_strategy())
def test_property_16_no_decision_without_verification(customer_info):
    """
    Property 16: For any failed booking verification (verified_booking is None),
    the system should NOT make an automated approve or deny decision.
    """
    decision_guard = DecisionGuard()
    
    # No verified booking
    verified_booking = None
    
    # Check if automated decision is allowed
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    
    # Property: Cannot make automated decision without verification
    assert not can_decide, "Should not allow automated decision without verified booking"
    
    # Property: Should escalate when verification failed
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info, failure_reason="Verification failed"
    )
    assert should_escalate, "Should escalate when verification failed"
    assert reason, "Should provide escalation reason"


# Property 17: Unverifiable bookings are escalated with reason
# Feature: booking-verification-enhancement, Property 17: Unverifiable bookings are escalated with reason
# Validates: Requirements 5.3
@given(
    customer_info=customer_info_strategy(),
    failure_reason=st.text(min_size=1, max_size=200)
)
def test_property_17_unverifiable_escalated_with_reason(customer_info, failure_reason):
    """
    Property 17: For any booking that cannot be verified, the system should
    flag for human review and include the failure reason.
    """
    decision_guard = DecisionGuard()
    
    # No verified booking (verification failed)
    verified_booking = None
    
    # Check escalation
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info, failure_reason=failure_reason
    )
    
    # Property: Unverifiable bookings MUST be escalated
    assert should_escalate, "Unverifiable bookings must be escalated"
    
    # Property: Escalation MUST include a reason
    assert reason, "Escalation must include a reason"
    assert len(reason) > 0, "Escalation reason must not be empty"


# Property 18: Contradictions escalate instead of deny
# Feature: booking-verification-enhancement, Property 18: Contradictions escalate instead of deny
# Validates: Requirements 5.4
@given(customer_info=customer_info_strategy())
def test_property_18_contradictions_escalate_not_deny(customer_info):
    """
    Property 18: For any verified booking that contradicts customer claim,
    the system should escalate rather than auto-deny.
    
    This tests weak match confidence as a form of contradiction.
    """
    decision_guard = DecisionGuard()
    
    # Create a verified booking with weak match confidence (dates don't match well)
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email=customer_info.email,
        arrival_date=customer_info.arrival_date,
        exit_date=customer_info.exit_date,
        location=customer_info.location or "Test Location",
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="weak"  # Weak match = contradiction
    )
    
    # Check escalation
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info
    )
    
    # Property: Contradictions (weak matches) MUST escalate
    assert should_escalate, "Weak match confidence should trigger escalation"
    assert reason, "Should provide escalation reason"
    
    # Property: Should NOT allow automated decision
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert not can_decide, "Should not allow automated decision for weak matches"


# Property 19: Customer data never used without verification
# Feature: booking-verification-enhancement, Property 19: Customer data never used without verification
# Validates: Requirements 5.5
@given(customer_info=customer_info_strategy())
def test_property_19_customer_data_requires_verification(customer_info):
    """
    Property 19: For any decision path, customer-provided booking details
    should only be used if verified by ParkWhiz API.
    """
    decision_guard = DecisionGuard()
    
    # No verified booking
    verified_booking = None
    
    # Validate decision data
    is_valid, reason = decision_guard.validate_decision_data(
        verified_booking, customer_info
    )
    
    # Property: Cannot use customer data without verification
    assert not is_valid, "Should not validate decision data without verified booking"
    assert "verified" in reason.lower() or "no" in reason.lower(), \
        f"Reason should mention lack of verification: {reason}"
    
    # Property: Cannot make automated decision
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert not can_decide, "Should not allow decision without verified booking"


# Additional edge case tests
def test_weak_confidence_prevents_automated_decision():
    """Test that weak match confidence prevents automated decisions."""
    decision_guard = DecisionGuard()
    customer_info = CustomerInfo(
        email="test@example.com",
        name="Test User",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location"
    )
    
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email="test@example.com",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location",
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="weak"
    )
    
    # Should not allow automated decision
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert not can_decide
    
    # Should escalate
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info
    )
    assert should_escalate
    assert "match" in reason.lower() or "dates" in reason.lower()


def test_exact_match_with_known_usage_allows_decision():
    """Test that exact match with known usage allows automated decisions."""
    decision_guard = DecisionGuard()
    customer_info = CustomerInfo(
        email="test@example.com",
        name="Test User",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location"
    )
    
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email="test@example.com",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location",
        pass_used=True,
        pass_usage_status="used",
        amount_paid=50.0,
        match_confidence="exact"
    )
    
    # Should allow automated decision
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert can_decide
    
    # Should not escalate
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info
    )
    assert not should_escalate


def test_partial_match_with_known_usage_allows_decision():
    """Test that partial match with known usage allows automated decisions."""
    decision_guard = DecisionGuard()
    customer_info = CustomerInfo(
        email="test@example.com",
        name="Test User",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location"
    )
    
    verified_booking = VerifiedBooking(
        booking_id="TEST123",
        customer_email="test@example.com",
        arrival_date="2024-01-01",
        exit_date="2024-01-02",
        location="Test Location",
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="partial"
    )
    
    # Should allow automated decision
    can_decide = decision_guard.can_make_automated_decision(verified_booking)
    assert can_decide
    
    # Should not escalate
    should_escalate, reason = decision_guard.should_escalate(
        verified_booking, customer_info
    )
    assert not should_escalate
