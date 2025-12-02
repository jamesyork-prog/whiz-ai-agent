"""
Tests for CustomerInfoExtractor component.

Tests cover:
- Property-based tests for customer info validation
- Unit tests for extraction with complete information
- Unit tests for extraction with partial information
- Unit tests for extraction with missing information
- Mock Gemini API responses
- Error handling and timeouts
"""

import pytest
import json
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings
from app_tools.tools.customer_info_extractor import CustomerInfo, CustomerInfoExtractor


@pytest.fixture
def mock_gemini_api_key(monkeypatch):
    """Mock GEMINI_API_KEY environment variable."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")


@pytest.fixture
def extractor(mock_gemini_api_key):
    """Create CustomerInfoExtractor instance."""
    return CustomerInfoExtractor()


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================

# Feature: booking-verification-enhancement, Property 3: Customer info extraction validates required fields
# Validates: Requirements 1.3, 1.4
@given(
    email=st.one_of(
        st.just(""),  # Empty email
        st.just("   "),  # Whitespace-only email
        st.none(),  # None email (will be converted to empty string in CustomerInfo)
    ),
    arrival_date=st.text(min_size=0, max_size=20),
    exit_date=st.text(min_size=0, max_size=20)
)
@settings(max_examples=100)
def test_property_customer_info_validates_required_fields_missing_email(email, arrival_date, exit_date):
    """
    Property 3: Customer info extraction validates required fields.
    
    For any extracted customer information where email is missing or empty,
    the system should flag for human review (is_complete() returns False).
    
    This property tests that:
    - Missing email causes validation failure
    - Empty email causes validation failure
    - Whitespace-only email causes validation failure
    - Validation works regardless of other fields
    """
    # Create CustomerInfo with missing/empty email
    customer_info = CustomerInfo(
        email=email if email is not None else "",
        arrival_date=arrival_date,
        exit_date=exit_date
    )
    
    # Property: Should NOT be complete if email is missing/empty
    assert customer_info.is_complete() is False, (
        f"CustomerInfo should not be complete with email='{email}', "
        f"arrival_date='{arrival_date}', exit_date='{exit_date}'"
    )


@given(
    email=st.emails(),  # Valid email
    arrival_date=st.one_of(
        st.just(""),  # Empty date
        st.just("   "),  # Whitespace-only date
    ),
    exit_date=st.text(min_size=0, max_size=20)
)
@settings(max_examples=100)
def test_property_customer_info_validates_required_fields_missing_arrival(email, arrival_date, exit_date):
    """
    Property 3: Customer info extraction validates required fields.
    
    For any extracted customer information where arrival_date is missing or empty,
    the system should flag for human review (is_complete() returns False).
    
    This property tests that:
    - Missing arrival_date causes validation failure
    - Empty arrival_date causes validation failure
    - Whitespace-only arrival_date causes validation failure
    """
    # Create CustomerInfo with missing/empty arrival_date
    customer_info = CustomerInfo(
        email=email,
        arrival_date=arrival_date,
        exit_date=exit_date
    )
    
    # Property: Should NOT be complete if arrival_date is missing/empty
    assert customer_info.is_complete() is False, (
        f"CustomerInfo should not be complete with email='{email}', "
        f"arrival_date='{arrival_date}', exit_date='{exit_date}'"
    )


@given(
    email=st.emails(),  # Valid email
    arrival_date=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),  # Non-empty date
    exit_date=st.one_of(
        st.just(""),  # Empty date
        st.just("   "),  # Whitespace-only date
    )
)
@settings(max_examples=100)
def test_property_customer_info_validates_required_fields_missing_exit(email, arrival_date, exit_date):
    """
    Property 3: Customer info extraction validates required fields.
    
    For any extracted customer information where exit_date is missing or empty,
    the system should flag for human review (is_complete() returns False).
    
    This property tests that:
    - Missing exit_date causes validation failure
    - Empty exit_date causes validation failure
    - Whitespace-only exit_date causes validation failure
    """
    # Create CustomerInfo with missing/empty exit_date
    customer_info = CustomerInfo(
        email=email,
        arrival_date=arrival_date,
        exit_date=exit_date
    )
    
    # Property: Should NOT be complete if exit_date is missing/empty
    assert customer_info.is_complete() is False, (
        f"CustomerInfo should not be complete with email='{email}', "
        f"arrival_date='{arrival_date}', exit_date='{exit_date}'"
    )


@given(
    email=st.emails(),  # Valid email
    arrival_date=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),  # Non-empty date
    exit_date=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),  # Non-empty date
    name=st.one_of(st.none(), st.text(max_size=50)),  # Optional name
    location=st.one_of(st.none(), st.text(max_size=100))  # Optional location
)
@settings(max_examples=100)
def test_property_customer_info_complete_with_all_required_fields(email, arrival_date, exit_date, name, location):
    """
    Property 3: Customer info extraction validates required fields.
    
    For any extracted customer information where all required fields (email, arrival_date, exit_date)
    are present and non-empty, the system should consider it complete regardless of optional fields.
    
    This property tests that:
    - Complete info with all required fields passes validation
    - Optional fields (name, location) don't affect validation
    - Validation is consistent across all valid combinations
    """
    # Create CustomerInfo with all required fields
    customer_info = CustomerInfo(
        email=email,
        name=name,
        arrival_date=arrival_date,
        exit_date=exit_date,
        location=location
    )
    
    # Property: Should be complete if all required fields are present
    assert customer_info.is_complete() is True, (
        f"CustomerInfo should be complete with email='{email}', "
        f"arrival_date='{arrival_date}', exit_date='{exit_date}', "
        f"name='{name}', location='{location}'"
    )


# ============================================================================
# UNIT TESTS - Specific Examples and Edge Cases
# ============================================================================

# Mock Gemini API responses
def create_mock_gemini_response(data):
    """Create a mock Gemini API response."""
    mock_response = Mock()
    mock_response.text = json.dumps(data)
    return mock_response


@pytest.fixture
def mock_complete_extraction():
    """Mock complete customer info extraction response."""
    return {
        "email": "customer@example.com",
        "name": "John Doe",
        "arrival_date": "2025-11-15",
        "exit_date": "2025-11-17",
        "location": "Downtown Parking Garage"
    }


@pytest.fixture
def mock_partial_extraction_no_email():
    """Mock partial extraction missing email."""
    return {
        "name": "John Doe",
        "arrival_date": "2025-11-15",
        "exit_date": "2025-11-17",
        "location": "Downtown Parking Garage"
    }


@pytest.fixture
def mock_partial_extraction_no_dates():
    """Mock partial extraction missing dates."""
    return {
        "email": "customer@example.com",
        "name": "John Doe",
        "location": "Downtown Parking Garage"
    }


@pytest.fixture
def mock_minimal_extraction():
    """Mock minimal extraction with only required fields."""
    return {
        "email": "customer@example.com",
        "arrival_date": "2025-11-15",
        "exit_date": "2025-11-17"
    }


@pytest.fixture
def mock_empty_extraction():
    """Mock empty extraction response."""
    return {}


# Test CustomerInfo dataclass
def test_customer_info_is_complete_with_all_required():
    """Test that CustomerInfo is complete with all required fields."""
    info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-11-15",
        exit_date="2025-11-17"
    )
    assert info.is_complete() is True


def test_customer_info_is_complete_with_optional_fields():
    """Test that CustomerInfo is complete with optional fields."""
    info = CustomerInfo(
        email="test@example.com",
        name="John Doe",
        arrival_date="2025-11-15",
        exit_date="2025-11-17",
        location="Downtown"
    )
    assert info.is_complete() is True


def test_customer_info_incomplete_missing_email():
    """Test that CustomerInfo is incomplete without email."""
    info = CustomerInfo(
        email="",
        arrival_date="2025-11-15",
        exit_date="2025-11-17"
    )
    assert info.is_complete() is False


def test_customer_info_incomplete_whitespace_email():
    """Test that CustomerInfo is incomplete with whitespace-only email."""
    info = CustomerInfo(
        email="   ",
        arrival_date="2025-11-15",
        exit_date="2025-11-17"
    )
    assert info.is_complete() is False


def test_customer_info_incomplete_missing_arrival_date():
    """Test that CustomerInfo is incomplete without arrival_date."""
    info = CustomerInfo(
        email="test@example.com",
        arrival_date="",
        exit_date="2025-11-17"
    )
    assert info.is_complete() is False


def test_customer_info_incomplete_missing_exit_date():
    """Test that CustomerInfo is incomplete without exit_date."""
    info = CustomerInfo(
        email="test@example.com",
        arrival_date="2025-11-15",
        exit_date=""
    )
    assert info.is_complete() is False


def test_customer_info_incomplete_all_missing():
    """Test that CustomerInfo is incomplete with all fields missing."""
    info = CustomerInfo(email="")
    assert info.is_complete() is False


# Test CustomerInfoExtractor initialization
def test_extractor_initialization(mock_gemini_api_key):
    """Test CustomerInfoExtractor initializes correctly."""
    extractor = CustomerInfoExtractor()
    
    assert extractor.model_name == "gemini-2.5-flash"
    assert extractor.client is not None


def test_extractor_custom_model(mock_gemini_api_key):
    """Test CustomerInfoExtractor with custom model name."""
    extractor = CustomerInfoExtractor(model_name="gemini-2.0-flash-exp")
    
    assert extractor.model_name == "gemini-2.0-flash-exp"


def test_extractor_no_api_key(monkeypatch):
    """Test CustomerInfoExtractor raises error without API key."""
    # Remove the API key from environment
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    with pytest.raises(ValueError) as exc_info:
        CustomerInfoExtractor()
    
    assert "GEMINI_API_KEY" in str(exc_info.value)


# Test extraction with complete information
@pytest.mark.asyncio
async def test_extract_complete_customer_info(extractor, mock_complete_extraction):
    """Test extraction of complete customer information."""
    ticket_description = """
    Customer: John Doe (customer@example.com)
    Parking Date: November 15-17, 2025
    Location: Downtown Parking Garage
    
    Customer is requesting a refund for their parking reservation.
    """
    
    mock_response = create_mock_gemini_response(mock_complete_extraction)
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == "customer@example.com"
        assert result.name == "John Doe"
        assert result.arrival_date == "2025-11-15"
        assert result.exit_date == "2025-11-17"
        assert result.location == "Downtown Parking Garage"
        assert result.is_complete() is True


# Test extraction with partial information
@pytest.mark.asyncio
async def test_extract_partial_no_email(extractor, mock_partial_extraction_no_email):
    """Test extraction when email is missing."""
    ticket_description = """
    Customer: John Doe
    Parking Date: November 15-17, 2025
    Location: Downtown Parking Garage
    """
    
    mock_response = create_mock_gemini_response(mock_partial_extraction_no_email)
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == ""
        assert result.name == "John Doe"
        assert result.arrival_date == "2025-11-15"
        assert result.exit_date == "2025-11-17"
        assert result.is_complete() is False  # Missing email


@pytest.mark.asyncio
async def test_extract_partial_no_dates(extractor, mock_partial_extraction_no_dates):
    """Test extraction when dates are missing."""
    ticket_description = """
    Customer: John Doe (customer@example.com)
    Location: Downtown Parking Garage
    """
    
    mock_response = create_mock_gemini_response(mock_partial_extraction_no_dates)
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == "customer@example.com"
        assert result.name == "John Doe"
        assert result.arrival_date == ""
        assert result.exit_date == ""
        assert result.is_complete() is False  # Missing dates


@pytest.mark.asyncio
async def test_extract_minimal_required_fields(extractor, mock_minimal_extraction):
    """Test extraction with only required fields."""
    ticket_description = """
    Email: customer@example.com
    Parking: November 15-17, 2025
    """
    
    mock_response = create_mock_gemini_response(mock_minimal_extraction)
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == "customer@example.com"
        assert result.name is None
        assert result.arrival_date == "2025-11-15"
        assert result.exit_date == "2025-11-17"
        assert result.location is None
        assert result.is_complete() is True  # Has all required fields


# Test extraction with no information
@pytest.mark.asyncio
async def test_extract_no_customer_info(extractor, mock_empty_extraction):
    """Test extraction when no customer info is found."""
    ticket_description = """
    General inquiry about parking rates.
    """
    
    mock_response = create_mock_gemini_response(mock_empty_extraction)
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == ""
        assert result.is_complete() is False


# Test empty input handling
@pytest.mark.asyncio
async def test_extract_empty_text(extractor):
    """Test extraction with empty text."""
    result = await extractor.extract("")
    
    assert result.email == ""
    assert result.is_complete() is False


@pytest.mark.asyncio
async def test_extract_whitespace_only(extractor):
    """Test extraction with whitespace-only text."""
    result = await extractor.extract("   \n\t  ")
    
    assert result.email == ""
    assert result.is_complete() is False


# Test error handling
@pytest.mark.asyncio
async def test_llm_timeout_handling(extractor):
    """Test that LLM timeout is handled gracefully."""
    import asyncio
    
    ticket_description = "Customer: test@example.com, Date: Nov 15-17"
    
    # Simulate a timeout by raising TimeoutError
    with patch.object(
        extractor.client.models,
        'generate_content',
        side_effect=asyncio.TimeoutError("Timeout after 10 seconds")
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == ""
        assert result.is_complete() is False


@pytest.mark.asyncio
async def test_llm_json_parse_error(extractor):
    """Test handling of invalid JSON response from LLM."""
    ticket_description = "Customer: test@example.com, Date: Nov 15-17"
    
    mock_response = Mock()
    mock_response.text = "Invalid JSON {not valid}"
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        return_value=mock_response
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == ""
        assert result.is_complete() is False


@pytest.mark.asyncio
async def test_llm_api_error(extractor):
    """Test handling of LLM API errors."""
    ticket_description = "Customer: test@example.com, Date: Nov 15-17"
    
    with patch.object(
        extractor.client.models,
        'generate_content',
        side_effect=Exception("API Error: Rate limit exceeded")
    ):
        result = await extractor.extract(ticket_description)
        
        assert result.email == ""
        assert result.is_complete() is False


# Test prompt creation
def test_create_extraction_prompt(extractor):
    """Test that extraction prompt is created correctly."""
    ticket_description = "Test ticket with customer info"
    prompt = extractor._create_extraction_prompt(ticket_description)
    
    assert "Extract customer information" in prompt
    assert "Email" in prompt
    assert "Name" in prompt
    assert "Arrival Date" in prompt
    assert "Exit Date" in prompt
    assert "Location" in prompt
    assert ticket_description in prompt
    assert "ISO format" in prompt


# Test edge cases with dates
@pytest.mark.asyncio
async def test_extract_various_date_formats(extractor):
    """Test extraction handles various date formats."""
    test_cases = [
        {
            "input": {
                "email": "test@example.com",
                "arrival_date": "2025-11-15",
                "exit_date": "2025-11-17"
            },
            "expected_complete": True
        },
        {
            "input": {
                "email": "test@example.com",
                "arrival_date": "11/15/2025",
                "exit_date": "11/17/2025"
            },
            "expected_complete": True
        },
        {
            "input": {
                "email": "test@example.com",
                "arrival_date": "November 15, 2025",
                "exit_date": "November 17, 2025"
            },
            "expected_complete": True
        }
    ]
    
    for test_case in test_cases:
        mock_response = create_mock_gemini_response(test_case["input"])
        
        with patch.object(
            extractor.client.models,
            'generate_content',
            return_value=mock_response
        ):
            result = await extractor.extract("Test ticket")
            
            assert result.is_complete() == test_case["expected_complete"]


# Test whitespace handling in fields
def test_customer_info_whitespace_in_required_fields():
    """Test that whitespace in required fields is handled correctly."""
    # Leading/trailing whitespace should not affect validation
    info = CustomerInfo(
        email="  test@example.com  ",
        arrival_date="  2025-11-15  ",
        exit_date="  2025-11-17  "
    )
    # is_complete() checks if fields are non-empty after strip()
    assert info.is_complete() is True


def test_customer_info_only_whitespace_in_required_fields():
    """Test that only whitespace in required fields fails validation."""
    info = CustomerInfo(
        email="   ",
        arrival_date="   ",
        exit_date="   "
    )
    assert info.is_complete() is False
