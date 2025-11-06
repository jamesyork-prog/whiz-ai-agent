
import httpx

import parlant.sdk as p


@p.tool
async def get_ticket(context: p.ToolContext) -> p.ToolResult:
    """
    Retrieves the details of a specific Freshdesk ticket.

    Args:
        ticket_id (str): The ID of the ticket to retrieve.
    """
    ticket_id = context.inputs.get("ticket_id")
    # This function would make a GET request to the Freshdesk API:
    # /api/v2/tickets/{ticket_id}
    #
    # The result would be a JSON object containing the ticket details.
    # For now, we will return a mock result.
    mock_result = {
        "id": ticket_id,
        "subject": "Refund Request for Booking #12345",
        "description": "The customer is requesting a refund for their booking.",
        "status": 2,  # Open
        "priority": 1,  # Low
        "tags": [],
    }
    return p.ToolResult(result=mock_result, summary=f"Fetched ticket details for {ticket_id}")

@p.tool
async def add_note(context: p.ToolContext) -> p.ToolResult:
    """
    Adds a private note to a Freshdesk ticket.

    Args:
        ticket_id (str): The ID of the ticket to add the note to.
        note (str): The content of the note.
    """
    ticket_id = context.inputs.get("ticket_id")
    note = context.inputs.get("note")
    # This function would make a POST request to the Freshdesk API:
    # /api/v2/tickets/{ticket_id}/notes
    # with the note content in the request body.
    #
    # The result would be a confirmation of the note creation.
    # For now, we will return a mock result.
    mock_result = {
        "id": 123,
        "body": note,
        "private": True,
    }
    return p.ToolResult(result=mock_result, summary=f"Added note to ticket {ticket_id}")

@p.tool
async def update_ticket(context: p.ToolContext) -> p.ToolResult:
    """
    Updates the status, priority, and/or tags of a Freshdesk ticket.

    Args:
        ticket_id (str): The ID of the ticket to update.
        status (int, optional): The new status of the ticket.
        priority (int, optional): The new priority of the ticket.
        tags (list, optional): A list of tags to add to the ticket.
    """
    ticket_id = context.inputs.get("ticket_id")
    status = context.inputs.get("status")
    priority = context.inputs.get("priority")
    tags = context.inputs.get("tags")
    # This function would make a PUT request to the Freshdesk API:
    # /api/v2/tickets/{ticket_id}
    # with the updated fields in the request body.
    #
    # The result would be the updated ticket object.
    # For now, we will return a mock result.
    mock_result = {
        "id": ticket_id,
        "status": status,
        "priority": priority,
        "tags": tags,
    }
    return p.ToolResult(result=mock_result, summary=f"Updated ticket {ticket_id}")
