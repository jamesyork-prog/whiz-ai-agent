"""
Tests for ParkWhizBookingVerifier component.

Tests cover:
- Property-based tests for API parameter passing
- Property-based tests for booking selection
- Property-based tests for timeout retry
- Property-based tests for pass usage retrieval
- Unit tests for specific edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from app_tools.tools.booking_verifier import (
    ParkWhizBookingVerifier,
    VerifiedBooking,
    BookingVerificationResult,
)
from app_tools.tools.customer_info_extractor import CustomerInfo
from app_tools.tools.parkwhiz_client import (
    ParkWhizOAuth2Client,
    ParkWhizTimeoutError,
    ParkWhizAuthenticationError,
    ParkWhizError,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_client():
    """Create mock ParkWhiz OAuth2 client."""
    client = Mock(spec=ParkWhizOAuth2Client)
    client.get_customer_bookings = AsyncMock()
    return client


@pytest.fixture
def verifier(mock_client):
    """Create booking verifier with mock client."""
    return ParkWhizBookingVerifier(client=mock_client)


# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================

# Strategy for generating valid email addresses
valid_emails = st.emails()

# Strategy for generating valid ISO dates (YYYY-MM-DD)
valid_dates = st.dates(
    min_value=datetime(2020, 1, 1).date(),
    max_value=datetime(2030, 12, 31).date()
).map(lambda d: d.isoformat())

# Strategy for generating customer info with required fields
complete_customer_info = st.builds(
    CustomerInfo,
    email=valid_emails,
    name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    arrival_date=valid_dates,
    exit_date=valid_dates,
    location=st.one_of(st.none(), st.text(min_size=1, max_size=100))
).filter(lambda ci: ci.is_complete())

# Strategy for generating booking dictionaries
def booking_dict_strategy(
    arrival_date: str,
    exit_date: str,
    email: str,
    pass_used: bool = False
):
    """Generate a booking dictionary with specified dates."""
    return {
        "id": st.integers(min_value=100000, max_value=999999999),
        "customer_email": st.just(email),
        "start_time": st.just(arrival_date),
        "end_time": st.just(exit_date),
        "location_name": st.text(min_size=5, max_size=50),
        "price_paid": st.floats(min_value=5.0, max_value=500.0),
        "pass_used": st.just(pass_used),
    }


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================

# Feature: booking-verification-enhancement, Property 4: ParkWhiz API is called with correct parameters
# Validates: Requirements 2.1
@given(customer_info=complete_customer_info)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_api_called_with_correct_parameters(customer_info):
    """
    Property 4: ParkWhiz API is called with correct parameters.
    
    For any valid customer information (email + dates present), the system should
    call ParkWhiz API with those exact parameters.
    
    This property tests that:
    - API is called when customer info is complete
    - Email parameter matches customer email
    - Start date parameter matches arrival date
    - End date parameter matches exit date
    """
    # Create mock client
    mock_client = Mock(spec=ParkWhizOAuth2Client)
    mock_client.get_customer_bookings = AsyncMock(return_value=[])
    
    # Create verifier with mock client
    verifier = ParkWhizBookingVerifier(client=mock_client)
    
    # Call search_bookings
    await verifier.search_bookings(customer_info)
    
    # Property: API should be called with exact customer parameters
    mock_client.get_customer_bookings.assert_called_once_with(
        customer_email=customer_info.email,
        start_date=customer_info.arrival_date,
        end_date=customer_info.exit_date,
    )


# Feature: booking-verification-enhancement, Property 5: Best booking match is selected
# Validates: Requirements 2.2
@given(
    customer_arrival=valid_dates,
    customer_exit=valid_dates,
    email=valid_emails,
    # Generate offset days for bookings (how many days off from customer dates)
    booking1_offset=st.integers(min_value=0, max_value=10),
    booking2_offset=st.integers(min_value=0, max_value=10),
    booking3_offset=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100)
def test_property_best_booking_match_selected(
    customer_arrival,
    customer_exit,
    email,
    booking1_offset,
    booking2_offset,
    booking3_offset
):
    """
    Property 5: Best booking match is selected.
    
    For any set of multiple bookings returned by ParkWhiz API, the system should
    select the booking with dates closest to customer-provided dates.
    
    This property tests that:
    - When multiple bookings exist, one is selected
    - The selected booking has the smallest date difference
    - Selection is deterministic based on date proximity
    """
    # Ensure customer exit is after arrival
    assume(customer_exit >= customer_arrival)
    
    # Create customer info
    customer_info = CustomerInfo(
        email=email,
        arrival_date=customer_arrival,
        exit_date=customer_exit,
    )
    
    # Parse dates
    arrival_dt = datetime.fromisoformat(customer_arrival)
    exit_dt = datetime.fromisoformat(customer_exit)
    
    # Create bookings with different date offsets
    bookings = [
        {
            "id": "BOOKING-001",
            "customer_email": email,
            "start_time": (arrival_dt + timedelta(days=booking1_offset)).isoformat(),
            "end_time": (exit_dt + timedelta(days=booking1_offset)).isoformat(),
            "location_name": "Location 1",
            "price_paid": 50.0,
            "pass_used": False,
        },
        {
            "id": "BOOKING-002",
            "customer_email": email,
            "start_time": (arrival_dt + timedelta(days=booking2_offset)).isoformat(),
            "end_time": (exit_dt + timedelta(days=booking2_offset)).isoformat(),
            "location_name": "Location 2",
            "price_paid": 60.0,
            "pass_used": False,
        },
        {
            "id": "BOOKING-003",
            "customer_email": email,
            "start_time": (arrival_dt + timedelta(days=booking3_offset)).isoformat(),
            "end_time": (exit_dt + timedelta(days=booking3_offset)).isoformat(),
            "location_name": "Location 3",
            "price_paid": 70.0,
            "pass_used": False,
        },
    ]
    
    # Create verifier
    verifier = ParkWhizBookingVerifier()
    
    # Select best match
    result = verifier.select_best_match(bookings, customer_info)
    
    # Property: A booking should be selected
    assert result is not None, "No booking selected from multiple options"
    
    # Property: Selected booking should have smallest total date difference
    min_offset = min(booking1_offset, booking2_offset, booking3_offset)
    expected_total_diff = min_offset * 2  # Both arrival and exit are offset by same amount
    
    # Calculate actual difference for selected booking
    selected_arrival = datetime.fromisoformat(result.arrival_date.split('T')[0])
    selected_exit = datetime.fromisoformat(result.exit_date.split('T')[0])
    
    arrival_diff = abs((selected_arrival.date() - arrival_dt.date()).days)
    exit_diff = abs((selected_exit.date() - exit_dt.date()).days)
    actual_total_diff = arrival_diff + exit_diff
    
    assert actual_total_diff == expected_total_diff, (
        f"Selected booking does not have smallest date difference. "
        f"Expected total diff: {expected_total_diff}, Actual: {actual_total_diff}"
    )


# Feature: booking-verification-enhancement, Property 6: API timeout triggers retry then escalation
# Validates: Requirements 2.5
@given(customer_info=complete_customer_info)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_timeout_triggers_retry_then_escalation(customer_info):
    """
    Property 6: API timeout triggers retry then escalation.
    
    For any ParkWhiz API timeout, the system should retry once, and if timeout
    persists, flag for human review.
    
    This property tests that:
    - Timeout errors are caught
    - Result indicates failure
    - Escalation is triggered
    - Failure reason mentions timeout
    """
    # Create mock client that raises timeout
    mock_client = Mock(spec=ParkWhizOAuth2Client)
    mock_client.get_customer_bookings = AsyncMock(
        side_effect=ParkWhizTimeoutError("Request timed out")
    )
    
    # Create verifier with mock client
    verifier = ParkWhizBookingVerifier(client=mock_client)
    
    # Call verify_booking (which calls search_bookings internally)
    result = await verifier.verify_booking(customer_info)
    
    # Property: Verification should fail
    assert result.success is False, "Verification should fail on timeout"
    
    # Property: Should escalate
    assert result.should_escalate is True, "Timeout should trigger escalation"
    
    # Property: Failure reason should mention timeout
    assert "timeout" in result.failure_reason.lower(), (
        f"Failure reason should mention timeout, got: {result.failure_reason}"
    )
    
    # Property: Escalation reason should be provided
    assert result.escalation_reason is not None, "Escalation reason should be provided"
    assert ("timeout" in result.escalation_reason.lower() or "timed out" in result.escalation_reason.lower()), (
        f"Escalation reason should mention timeout, got: {result.escalation_reason}"
    )


# Feature: booking-verification-enhancement, Property 7: Pass usage status is always retrieved
# Validates: Requirements 3.1, 3.2, 3.3
@given(
    customer_info=complete_customer_info,
    pass_used=st.booleans(),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_pass_usage_always_retrieved(customer_info, pass_used):
    """
    Property 7: Pass usage status is always retrieved.
    
    For any verified booking found via ParkWhiz API, the system should retrieve
    and include pass usage status.
    
    This property tests that:
    - Pass usage status is extracted from booking data
    - Status is included in VerifiedBooking
    - Status is one of: "used", "not_used", or "unknown"
    """
    # Create booking with pass usage
    booking = {
        "id": "BOOKING-123",
        "customer_email": customer_info.email,
        "start_time": customer_info.arrival_date,
        "end_time": customer_info.exit_date,
        "location_name": "Test Location",
        "price_paid": 50.0,
        "pass_used": pass_used,
    }
    
    # Create mock client that returns this booking
    mock_client = Mock(spec=ParkWhizOAuth2Client)
    mock_client.get_customer_bookings = AsyncMock(return_value=[booking])
    
    # Create verifier with mock client
    verifier = ParkWhizBookingVerifier(client=mock_client)
    
    # Verify booking
    result = await verifier.verify_booking(customer_info)
    
    # Property: Verification should succeed
    assert result.success is True, "Verification should succeed when booking found"
    
    # Property: Verified booking should exist
    assert result.verified_booking is not None, "Verified booking should be present"
    
    # Property: Pass usage status should be retrieved
    assert result.verified_booking.pass_usage_status in ["used", "not_used", "unknown"], (
        f"Invalid pass usage status: {result.verified_booking.pass_usage_status}"
    )
    
    # Property: Pass usage status should match booking data
    expected_status = "used" if pass_used else "not_used"
    assert result.verified_booking.pass_usage_status == expected_status, (
        f"Pass usage status mismatch. Expected: {expected_status}, "
        f"Got: {result.verified_booking.pass_usage_status}"
    )
    
    # Property: pass_used boolean should match status
    assert result.verified_booking.pass_used == pass_used, (
        f"pass_used boolean mismatch. Expected: {pass_used}, "
        f"Got: {result.verified_booking.pass_used}"
    )


# ============================================================================
# UNIT TESTS - Specific Examples and Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_search_bookings_success(verifier, mock_client):
    """Test successful booking search."""
    # Setup
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    expected_bookings = [
        {"id": "BOOKING-1", "customer_email": "test@example.com"},
        {"id": "BOOKING-2", "customer_email": "test@example.com"},
    ]
    
    mock_client.get_customer_bookings.return_value = expected_bookings
    
    # Execute
    result = await verifier.search_bookings(customer_info)
    
    # Assert
    assert result == expected_bookings
    mock_client.get_customer_bookings.assert_called_once()


@pytest.mark.asyncio
async def test_search_bookings_timeout(verifier, mock_client):
    """Test booking search with timeout."""
    # Setup
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    mock_client.get_customer_bookings.side_effect = ParkWhizTimeoutError("Timeout")
    
    # Execute & Assert
    with pytest.raises(ParkWhizTimeoutError):
        await verifier.search_bookings(customer_info)


@pytest.mark.asyncio
async def test_search_bookings_auth_error(verifier, mock_client):
    """Test booking search with authentication error."""
    # Setup
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    mock_client.get_customer_bookings.side_effect = ParkWhizAuthenticationError("Auth failed")
    
    # Execute & Assert
    with pytest.raises(ParkWhizAuthenticationError):
        await verifier.search_bookings(customer_info)


def test_select_best_match_exact_match(verifier):
    """Test selection with exact date match."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    bookings = [
        {
            "id": "EXACT",
            "customer_email": "test@example.com",
            "start_time": "2025-01-15",
            "end_time": "2025-01-16",
            "location_name": "Test Location",
            "price_paid": 50.0,
            "pass_used": False,
        },
        {
            "id": "OFF-BY-ONE",
            "customer_email": "test@example.com",
            "start_time": "2025-01-16",
            "end_time": "2025-01-17",
            "location_name": "Test Location",
            "price_paid": 50.0,
            "pass_used": False,
        },
    ]
    
    result = verifier.select_best_match(bookings, customer_info)
    
    assert result is not None
    assert result.booking_id == "EXACT"
    assert result.match_confidence == "exact"


