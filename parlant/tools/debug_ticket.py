import parlant.sdk as p
from .freshdesk_tools import get_ticket, get_ticket_conversations


@p.tool
async def debug_ticket_notes(context: p.ToolContext, ticket_id: str) -> p.ToolResult:
    """
    Debug tool to see exactly what notes are in a ticket.
    
    Args:
        ticket_id (str): The Freshdesk ticket ID
    """
    # Get conversations
    conv_result = await get_ticket_conversations(context, ticket_id)
    
    if "error" in conv_result.data:
        return p.ToolResult(
            {"error": "Failed to get conversations", "details": conv_result.data},
            metadata={"summary": "Error fetching conversations"}
        )
    
    conversations = conv_result.data.get("conversations", [])
    
    # Extract all note text - keep it minimal
    all_notes = []
    for i, conv in enumerate(conversations[:3]):  # Only first 3 conversations
        note_info = {
            "index": i,
            "private": conv.get("private", False),
            "body_text": conv.get("body_text", "")[:200],  # Only 200 chars
            "full_length": len(conv.get("body_text", ""))
        }
        all_notes.append(note_info)
    
    return p.ToolResult(
        {
            "ticket_id": ticket_id,
            "total_conversations": len(conversations),
            "showing_first": min(3, len(conversations)),
            "notes": all_notes
        },
        metadata={"summary": f"Found {len(conversations)} conversations, showing first 3"}
    )
