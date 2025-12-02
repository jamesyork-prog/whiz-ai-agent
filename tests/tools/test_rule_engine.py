"""
Tests for RuleEngine component.

Tests cover:
- 7+ days rule (approve)
- <3 days on-demand rule (deny)
- After event rule (deny)
- Edge cases (uncertain)
- Date calculation logic
- Special scenario handling (oversold, duplicate, paid again)
"""

import pytest
from datetime import datetime, timedelta, timezone
from app_tools.tools.rule_engine import RuleEngine


@pytest.fixture
def mock_rules():
    """Mock policy rules for testing."""
    return {
        "pre_arrival_days": 7,
        "on_demand_minimum_days": 3,
        "confirmed_minimum_days": 3
    }


@pytest.fixture
def rule_engine(mock_rules):
    """Create RuleEngine instance with mock rules."""
    return RuleEngine(mock_rules)


@pytest.fixture
def base_booking_info():
    """Base booking information for tests."""
    return {
        "booking_id": "PW-123456789",
        "amount": 45.00,
        "reservation_date": "2025-11-01",
        "location": "Downtown Parking Garage",
        "customer_email": "customer@example.com"
    }


@pytest.fixture
def base_ticket_data():
    """Base ticket data for tests."""
    return {
        "ticket_id": "1206331",
        "subject": "Refund Request",
        "description": "Customer requesting refund for parking reservation."
    }


# Helper function to create dates
def get_date_string(days_from_now):
    """Get ISO date string for days from now."""
    date = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    return date.strftime("%Y-%m-%d")


def get_cancellation_date_string(days_from_now):
    """Get ISO date string for cancellation date."""
    date = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    return date.strftime("%Y-%m-%d")


# Test 7+ days rule (approve)
def test_seven_plus_days_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that 7+ days before event is automatically approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(10)  # 10 days from now
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"
    assert "Pre-Arrival" in result["policy_rule"]
    assert "7+ days" in result["reasoning"]


def test_exactly_seven_days_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that exactly 7 days before event is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(7)  # Exactly 7 days from now
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"
    assert "Pre-Arrival" in result["policy_rule"]


def test_eight_days_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that 8 days before event is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(8)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "on-demand"  # Even on-demand is approved at 7+ days
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"


# Test <3 days on-demand rule (deny)
def test_less_than_three_days_on_demand_deny(rule_engine, base_booking_info, base_ticket_data):
    """Test that <3 days on-demand booking is denied."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)  # 2 days from now
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "on-demand"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert result["confidence"] == "high"
    assert "On-Demand" in result["policy_rule"]
    assert "3+ days notice" in result["reasoning"]


def test_one_day_on_demand_deny(rule_engine, base_booking_info, base_ticket_data):
    """Test that 1 day on-demand booking is denied."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(1)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "on-demand"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert result["confidence"] == "high"


def test_zero_days_on_demand_deny(rule_engine, base_booking_info, base_ticket_data):
    """Test that same-day on-demand booking is denied."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(0)  # Today
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "on-demand"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert result["confidence"] == "high"


# Test after event rule (deny)
def test_after_event_deny(rule_engine, base_booking_info, base_ticket_data):
    """Test that post-event cancellation is denied."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-5)  # 5 days ago
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert result["confidence"] == "high"
    assert "Post-Event" in result["policy_rule"]
    assert "after event start" in result["reasoning"]


def test_one_day_after_event_deny(rule_engine, base_booking_info, base_ticket_data):
    """Test that 1 day after event is denied."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-1)  # Yesterday
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert result["confidence"] == "high"


# Test 3-7 days confirmed booking (approve with medium confidence)
def test_three_to_seven_days_confirmed_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that 3-7 days confirmed booking is approved with medium confidence."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(5)  # 5 days from now
    booking_info["cancellation_date"] = get_date_string(0)  # Today
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "medium"
    assert "Confirmed Booking" in result["policy_rule"]
    assert "3-7 days" in result["policy_rule"]


def test_exactly_three_days_confirmed_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that exactly 3 days confirmed booking is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(3)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "medium"


def test_six_days_confirmed_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that 6 days confirmed booking is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(6)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "medium"


# Test edge cases (uncertain)
def test_missing_event_date_uncertain(rule_engine, base_booking_info, base_ticket_data):
    """Test that missing event date returns uncertain."""
    booking_info = base_booking_info.copy()
    # No event_date
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Uncertain"
    assert result["confidence"] == "low"
    assert "Missing event date" in result["reasoning"]


def test_invalid_date_format_uncertain(rule_engine, base_booking_info, base_ticket_data):
    """Test that invalid date format returns uncertain."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = "invalid-date"
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Uncertain"
    assert result["confidence"] == "low"
    assert "invalid date format" in result["reasoning"].lower()