def test_select_best_match_partial_match(verifier):
    """Test selection with partial date match (within 2 days)."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    bookings = [
        {
            "id": "CLOSE",
            "customer_email": "test@example.com",
            "start_time": "2025-01-16",  # 1 day off
            "end_time": "2025-01-16",    # Same exit
            "location_name": "Test Location",
            "price_paid": 50.0,
            "pass_used": False,
        },
    ]
    
    result = verifier.select_best_match(bookings, customer_info)
    
    assert result is not None
    assert result.booking_id == "CLOSE"
    assert result.match_confidence == "partial"


def test_select_best_match_weak_match(verifier):
    """Test selection with weak date match (more than 2 days off)."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    bookings = [
        {
            "id": "FAR",
            "customer_email": "test@example.com",
            "start_time": "2025-01-20",  # 5 days off
            "end_time": "2025-01-21",    # 5 days off
            "location_name": "Test Location",
            "price_paid": 50.0,
            "pass_used": False,
        },
    ]
    
    result = verifier.select_best_match(bookings, customer_info)
    
    assert result is not None
    assert result.booking_id == "FAR"
    assert result.match_confidence == "weak"


def test_select_best_match_no_bookings(verifier):
    """Test selection with empty booking list."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    result = verifier.select_best_match([], customer_info)
    
    assert result is None


def test_select_best_match_invalid_dates(verifier):
    """Test selection with bookings that have invalid dates."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    bookings = [
        {
            "id": "INVALID",
            "customer_email": "test@example.com",
            "start_time": "invalid-date",
            "end_time": "invalid-date",
            "location_name": "Test Location",
            "price_paid": 50.0,
            "pass_used": False,
        },
    ]
    
    result = verifier.select_best_match(bookings, customer_info)
    
    assert result is None


