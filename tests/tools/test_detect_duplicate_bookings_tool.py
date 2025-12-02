"""
Tests for Duplicate Booking Detection Tool

Tests the Parlant tool integration including:
- ToolContext integration
- Successful duplicate detection and refund
- No duplicates scenario (deny)
- 3+ duplicates scenario (escalate)
- Error handling and escalation
- Result formatting for decision engine

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import parlant.sdk as p

from app_tools.tools.detect_duplicate_bookings_tool import detect_duplicate_bookings
from app_tools.tools.parkwhiz_client import (
    ParkWhizAuthenticationError,
    ParkWhizNotFoundError,
    ParkWhizTimeoutError,
    ParkWhizError,
)
from app_tools.tools.duplicate_booking_analyzer import DuplicateDetectionResult


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext for testing."""
    context = Mock(spec=p.ToolContext)
    context.agent_id = "test_agent"
    context.customer_id = "test_customer"
    context.session_id = "test_session"
    return context


@pytest.fixture
def sample_duplicate_bookings():
    """Sample bookings with duplicates (2 bookings, same location, overlapping time)."""
    return [
        {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed",  # Used
            "price_paid": {"USD": "15.0"},
        },
        {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "confirmed",  # Unused
            "price_paid": {"USD": "15.0"},
        },
    ]


@pytest.fixture
def sample_single_booking():
    """Sample with single booking (no duplicates)."""
    return [
        {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed",
            "price_paid": {"USD": "15.0"},
        }
    ]


@pytest.fixture
def sample_triple_duplicates():
    """Sample with 3 duplicate bookings (escalation scenario)."""
    return [
        {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed",
            "price_paid": {"USD": "15.0"},
        },
        {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "confirmed",
            "price_paid": {"USD": "15.0"},
        },
        {
            "id": 12347,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "pending",
            "price_paid": {"USD": "15.0"},
        },
    ]


# ============================================================================
# Successful Duplicate Detection and Refund Tests
# ============================================================================

@pytest.mark.asyncio
async def test_successful_duplicate_detection_and_refund(
    mock_tool_context, sample_duplicate_bookings
):
    """Test successful duplicate detection with automatic refund."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        # Mock client instance
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Mock get_customer_bookings to return duplicates
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_duplicate_bookings)
        
        # Mock delete_booking to return refund confirmation
        mock_client.delete_booking = AsyncMock(
            return_value={
                "success": True,
                "booking_id": 12346,
                "refund_amount": 15.00,
                "status": "cancelled",
            }
        )
        
        # Mock close method
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
            location_name="Downtown Garage",
        )
        
        # Verify result
        assert isinstance(result, p.ToolResult)
        assert result.data["has_duplicates"] is True
        assert result.data["action_taken"] == "refunded"
        assert result.data["refunded_booking_id"] == 12346
        assert result.data["kept_booking_id"] == 12345
        assert result.data["refund_amount"] == 15.00
        assert "explanation" in result.data
        
        # Verify summary
        assert "Refunded duplicate booking 12346" in result.metadata["summary"]
        
        # Verify client methods were called correctly
        mock_client.get_customer_bookings.assert_called_once()
        call_args = mock_client.get_customer_bookings.call_args
        assert call_args.kwargs["customer_email"] == "customer@example.com"
        assert call_args.kwargs["start_date"] == "2024-01-14"  # -1 day
        assert call_args.kwargs["end_date"] == "2024-01-16"  # +1 day
        
        mock_client.delete_booking.assert_called_once_with("12346")
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_detection_with_datetime_format(
    mock_tool_context, sample_duplicate_bookings
):
    """Test duplicate detection with datetime format (YYYY-MM-DDTHH:MM:SS)."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_duplicate_bookings)
        mock_client.delete_booking = AsyncMock(
            return_value={"success": True, "booking_id": 12346, "refund_amount": 15.00}
        )
        mock_client.close = AsyncMock()
        
        # Call with datetime format
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15T14:30:00Z",
            location_name="Downtown Garage",
        )
        
        # Verify result
        assert result.data["action_taken"] == "refunded"
        
        # Verify date range calculation
        call_args = mock_client.get_customer_bookings.call_args
        assert call_args.kwargs["start_date"] == "2024-01-14"
        assert call_args.kwargs["end_date"] == "2024-01-16"