def test_three_to_seven_days_unclear_type_uncertain(rule_engine, base_booking_info, base_ticket_data):
    """Test that 3-7 days with unclear booking type is uncertain."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(5)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "unknown"  # Not confirmed or on-demand
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Uncertain"
    assert result["confidence"] == "low"
    assert "Ambiguous Booking Type" in result["policy_rule"]


def test_less_than_three_days_non_on_demand_uncertain(rule_engine, base_booking_info, base_ticket_data):
    """Test that <3 days with non-on-demand booking is uncertain."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "third-party"  # Not on-demand
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Uncertain"
    assert result["confidence"] == "low"
    assert "Short Notice" in result["policy_rule"]


def test_empty_booking_type_uncertain(rule_engine, base_booking_info, base_ticket_data):
    """Test that empty booking type with 3-7 days is uncertain."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(4)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = ""
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Uncertain"
    assert result["confidence"] == "low"


# Test special scenarios (oversold, duplicate, paid again)
def test_oversold_location_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that oversold location is approved regardless of timing."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-2)  # 2 days ago (post-event)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "The garage was full and I couldn't park despite my reservation."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"
    assert "Oversold" in result["policy_rule"]


def test_oversold_keywords(rule_engine, base_booking_info, base_ticket_data):
    """Test various oversold keywords are detected."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)  # Use 2 days (short notice)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "third-party"  # Use third-party to avoid on-demand denial
    
    oversold_phrases = [
        "garage was oversold",
        "lot was full",
        "no space available",
        "no spots left",
        "at capacity",
        "turned away at gate",
        "garage full",
        "lot full",
        "sold out"
    ]
    
    for phrase in oversold_phrases:
        ticket_data = base_ticket_data.copy()
        ticket_data["description"] = f"Customer says: {phrase}"
        
        result = rule_engine.apply_rules(booking_info, ticket_data)
        
        assert result["decision"] == "Approved", f"Failed for phrase: {phrase}"
        assert "Oversold" in result["policy_rule"]


def test_duplicate_booking_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that duplicate booking is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-1)  # Post-event
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "I was charged twice for the same booking. This is a duplicate."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"
    assert "Duplicate" in result["policy_rule"]


def test_duplicate_keywords(rule_engine, base_booking_info, base_ticket_data):
    """Test various duplicate keywords are detected."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)  # Use 2 days (short notice)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "third-party"  # Use third-party to avoid on-demand denial
    
    duplicate_phrases = [
        "duplicate booking",
        "charged twice",
        "double charge",
        "two passes for same time",
        "bought twice by mistake",
        "multiple passes",
        "booked same time twice"
    ]
    
    for phrase in duplicate_phrases:
        ticket_data = base_ticket_data.copy()
        ticket_data["description"] = f"Customer issue: {phrase}"
        
        result = rule_engine.apply_rules(booking_info, ticket_data)
        
        assert result["decision"] == "Approved", f"Failed for phrase: {phrase}"
        assert "Duplicate" in result["policy_rule"]


def test_paid_again_approve(rule_engine, base_booking_info, base_ticket_data):
    """Test that paid again scenario is approved."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-3)  # Post-event
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "I had to pay again at the gate even though I had a reservation."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"
    assert "Paid Again" in result["policy_rule"]