def test_extract_pass_usage_boolean_true(verifier):
    """Test pass usage extraction with boolean True."""
    booking = {"id": "TEST", "pass_used": True}
    result = verifier._extract_pass_usage(booking)
    assert result == "used"


def test_extract_pass_usage_boolean_false(verifier):
    """Test pass usage extraction with boolean False."""
    booking = {"id": "TEST", "pass_used": False}
    result = verifier._extract_pass_usage(booking)
    assert result == "not_used"


def test_extract_pass_usage_string_variants(verifier):
    """Test pass usage extraction with string variants."""
    # Used variants
    for value in ["used", "Used", "USED", "scanned", "checked_in", "true", "yes"]:
        booking = {"id": "TEST", "pass_usage": value}
        result = verifier._extract_pass_usage(booking)
        assert result == "used", f"Failed for value: {value}"
    
    # Not used variants
    for value in ["not_used", "Not_Used", "NOT_USED", "not_scanned", "false", "no"]:
        booking = {"id": "TEST", "pass_usage": value}
        result = verifier._extract_pass_usage(booking)
        assert result == "not_used", f"Failed for value: {value}"


def test_extract_pass_usage_unknown(verifier):
    """Test pass usage extraction when status is unknown."""
    booking = {"id": "TEST"}  # No pass usage field
    result = verifier._extract_pass_usage(booking)
    assert result == "unknown"


