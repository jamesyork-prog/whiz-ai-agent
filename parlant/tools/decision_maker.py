"""
DecisionMaker orchestrator for hybrid refund decision-making.

This module provides the DecisionMaker class that orchestrates the complete
decision-making process by integrating PolicyLoader, BookingExtractor, RuleEngine,
LLMAnalyzer, and CancellationReasonMapper components.
"""

import time
import logging
from typing import Dict, Optional
from .policy_loader import PolicyLoader
from .booking_extractor import BookingExtractor
from .rule_engine import RuleEngine
from .llm_analyzer import LLMAnalyzer
from .cancellation_reason_mapper import CancellationReasonMapper

# Configure logger
logger = logging.getLogger(__name__)


class DecisionMaker:
    """
    Orchestrates the hybrid refund decision-making process.
    
    This class integrates all decision-making components to provide a complete
    workflow: extract booking info → apply rules → use LLM if needed → map
    cancellation reason. It tracks processing time and method used for monitoring.
    """
    
    def __init__(self):
        """Initialize the DecisionMaker with all required components."""
        # Initialize components
        self.policy_loader = PolicyLoader()
        self.booking_extractor = BookingExtractor()
        self.rule_engine = RuleEngine(self.policy_loader.get_rules())
        self.llm_analyzer = LLMAnalyzer()
        self.cancellation_reason_mapper = CancellationReasonMapper()
    
    async def make_decision(
        self,
        ticket_data: Dict,
        ticket_notes: Optional[str] = None,
        booking_info: Optional[Dict] = None
    ) -> Dict:
        """
        Make a refund decision using hybrid approach.
        
        This method orchestrates the complete decision flow:
        1. Extract booking info (if not provided)
        2. Validate booking info completeness
        3. Apply rule-based logic
        4. Use LLM analysis if rules are uncertain
        5. Map to ParkWhiz cancellation reason (if Approved)
        6. Return final decision with metadata
        
        Args:
            ticket_data: Dictionary containing ticket information:
                - ticket_id (str): Freshdesk ticket ID
                - subject (str): Ticket subject
                - description (str): Ticket description
                - status (str): Current ticket status
            ticket_notes: Optional raw text from ticket notes/conversations
            booking_info: Optional pre-extracted booking information
        
        Returns:
            Dictionary containing:
                - decision (str): "Approved", "Denied", or "Needs Human Review"
                - reasoning (str): Human-readable explanation
                - policy_applied (str): Specific policy rule applied
                - confidence (str): "high", "medium", or "low"
                - cancellation_reason (str): ParkWhiz cancellation reason (if Approved)
                - booking_info_found (bool): Whether booking info was extracted
                - method_used (str): "rules", "llm", or "hybrid"
                - processing_time_ms (int): Time taken to make decision
        """
        start_time = time.time()
        
        logger.info(f"Starting decision-making process for ticket: {ticket_data.get('ticket_id', 'unknown')}")
        
        # Step 1: Extract booking info if not provided
        if not booking_info:
            logger.info("Booking info not provided, extracting from ticket notes")
            if not ticket_notes:
                # Try to extract from ticket description
                ticket_notes = ticket_data.get("description", "")
                logger.debug("Using ticket description for extraction")
            
            try:
                extraction_result = await self.booking_extractor.extract_booking_info(ticket_notes)
                booking_info = extraction_result.get("booking_info", {})
                booking_info_found = extraction_result.get("found", False)
                
                # Check if extraction had an error
                if extraction_result.get("error"):
                    logger.error(f"Booking extraction error: {extraction_result['error']}")
                
                # If booking info not found or has low confidence, escalate
                if not booking_info_found or extraction_result.get("confidence") == "low":
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    error_detail = extraction_result.get("error", "")
                    reasoning = (
                        "Unable to extract complete booking information from ticket. "
                        "Missing critical details like booking ID or event date. "
                        "Human review required to gather necessary information."
                    )
                    if error_detail:
                        reasoning += f" (Extraction error: {error_detail})"
                    
                    logger.warning(f"Escalating due to incomplete booking info. Processing time: {processing_time_ms}ms")
                    return {
                        "decision": "Needs Human Review",
                        "reasoning": reasoning,
                        "policy_applied": "Data Validation - Incomplete Information",
                        "confidence": "low",
                        "cancellation_reason": None,
                        "booking_info_found": False,
                        "method_used": "extraction_failed",
                        "processing_time_ms": processing_time_ms
                    }
            
            except Exception as e:
                # Handle unexpected errors in extraction
                logger.error(f"Unexpected error during booking extraction: {type(e).__name__}: {e}")
                processing_time_ms = int((time.time() - start_time) * 1000)
                return {
                    "decision": "Needs Human Review",
                    "reasoning": (
                        "Technical error occurred while extracting booking information. "
                        "Human review required to process this ticket. "
                        f"Error: {str(e)}"
                    ),
                    "policy_applied": "Technical Error - Extraction Failed",
                    "confidence": "low",
                    "cancellation_reason": None,
                    "booking_info_found": False,
                    "method_used": "extraction_error",
                    "processing_time_ms": processing_time_ms
                }
        else:
            logger.info("Using pre-extracted booking info")
            booking_info_found = True
        
        # Step 2: Validate critical fields
        if not booking_info.get("event_date"):
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Missing event date, escalating. Processing time: {processing_time_ms}ms")
            return {
                "decision": "Needs Human Review",
                "reasoning": (
                    "Missing event date - cannot evaluate refund eligibility without "
                    "knowing when the parking was scheduled. Human review required."
                ),
                "policy_applied": "Data Validation - Missing Event Date",
                "confidence": "low",
                "cancellation_reason": None,
                "booking_info_found": booking_info_found,
                "method_used": "validation_failed",
                "processing_time_ms": processing_time_ms
            }
        
        # Step 3: Apply rule-based logic
        logger.info("Applying rule-based decision logic")
        try:
            rule_result = await self.rule_engine.apply_rules(booking_info, ticket_data, ticket_notes)
            logger.info(f"Rule-based result: {rule_result.get('decision')} "
                       f"(confidence: {rule_result.get('confidence')})")
        except Exception as e:
            # Handle unexpected errors in rule engine
            logger.error(f"Error in rule engine: {type(e).__name__}: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "decision": "Needs Human Review",
                "reasoning": (
                    "Technical error occurred while applying refund rules. "
                    "Human review required to process this ticket. "
                    f"Error: {str(e)}"
                ),
                "policy_applied": "Technical Error - Rule Engine Failed",
                "confidence": "low",
                "cancellation_reason": None,
                "booking_info_found": booking_info_found,
                "method_used": "rule_error",
                "processing_time_ms": processing_time_ms
            }
        
        # Step 4: Decide if LLM analysis is needed
        # Check if rule engine already used LLM (e.g., for vehicle classification)
        method_used = rule_result.get("method_used", "rules")
        final_decision = rule_result
        
        # If rule-based decision is uncertain or has low confidence, use LLM
        if rule_result.get("decision") == "Uncertain" or rule_result.get("confidence") == "low":
            logger.info("Rule-based decision uncertain or low confidence, invoking LLM analysis")
            method_used = "hybrid"
            
            try:
                # Get condensed policy text for LLM (more efficient than full policy)
                policy_text = self.policy_loader.get_condensed_policy_text()
                
                # Invoke LLM analysis
                llm_result = await self.llm_analyzer.analyze_case(
                    ticket_data=ticket_data,
                    booking_info=booking_info,
                    policy_text=policy_text,
                    rule_result=rule_result
                )
                
                # Use LLM result as final decision
                final_decision = llm_result
                logger.info(f"LLM analysis result: {llm_result.get('decision')} "
                           f"(confidence: {llm_result.get('confidence')})")
            
            except Exception as e:
                # Handle unexpected errors in LLM analysis
                # Fall back to rule-based decision if available
                logger.error(f"Unexpected error in LLM analysis: {type(e).__name__}: {e}")
                
                if rule_result.get("decision") != "Uncertain":
                    # Use rule-based decision as fallback
                    logger.info("Falling back to rule-based decision")
                    final_decision = {
                        "decision": rule_result.get("decision"),
                        "reasoning": f"{rule_result.get('reasoning')} (LLM analysis failed, using rule-based decision)",
                        "policy_applied": rule_result.get("policy_rule", "Rule-Based Fallback"),
                        "confidence": "medium",  # Downgrade confidence
                        "key_factors": [
                            "LLM analysis unavailable",
                            "Using rule-based decision as fallback",
                            f"Error: {str(e)}"
                        ]
                    }
                    method_used = "rules_fallback"
                else:
                    # No fallback available, escalate
                    logger.warning("No fallback available, escalating to human review")
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    return {
                        "decision": "Needs Human Review",
                        "reasoning": (
                            "Unable to complete automated analysis due to technical error. "
                            "This case requires human review to ensure accurate decision-making. "
                            f"Error: {str(e)}"
                        ),
                        "policy_applied": "Technical Error - Analysis Failed",
                        "confidence": "low",
                        "cancellation_reason": None,
                        "booking_info_found": booking_info_found,
                        "method_used": "llm_error",
                        "processing_time_ms": processing_time_ms
                    }
        else:
            logger.info("Rule-based decision has sufficient confidence, skipping LLM analysis")
        
        # Step 5: Map to ParkWhiz cancellation reason (if Approved)
        cancellation_reason = None
        if final_decision.get("decision") == "Approved":
            logger.info("Decision is Approved, mapping to ParkWhiz cancellation reason")
            try:
                cancellation_reason = self.cancellation_reason_mapper.map_reason(
                    decision_reasoning=final_decision.get("reasoning", ""),
                    policy_applied=final_decision.get("policy_applied", ""),
                    booking_info=booking_info
                )
                logger.info(f"Mapped cancellation reason: {cancellation_reason}")
            except Exception as e:
                # Handle errors in cancellation reason mapping
                # Default to "Other" if mapping fails
                logger.error(f"Error mapping cancellation reason: {e}, defaulting to 'Other'")
                cancellation_reason = "Other"
        
        # Step 6: Calculate processing time and return result
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Decision-making complete. Decision: {final_decision.get('decision')}, "
                   f"Method: {method_used}, Processing time: {processing_time_ms}ms")
        
        return {
            "decision": final_decision.get("decision"),
            "reasoning": final_decision.get("reasoning"),
            "policy_applied": final_decision.get("policy_applied", final_decision.get("policy_rule")),
            "confidence": final_decision.get("confidence"),
            "cancellation_reason": cancellation_reason,
            "booking_info_found": booking_info_found,
            "method_used": method_used,
            "processing_time_ms": processing_time_ms,
            "key_factors": final_decision.get("key_factors", [])
        }