def test_paid_again_keywords(rule_engine, base_booking_info, base_ticket_data):
    """Test various paid again keywords are detected."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)  # Use 2 days (short notice)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "third-party"  # Use third-party to avoid on-demand denial
    
    paid_again_phrases = [
        "paid again at entrance",
        "charged at gate",
        "paid onsite",
        "paid on-site",
        "paid twice total",
        "charged extra fee",
        "had to pay when I arrived"
    ]
    
    for phrase in paid_again_phrases:
        ticket_data = base_ticket_data.copy()
        ticket_data["description"] = f"Issue: {phrase}"
        
        result = rule_engine.apply_rules(booking_info, ticket_data)
        
        assert result["decision"] == "Approved", f"Failed for phrase: {phrase}"
        assert "Paid Again" in result["policy_rule"]


# Test date calculation
def test_calculate_days_before_event_positive(rule_engine):
    """Test calculating days before event (positive)."""
    cancellation_date = "2025-11-01"
    event_date = "2025-11-15"
    
    days = rule_engine._calculate_days_before_event(cancellation_date, event_date)
    
    assert days == 14


def test_calculate_days_before_event_negative(rule_engine):
    """Test calculating days after event (negative)."""
    cancellation_date = "2025-11-20"
    event_date = "2025-11-15"
    
    days = rule_engine._calculate_days_before_event(cancellation_date, event_date)
    
    assert days == -5


def test_calculate_days_same_day(rule_engine):
    """Test calculating days when cancellation and event are same day."""
    date = "2025-11-15"
    
    days = rule_engine._calculate_days_before_event(date, date)
    
    assert days == 0


def test_calculate_days_no_cancellation_date(rule_engine):
    """Test calculating days with no cancellation date (uses current date)."""
    future_date = get_date_string(10)
    
    days = rule_engine._calculate_days_before_event(None, future_date)
    
    # Should be approximately 10 days (may vary by seconds)
    assert 9 <= days <= 10


def test_calculate_days_invalid_format(rule_engine):
    """Test calculating days with invalid date format."""
    days = rule_engine._calculate_days_before_event("invalid", "2025-11-15")
    
    assert days is None


def test_calculate_days_with_timezone(rule_engine):
    """Test calculating days with timezone-aware dates."""
    cancellation_date = "2025-11-01T10:00:00Z"
    event_date = "2025-11-15T14:00:00Z"
    
    days = rule_engine._calculate_days_before_event(cancellation_date, event_date)
    
    assert days == 14


# Test case sensitivity
def test_booking_type_case_insensitive(rule_engine, base_booking_info, base_ticket_data):
    """Test that booking type matching is case insensitive."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "ON-DEMAND"  # Uppercase
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    assert result["decision"] == "Denied"
    assert "On-Demand" in result["policy_rule"]


def test_description_case_insensitive(rule_engine, base_booking_info, base_ticket_data):
    """Test that description keyword matching is case insensitive."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(2)  # Use 2 days (short notice)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "third-party"  # Use third-party to avoid on-demand denial
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "GARAGE WAS OVERSOLD"  # Uppercase
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    assert result["decision"] == "Approved"
    assert "Oversold" in result["policy_rule"]


# Test priority of rules
def test_seven_days_overrides_on_demand(rule_engine, base_booking_info, base_ticket_data):
    """Test that 7+ days rule takes priority over on-demand restrictions."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(10)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "on-demand"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    # Should approve due to 7+ days, not deny due to on-demand
    assert result["decision"] == "Approved"
    assert "Pre-Arrival" in result["policy_rule"]


def test_oversold_overrides_post_event(rule_engine, base_booking_info, base_ticket_data):
    """Test that oversold exception overrides post-event denial."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-5)  # Post-event
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "The lot was full when I arrived."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    # Should approve due to oversold, not deny due to post-event
    assert result["decision"] == "Approved"
    assert "Oversold" in result["policy_rule"]


def test_duplicate_overrides_post_event(rule_engine, base_booking_info, base_ticket_data):
    """Test that duplicate exception overrides post-event denial."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(-2)  # Post-event
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "I was charged twice for this booking."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    # Should approve due to duplicate, not deny due to post-event
    assert result["decision"] == "Approved"
    assert "Duplicate" in result["policy_rule"]


# Test edge cases with missing optional fields
def test_missing_cancellation_date_uses_current(rule_engine, base_booking_info, base_ticket_data):
    """Test that missing cancellation date uses current date."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(10)
    # No cancellation_date
    booking_info["booking_type"] = "confirmed"
    
    result = rule_engine.apply_rules(booking_info, base_ticket_data)
    
    # Should still work and approve
    assert result["decision"] == "Approved"
    assert result["confidence"] == "high"


def test_missing_booking_type_with_special_scenario(rule_engine, base_booking_info, base_ticket_data):
    """Test that special scenarios work even without booking type."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(1)
    booking_info["cancellation_date"] = get_date_string(0)
    # No booking_type
    
    ticket_data = base_ticket_data.copy()
    ticket_data["description"] = "The garage was full."
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    assert result["decision"] == "Approved"
    assert "Oversold" in result["policy_rule"]


def test_missing_description_no_special_scenarios(rule_engine, base_booking_info, base_ticket_data):
    """Test that missing description doesn't trigger false positives."""
    booking_info = base_booking_info.copy()
    booking_info["event_date"] = get_date_string(5)
    booking_info["cancellation_date"] = get_date_string(0)
    booking_info["booking_type"] = "confirmed"
    
    ticket_data = {"ticket_id": "123", "subject": "Refund"}
    # No description
    
    result = rule_engine.apply_rules(booking_info, ticket_data)
    
    # Should apply normal rules, not special scenarios
    assert result["decision"] == "Approved"
    assert "Confirmed Booking" in result["policy_rule"]