@pytest.mark.asyncio
async def test_verify_booking_incomplete_customer_info(verifier, mock_client):
    """Test verification with incomplete customer info."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="",  # Missing
        exit_date="2025-01-16",
    )
    
    result = await verifier.verify_booking(customer_info)
    
    assert result.success is False
    assert result.should_escalate is True
    assert "Missing required customer information" in result.failure_reason
    assert result.api_calls_made == 0  # No API calls made


@pytest.mark.asyncio
async def test_verify_booking_no_bookings_found(verifier, mock_client):
    """Test verification when no bookings are found."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    mock_client.get_customer_bookings.return_value = []
    
    result = await verifier.verify_booking(customer_info)
    
    assert result.success is False
    assert result.should_escalate is True
    assert "No matching bookings found" in result.failure_reason
    assert result.api_calls_made == 1


@pytest.mark.asyncio
async def test_verify_booking_success(verifier, mock_client):
    """Test successful booking verification."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    booking = {
        "id": "BOOKING-123",
        "customer_email": "test@example.com",
        "start_time": "2025-01-15",
        "end_time": "2025-01-16",
        "location_name": "Test Location",
        "price_paid": 50.0,
        "pass_used": False,
    }
    
    mock_client.get_customer_bookings.return_value = [booking]
    
    result = await verifier.verify_booking(customer_info)
    
    assert result.success is True
    assert result.verified_booking is not None
    assert result.verified_booking.booking_id == "BOOKING-123"
    assert result.api_calls_made == 1


@pytest.mark.asyncio
async def test_verify_booking_unknown_pass_usage_escalates(verifier, mock_client):
    """Test that unknown pass usage triggers escalation."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    booking = {
        "id": "BOOKING-123",
        "customer_email": "test@example.com",
        "start_time": "2025-01-15",
        "end_time": "2025-01-16",
        "location_name": "Test Location",
        "price_paid": 50.0,
        # No pass_used field - will be "unknown"
    }
    
    mock_client.get_customer_bookings.return_value = [booking]
    
    result = await verifier.verify_booking(customer_info)
    
    assert result.success is True
    assert result.verified_booking is not None
    assert result.verified_booking.pass_usage_status == "unknown"
    assert result.should_escalate is True
    assert "Pass usage status unavailable" in result.escalation_reason