# ============================================================================
# No Duplicates Scenario (Deny) Tests
# ============================================================================

@pytest.mark.asyncio
async def test_no_duplicates_deny(mock_tool_context, sample_single_booking):
    """Test no duplicates scenario returns deny action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_single_booking)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["has_duplicates"] is False
        assert result.data["action_taken"] == "deny"
        assert result.data["duplicate_count"] == 1
        assert "1 booking" in result.data["explanation"]
        
        # Verify no delete was called
        mock_client.delete_booking.assert_not_called()


@pytest.mark.asyncio
async def test_no_bookings_deny(mock_tool_context):
    """Test no bookings scenario returns deny action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=[])
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["has_duplicates"] is False
        assert result.data["action_taken"] == "deny"
        assert result.data["duplicate_count"] == 0
        assert "0 booking" in result.data["explanation"]


@pytest.mark.asyncio
async def test_different_locations_deny(mock_tool_context):
    """Test bookings at different locations returns deny."""
    bookings = [
        {
            "id": 12345,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 789, "name": "Downtown Garage"},
            "status": "completed",
        },
        {
            "id": 12346,
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T18:00:00Z",
            "location": {"id": 790, "name": "Airport Parking"},
            "status": "confirmed",
        },
    ]
    
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=bookings)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["has_duplicates"] is False
        assert result.data["action_taken"] == "deny"
        assert "different locations" in result.data["explanation"]


# ============================================================================
# 3+ Duplicates Scenario (Escalate) Tests
# ============================================================================

@pytest.mark.asyncio
async def test_three_duplicates_escalate(mock_tool_context, sample_triple_duplicates):
    """Test 3+ duplicates scenario returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_triple_duplicates)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["has_duplicates"] is True
        assert result.data["action_taken"] == "escalate"
        assert result.data["duplicate_count"] == 3
        assert "Too complex" in result.data["explanation"]
        
        # Verify no delete was called
        mock_client.delete_booking.assert_not_called()


# ============================================================================
# Error Handling and Escalation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_authentication_error_escalate(mock_tool_context):
    """Test authentication error returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Mock authentication error
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=ParkWhizAuthenticationError("Invalid credentials")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "authentication_failed"
        assert result.data["action_taken"] == "escalate"
        assert "authentication failed" in result.metadata["summary"].lower()


@pytest.mark.asyncio
async def test_timeout_error_escalate(mock_tool_context):
    """Test timeout error returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Mock timeout error
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=ParkWhizTimeoutError("Request timed out")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "api_timeout"
        assert result.data["action_taken"] == "escalate"
        assert "timeout" in result.metadata["summary"].lower()


@pytest.mark.asyncio
async def test_api_error_escalate(mock_tool_context):
    """Test general API error returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Mock API error
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=ParkWhizError("API error 500")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "api_error"
        assert result.data["action_taken"] == "escalate"


