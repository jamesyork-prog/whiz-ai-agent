"""
Tests for journey routing logic.

This module tests the routing functionality that determines which journey
to activate based on the trigger source (webhook vs chat).
"""

import pytest
from app_tools.journey_router import (
    route_to_journey,
    detect_trigger_source,
    AUTOMATED_JOURNEY_NAME,
    INTERACTIVE_JOURNEY_NAME
)


class TestRouteToJourney:
    """Tests for the route_to_journey function."""
    
    def test_webhook_trigger_routes_to_automated_journey(self):
        """Verify webhook triggers route to automated journey."""
        journey_name = route_to_journey(
            trigger_source="webhook",
            ticket_id="12345"
        )
        
        assert journey_name == AUTOMATED_JOURNEY_NAME
        assert journey_name == "Automated Ticket Processing"
    
    def test_chat_trigger_routes_to_interactive_journey(self):
        """Verify chat triggers route to interactive journey."""
        journey_name = route_to_journey(
            trigger_source="chat",
            ticket_id="12345"
        )
        
        assert journey_name == INTERACTIVE_JOURNEY_NAME
        assert journey_name == "Interactive Ticket Processing"
    
    def test_unknown_trigger_defaults_to_interactive_journey(self):
        """Verify unknown triggers default to interactive journey."""
        journey_name = route_to_journey(
            trigger_source="unknown",
            ticket_id="12345"
        )
        
        assert journey_name == INTERACTIVE_JOURNEY_NAME
        assert journey_name == "Interactive Ticket Processing"
    
    def test_routing_with_different_ticket_ids(self):
        """Verify routing works correctly with different ticket IDs."""
        # Webhook with different ticket IDs
        assert route_to_journey("webhook", "111") == AUTOMATED_JOURNEY_NAME
        assert route_to_journey("webhook", "999") == AUTOMATED_JOURNEY_NAME
        
        # Chat with different ticket IDs
        assert route_to_journey("chat", "111") == INTERACTIVE_JOURNEY_NAME
        assert route_to_journey("chat", "999") == INTERACTIVE_JOURNEY_NAME


class TestDetectTriggerSource:
    """Tests for the detect_trigger_source function."""
    
    def test_webhook_flag_detected(self):
        """Verify webhook flag is correctly detected."""
        trigger = detect_trigger_source(from_webhook=True)
        assert trigger == "webhook"
    
    def test_chat_flag_detected(self):
        """Verify chat flag is correctly detected."""
        trigger = detect_trigger_source(from_chat=True)
        assert trigger == "chat"
    
    def test_no_flags_returns_unknown(self):
        """Verify no flags returns unknown."""
        trigger = detect_trigger_source()
        assert trigger == "unknown"
    
    def test_both_flags_returns_unknown(self):
        """Verify ambiguous case (both flags) returns unknown."""
        trigger = detect_trigger_source(from_webhook=True, from_chat=True)
        assert trigger == "unknown"
    
    def test_webhook_takes_precedence_when_only_webhook_set(self):
        """Verify webhook is detected when only webhook flag is True."""
        trigger = detect_trigger_source(from_webhook=True, from_chat=False)
        assert trigger == "webhook"
    
    def test_chat_detected_when_only_chat_set(self):
        """Verify chat is detected when only chat flag is True."""
        trigger = detect_trigger_source(from_webhook=False, from_chat=True)
        assert trigger == "chat"


class TestJourneyRouterIntegration:
    """Integration tests for the complete routing workflow."""
    
    def test_webhook_workflow(self):
        """Test complete workflow for webhook trigger."""
        # Detect trigger source
        trigger = detect_trigger_source(from_webhook=True)
        assert trigger == "webhook"
        
        # Route to journey
        journey = route_to_journey(trigger, "12345")
        assert journey == AUTOMATED_JOURNEY_NAME
    
    def test_chat_workflow(self):
        """Test complete workflow for chat trigger."""
        # Detect trigger source
        trigger = detect_trigger_source(from_chat=True)
        assert trigger == "chat"
        
        # Route to journey
        journey = route_to_journey(trigger, "12345")
        assert journey == INTERACTIVE_JOURNEY_NAME
    
    def test_ambiguous_workflow_defaults_to_interactive(self):
        """Test that ambiguous triggers default to interactive journey."""
        # Detect ambiguous trigger
        trigger = detect_trigger_source()
        assert trigger == "unknown"
        
        # Route should default to interactive
        journey = route_to_journey(trigger, "12345")
        assert journey == INTERACTIVE_JOURNEY_NAME
    
    def test_no_cross_contamination(self):
        """Verify webhook and chat triggers don't cross-contaminate."""
        # Process webhook trigger
        webhook_trigger = detect_trigger_source(from_webhook=True)
        webhook_journey = route_to_journey(webhook_trigger, "111")
        
        # Process chat trigger
        chat_trigger = detect_trigger_source(from_chat=True)
        chat_journey = route_to_journey(chat_trigger, "222")
        
        # Verify they route to different journeys
        assert webhook_journey == AUTOMATED_JOURNEY_NAME
        assert chat_journey == INTERACTIVE_JOURNEY_NAME
        assert webhook_journey != chat_journey


class TestErrorHandling:
    """Tests for error handling in journey routing."""
    
    def test_route_with_empty_ticket_id(self):
        """Verify routing works even with empty ticket ID."""
        journey = route_to_journey("webhook", "")
        assert journey == AUTOMATED_JOURNEY_NAME
    
    def test_route_with_none_ticket_id(self):
        """Verify routing handles None ticket ID gracefully."""
        # This should not crash - routing logic doesn't depend on ticket_id
        journey = route_to_journey("webhook", None)
        assert journey == AUTOMATED_JOURNEY_NAME
    
    def test_route_with_special_characters_in_ticket_id(self):
        """Verify routing handles special characters in ticket ID."""
        journey = route_to_journey("webhook", "ticket-123!@#$%")
        assert journey == AUTOMATED_JOURNEY_NAME
    
    def test_detect_trigger_with_explicit_false_values(self):
        """Verify explicit False values are handled correctly."""
        trigger = detect_trigger_source(from_webhook=False, from_chat=False)
        assert trigger == "unknown"
    
    def test_route_to_journey_is_consistent(self):
        """Verify routing is consistent for same inputs."""
        # Call multiple times with same inputs
        journey1 = route_to_journey("webhook", "12345")
        journey2 = route_to_journey("webhook", "12345")
        journey3 = route_to_journey("webhook", "12345")
        
        # All should return same result
        assert journey1 == journey2 == journey3 == AUTOMATED_JOURNEY_NAME
    
    def test_journey_names_are_strings(self):
        """Verify journey names are always strings."""
        webhook_journey = route_to_journey("webhook", "12345")
        chat_journey = route_to_journey("chat", "12345")
        unknown_journey = route_to_journey("unknown", "12345")
        
        assert isinstance(webhook_journey, str)
        assert isinstance(chat_journey, str)
        assert isinstance(unknown_journey, str)