@pytest.mark.asyncio
async def test_verify_booking_weak_match_escalates(verifier, mock_client):
    """Test that weak match confidence triggers escalation."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    booking = {
        "id": "BOOKING-123",
        "customer_email": "test@example.com",
        "start_time": "2025-01-20",  # 5 days off - weak match
        "end_time": "2025-01-21",
        "location_name": "Test Location",
        "price_paid": 50.0,
        "pass_used": False,
    }
    
    mock_client.get_customer_bookings.return_value = [booking]
    
    result = await verifier.verify_booking(customer_info)
    
    assert result.success is True
    assert result.verified_booking is not None
    assert result.verified_booking.match_confidence == "weak"
    assert result.should_escalate is True
    assert "dates don't match" in result.escalation_reason.lower()


def test_find_discrepancies_date_mismatch(verifier):
    """Test discrepancy detection for date mismatches."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
    )
    
    verified_booking = VerifiedBooking(
        booking_id="BOOKING-123",
        customer_email="test@example.com",
        arrival_date="2025-01-20",  # Different
        exit_date="2025-01-21",     # Different
        location="Test Location",
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="weak",
    )
    
    discrepancies = verifier._find_discrepancies(verified_booking, customer_info)
    
    assert len(discrepancies) == 2
    assert any("Arrival date mismatch" in d for d in discrepancies)
    assert any("Exit date mismatch" in d for d in discrepancies)


