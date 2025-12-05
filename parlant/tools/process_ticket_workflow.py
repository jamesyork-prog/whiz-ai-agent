import parlant.sdk as p
import os
from datetime import datetime
from .freshdesk_tools import get_ticket, get_ticket_description, get_ticket_conversations
from .lakera_security_tool import check_content
from .journey_helpers import extract_booking_info_from_note, triage_ticket
from .structured_logger import (
    configure_structured_logging,
    log_journey_start,
    log_journey_end,
    log_tool_execution,
    log_decision_outcome,
    log_error_with_context
)
from .zapier_failure_detector import ZapierFailureDetector
from .customer_info_extractor import CustomerInfoExtractor
from .decision_guard import DecisionGuard
from .verification_note_generator import VerificationNoteGenerator

# Configure structured logging
logger = configure_structured_logging(
    level=os.getenv("WEBHOOK_LOG_LEVEL", "INFO"),
    component_name="process_ticket_workflow"
)


def _is_paid_again_claim(ticket_text: str) -> bool:
    """
    Detect if ticket mentions 'paid again' or similar duplicate charge claims.
    
    This function distinguishes between:
    - Duplicate bookings (two separate reservations for same event)
    - Overstay charges (additional fees at exit for exceeding booking time)
    
    Args:
        ticket_text (str): Combined ticket text (subject + description + conversations)
    
    Returns:
        bool: True if ticket contains duplicate charge keywords AND not an overstay scenario
    """
    if not ticket_text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = ticket_text.lower()
    
    # Exclusion keywords that indicate overstay/exit charges (NOT duplicates)
    overstay_keywords = [
        "additional",
        "overstay",
        "over stay",
        "exceeded",
        "extra time",
        "stayed longer",
        "exit",
        "release",
        "retrieve",
        "pick up",
        "attendant",
        "gate",
        "before they would release",
        "additional.*due",
        "told.*due",
        "had to pay.*leave",
        "pay.*exit",
        "pay.*retrieve",
    ]
    
    # Check if this is an overstay scenario first
    if any(keyword in text_lower for keyword in overstay_keywords):
        # If overstay keywords present, NOT a duplicate booking
        return False
    
    # Keywords that indicate duplicate charge claims
    duplicate_keywords = [
        "paid again",
        "charged twice",
        "double charged",
        "charged multiple times",
        "billed twice",
        "duplicate charge",
        "charged me again",
        "two bookings",
        "booked twice",
        "duplicate booking",
        "charged 2 times",
        "paid 2 times",
        "paid two times",
        "charged two times",
        "double payment",
        "duplicate payment",
        "two reservations",
        "multiple reservations",
        "same event",
        "same date",
    ]
    
    return any(keyword in text_lower for keyword in duplicate_keywords)


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
    start_time = datetime.utcnow()
    
    # Log journey start
    log_journey_start(logger, ticket_id, "Automated Ticket Processing")
    
    results = {
        "ticket_id": ticket_id,
        "steps_completed": [],
        "errors": []
    }
    
    try:
    
        # Step 1: Fetch ticket metadata
        log_tool_execution(logger, ticket_id, "get_ticket")
        ticket_result = await get_ticket(context, ticket_id)
        if "error" in ticket_result.data:
            log_tool_execution(logger, ticket_id, "get_ticket", success=False, error=str(ticket_result.data))
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
        log_tool_execution(logger, ticket_id, "get_ticket_description")
        desc_result = await get_ticket_description(context, ticket_id)
        description_text = ""
        if "error" not in desc_result.data:
            description_text = desc_result.data.get('description_text', '')
            results["steps_completed"].append("Fetched ticket description")
        
        # Step 3: Fetch conversations
        log_tool_execution(logger, ticket_id, "get_ticket_conversations")
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
            
            log_tool_execution(logger, ticket_id, "check_content")
            security_result = await check_content(security_context)
            results["security_scan"] = security_result.data
            results["steps_completed"].append("Completed security scan")
        
            # Only escalate if actually flagged (not just missing data)
            if security_result.data.get("flagged", False):
                results["decision"] = "SECURITY_ESCALATION"
                results["reasoning"] = f"Content flagged by security scan: {security_result.data.get('categories', {})}"
                
                # Log security escalation decision
                log_decision_outcome(logger, ticket_id, "SECURITY_ESCALATION", reasoning=results["reasoning"])
                
                # Build shadcn-style security alert note
                from html import escape
                categories = security_result.data.get('categories', {})
                categories_str = ', '.join([f"{k}: {v}" for k, v in categories.items()]) if categories else "Unknown"
                
                note_parts = [
                    # Card container with soft blue glow (reduced width + margin for glow visibility)
                    "<div style='background-color: #ffffff; border: 1px solid #bae6fd; border-radius: 8px; "
                    "box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(32, 185, 226, 0.1); overflow: hidden; "
                    "font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; max-width: 580px; margin: 10px;'>",
                    
                    # Header
                    "<div style='padding: 24px 24px 10px 24px; display: flex; align-items: flex-start; justify-content: space-between;'>",
                    "<div>",
                    "<h3 style='margin: 0; font-size: 18px; font-weight: 700; color: #0f172a;'>",
                    "⚠️ Security Alert</h3>",
                    "<p style='margin: 4px 0 0 0; font-size: 13px; color: #64748b;'>Automated security scan</p>",
                    "</div>",
                    # Badge
                    "<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
                    "padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
                    "color: #991b1b; background-color: #fee2e2;'>FLAGGED</span>",
                    "</div>",
                    
                    # Content
                    "<div style='padding: 0 24px 24px 24px;'>",
                    
                    # Alert box
                    "<div style='border: 1px solid #fca5a5; background-color: #fef2f2; color: #991b1b; "
                    "border-radius: 6px; padding: 12px 16px; margin-top: 8px; font-size: 13px;'>"
                    "<div style='font-weight: 600; margin-bottom: 4px;'>Content Flagged by Security Scan</div>"
                    "<div style='font-weight: 600;'>This ticket contains content that triggered automated security filters and requires manual review.</div>"
                    "</div>",
                    
                    # Categories
                    "<div style='background-color: #f8fafc; padding: 16px; border-radius: 6px; margin-top: 16px;'>"
                    "<div style='font-size: 12px; font-weight: 500; color: #64748b; margin-bottom: 4px;'>Detected Categories</div>"
                    f"<div style='font-size: 14px; color: #0f172a;'>{escape(categories_str)}</div>"
                    "</div>",
                    
                    # Action required
                    "<div style='background-color: #fffaf0; border: 1px solid #fed7aa; border-radius: 6px; "
                    "padding: 12px 16px; margin-top: 16px; font-size: 13px;'>"
                    "<div style='font-weight: 600; color: #92400e; margin-bottom: 4px;'>🔒 Action Required</div>"
                    "<div style='color: #78350f;'>Manual security review needed before processing this ticket.</div>"
                    "</div>",
                    
                    "</div>",  # End content
                    
                    # Footer
                    "<div style='border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 24px;'>"
                    "<div style='font-size: 12px; color: #64748b;'>Scanned by Lakera Guard</div>"
                    "</div>",
                    
                    "</div>",  # End card
                ]
                
                note_text = "".join(note_parts)
                
                from .freshdesk_tools import add_note, update_ticket
                log_tool_execution(logger, ticket_id, "add_note")
                await add_note(context, ticket_id, note_text)
                log_tool_execution(logger, ticket_id, "update_ticket")
                await update_ticket(context, ticket_id, tags=["security_flagged", "needs_review"])
                
                # Log journey end
                processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                log_journey_end(logger, ticket_id, "Automated Ticket Processing", processing_time_ms, "SECURITY_ESCALATION")
                
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
        
        log_tool_execution(logger, ticket_id, "extract_booking_info_from_note")
        booking_result = await extract_booking_info_from_note(booking_context)
        results["booking_info"] = booking_result.data
        results["steps_completed"].append("Extracted booking information")
    
        # Debug: Log what we're analyzing
        results["debug_notes_length"] = len(notes_text)
        results["debug_notes_sample"] = notes_text[:500] if notes_text else "No notes"
        
        # Step 6: Detect Zapier failures and verify booking if needed
        zapier_detector = ZapierFailureDetector()
        booking_info = booking_result.data.get("booking_info", {})
        booking_id = booking_info.get("booking_id")
        
        # Check if Zapier failed or booking ID is invalid
        zapier_failure = zapier_detector.is_zapier_failure(notes_text)
        invalid_booking_id = zapier_detector.is_invalid_booking_id(booking_id)
        
        verification_result = None
        verified_booking = None
        
        if zapier_failure or invalid_booking_id:
            logger.info(
                f"Zapier failure detected for ticket {ticket_id} - booking verification disabled due to API limitations",
                extra={
                    "ticket_id": ticket_id,
                    "zapier_failure": zapier_failure,
                    "invalid_booking_id": invalid_booking_id,
                    "booking_id": booking_id,
                    "reason": "ParkWhiz API cannot search bookings by customer email"
                }
            )
            results["steps_completed"].append("Zapier failure detected - verification unavailable (API limitation)")
        
        # Set booking info source based on verification
        if verified_booking:
            results["booking_info_source"] = "parkwhiz_api_verified"
        elif not booking_result.data.get("booking_info"):
            results["booking_info_source"] = "missing"
        else:
            results["booking_info_source"] = "ticket_notes"
        
        # Step 6.5: Check for "paid again" / duplicate claims
        duplicate_detection_result = None
        if _is_paid_again_claim(notes_text):
            logger.info(f"Detected duplicate booking claim in ticket {ticket_id} - escalating to human review")
            results["steps_completed"].append("Detected duplicate booking claim - escalating for manual verification")
            
            duplicate_detection_result = type('obj', (object,), {
                'data': {
                    "action_taken": "escalate",
                    "explanation": (
                        "Customer reports being charged for multiple bookings for the same event. "
                        "This requires manual review to verify if duplicate reservations exist in the system. "
                        "A specialist will check the customer's account history to locate any duplicate bookings."
                    ),
                    "has_duplicates": None,
                    "api_limitation": True
                }
            })()
            
            results["duplicate_detection"] = duplicate_detection_result.data
            results["steps_completed"].append("Duplicate claim flagged for human review")
        
        # Step 7: Make decision based on duplicate detection or triage
        # If duplicate detection was run, use its results for decision
        if duplicate_detection_result:
            detection_data = duplicate_detection_result.data
            action_taken = detection_data.get("action_taken")
            
            if action_taken == "refunded":
                # Duplicate found and refunded - APPROVE
                decision = "Approved"
                reasoning = (
                    f"Duplicate booking detected and refunded. "
                    f"Refunded booking {detection_data.get('refunded_booking_id')}, "
                    f"kept booking {detection_data.get('kept_booking_id')}. "
                    f"{detection_data.get('explanation', '')}"
                )
                confidence = "high"
                policy_applied = "Duplicate Booking Detection"
                refunded = True
                
            elif action_taken == "escalate":
                # 3+ duplicates or error - ESCALATE
                decision = "Needs Human Review"
                reasoning = f"Duplicate detection requires human review. {detection_data.get('explanation', '')}"
                confidence = "medium"
                policy_applied = "Duplicate Booking Detection"
                refunded = False
                
            elif action_taken == "deny":
                # No duplicates found - DENY
                decision = "Denied"
                reasoning = f"No duplicate bookings found. {detection_data.get('explanation', '')}"
                confidence = "high"
                policy_applied = "Duplicate Booking Detection"
                refunded = False
                
            else:
                # Unknown action or error - ESCALATE
                decision = "Needs Human Review"
                reasoning = f"Duplicate detection inconclusive. {detection_data.get('explanation', 'Unknown error')}"
                confidence = "low"
                policy_applied = "Duplicate Booking Detection"
                refunded = False
            
            results["triage_decision"] = {
                "decision": decision,
                "reasoning": reasoning,
                "confidence": confidence,
                "policy_applied": policy_applied,
                "duplicate_detection_used": True,
                "refunded": refunded,
                "method_used": "rules"  # Duplicate detection uses rule-based logic
            }
            results["steps_completed"].append("Decision made based on duplicate detection")
            
        else:
            # No duplicate detection - check if we should use verified data or escalate
            if verification_result and verification_result.success and verified_booking:
                # Use verified booking data for decision
                decision_guard = DecisionGuard()
                
                # Check if automated decision is safe
                can_decide = decision_guard.can_make_automated_decision(verified_booking)
                should_escalate, escalation_reason = decision_guard.should_escalate(
                    verified_booking,
                    verification_result.customer_info,
                    verification_result.failure_reason
                )
                
                if should_escalate or not can_decide:
                    # Escalate to human review
                    decision = "Needs Human Review"
                    reasoning = escalation_reason or "Booking verified but requires human review"
                    confidence = "medium"
                    policy_applied = "Booking Verification"
                    refunded = False
                    
                    logger.info(
                        f"Escalating ticket {ticket_id} after verification",
                        extra={
                            "ticket_id": ticket_id,
                            "reason": escalation_reason,
                            "booking_id": verified_booking.booking_id
                        }
                    )
                    
                else:
                    # Use standard triage with verified booking data
                    from unittest.mock import Mock
                    triage_context = Mock()
                    
                    # Include full ticket text and VERIFIED booking info
                    full_ticket_data = results['ticket_metadata'].copy()
                    full_ticket_data['description'] = notes_text
                    
                    # Use verified booking data instead of customer-provided
                    verified_booking_info = {
                        "booking_id": verified_booking.booking_id,
                        "customer_email": verified_booking.customer_email,
                        "event_date": verified_booking.arrival_date,
                        "location": verified_booking.location,
                        "pass_used": verified_booking.pass_used,
                        "pass_usage_status": verified_booking.pass_usage_status,
                        "amount_paid": verified_booking.amount_paid,
                        "verified": True  # Flag to indicate this is verified data
                    }
                    
                    triage_context.inputs = {
                        'ticket_data': full_ticket_data,
                        'booking_info': verified_booking_info,
                        'ticket_notes': notes_text,  # Include full notes for vehicle classification
                        'refund_policy': "Standard refund policy applies"
                    }
                    triage_context.agent_id = context.agent_id
                    triage_context.customer_id = context.customer_id
                    triage_context.session_id = context.session_id
                    
                    log_tool_execution(logger, ticket_id, "triage_ticket")
                    triage_result = await triage_ticket(triage_context)
                    
                    decision = triage_result.data.get("decision", "Needs Human Review")
                    reasoning = triage_result.data.get("reasoning", "Analysis complete")
                    confidence = triage_result.data.get("confidence", "N/A")
                    policy_applied = triage_result.data.get("policy_applied", "Standard refund policy")
                    method_used = triage_result.data.get("method_used", "unknown")
                    refunded = False
                    
                    # Add note that decision used verified data
                    reasoning += " (Decision based on ParkWhiz verified booking data)"
                    
                    logger.info(
                        f"Decision made using verified booking data for ticket {ticket_id}",
                        extra={
                            "ticket_id": ticket_id,
                            "decision": decision,
                            "booking_id": verified_booking.booking_id
                        }
                    )
                
                results["triage_decision"] = {
                    "decision": decision,
                    "reasoning": reasoning,
                    "confidence": confidence,
                    "policy_applied": policy_applied,
                    "duplicate_detection_used": False,
                    "refunded": refunded,
                    "used_verified_data": True,
                    "method_used": method_used
                }
                results["steps_completed"].append("Decision made using verified booking data")
                
            elif verification_result and not verification_result.success:
                # Verification failed - escalate
                decision = "Needs Human Review"
                reasoning = verification_result.failure_reason or "Booking verification failed"
                confidence = "low"
                policy_applied = "Booking Verification"
                refunded = False
                
                logger.info(
                    f"Escalating ticket {ticket_id} due to verification failure",
                    extra={
                        "ticket_id": ticket_id,
                        "failure_reason": verification_result.failure_reason
                    }
                )
                
                results["triage_decision"] = {
                    "decision": decision,
                    "reasoning": reasoning,
                    "confidence": confidence,
                    "policy_applied": policy_applied,
                    "duplicate_detection_used": False,
                    "refunded": refunded,
                    "used_verified_data": False,
                    "method_used": "rules"  # Verification failure uses rule-based escalation
                }
                results["steps_completed"].append("Escalated due to verification failure")
                
            else:
                # No verification attempted - use standard triage
                from unittest.mock import Mock
                triage_context = Mock()
                
                # Include full ticket text (description + conversations) for rule matching
                full_ticket_data = results['ticket_metadata'].copy()
                full_ticket_data['description'] = notes_text  # Include all notes for keyword matching
                
                triage_context.inputs = {
                    'ticket_data': full_ticket_data,
                    'booking_info': results['booking_info'].get('booking_info'),
                    'ticket_notes': notes_text,  # Include full notes for vehicle classification
                    'refund_policy': "Standard refund policy applies"  # Would come from retriever
                }
                triage_context.agent_id = context.agent_id
                triage_context.customer_id = context.customer_id
                triage_context.session_id = context.session_id
                
                log_tool_execution(logger, ticket_id, "triage_ticket")
                triage_result = await triage_ticket(triage_context)
                results["triage_decision"] = triage_result.data
                results["triage_decision"]["duplicate_detection_used"] = False
                results["triage_decision"]["refunded"] = False
                results["triage_decision"]["used_verified_data"] = False
                results["steps_completed"].append("Completed triage analysis")
                
                # Extract decision info from triage
                decision = triage_result.data.get("decision", "Needs Human Review")
                reasoning = triage_result.data.get("reasoning", "Analysis complete")
                confidence = triage_result.data.get("confidence", "N/A")
                policy_applied = triage_result.data.get("policy_applied", "Standard refund policy")
                method_used = triage_result.data.get("method_used", "unknown")
                refunded = False
        
        # Log decision outcome
        log_decision_outcome(
            logger,
            ticket_id,
            decision,
            confidence=confidence,
            reasoning=reasoning
        )
        
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
            if confidence == 'pending' or confidence == 'low':
                reasons.append("Insufficient data to make automated decision")
            
            if reasons:
                detailed_reasoning += "<br><br><strong>Specific reasons for human review:</strong><ul>"
                for reason in reasons:
                    detailed_reasoning += f"<li>{reason}</li>"
                detailed_reasoning += "</ul>"
        
        # Build shadcn-style HTML note
        from html import escape
        
        # Determine badge style based on decision
        if decision == "Approved":
            badge_bg = "#dcfce7"
            badge_color = "#166534"
            badge_text = "APPROVED"
        elif decision == "Denied":
            badge_bg = "#fee2e2"
            badge_color = "#991b1b"
            badge_text = "DENIED"
        else:
            # NEEDS REVIEW - red like Denied
            badge_bg = "#fee2e2"
            badge_color = "#991b1b"
            badge_border = "#fca5a5"
            badge_text = "NEEDS REVIEW"
        
        # Determine if LLM was used for deeper analysis
        # Extract method_used from triage_decision if available
        method_used = results.get("triage_decision", {}).get("method_used", "unknown")
        used_llm = method_used in ["llm", "hybrid"]
        
        logger.info(f"Title generation: method_used={method_used}, used_llm={used_llm}")
        
        # Build title with optional "Ultrathink" when LLM is used
        if used_llm:
            title_html = (
                "<span style='background: linear-gradient(90deg, #0c4a6e 0%, #20B9E2 100%); "
                "-webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Whiz</span> "
                "<span style='background: linear-gradient(90deg, #8b5cf6 0%, #ec4899 50%, #f59e0b 100%); "
                "-webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; "
                "animation: rainbow-shift 3s ease-in-out infinite;'>Ultrathink</span> "
                "<span style='color: #0f172a;'>Analysis</span>"
            )
            subtitle = "AI-powered analysis"
        else:
            title_html = (
                "<span style='background: linear-gradient(90deg, #0c4a6e 0%, #20B9E2 100%); "
                "-webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Whiz</span> "
                "<span style='color: #0f172a;'>Analysis</span>"
            )
            subtitle = "Automated refund decision"
        
        note_parts = [
            # Add CSS animation for rainbow gradient (only if LLM used)
            "<style>@keyframes rainbow-shift { "
            "0%, 100% { background-position: 0% 50%; } "
            "50% { background-position: 100% 50%; } "
            "}</style>" if used_llm else "",
            
            # Card container with soft blue glow (reduced width + margin for glow visibility)
            "<div style='background-color: #ffffff; border: 1px solid #bae6fd; border-radius: 8px; "
            "box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(32, 185, 226, 0.1); overflow: hidden; "
            "font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; max-width: 580px; margin: 10px;'>",
            
            # Header
            "<div style='padding: 24px 24px 10px 24px; display: flex; align-items: flex-start; justify-content: space-between;'>",
            "<div>",
            f"<h3 style='margin: 0; font-size: 18px; font-weight: 700;'>{title_html}</h3>",
            f"<p style='margin: 4px 0 0 0; font-size: 13px; color: #64748b;'>{subtitle}</p>",
            "</div>",
        ]
        
        # Badge
        if decision == "Needs Human Review":
            note_parts.append(
                f"<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
                f"padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
                f"border: 1px solid {badge_border}; color: {badge_color}; background-color: {badge_bg};'>{badge_text}</span>"
            )
        else:
            note_parts.append(
                f"<span style='display: inline-flex; align-items: center; border-radius: 9999px; "
                f"padding: 2px 10px; font-size: 11px; font-weight: 600; line-height: 1; white-space: nowrap; "
                f"color: {badge_color}; background-color: {badge_bg};'>{badge_text}</span>"
            )
        
        note_parts.append("</div>")
        
        # Content
        note_parts.append("<div style='padding: 0 24px 24px 24px;'>")
        
        # Analysis text - bold the reasoning
        note_parts.append(
            f"<div style='margin-top: 8px;'>"
            f"<p style='margin: 0; font-size: 14px; line-height: 1.6; color: #334155; font-weight: 600;'>{detailed_reasoning}</p>"
            f"</div>"
        )
        
        # Details grid with pill-style badges - centered and spaced
        note_parts.append(
            "<div style='display: flex; justify-content: center; gap: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e2e8f0;'>"
        )
        
        # Security pill
        if is_safe:
            security_bg = "#dcfce7"
            security_color = "#166534"
            security_text = "Safe"
            security_icon = "✓"
        else:
            security_bg = "#fee2e2"
            security_color = "#991b1b"
            security_text = "Flagged"
            security_icon = "⚠"
        
        note_parts.append(
            f"<div style='background-color: {security_bg}; color: {security_color}; "
            f"padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; text-align: center; min-width: 100px;'>"
            f"<div style='font-size: 11px; opacity: 0.7; margin-bottom: 4px;'>Security</div>"
            f"<div style='font-size: 14px;'>{security_icon} {security_text}</div>"
            f"</div>"
        )
        
        # Confidence pill with colored background and text (ensure proper capitalization)
        # Handle various confidence formats: "high", "HIGH", "High" -> "High"
        if confidence:
            confidence_display = confidence.strip().capitalize()
        else:
            confidence_display = "Unknown"
        
        confidence_styles = {
            "High": {"bg": "#dcfce7", "color": "#166534", "label_color": "#15803d"},
            "Medium": {"bg": "#fef3c7", "color": "#92400e", "label_color": "#a16207"},
            "Low": {"bg": "#fee2e2", "color": "#991b1b", "label_color": "#b91c1c"}
        }
        conf_style = confidence_styles.get(confidence_display, {"bg": "#f1f5f9", "color": "#475569", "label_color": "#64748b"})
        
        note_parts.append(
            f"<div style='background-color: {conf_style['bg']}; "
            f"padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; text-align: center; min-width: 100px;'>"
            f"<div style='font-size: 11px; color: {conf_style['label_color']}; margin-bottom: 4px;'>Confidence</div>"
            f"<div style='font-size: 14px; color: {conf_style['color']};'>{escape(confidence_display)}</div>"
            f"</div>"
        )
        
        # Booking ID pill - green if found, red if not found
        booking_id_display = "N/A"
        booking_id_found = False
        
        if verified_booking:
            booking_id_display = verified_booking.booking_id
            booking_id_found = True
        elif results.get('booking_info'):
            # booking_info is nested: results['booking_info']['booking_info']['booking_id']
            nested_booking = results['booking_info'].get('booking_info', {})
            booking_id_value = nested_booking.get('booking_id', 'N/A')
            if booking_id_value and booking_id_value != 'N/A':
                booking_id_display = booking_id_value
                booking_id_found = True
        
        # Color-code based on whether booking ID was found
        if booking_id_found:
            booking_bg = "#dcfce7"
            booking_color = "#166534"
            booking_label_color = "#15803d"
        else:
            booking_bg = "#fee2e2"
            booking_color = "#991b1b"
            booking_label_color = "#b91c1c"
        
        note_parts.append(
            f"<div style='background-color: {booking_bg}; "
            f"padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; text-align: center; min-width: 100px;'>"
            f"<div style='font-size: 11px; color: {booking_label_color}; margin-bottom: 4px;'>Booking ID</div>"
            f"<div style='font-size: 14px; color: {booking_color}; font-family: monospace;'>{escape(str(booking_id_display))}</div>"
            f"</div>"
        )
        
        note_parts.append("</div>")  # End pills row
        
        # Policy & Refund info in clean cards
        note_parts.append(
            "<div style='display: flex; gap: 8px; margin-top: 12px;'>"
        )
        
        note_parts.append(
            f"<div style='flex: 1; background-color: #f8fafc; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 4px;'>Policy Applied</div>"
            f"<div style='font-size: 13px; font-weight: 600; color: #0f172a;'>{escape(policy_applied)}</div>"
            f"</div>"
        )
        
        # Refunded card matching Policy Applied style with icon
        if refunded:
            refund_icon = "✓"  # Checkmark for Yes
            refund_text = "Yes"
        else:
            refund_icon = "⚠"  # Warning triangle for No
            refund_text = "No"
        
        note_parts.append(
            f"<div style='flex: 1; background-color: #f8fafc; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;'>"
            f"<div style='font-size: 11px; font-weight: 500; color: #64748b; margin-bottom: 4px;'>Refunded</div>"
            f"<div style='font-size: 13px; font-weight: 600; color: #0f172a;'>{refund_icon} {refund_text}</div>"
            f"</div>"
        )
        
        note_parts.append("</div>")  # End cards row
        
        # Discrepancies alert (if any exist from verification)
        if verified_booking and hasattr(verified_booking, 'discrepancies') and verified_booking.discrepancies:
            note_parts.append(
                "<div style='border: 1px solid #fca5a5; background-color: #fef2f2; color: #991b1b; "
                "border-radius: 6px; padding: 12px 16px; margin-top: 20px; font-size: 13px;'>"
                "<div style='margin-bottom: 4px; font-weight: 600; display: flex; align-items: center; gap: 8px;'>"
                "⚠️ Discrepancies Detected</div>"
                "<ul style='margin: 4px 0 0 24px; padding: 0; line-height: 1.5; color: #7f1d1d;'>"
            )
            for discrepancy in verified_booking.discrepancies:
                note_parts.append(f"<li>{escape(discrepancy)}</li>")
            note_parts.append("</ul></div>")
        
        note_parts.append("</div>")  # End content
        
        # Footer
        verification_source = {
            'parkwhiz_api_verified': 'Verified via ParkWhiz API',
            'ticket_notes': 'From ticket notes',
            'not_found': 'No booking data'
        }.get(results.get('booking_info_source'), 'Unknown source')
        
        note_parts.append(
            "<div style='border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 24px; "
            "display: flex; align-items: center; justify-content: space-between;'>"
            f"<div style='font-size: 12px; color: #64748b;'>{verification_source}</div>"
            f"<a href='https://forms.gle/NdDu8GKguHXXmqyYA?entry.ticket_id={ticket_id}' target='_blank' "
            f"style='display: inline-flex; align-items: center; justify-content: center; "
            f"background: linear-gradient(90deg, #0c4a6e 0%, #20B9E2 100%); "
            f"color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; "
            f"text-decoration: none; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); "
            f"transition: box-shadow 0.2s, transform 0.1s;'>Report Issue</a>"
            "</div>"
        )
        
        note_parts.append("</div>")  # End card
        
        note_text = "".join(note_parts)
        
        from .freshdesk_tools import add_note, update_ticket
        
        log_tool_execution(logger, ticket_id, "add_note")
        note_result = await add_note(context, ticket_id, note_text)
        if "error" not in note_result.data:
            results["steps_completed"].append("Added analysis note to ticket")
        
        # Step 9: Update ticket tags based on decision
        tags = ["Processed by Whiz AI"]  # Always add this tag
        
        if decision == "Approved":
            tags.extend(["Refund Approved", "Automated Decision"])
        elif decision == "Denied":
            tags.extend(["Refund Denied", "Automated Decision"])
        else:
            tags.extend(["Needs Human Review", "Automated Analysis"])
        
        # Add "Refunded" tag if a refund was processed
        if refunded:
            tags.append("Refunded")
        
        # Add verification tags
        if results['booking_info_source'] == 'parkwhiz_api_verified':
            tags.append("ParkWhiz Verified")
        
        if verification_result and not verification_result.success:
            tags.append("Verification Failed")
        
        log_tool_execution(logger, ticket_id, "update_ticket")
        update_result = await update_ticket(context, ticket_id, tags=tags)
        if "error" not in update_result.data:
            results["steps_completed"].append("Updated ticket tags")
        
        # Calculate processing time and log journey end
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_journey_end(logger, ticket_id, "Automated Ticket Processing", processing_time_ms, decision)
        
        # Return only essential information with minimal debug data
        return p.ToolResult(
            {
                "ticket_id": ticket_id,
                "decision": decision,
                "reasoning": reasoning,
                "policy_applied": policy_applied,
                "confidence": confidence,
                "refunded": refunded,
                "duplicate_detection_used": results["triage_decision"].get("duplicate_detection_used", False),
                "used_verified_data": results["triage_decision"].get("used_verified_data", False),
                "recommended_action": results["triage_decision"].get("recommended_action", ""),
                "steps_completed": results["steps_completed"],
                "security_status": "safe" if (results["security_scan"].get("safe", True) and not results["security_scan"].get("flagged", False)) else "flagged",
                "booking_info_found": results["booking_info_source"] != "missing",
                "booking_info_source": results["booking_info_source"],
                "verification_attempted": verification_result is not None,
                "verification_success": verification_result.success if verification_result else False,
                "note_added": "error" not in note_result.data,
                "ticket_updated": "error" not in update_result.data,
                "processing_time_ms": processing_time_ms,
                "debug": {
                    "notes_length": results.get("debug_notes_length", 0),
                    "notes_sample": results.get("debug_notes_sample", "")[:200],  # Only 200 chars
                    "booking_found": results["booking_info"].get("found", False),
                    "security_flagged": results["security_scan"].get("flagged", False),
                    "paid_again_detected": duplicate_detection_result is not None,
                    "zapier_failure_detected": zapier_failure or invalid_booking_id,
                    "verified_booking_id": verified_booking.booking_id if verified_booking else None
                }
            },
            metadata={"summary": f"Ticket {ticket_id}: {decision} - {'Verified' if verified_booking else 'Not verified'} - {'Refunded' if refunded else 'Not refunded'} - Note added, tags updated"}
        )
    
    except Exception as e:
        # Log error with full context
        log_error_with_context(
            logger,
            e,
            ticket_id=ticket_id,
            journey_name="Automated Ticket Processing",
            tool_name="process_ticket_end_to_end"
        )
        
        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_journey_end(logger, ticket_id, "Automated Ticket Processing", processing_time_ms, "ERROR")
        
        # Re-raise the exception
        raise
