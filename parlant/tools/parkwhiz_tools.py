
import parlant.sdk as p
import httpx

@p.tool
async def get_booking(context: p.ToolContext) -> p.ToolResult:
    """
    Retrieves the details of a specific booking.

    Args:
        booking_id (str): The ID of the booking to retrieve.
    """
    booking_id = context.inputs.get("booking_id")
    # This function would make a GET request to the ParkWhiz API:
    # /v4/bookings/{booking_id}
    #
    # The result would be a JSON object containing the booking details.
    # For now, we will return a mock result.
    mock_result = {
        "booking_id": booking_id,
        "status": "active",
        "start_time": "2025-12-01T12:00:00Z",
        "end_time": "2025-12-01T15:00:00Z",
        "value": 25.00,
        "mor": "ParkWhiz",
        "product_type": "transient",
        "is_used": False,
        "is_reseller": False,
        "is_season_package": False,
    }
    return p.ToolResult(result=mock_result, summary=f"Fetched booking details for {booking_id}")

@p.tool
async def list_bookings(context: p.ToolContext) -> p.ToolResult:
    """
    Retrieves a list of a user's bookings.

    Args:
        customer_id (str): The ID of the customer to retrieve bookings for.
    """
    customer_id = context.inputs.get("customer_id")
    # This function would make a GET request to the ParkWhiz API:
    # /v4/bookings?customer_id={customer_id}
    #
    # The result would be a JSON array of booking objects.
    # For now, we will return a mock result.
    mock_result = [
        {
            "booking_id": "12345",
            "status": "active",
            "start_time": "2025-12-01T12:00:00Z",
            "end_time": "2025-12-01T15:00:00Z",
        },
        {
            "booking_id": "67890",
            "status": "active",
            "start_time": "2025-12-02T10:00:00Z",
            "end_time": "2025-12-02T11:00:00Z",
        },
    ]
    return p.ToolResult(result=mock_result, summary=f"Fetched bookings for customer {customer_id}")

@p.tool
async def cancel_booking(context: p.ToolContext) -> p.ToolResult:
    """
    Cancels a booking and processes a refund.

    Args:
        booking_id (str): The ID of the booking to cancel.
        reason (str): The reason for the cancellation.
    """
    booking_id = context.inputs.get("booking_id")
    reason = context.inputs.get("reason")
    # This function would make a POST request to the ParkWhiz API:
    # /v4/bookings/{booking_id}/cancel
    # with the reason in the request body.
    #
    # The result would be a confirmation of the cancellation.
    # For now, we will return a mock result.
    mock_result = {
        "booking_id": booking_id,
        "status": "canceled",
        "refund_status": "processed",
    }
    return p.ToolResult(result=mock_result, summary=f"Canceled booking {booking_id} for reason: {reason}")

@p.tool
async def get_account_information(context: p.ToolContext) -> p.ToolResult:
    """
    Retrieves the user's account details.

    Args:
        customer_id (str): The ID of the customer to retrieve information for.
    """
    customer_id = context.inputs.get("customer_id")
    # This function would make a GET request to the ParkWhiz API:
    # /v4/accounts/{customer_id}
    #
    # The result would be a JSON object containing the account details.
    # For now, we will return a mock result.
    mock_result = {
        "customer_id": customer_id,
        "name": "John Doe",
        "email": "john.doe@example.com",
    }
    return p.ToolResult(result=mock_result, summary=f"Fetched account information for customer {customer_id}")
