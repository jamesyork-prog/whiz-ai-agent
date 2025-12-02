"""
LLMAnalyzer component for analyzing complex refund cases using Gemini.

This module provides an LLMAnalyzer class that uses Gemini to analyze edge cases
and complex refund scenarios with full policy context, providing structured decisions
with reasoning and confidence levels.
"""

import os
import json
import logging
from typing import Dict, Optional
from google import genai
from google.genai import types

# Configure logger
logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """
    Uses Gemini to analyze complex refund cases with full policy context.
    
    This class is invoked when rule-based logic produces uncertain results or
    low confidence. It provides the LLM with comprehensive policy documents,
    ticket data, and booking information to make informed decisions.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the LLMAnalyzer with Gemini model.
        
        Args:
            model_name: Gemini model to use (defaults to GEMINI_MODEL env var or gemini-2.5-flash)
        """
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Please add it to your .env file."
            )
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)
        
        # Use provided model or fall back to environment variable or default
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    async def analyze_case(
        self,
        ticket_data: Dict,
        booking_info: Dict,
        policy_text: str,
        rule_result: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze a refund case using LLM with policy context, timeout, and error handling.
        
        This method constructs a detailed prompt with policy documents, ticket
        information, and booking details, then asks Gemini to make a decision
        following the policy guidelines. Includes comprehensive error handling
        and fallback to rule-based logic when available.
        
        Args:
            ticket_data: Dictionary containing ticket information:
                - ticket_id (str): Freshdesk ticket ID
                - subject (str): Ticket subject
                - description (str): Ticket description
                - status (str): Current ticket status
            booking_info: Dictionary containing booking details:
                - booking_id (str): Booking identifier
                - amount (float): Booking amount
                - event_date (str): ISO format date of the event
                - booking_type (str): Type of booking
                - location (str): Parking location
            policy_text: Full policy text from PolicyLoader
            rule_result: Optional result from RuleEngine (provides context)
        
        Returns:
            Dictionary containing:
                - decision (str): "Approved", "Denied", or "Needs Human Review"
                - reasoning (str): Detailed explanation of the decision
                - policy_applied (str): Specific policy rule or section applied
                - confidence (str): "high", "medium", or "low"
                - key_factors (list[str]): Important factors that influenced the decision
        """
        import asyncio
        import time
        
        logger.info("Starting LLM analysis for complex case")
        logger.debug(f"Using model: {self.model_name}")
        
        if rule_result:
            logger.info(f"Rule-based result available: {rule_result.get('decision')} "
                       f"(confidence: {rule_result.get('confidence')})")
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(
            ticket_data,
            booking_info,
            policy_text,
            rule_result
        )
        
        start_time = time.time()
        
        try:
            # Make Gemini API call with structured JSON response and 10-second timeout
            logger.debug("Calling Gemini API for case analysis")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,  # Low temperature for consistent decisions
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "decision": {
                                    "type": "string",
                                    "enum": ["Approved", "Denied", "Needs Human Review"]
                                },
                                "reasoning": {"type": "string"},
                                "policy_applied": {"type": "string"},
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                },
                                "key_factors": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["decision", "reasoning", "policy_applied", "confidence", "key_factors"]
                        }
                    )
                ),
                timeout=10.0  # 10-second timeout
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse and validate response
            result = json.loads(response.text)
            
            # Validate decision value
            valid_decisions = ["Approved", "Denied", "Needs Human Review"]
            if result.get("decision") not in valid_decisions:
                logger.error(f"LLM returned invalid decision: {result.get('decision')}")
                raise ValueError(f"Invalid decision: {result.get('decision')}")
            
            # Validate confidence value
            valid_confidence = ["high", "medium", "low"]
            if result.get("confidence") not in valid_confidence:
                logger.warning(f"LLM returned invalid confidence: {result.get('confidence')}, defaulting to medium")
                result["confidence"] = "medium"  # Default to medium if invalid
            
            logger.info(f"LLM analysis completed in {processing_time_ms}ms. "
                       f"Decision: {result.get('decision')}, "
                       f"Confidence: {result.get('confidence')}, "
                       f"Policy: {result.get('policy_applied')}")
            
            if result.get("key_factors"):
                logger.debug(f"Key factors: {', '.join(result.get('key_factors', []))}")
            
            return result
        
        except asyncio.TimeoutError:
            # Handle timeout - fall back to rule-based decision or escalate
            logger.error("LLM analysis timeout after 10 seconds")
            return self._create_fallback_decision("Timeout after 10 seconds", rule_result)
        
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            logger.error(f"Error parsing LLM response: {e}")
            return self._create_fallback_decision(f"JSON parsing error: {str(e)}", rule_result)
        
        except ValueError as e:
            # Handle validation errors (invalid decision values)
            logger.error(f"LLM returned invalid response: {e}")
            return self._create_fallback_decision(f"Invalid response: {str(e)}", rule_result)
        
        except Exception as e:
            # Handle all other errors (API failures, network issues, etc.)
            error_type = type(e).__name__
            logger.error(f"Error in LLM analysis ({error_type}): {e}")
            return self._create_fallback_decision(f"{error_type}: {str(e)}", rule_result)
    
    def _create_analysis_prompt(
        self,
        ticket_data: Dict,
        booking_info: Dict,
        policy_text: str,
        rule_result: Optional[Dict]
    ) -> str:
        """
        Create a detailed prompt for LLM analysis.
        
        Args:
            ticket_data: Ticket information
            booking_info: Booking details
            policy_text: Full policy text
            rule_result: Optional rule-based analysis result
        
        Returns:
            Formatted prompt string
        """
        # Format booking info for display
        booking_summary = self._format_booking_info(booking_info)
        
        # Format ticket info for display
        ticket_summary = self._format_ticket_info(ticket_data)
        
        # Format rule result if available
        rule_context = ""
        if rule_result:
            rule_context = f"""
**Rule-Based Analysis:**
- Decision: {rule_result.get('decision', 'N/A')}
- Reasoning: {rule_result.get('reasoning', 'N/A')}
- Policy Rule: {rule_result.get('policy_rule', 'N/A')}
- Confidence: {rule_result.get('confidence', 'N/A')}

The rule-based system was uncertain about this case, so your analysis is needed.
"""
        
        prompt = f"""You are a refund policy expert analyzing a parking refund request. Your job is to make a fair, policy-compliant decision based on the information provided.

# REFUND POLICY DOCUMENTS

{policy_text}

# TICKET INFORMATION

{ticket_summary}

# BOOKING INFORMATION

{booking_summary}

{rule_context}

# YOUR TASK

Analyze this refund request and make a decision following these guidelines:

1. **Review the policy documents** to understand the rules and scenarios
2. **Evaluate the booking details** (timing, type, amount, circumstances)
3. **Consider the customer's situation** described in the ticket
4. **Apply the appropriate policy** to make a fair decision

**Decision Options:**
- **Approved**: Clear policy support for refund, no violations
- **Denied**: Clear policy violation, refund not warranted
- **Needs Human Review**: Ambiguous case, missing information, or requires judgment call

**Confidence Levels:**
- **high**: Clear-cut case with strong policy support
- **medium**: Reasonable case but some ambiguity
- **low**: Uncertain case, borderline, or missing critical information

**Key Factors to Consider:**
- Timing of cancellation relative to event
- Booking type (confirmed, on-demand, third-party)
- Special circumstances (oversold, duplicate, paid again, poor experience)
- Customer communication and tone
- Policy precedents and guidelines

**Important Notes:**
- Be fair and consistent with policy
- Err on the side of customer satisfaction when policy allows
- Escalate to human review when uncertain or when policy is ambiguous
- Provide clear, specific reasoning that references the policy
- List the key factors that influenced your decision

Provide your analysis as a JSON object with the required fields."""
        
        return prompt
    
    def _format_booking_info(self, booking_info: Dict) -> str:
        """
        Format booking information for prompt display.
        
        Args:
            booking_info: Booking details dictionary
        
        Returns:
            Formatted string
        """
        if not booking_info:
            return "**No booking information available**"
        
        lines = []
        
        if booking_info.get("booking_id"):
            lines.append(f"- **Booking ID**: {booking_info['booking_id']}")
        
        if booking_info.get("amount"):
            lines.append(f"- **Amount**: ${booking_info['amount']:.2f}")
        
        if booking_info.get("event_date"):
            lines.append(f"- **Event Date**: {booking_info['event_date']}")
        
        if booking_info.get("reservation_date"):
            lines.append(f"- **Reservation Date**: {booking_info['reservation_date']}")
        
        if booking_info.get("cancellation_date"):
            lines.append(f"- **Cancellation Date**: {booking_info['cancellation_date']}")
        
        if booking_info.get("booking_type"):
            lines.append(f"- **Booking Type**: {booking_info['booking_type']}")
        
        if booking_info.get("location"):
            lines.append(f"- **Location**: {booking_info['location']}")
        
        if booking_info.get("customer_email"):
            lines.append(f"- **Customer Email**: {booking_info['customer_email']}")
        
        return "\n".join(lines) if lines else "**Minimal booking information available**"
    
    def _format_ticket_info(self, ticket_data: Dict) -> str:
        """
        Format ticket information for prompt display.
        
        Args:
            ticket_data: Ticket details dictionary
        
        Returns:
            Formatted string
        """
        if not ticket_data:
            return "**No ticket information available**"
        
        lines = []
        
        if ticket_data.get("ticket_id"):
            lines.append(f"- **Ticket ID**: {ticket_data['ticket_id']}")
        
        if ticket_data.get("subject"):
            lines.append(f"- **Subject**: {ticket_data['subject']}")
        
        if ticket_data.get("status"):
            lines.append(f"- **Status**: {ticket_data['status']}")
        
        if ticket_data.get("description"):
            # Truncate long descriptions
            description = ticket_data['description']
            if len(description) > 1000:
                description = description[:1000] + "... (truncated)"
            lines.append(f"- **Description**: {description}")
        
        return "\n".join(lines) if lines else "**Minimal ticket information available**"
    
    def _create_fallback_decision(
        self,
        error_message: str,
        rule_result: Optional[Dict]
    ) -> Dict:
        """
        Create a fallback decision when LLM analysis fails.
        
        If rule-based analysis is available and has medium/high confidence,
        use that. Otherwise, escalate to human review.
        
        Args:
            error_message: Error message from LLM failure
            rule_result: Optional rule-based analysis result
        
        Returns:
            Fallback decision dictionary
        """
        # If we have a rule result with medium or high confidence, use it
        if rule_result and rule_result.get("confidence") in ["medium", "high"]:
            logger.info(f"Using rule-based fallback decision: {rule_result.get('decision')}")
            return {
                "decision": rule_result.get("decision", "Needs Human Review"),
                "reasoning": f"{rule_result.get('reasoning', '')} (LLM analysis failed, using rule-based decision)",
                "policy_applied": rule_result.get("policy_rule", "Rule-Based Fallback"),
                "confidence": "medium",  # Downgrade confidence slightly
                "key_factors": [
                    "LLM analysis unavailable",
                    "Using rule-based decision as fallback",
                    f"Original confidence: {rule_result.get('confidence', 'unknown')}"
                ]
            }
        
        # Otherwise, escalate to human review
        logger.warning("No fallback available, escalating to human review")
        return {
            "decision": "Needs Human Review",
            "reasoning": (
                "Unable to complete automated analysis due to technical error. "
                "This case requires human review to ensure accurate decision-making. "
                f"Error: {error_message}"
            ),
            "policy_applied": "Escalation - Technical Failure",
            "confidence": "low",
            "key_factors": [
                "LLM analysis failed",
                "No high-confidence rule-based decision available",
                "Escalating to human review for safety"
            ]
        }
