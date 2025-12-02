"""
Property-based tests for verification note generator.

Tests verify that notes contain required information and are properly formatted.
"""

import pytest
from hypothesis import given, strategies as st, settings
from app_tools.tools.verification_note_generator import VerificationNoteGenerator
from app_tools.tools.booking_verifier import VerifiedBooking
from app_tools.tools.customer_info_extractor import CustomerInfo


# Strategies for generating test data
@st.composite
def verified_booking_strategy(draw):
    """Generate random VerifiedBooking instances."""
    booking_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    email = draw(st.emails())
    arrival_date = draw(st.dates().map(lambda d: d.isoformat()))
    exit_date = draw(st.dates().map(lambda d: d.isoformat()))
    location = draw(st.text(min_size=1, max_size=50))
    pass_used = draw(st.booleans())
    pass_usage_status = draw(st.sampled_from(["used", "not_used", "unknown"]))
    amount_paid = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    match_confidence = draw(st.sampled_from(["exact", "partial", "weak"]))
    
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


@st.composite
def customer_info_strategy(draw):
    """Generate random CustomerInfo instances."""
    email = draw(st.emails())
    name = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    arrival_date = draw(st.dates().map(lambda d: d.isoformat()))
    exit_date = draw(st.dates().map(lambda d: d.isoformat()))
    location = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    
    return CustomerInfo(
        email=email,
        name=name,
        arrival_date=arrival_date,
        exit_date=exit_date,
        location=location
    )


