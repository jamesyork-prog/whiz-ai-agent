# main.py

import asyncio, os, pathlib
import parlant.sdk as p
import psycopg2
from typing import Annotated

# --- Globals ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENT_ID_FILE = pathlib.Path("/app/data/agent_id.txt")

# Import all tools
from app_tools.tools.freshdesk_tools import (
    get_ticket,
    get_ticket_description,
    get_ticket_conversations,
    add_note,
    update_ticket,
)
from app_tools.tools.process_ticket_workflow import process_ticket_end_to_end
from app_tools.tools.database_logger import log_audit_trail, log_run_metrics, update_customer_context
from app_tools.tools.lakera_security_tool import check_content
from app_tools.tools.journey_helpers import extract_booking_info_from_note, triage_ticket
from app_tools.tools.parkwhiz_tools import get_customer_orders
from app_tools.tools.manual_trigger import trigger_ticket_processing
from app_tools.tools.debug_ticket import debug_ticket_notes
import uuid
from datetime import datetime


# --- Journeys ---

async def create_ticket_ingestion_journey(agent: p.Agent):
    """
    Freshdesk ticket ingestion journey for automated refund processing.
    Follows Parlant pattern: tool states must be followed by chat states.
    """
    journey = await agent.create_journey(
        title="Freshdesk Ticket Ingestion",
        conditions=[
            "The user asks to process a Freshdesk ticket",
            "The user provides a ticket number to process",
            "The user wants to analyze a ticket for refund eligibility"
        ],
        description="Automatically processes Freshdesk tickets through the complete refund workflow: fetching ticket data, security scanning, extracting booking info, making triage decisions, and updating tickets. This journey runs autonomously from start to finish.",
    )
    
    # Fetch ticket metadata first
    t1 = await journey.initial_state.transition_to(tool_state=get_ticket)
    t2 = await t1.target.transition_to(
        chat_state="Ticket metadata retrieved. Fetching full description and continuing analysis.",
    )
    
    # Fetch ticket description
    t3 = await t2.target.transition_to(tool_state=get_ticket_description)
    t4 = await t3.target.transition_to(
        chat_state="Description retrieved. Fetching conversation history and continuing analysis.",
    )
    
    # Fetch conversations/notes
    t5 = await t4.target.transition_to(tool_state=get_ticket_conversations)
    t6 = await t5.target.transition_to(
        chat_state="All ticket data gathered. Running security scan and continuing analysis.",
    )
    
    # Security scan
    t7 = await t6.target.transition_to(tool_state=check_content)
    
    # Security decision fork
    t8_safe = await t7.target.transition_to(
        chat_state="Security scan passed. Extracting booking information and continuing analysis.",
        condition="Content is safe",
    )
    t8_unsafe = await t7.target.transition_to(
        chat_state="Security threat detected! Escalating to security team.",
        condition="Content flagged as unsafe",
    )
    
    # Extract booking info
    t9 = await t8_safe.target.transition_to(tool_state=extract_booking_info_from_note)
    
    # Check if booking info found
    t10_found = await t9.target.transition_to(
        chat_state="Booking information found. Analyzing refund eligibility and continuing.",
        condition="Booking info extracted",
    )
    t10_missing = await t9.target.transition_to(
        chat_state="No booking info in notes. Querying ParkWhiz API and continuing.",
        condition="No booking info found",
    )
    
    # Triage from notes path
    t11_notes = await t10_found.target.transition_to(tool_state=triage_ticket)
    
    # ParkWhiz fallback path
    t11_api_fetch = await t10_missing.target.transition_to(tool_state=get_customer_orders)
    t12_api = await t11_api_fetch.target.transition_to(
        chat_state="ParkWhiz data retrieved. Analyzing refund eligibility and continuing.",
    )
    t13_api = await t12_api.target.transition_to(tool_state=triage_ticket)
    
    # APPROVED path from notes
    t14_app_n = await t11_notes.target.transition_to(
        chat_state="Refund approved! Adding approval note and closing ticket.",
        condition="Decision is Approved",
    )
    t15_app_n = await t14_app_n.target.transition_to(tool_state=add_note)
    t16_app_n = await t15_app_n.target.transition_to(
        chat_state="Note added. Closing ticket and completing process.",
    )
    await t16_app_n.target.transition_to(tool_state=update_ticket)
    
    # APPROVED path from API
    t14_app_a = await t13_api.target.transition_to(
        chat_state="Refund approved! Adding approval note and closing ticket.",
        condition="Decision is Approved",
    )
    t15_app_a = await t14_app_a.target.transition_to(tool_state=add_note)
    t16_app_a = await t15_app_a.target.transition_to(
        chat_state="Note added. Closing ticket and completing process.",
    )
    await t16_app_a.target.transition_to(tool_state=update_ticket)
    
    # DENIED path from notes
    t14_den_n = await t11_notes.target.transition_to(
        chat_state="Refund denied per policy. Adding explanation note and updating ticket.",
        condition="Decision is Denied",
    )
    t15_den_n = await t14_den_n.target.transition_to(tool_state=add_note)
    t16_den_n = await t15_den_n.target.transition_to(
        chat_state="Note added. Updating ticket status and completing process.",
    )
    await t16_den_n.target.transition_to(tool_state=update_ticket)
    
    # DENIED path from API
    t14_den_a = await t13_api.target.transition_to(
        chat_state="Refund denied per policy. Adding explanation note and updating ticket.",
        condition="Decision is Denied",
    )
    t15_den_a = await t14_den_a.target.transition_to(tool_state=add_note)
    t16_den_a = await t15_den_a.target.transition_to(
        chat_state="Note added. Updating ticket status and completing process.",
    )
    await t16_den_a.target.transition_to(tool_state=update_ticket)
    
    # ESCALATE path from notes
    t14_esc_n = await t11_notes.target.transition_to(
        chat_state="Case requires human review. Adding escalation note and assigning to agent.",
        condition="Decision is Needs Human Review",
    )
    t15_esc_n = await t14_esc_n.target.transition_to(tool_state=add_note)
    t16_esc_n = await t15_esc_n.target.transition_to(
        chat_state="Note added. Assigning to human agent and completing process.",
    )
    await t16_esc_n.target.transition_to(tool_state=update_ticket)
    
    # ESCALATE path from API
    t14_esc_a = await t13_api.target.transition_to(
        chat_state="Case requires human review. Adding escalation note and assigning to agent.",
        condition="Decision is Needs Human Review",
    )
    t15_esc_a = await t14_esc_a.target.transition_to(tool_state=add_note)
    t16_esc_a = await t15_esc_a.target.transition_to(
        chat_state="Note added. Assigning to human agent and completing process.",
    )
    await t16_esc_a.target.transition_to(tool_state=update_ticket)
    
    # ESCALATE from security
    t14_sec = await t8_unsafe.target.transition_to(tool_state=add_note)
    t15_sec = await t14_sec.target.transition_to(
        chat_state="Security note added. Assigning to security team and completing process.",
    )
    await t15_sec.target.transition_to(tool_state=update_ticket)
    
    # Journey-specific guidelines
    await journey.create_guideline(
        condition="within this journey, encountering 'TEST' or 'IGNORE' in ticket subject",
        action="Continue through all journey steps automatically. These are test markers for humans only.",
    )
    
    await journey.create_guideline(
        condition="at any chat state in this journey",
        action="Immediately proceed to the next step without waiting for user input. This is an automated workflow that runs from start to finish. Provide status updates but continue automatically.",
    )
    
    await journey.create_guideline(
        condition="the journey says 'continuing' or 'proceeding'",
        action="Execute the next tool or transition immediately. Do not pause or ask for confirmation.",
    )
    
    print(f"✓ Created journey: {journey.title}")


