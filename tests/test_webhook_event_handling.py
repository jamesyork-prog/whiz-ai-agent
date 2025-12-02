"""
Tests for webhook event handling features.

This module tests:
- Event type filtering
- Event deduplication
- Refund-related change detection
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app_tools.webhook_server import (
    app,
    is_duplicate_event,
    is_supported_event_type,
    is_refund_related,
    event_deduplication_storage
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_deduplication_storage():
    """Clear deduplication storage before each test."""
    event_deduplication_storage.clear()
    yield
    event_deduplication_storage.clear()


class TestEventTypeFiltering:
    """Tests for event type filtering."""
    
    def test_supported_event_types(self):
        """Verify ticket_created and ticket_updated are supported."""
        assert is_supported_event_type("ticket_created") is True
        assert is_supported_event_type("ticket_updated") is True
    
    def test_unsupported_event_types(self):
        """Verify other event types are not supported."""
        assert is_supported_event_type("note_added") is False
        assert is_supported_event_type("ticket_deleted") is False
        assert is_supported_event_type("unknown_event") is False
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    def test_webhook_ignores_unsupported_event(self, mock_validate, client):
        """Verify webhook endpoint ignores unsupported event types."""
        mock_validate.return_value = True
        
        payload = {
            "ticket_id": "12345",
            "event": "note_added",
            "triggered_at": "2025-11-17T10:30:00Z"
        }
        
        response = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "ignored" in response_data["message"].lower()
        assert "not supported" in response_data["message"].lower()


class TestEventDeduplication:
    """Tests for event deduplication."""
    
    def test_first_event_not_duplicate(self):
        """Verify first occurrence of an event is not a duplicate."""
        assert is_duplicate_event("12345", "ticket_created") is False
    
    def test_same_event_is_duplicate(self):
        """Verify same event within window is detected as duplicate."""
        # First call - not duplicate
        assert is_duplicate_event("12345", "ticket_created") is False
        
        # Second call - is duplicate
        assert is_duplicate_event("12345", "ticket_created") is True
    
    def test_different_ticket_not_duplicate(self):
        """Verify different ticket IDs are not duplicates."""
        assert is_duplicate_event("12345", "ticket_created") is False
        assert is_duplicate_event("67890", "ticket_created") is False
    
    def test_different_event_type_not_duplicate(self):
        """Verify different event types for same ticket are not duplicates."""
        assert is_duplicate_event("12345", "ticket_created") is False
        assert is_duplicate_event("12345", "ticket_updated") is False
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    @patch('app_tools.webhook_server.route_to_journey')
    def test_webhook_rejects_duplicate_event(
        self,
        mock_route,
        mock_validate,
        client
    ):
        """Verify webhook endpoint rejects duplicate events."""
        mock_validate.return_value = True
        mock_route.return_value = "Automated Ticket Processing"
        
        payload = {
            "ticket_id": "12345",
            "event": "ticket_created",
            "triggered_at": "2025-11-17T10:30:00Z",
            "ticket_subject": "Refund request"
        }
        
        # First request - should succeed
        response1 = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        assert response1.status_code == 200
        assert "queued for processing" in response1.json()["message"].lower()
        
        # Second request - should be ignored as duplicate
        response2 = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        assert response2.status_code == 200
        assert "duplicate" in response2.json()["message"].lower()


class TestRefundRelatedDetection:
    """Tests for refund-related change detection."""
    
    def test_ticket_created_always_refund_related(self):
        """Verify ticket_created events are always processed."""
        payload = {
            "event": "ticket_created",
            "ticket_subject": "General inquiry"
        }
        assert is_refund_related(payload) is True
    
    def test_refund_keyword_in_subject(self):
        """Verify refund keywords in subject are detected."""
        refund_subjects = [
            "I need a refund",
            "Request for reimbursement",
            "Cancel my booking",
            "Cancellation request",
            "Money back please",
            "Chargeback dispute"
        ]
        
        for subject in refund_subjects:
            payload = {
                "event": "ticket_updated",
                "ticket_subject": subject
            }
            assert is_refund_related(payload) is True, f"Failed for: {subject}"
    
    def test_non_refund_subject_ignored(self):
        """Verify non-refund-related updates are ignored."""
        non_refund_subjects = [
            "General question",
            "How do I book?",
            "Account settings",
            "Password reset"
        ]
        
        for subject in non_refund_subjects:
            payload = {
                "event": "ticket_updated",
                "ticket_subject": subject
            }
            assert is_refund_related(payload) is False, f"Failed for: {subject}"
    
    def test_refund_keyword_in_description(self):
        """Verify refund keywords in description are detected."""
        payload = {
            "event": "ticket_updated",
            "ticket_subject": "Question",
            "ticket_description": "I would like to request a refund for my booking"
        }
        assert is_refund_related(payload) is True
    
    def test_refund_keyword_in_tags(self):
        """Verify refund keywords in tags are detected."""
        payload = {
            "event": "ticket_updated",
            "ticket_subject": "Question",
            "ticket_tags": ["refund", "urgent"]
        }
        assert is_refund_related(payload) is True
    
    def test_refund_keyword_in_custom_fields(self):
        """Verify refund keywords in custom fields are detected."""
        payload = {
            "event": "ticket_updated",
            "ticket_subject": "Question",
            "custom_fields": {
                "request_type": "cancellation",
                "priority": "high"
            }
        }
        assert is_refund_related(payload) is True
    
    @patch('app_tools.webhook_server.validate_freshdesk_signature')
    def test_webhook_ignores_non_refund_update(self, mock_validate, client):
        """Verify webhook endpoint ignores non-refund-related updates."""
        mock_validate.return_value = True
        
        payload = {
            "ticket_id": "12345",
            "event": "ticket_updated",
            "triggered_at": "2025-11-17T10:30:00Z",
            "ticket_subject": "General question about parking"
        }
        
        response = client.post(
            "/webhook/freshdesk",
            json=payload,
            headers={"X-Freshdesk-Signature": "test-signature"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "non-refund" in response_data["message"].lower()
        assert "ignored" in response_data["message"].lower()