class TestVerificationNoteGenerator:
    """Test suite for VerificationNoteGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = VerificationNoteGenerator()
    
    # Feature: booking-verification-enhancement, Property 10: Verified booking ID appears in note
    # **Validates: Requirements 4.1**
    @given(
        verified_booking=verified_booking_strategy(),
        customer_info=customer_info_strategy()
    )
    @settings(max_examples=100)
    def test_property_booking_id_in_note(self, verified_booking, customer_info):
        """
        Property 10: Verified booking ID appears in note.
        
        For any verified booking, the generated note should contain the booking ID.
        """
        # Generate note
        note = self.generator.generate_verified_note(verified_booking, customer_info)
        
        # Verify booking ID appears in the note
        assert verified_booking.booking_id in note, \
            f"Booking ID '{verified_booking.booking_id}' not found in note"
    
    # Feature: booking-verification-enhancement, Property 11: Pass usage appears in note
    # **Validates: Requirements 4.2**
    @given(
        verified_booking=verified_booking_strategy(),
        customer_info=customer_info_strategy()
    )
    @settings(max_examples=100)
    def test_property_pass_usage_in_note(self, verified_booking, customer_info):
        """
        Property 11: Pass usage appears in note.
        
        For any verified booking, the generated note should include pass usage status.
        """
        # Generate note
        note = self.generator.generate_verified_note(verified_booking, customer_info)
        
        # Verify pass usage status appears in the note
        assert verified_booking.pass_usage_status in note, \
            f"Pass usage status '{verified_booking.pass_usage_status}' not found in note"
        
        # Also verify the visual indicator (USED or NOT USED)
        if verified_booking.pass_used:
            assert "USED" in note, "Pass used indicator 'USED' not found in note"
        else:
            assert "NOT USED" in note, "Pass not used indicator 'NOT USED' not found in note"
    
    # Feature: booking-verification-enhancement, Property 12: Discrepancies are highlighted
    # **Validates: Requirements 4.3**
    @given(
        verified_booking=verified_booking_strategy(),
        customer_info=customer_info_strategy()
    )
    @settings(max_examples=100)
    def test_property_discrepancies_highlighted(self, verified_booking, customer_info):
        """
        Property 12: Discrepancies are highlighted.
        
        For any differences between verified and customer-provided data,
        the note should highlight those discrepancies.
        """
        # Generate note
        note = self.generator.generate_verified_note(verified_booking, customer_info)
        
        # Find discrepancies
        discrepancies = self.generator.highlight_discrepancies(verified_booking, customer_info)
        
        # If there are discrepancies, they should appear in the note
        if discrepancies:
            # Check that discrepancies section exists
            assert "Discrepancies" in note or "discrepancies" in note, \
                "Discrepancies section not found in note when discrepancies exist"
            
            # Check that each discrepancy appears in the note
            for discrepancy in discrepancies:
                # The note may escape HTML, so check for key parts of the discrepancy
                # Extract key terms from discrepancy message
                if "mismatch" in discrepancy.lower():
                    assert "mismatch" in note.lower(), \
                        f"Discrepancy '{discrepancy}' not properly highlighted in note"
    
    # Feature: booking-verification-enhancement, Property 13: Notes are properly formatted
    # **Validates: Requirements 4.4**
    @given(
        verified_booking=verified_booking_strategy(),
        customer_info=customer_info_strategy()
    )
    @settings(max_examples=100)
    def test_property_note_formatting(self, verified_booking, customer_info):
        """
        Property 13: Notes are properly formatted.
        
        For any generated note, it should contain clear labels for each field.
        """
        # Generate note
        note = self.generator.generate_verified_note(verified_booking, customer_info)
        
        # Verify required labels are present
        required_labels = [
            "Booking ID",
            "Pass Usage",
            "Customer Email",
            "Arrival Date",
            "Exit Date",
            "Amount Paid",
            "Match Confidence"
        ]
        
        for label in required_labels:
            assert label in note, f"Required label '{label}' not found in note"
        
        # Verify HTML structure
        assert "<div" in note, "Note should be HTML formatted with div tags"
        assert "</div>" in note, "Note should have closing div tags"
        
        # Verify styling is present
        assert "style=" in note, "Note should include inline CSS styling"
    
    # Feature: booking-verification-enhancement, Property 14: Multiple bookings are all listed
    # **Validates: Requirements 4.5**
    @given(
        bookings=st.lists(verified_booking_strategy(), min_size=2, max_size=5),
        customer_info=customer_info_strategy()
    )
    @settings(max_examples=100)
    def test_property_multiple_bookings_listed(self, bookings, customer_info):
        """
        Property 14: Multiple bookings are all listed.
        
        For any case where multiple bookings are found,
        the note should list all matching booking IDs.
        """
        # Generate multiple bookings note
        note = self.generator.generate_multiple_bookings_note(bookings, customer_info)
        
        # Verify all booking IDs appear in the note
        for booking in bookings:
            assert booking.booking_id in note, \
                f"Booking ID '{booking.booking_id}' not found in multiple bookings note"
        
        # Verify the count is mentioned
        assert str(len(bookings)) in note, \
            f"Booking count '{len(bookings)}' not found in note"
        
        # Verify it's clearly marked as multiple bookings
        assert "Multiple" in note or "multiple" in note, \
            "Note should indicate multiple bookings were found"


class TestVerificationFailedNote:
    """Test suite for verification failed notes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = VerificationNoteGenerator()
    
    @given(
        customer_info=customer_info_strategy(),
        failure_reason=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_failed_note_contains_reason(self, customer_info, failure_reason):
        """
        Verify that failed verification notes contain the failure reason.
        """
        from html import escape
        
        # Generate failed note
        note = self.generator.generate_verification_failed_note(customer_info, failure_reason)
        
        # Verify failure reason appears in note (may be HTML escaped)
        assert failure_reason in note or escape(failure_reason) in note, \
            f"Failure reason '{failure_reason}' (or escaped version) not found in note"
        
        # Verify it's marked as failed
        assert "Failed" in note or "failed" in note, \
            "Note should indicate verification failed"
    
    @given(customer_info=customer_info_strategy())
    @settings(max_examples=100)
    def test_failed_note_contains_customer_info(self, customer_info):
        """
        Verify that failed verification notes contain customer information.
        """
        from html import escape
        
        failure_reason = "Test failure"
        
        # Generate failed note
        note = self.generator.generate_verification_failed_note(customer_info, failure_reason)
        
        # Verify customer email appears if present (may be HTML escaped)
        if customer_info.email:
            assert customer_info.email in note or escape(customer_info.email) in note, \
                f"Customer email '{customer_info.email}' (or escaped version) not found in failed note"


class TestDiscrepancyHighlighting:
    """Test suite for discrepancy highlighting logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = VerificationNoteGenerator()
    
    def test_no_discrepancies_when_dates_match(self):
        """Verify no discrepancies when dates match exactly."""
        verified = VerifiedBooking(
            booking_id="12345",
            customer_email="test@example.com",
            arrival_date="2025-01-15",
            exit_date="2025-01-17",
            location="Test Location",
            pass_used=True,
            pass_usage_status="used",
            amount_paid=50.0,
            match_confidence="exact"
        )
        
        customer = CustomerInfo(
            email="test@example.com",
            arrival_date="2025-01-15",
            exit_date="2025-01-17",
            location="Test Location"
        )
        
        discrepancies = self.generator.highlight_discrepancies(verified, customer)
        
        assert len(discrepancies) == 0, "Should have no discrepancies when dates match"
    
    def test_discrepancy_when_arrival_differs(self):
        """Verify discrepancy detected when arrival dates differ."""
        verified = VerifiedBooking(
            booking_id="12345",
            customer_email="test@example.com",
            arrival_date="2025-01-15",
            exit_date="2025-01-17",
            location="Test Location",
            pass_used=True,
            pass_usage_status="used",
            amount_paid=50.0,
            match_confidence="partial"
        )
        
        customer = CustomerInfo(
            email="test@example.com",
            arrival_date="2025-01-16",  # Different
            exit_date="2025-01-17",
            location="Test Location"
        )
        
        discrepancies = self.generator.highlight_discrepancies(verified, customer)
        
        assert len(discrepancies) > 0, "Should detect arrival date discrepancy"
        assert any("Arrival" in d or "arrival" in d for d in discrepancies), \
            "Discrepancy should mention arrival date"
    
    def test_discrepancy_when_location_differs(self):
        """Verify discrepancy detected when locations differ."""
        verified = VerifiedBooking(
            booking_id="12345",
            customer_email="test@example.com",
            arrival_date="2025-01-15",
            exit_date="2025-01-17",
            location="Downtown Parking",
            pass_used=True,
            pass_usage_status="used",
            amount_paid=50.0,
            match_confidence="exact"
        )
        
        customer = CustomerInfo(
            email="test@example.com",
            arrival_date="2025-01-15",
            exit_date="2025-01-17",
            location="Airport Parking"  # Different
        )
        
        discrepancies = self.generator.highlight_discrepancies(verified, customer)
        
        assert len(discrepancies) > 0, "Should detect location discrepancy"
        assert any("Location" in d or "location" in d for d in discrepancies), \
            "Discrepancy should mention location"