@pytest.mark.asyncio
async def test_refund_booking_not_found_escalate(mock_tool_context, sample_duplicate_bookings):
    """Test refund failure due to booking not found returns escalate."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_duplicate_bookings)
        
        # Mock delete_booking to raise not found error
        mock_client.delete_booking = AsyncMock(
            side_effect=ParkWhizNotFoundError("Booking not found")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "booking_not_found"
        assert result.data["action_taken"] == "escalate"
        assert "not found" in result.data["explanation"]


@pytest.mark.asyncio
async def test_refund_failure_escalate(mock_tool_context, sample_duplicate_bookings):
    """Test refund failure returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_duplicate_bookings)
        
        # Mock delete_booking to raise error
        mock_client.delete_booking = AsyncMock(
            side_effect=ParkWhizError("Refund processing failed")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "refund_failed"
        assert result.data["action_taken"] == "escalate"
        assert "refund failed" in result.data["explanation"].lower()


@pytest.mark.asyncio
async def test_analysis_failure_escalate(mock_tool_context):
    """Test analysis failure returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Return bookings that will cause analysis to fail
        mock_client.get_customer_bookings = AsyncMock(return_value=[{"invalid": "data"}])
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result - should handle gracefully
        assert result.data["action_taken"] == "deny"  # Malformed data results in no valid duplicates


@pytest.mark.asyncio
async def test_unexpected_error_escalate(mock_tool_context):
    """Test unexpected error returns escalate action."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Mock unexpected error
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify result
        assert result.data["error"] == "detection_failed"
        assert result.data["action_taken"] == "escalate"
        assert "Unexpected error" in result.data["message"]


# ============================================================================
# Result Formatting Tests
# ============================================================================

@pytest.mark.asyncio
async def test_result_format_for_decision_engine_refunded(
    mock_tool_context, sample_duplicate_bookings
):
    """Test result format is correct for decision engine when refunded."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_duplicate_bookings)
        mock_client.delete_booking = AsyncMock(
            return_value={"success": True, "booking_id": 12346, "refund_amount": 15.00}
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify all required fields for decision engine
        assert "has_duplicates" in result.data
        assert "action_taken" in result.data
        assert "refunded_booking_id" in result.data
        assert "kept_booking_id" in result.data
        assert "refund_amount" in result.data
        assert "explanation" in result.data
        assert "all_booking_ids" in result.data
        
        # Verify metadata has summary
        assert "summary" in result.metadata
        assert isinstance(result.metadata["summary"], str)


@pytest.mark.asyncio
async def test_result_format_for_decision_engine_deny(
    mock_tool_context, sample_single_booking
):
    """Test result format is correct for decision engine when denied."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_single_booking)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify all required fields for decision engine
        assert "has_duplicates" in result.data
        assert "action_taken" in result.data
        assert "duplicate_count" in result.data
        assert "explanation" in result.data
        assert "all_booking_ids" in result.data
        
        # Verify metadata has summary
        assert "summary" in result.metadata


@pytest.mark.asyncio
async def test_result_format_for_decision_engine_escalate(
    mock_tool_context, sample_triple_duplicates
):
    """Test result format is correct for decision engine when escalated."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_triple_duplicates)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify all required fields for decision engine
        assert "has_duplicates" in result.data
        assert "action_taken" in result.data
        assert "duplicate_count" in result.data
        assert "explanation" in result.data
        
        # Verify metadata has summary
        assert "summary" in result.metadata


# ============================================================================
# Safety Check Tests
# ============================================================================

@pytest.mark.asyncio
async def test_safety_check_missing_booking_ids(mock_tool_context):
    """Test safety check when booking IDs are missing."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        # Return bookings that will result in missing IDs
        bookings = [
            {
                "id": 12345,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"id": 789},
                "status": "completed",
            },
            {
                "id": 12346,
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T18:00:00Z",
                "location": {"id": 789},
                "status": "completed",  # Both used - should escalate
            },
        ]
        
        mock_client.get_customer_bookings = AsyncMock(return_value=bookings)
        mock_client.close = AsyncMock()
        
        # Call tool
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify escalation due to both bookings being used
        assert result.data["action_taken"] == "escalate"


# ============================================================================
# Invalid Input Tests
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_date_format(mock_tool_context):
    """Test handling of invalid date format."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        mock_client.close = AsyncMock()
        
        # Call with invalid date
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="invalid-date",
        )
        
        # Verify error response
        assert result.data["error"] == "invalid_date_format"
        assert "Invalid date format" in result.data["message"]


@pytest.mark.asyncio
async def test_optional_location_name(mock_tool_context, sample_single_booking):
    """Test that location_name parameter is optional."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_single_booking)
        mock_client.close = AsyncMock()
        
        # Call without location_name
        result = await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify it works without location_name
        assert result.data["action_taken"] == "deny"


# ============================================================================
# Client Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_client_cleanup_on_success(mock_tool_context, sample_single_booking):
    """Test that client is properly closed on success."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(return_value=sample_single_booking)
        mock_client.close = AsyncMock()
        
        # Call tool
        await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify close was called
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_client_cleanup_on_error(mock_tool_context):
    """Test that client is properly closed even on error."""
    with patch("app_tools.tools.detect_duplicate_bookings_tool.ParkWhizClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        
        mock_client.get_customer_bookings = AsyncMock(
            side_effect=ParkWhizError("API error")
        )
        mock_client.close = AsyncMock()
        
        # Call tool
        await detect_duplicate_bookings(
            context=mock_tool_context,
            customer_email="customer@example.com",
            event_date="2024-01-15",
        )
        
        # Verify close was called even though error occurred
        mock_client.close.assert_called_once()
