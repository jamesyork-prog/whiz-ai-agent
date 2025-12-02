"""
Integration tests for webhook endpoint routing.

This module tests that the webhook endpoint correctly integrates with
the journey router to determine which journey should be activated.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app_tools.webhook_server import app
from app_tools.journey_router import AUTOMATED_JOURNEY_NAME


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestWebhookRouting:
    """Tests for webhook endpoint routing integration."""
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    @patch('app_tools.webhook_server.route_to_journey')
    def test_webhook_endpoint_calls_router_with_webhook_trigger(
        self,
        mock_route_to_journey,
        mock_validate_signature,
        client
    ):
        """Verify webhook endpoint calls router with 'webhook' trigger source."""
        # Setup mocks
        mock_validate_signature.return_value = True
        mock_route_to_journey.return_value = AUTOMATED_JOURNEY_NAME
        
        # Prepare webhook payload
        payload = {
            "ticket_id": "12345",
            "event": "ticket_created",
            "triggered_at": "2025-11-17T10:30:00Z",
            "ticket_subject": "Refund request",
            "ticket_status": 2,
            "ticket_priority": 1,
            "requester_email": "customer@example.com"
        }
        
        # Send webhook request
        response = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["ticket_id"] == "12345"
        
        # Verify router was called with correct parameters
        mock_route_to_journey.assert_called_once_with(
            trigger_source="webhook",
            ticket_id="12345"
        )
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    @patch('app_tools.webhook_server.route_to_journey')
    def test_webhook_endpoint_receives_automated_journey_name(
        self,
        mock_route_to_journey,
        mock_validate_signature,
        client
    ):
        """Verify webhook endpoint receives the automated journey name from router."""
        # Setup mocks
        mock_validate_signature.return_value = True
        mock_route_to_journey.return_value = AUTOMATED_JOURNEY_NAME
        
        # Prepare webhook payload
        payload = {
            "ticket_id": "99999",
            "event": "ticket_updated",
            "triggered_at": "2025-11-17T11:00:00Z"
        }
        
        # Send webhook request
        response = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify router returned automated journey name
        journey_name = mock_route_to_journey.return_value
        assert journey_name == AUTOMATED_JOURNEY_NAME
        assert journey_name == "Automated Ticket Processing"
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    @patch('app_tools.webhook_server.route_to_journey')
    def test_webhook_routing_with_different_ticket_ids(
        self,
        mock_route_to_journey,
        mock_validate_signature,
        client
    ):
        """Verify routing works for different ticket IDs."""
        # Setup mocks
        mock_validate_signature.return_value = True
        mock_route_to_journey.return_value = AUTOMATED_JOURNEY_NAME
        
        # Test with multiple ticket IDs
        ticket_ids = ["111", "222", "333"]
        
        for ticket_id in ticket_ids:
            payload = {
                "ticket_id": ticket_id,
                "event": "ticket_created",
                "triggered_at": "2025-11-17T10:30:00Z"
            }
            
            response = client.post(
                "/webhook/freshdesk",
                json=payload,
                headers={"X-Freshdesk-Signature": "test-signature"}
            )
            
            assert response.status_code == 200
            assert response.json()["ticket_id"] == ticket_id
        
        # Verify router was called for each ticket
        assert mock_route_to_journey.call_count == len(ticket_ids)
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    def test_webhook_routing_fails_gracefully_on_invalid_payload(
        self,
        mock_validate_signature,
        client
    ):
        """Verify webhook endpoint handles invalid payloads gracefully."""
        # Setup mock
        mock_validate_signature.return_value = True
        
        # Send invalid payload (missing required fields)
        payload = {
            "invalid_field": "value"
        }
        
        response = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        
        # Verify error response
        assert response.status_code == 400
        assert "Invalid payload structure" in response.json()["detail"]