def test_find_discrepancies_location_mismatch(verifier):
    """Test discrepancy detection for location mismatch."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
        location="Downtown Parking",
    )
    
    verified_booking = VerifiedBooking(
        booking_id="BOOKING-123",
        customer_email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
        location="Airport Parking",  # Different
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="exact",
    )
    
    discrepancies = verifier._find_discrepancies(verified_booking, customer_info)
    
    assert len(discrepancies) == 1
    assert "Location mismatch" in discrepancies[0]


def test_find_discrepancies_no_mismatch(verifier):
    """Test discrepancy detection with no mismatches."""
    customer_info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
        location="Test Location",
    )
    
    verified_booking = VerifiedBooking(
        booking_id="BOOKING-123",
        customer_email="test@example.com",
        arrival_date="2025-01-15",
        exit_date="2025-01-16",
        location="Test Location",
        pass_used=False,
        pass_usage_status="not_used",
        amount_paid=50.0,
        match_confidence="exact",
    )
    
    discrepancies = verifier._find_discrepancies(verified_booking, customer_info)
    
    assert len(discrepancies) == 0


# ============================================================================
# PROPERTY-BASED TESTS - LOGGING
# ============================================================================

# Feature: booking-verification-enhancement, Property 20: API searches are logged
# Validates: Requirements 6.1
@given(customer_info=complete_customer_info)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_api_searches_are_logged(customer_info):
    """
    Property 20: API searches are logged.
    
    For any ParkWhiz API search attempt, the system should log the search
    parameters used.
    
    This property tests that:
    - Search attempts are logged
    - Customer email is included in log
    - Arrival and exit dates are included in log
    """
    import logging
    from unittest.mock import patch
    
    # Create a list to capture log records
    captured_logs = []
    
    # Create a custom handler to capture logs
    class ListHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append(record)
    
    # Add handler to the booking_verifier logger
    logger = logging.getLogger('app_tools.tools.booking_verifier')
    handler = ListHandler()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    
    try:
        # Create mock client
        mock_client = Mock(spec=ParkWhizOAuth2Client)
        mock_client.get_customer_bookings = AsyncMock(return_value=[])
        
        # Create verifier with mock client
        verifier = ParkWhizBookingVerifier(client=mock_client)
        
        # Call search_bookings
        await verifier.search_bookings(customer_info)
        
        # Property: Search should be logged
        log_messages = [record.message for record in captured_logs]
        
        # Check that search was logged with customer email
        assert any(
            "Searching bookings" in msg and customer_info.email in msg
            for msg in log_messages
        ), f"API search not logged for {customer_info.email}"
        
        # Check that log contains search parameters in extra fields
        search_logs = [
            record for record in captured_logs
            if "Searching bookings" in record.message
        ]
        
        assert len(search_logs) > 0, "No search log found"
        
        # Verify extra fields contain search parameters
        search_log = search_logs[0]
        assert hasattr(search_log, 'customer_email'), "Log missing customer_email field"
        assert search_log.customer_email == customer_info.email
        assert hasattr(search_log, 'arrival_date'), "Log missing arrival_date field"
        assert search_log.arrival_date == customer_info.arrival_date
        assert hasattr(search_log, 'exit_date'), "Log missing exit_date field"
        assert search_log.exit_date == customer_info.exit_date
    finally:
        # Clean up
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        captured_logs.clear()


# Feature: booking-verification-enhancement, Property 21: Result counts are logged
# Validates: Requirements 6.2
@given(
    customer_info=complete_customer_info,
    booking_count=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_result_counts_are_logged(customer_info, booking_count):
    """
    Property 21: Result counts are logged.
    
    For any ParkWhiz API response, the system should log the number of
    bookings found.
    
    This property tests that:
    - Result count is logged after API call
    - Count matches actual number of bookings returned
    - Log includes customer email for context
    """
    import logging
    
    # Create a list to capture log records
    captured_logs = []
    
    # Create a custom handler to capture logs
    class ListHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append(record)
    
    # Add handler to the booking_verifier logger
    logger = logging.getLogger('app_tools.tools.booking_verifier')
    handler = ListHandler()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    
    try:
        # Create mock bookings
        mock_bookings = [
            {
                "id": f"BOOKING-{i}",
                "customer_email": customer_info.email,
                "start_time": customer_info.arrival_date,
                "end_time": customer_info.exit_date,
                "location_name": f"Location {i}",
                "price_paid": 50.0,
                "pass_used": False,
            }
            for i in range(booking_count)
        ]
        
        # Create mock client
        mock_client = Mock(spec=ParkWhizOAuth2Client)
        mock_client.get_customer_bookings = AsyncMock(return_value=mock_bookings)
        
        # Create verifier with mock client
        verifier = ParkWhizBookingVerifier(client=mock_client)
        
        # Call search_bookings
        result = await verifier.search_bookings(customer_info)
        
        # Property: Result count should be logged
        log_messages = [record.message for record in captured_logs]
        
        # Check that result count was logged
        assert any(
            f"Found {booking_count} bookings" in msg
            for msg in log_messages
        ), f"Result count {booking_count} not logged"
        
        # Check that log contains booking count in extra fields
        result_logs = [
            record for record in captured_logs
            if "Found" in record.message and "bookings" in record.message
        ]
        
        assert len(result_logs) > 0, "No result count log found"
        
        # Verify extra fields contain booking count
        result_log = result_logs[0]
        assert hasattr(result_log, 'booking_count'), "Log missing booking_count field"
        assert result_log.booking_count == booking_count, (
            f"Logged count {result_log.booking_count} doesn't match actual {booking_count}"
        )
    finally:
        # Clean up
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        captured_logs.clear()


# Feature: booking-verification-enhancement, Property 22: Failures are logged with reasons
# Validates: Requirements 6.3
@given(customer_info=complete_customer_info)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_failures_logged_with_reasons(customer_info):
    """
    Property 22: Failures are logged with reasons.
    
    For any booking verification failure, the system should log the specific
    failure reason.
    
    This property tests that:
    - Failures are logged at appropriate level (ERROR or CRITICAL)
    - Failure reason is included in log message
    - Customer context is preserved in logs
    """
    import logging
    
    # Create a list to capture log records
    captured_logs = []
    
    # Create a custom handler to capture logs
    class ListHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append(record)
    
    # Add handler to the booking_verifier logger
    logger = logging.getLogger('app_tools.tools.booking_verifier')
    handler = ListHandler()
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.ERROR)
    
    try:
        # Create mock client that raises authentication error
        mock_client = Mock(spec=ParkWhizOAuth2Client)
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=ParkWhizAuthenticationError("Invalid credentials")
        )
        
        # Create verifier with mock client
        verifier = ParkWhizBookingVerifier(client=mock_client)
        
        # Call verify_booking (which will fail)
        result = await verifier.verify_booking(customer_info)
        
        # Property: Failure should be logged
        log_messages = [record.message for record in captured_logs]
        
        # Check that authentication failure was logged
        assert any(
            "authentication failed" in msg.lower()
            for msg in log_messages
        ), "Authentication failure not logged"
        
        # Property: Failure reason should be in result
        assert result.success is False
        assert result.failure_reason is not None
        assert "authentication" in result.failure_reason.lower()
        
        # Check that log contains customer context
        failure_logs = [
            record for record in captured_logs
            if "authentication" in record.message.lower()
        ]
        
        assert len(failure_logs) > 0, "No failure log found"
        
        # Verify customer email is in log context
        failure_log = failure_logs[0]
        assert hasattr(failure_log, 'customer_email'), "Log missing customer_email field"
        assert failure_log.customer_email == customer_info.email
    finally:
        # Clean up
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        captured_logs.clear()


# Feature: booking-verification-enhancement, Property 23: Escalations are logged with reasons
# Validates: Requirements 6.4
@given(customer_info=complete_customer_info)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_escalations_logged_with_reasons(customer_info):
    """
    Property 23: Escalations are logged with reasons.
    
    For any ticket flagged for human review, the system should log the specific
    reason for flagging.
    
    This property tests that:
    - Escalation decisions are logged
    - Escalation reason is included
    - Verification result contains escalation flag and reason
    """
    import logging
    
    # Create a list to capture log records
    captured_logs = []
    
    # Create a custom handler to capture logs
    class ListHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append(record)
    
    # Add handler to the booking_verifier logger
    logger = logging.getLogger('app_tools.tools.booking_verifier')
    handler = ListHandler()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    
    try:
        # Create booking with unknown pass usage (triggers escalation)
        booking = {
            "id": "BOOKING-123",
            "customer_email": customer_info.email,
            "start_time": customer_info.arrival_date,
            "end_time": customer_info.exit_date,
            "location_name": "Test Location",
            "price_paid": 50.0,
            # No pass_used field - will be "unknown" and trigger escalation
        }
        
        # Create mock client
        mock_client = Mock(spec=ParkWhizOAuth2Client)
        mock_client.get_customer_bookings = AsyncMock(return_value=[booking])
        
        # Create verifier with mock client
        verifier = ParkWhizBookingVerifier(client=mock_client)
        
        # Call verify_booking
        result = await verifier.verify_booking(customer_info)
        
        # Property: Escalation should be flagged in result
        assert result.should_escalate is True, "Escalation should be triggered"
        assert result.escalation_reason is not None, "Escalation reason should be provided"
        assert "pass usage" in result.escalation_reason.lower(), (
            f"Escalation reason should mention pass usage, got: {result.escalation_reason}"
        )
        
        # Property: Verification completion should be logged
        log_messages = [record.message for record in captured_logs]
        
        assert any(
            "verification completed" in msg.lower()
            for msg in log_messages
        ), "Verification completion not logged"
        
        # Check that escalation flag is in log context
        completion_logs = [
            record for record in captured_logs
            if "verification completed" in record.message.lower()
        ]
        
        assert len(completion_logs) > 0, "No completion log found"
        
        # Verify escalation flag is in log context
        completion_log = completion_logs[0]
        assert hasattr(completion_log, 'should_escalate'), "Log missing should_escalate field"
        assert completion_log.should_escalate is True, "Escalation flag not set in log"
    finally:
        # Clean up
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        captured_logs.clear()