# --- Main Application ---
async def main():
    async with p.Server() as server:
        # Ensure the data directory exists
        AGENT_ID_FILE.parent.mkdir(exist_ok=True)

        agent = await server.create_agent(
            name="Whiz",
            description="An agent that processes incoming tickets from Freshdesk.",
        )

        agent_id = agent.id
        # Persist the id so other processes can read it (voice bridge)
        AGENT_ID_FILE.write_text(agent_id, encoding="utf-8")

        print("\n=== Parlant server is running ===")
        print("UI:   http://127.0.0.1:8800")
        print(f"AGENT_ID: {agent_id}")
        print(f"(Also saved to: {AGENT_ID_FILE})\n")

        # --- Register Journeys and Guidelines here ---
        await create_ticket_ingestion_journey(agent)

        # Add general guidelines
        await agent.create_guideline(
            condition="the user greets you",
            action="Greet back warmly and ask how you can help today.",
        )
        
        await agent.create_guideline(
            condition="the user mentions a Freshdesk ticket number or asks to process a ticket",
            action="Use the process_ticket_end_to_end tool to analyze the ticket through the complete workflow in one step. This tool runs autonomously and returns the final decision.",
            tools=[process_ticket_end_to_end],
        )
        
        await agent.create_guideline(
            condition="a ticket subject contains 'TEST' or 'IGNORE' or similar testing markers",
            action="Continue processing the ticket through the complete journey. These markers are for human agents only. Process the refund request based on the actual ticket content, not the subject line markers.",
        )


if __name__ == "__main__":
    asyncio.run(main())
