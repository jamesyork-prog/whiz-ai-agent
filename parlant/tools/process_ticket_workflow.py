import parlant.sdk as p
from .freshdesk_tools import get_ticket, get_ticket_description, get_ticket_conversations
from .lakera_security_tool import check_content
from .journey_helpers import extract_booking_info_from_note, triage_ticket
from .parkwhiz_tools import get_customer_orders


@p.tool
async def process_ticket_end_to_end(context: p.ToolContext, ticket_id: str) -> p.ToolResult:
    """
    Processes a Freshdesk ticket through the complete refund workflow autonomously.
    
    This tool orchestrates the entire ticket processing pipeline:
    1. Fetches ticket metadata, description, and conversations
    2. Runs security scan on content
    3. Extracts booking information
    4. Makes triage decision (Approved/Denied/Escalate)
    5. Returns the decision and reasoning
    
    Args:
        ticket_id (str): The Freshdesk ticket ID to process
    
    Returns:
        Complete analysis with decision, reasoning, and next steps
    """
    
    results = {
        "ticket_id": ticket_id,
        "steps_completed": [],
        "errors": []
    }
    
    # Step 1: Fetch ticket metadata
    ticket_result = await get_ticket(context, ticket_id)
    if "error" in ticket_result.data:
        return p.ToolResult(
            {"error": "Failed to fetch ticket", "details": ticket_result.data},
            metadata={"summary": f"Error processing ticket {ticket_id}"}
        )
    # Store only essential metadata, not full response
    results["ticket_metadata"] = {
        "id": ticket_result.data.get("id"),
        "subject": ticket_result.data.get("subject"),
        "status": ticket_result.data.get("status")
    }
    results["steps_completed"].append("Fetched ticket metadata")
    
    # Step 2: Fetch description
    desc_result = await get_ticket_description(context, ticket_id)
    description_text = ""
    if "error" not in desc_result.data:
        description_text = desc_result.data.get('description_text', '')
        results["steps_completed"].append("Fetched ticket description")
    
    # Step 3: Fetch conversations
    conv_result = await get_ticket_conversations(context, ticket_id)
    conversations = []
    if "error" not in conv_result.data:
        conversations = conv_result.data.get('conversations', [])
        results["steps_completed"].append("Fetched conversation history")
    
    # Step 4: Security scan
    # Combine description and subject for security check
    subject = results['ticket_metadata'].get('subject', '')
    content_to_check = f"{subject}\n\n{description_text}".strip()
    
    # Only run security scan if there's actual content
    if content_to_check:
        # Call check_content directly with content parameter
        # Create proper context with content in inputs
        from unittest.mock import Mock
        security_context = Mock()
        security_context.inputs = {'content': content_to_check}
        security_context.agent_id = context.agent_id
        security_context.customer_id = context.customer_id
        security_context.session_id = context.session_id
        
        security_result = await check_content(security_context)
        results["security_scan"] = security_result.data
        results["steps_completed"].append("Completed security scan")
        
        # Only escalate if actually flagged (not just missing data)
        if security_result.data.get("flagged", False):
            results["decision"] = "SECURITY_ESCALATION"
            results["reasoning"] = f"Content flagged by security scan: {security_result.data.get('categories', {})}"
            
            # Still add note and update ticket for security escalation
            note_text = "<h3>⚠️ Security Alert</h3>"
            note_text += f"<p><strong>Status:</strong> Flagged by automated security scan</p>"
            note_text += f"<p><strong>Categories:</strong> {security_result.data.get('categories', {})}</p>"
            note_text += f"<p><strong>Action Required:</strong> Manual security review needed</p>"
            
            from .freshdesk_tools import add_note, update_ticket
            await add_note(context, ticket_id, note_text)
            await update_ticket(context, ticket_id, tags=["security_flagged", "needs_review"])
            
            return p.ToolResult(
                {
                    "ticket_id": ticket_id,
                    "decision": "SECURITY_ESCALATION",
                    "reasoning": results["reasoning"],
                    "security_details": security_result.data,
                },
                metadata={"summary": f"Ticket {ticket_id}: Security escalation - flagged content"}
            )
    else:
        # No content to scan
        results["security_scan"] = {"safe": True, "flagged": False, "note": "No content to scan"}
        results["steps_completed"].append("Security scan skipped (no content)")
    
    # Step 5: Extract booking info
    # Combine ALL available text sources for booking extraction
    notes_text = f"Subject: {results['ticket_metadata'].get('subject', '')}\n\n"
    notes_text += f"Description: {description_text}\n\n"
    
    # Add all conversations (private notes contain booking info)
    if conversations:
        notes_text += "Private Notes:\n"
        for conv in conversations:
            # Use full body_text, not truncated
            notes_text += f"\n{conv.get('body_text', '')}\n"
    
    from unittest.mock import Mock
    booking_context = Mock()
    booking_context.inputs = {'ticket_notes': notes_text}
    booking_context.agent_id = context.agent_id
    booking_context.customer_id = context.customer_id
    booking_context.session_id = context.session_id
    
    booking_result = await extract_booking_info_from_note(booking_context)
    results["booking_info"] = booking_result.data
    results["steps_completed"].append("Extracted booking information")
    
    # Debug: Log what we're analyzing
    results["debug_notes_length"] = len(notes_text)
    results["debug_notes_sample"] = notes_text[:500] if notes_text else "No notes"
    
    # Step 6: If no booking info, try ParkWhiz API
    if not booking_result.data.get("booking_info"):
        # Try ParkWhiz API (would need customer email or other identifier)
        results["steps_completed"].append("No booking info in notes - would query ParkWhiz API")
        results["booking_info_source"] = "missing"
    else:
        results["booking_info_source"] = "ticket_notes"
    
    # Step 7: Triage decision
    from unittest.mock import Mock
    triage_context = Mock()
    triage_context.inputs = {
        'ticket_data': results['ticket_metadata'],
        'booking_info': results['booking_info'].get('booking_info'),
        'refund_policy': "Standard refund policy applies"  # Would come from retriever
    }
    triage_context.agent_id = context.agent_id
    triage_context.customer_id = context.customer_id
    triage_context.session_id = context.session_id
    
    triage_result = await triage_ticket(triage_context)
    results["triage_decision"] = triage_result.data
    results["steps_completed"].append("Completed triage analysis")
    
    # Final summary - keep it concise to stay under 16KB
    decision = triage_result.data.get("decision", "Needs Human Review")
    reasoning = triage_result.data.get("reasoning", "Analysis complete")
    
    # Step 8: Add note to ticket with decision (HTML formatted for Freshdesk)
    # Check security status properly
    is_safe = results['security_scan'].get('safe', True) and not results['security_scan'].get('flagged', False)
    
    # Build detailed reasoning based on what was found
    detailed_reasoning = reasoning
    if decision == "Needs Human Review":
        reasons = []
        if results['booking_info_source'] == 'missing':
            reasons.append("No booking information found in ticket notes or description")
        if not is_safe:
            reasons.append("Security scan flagged content for review")
        if triage_result.data.get('confidence') == 'pending':
            reasons.append("Insufficient data to make automated decision")
        
        if reasons:
            detailed_reasoning += "<br><br><strong>Specific reasons for human review:</strong><ul>"
            for reason in reasons:
                detailed_reasoning += f"<li>{reason}</li>"
            detailed_reasoning += "</ul>"
    
    note_text = "<h3>🤖 Automated Analysis Complete</h3>"
    note_text += f"<p><strong>Decision:</strong> {decision}</p>"
    note_text += f"<p><strong>Analysis:</strong> {detailed_reasoning}</p>"
    note_text += f"<p><strong>Security Status:</strong> {'✅ Safe' if is_safe else '⚠️ Flagged'}</p>"
    note_text += f"<p><strong>Booking Info:</strong> {'✅ Found' if results['booking_info_source'] != 'missing' else '❌ Not found in ticket'}</p>"
    note_text += f"<p><strong>Policy Applied:</strong> {triage_result.data.get('policy_applied', 'Standard refund policy')}</p>"
    note_text += f"<p><strong>Confidence:</strong> {triage_result.data.get('confidence', 'N/A')}</p>"
    note_text += f"<hr><p><em>Automated by Whiz AI Agent</em></p>"
    
    from .freshdesk_tools import add_note, update_ticket
    
    note_result = await add_note(context, ticket_id, note_text)
    if "error" not in note_result.data:
        results["steps_completed"].append("Added analysis note to ticket")
    
    # Step 9: Update ticket tags based on decision
    tags = []
    if decision == "Approved":
        tags = ["refund_approved", "automated_decision"]
    elif decision == "Denied":
        tags = ["refund_denied", "automated_decision"]
    else:
        tags = ["needs_human_review", "automated_analysis"]
    
    update_result = await update_ticket(context, ticket_id, tags=tags)
    if "error" not in update_result.data:
        results["steps_completed"].append("Updated ticket tags")
    
    # Return only essential information with minimal debug data
    return p.ToolResult(
        {
            "ticket_id": ticket_id,
            "decision": decision,
            "reasoning": reasoning,
            "policy_applied": triage_result.data.get("policy_applied", ""),
            "confidence": triage_result.data.get("confidence", ""),
            "recommended_action": triage_result.data.get("recommended_action", ""),
            "steps_completed": results["steps_completed"],
            "security_status": "safe" if (results["security_scan"].get("safe", True) and not results["security_scan"].get("flagged", False)) else "flagged",
            "booking_info_found": results["booking_info_source"] != "missing",
            "note_added": "error" not in note_result.data,
            "ticket_updated": "error" not in update_result.data,
            "debug": {
                "notes_length": results.get("debug_notes_length", 0),
                "notes_sample": results.get("debug_notes_sample", "")[:200],  # Only 200 chars
                "booking_found": results["booking_info"].get("found", False),
                "security_flagged": results["security_scan"].get("flagged", False)
            }
        },
        metadata={"summary": f"Ticket {ticket_id}: {decision} - Note added, tags updated"}
    )
