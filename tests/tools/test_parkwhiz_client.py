"""
Tests for ParkWhiz OAuth2 API Client

Tests OAuth2 authentication, token management, and API operations.
All tests use pytest-httpx to mock external API calls.
"""

import pytest
import os
from app_tools.tools.parkwhiz_client import (
    ParkWhizOAuth2Client,
    ParkWhizAuthenticationError,
    validate_oauth2_credentials,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_env_oauth2(monkeypatch):
    """Mock environment variables for OAuth2 authentication."""
    monkeypatch.setenv("PARKWHIZ_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("PARKWHIZ_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("PARKWHIZ_SCOPE", "partner")
    monkeypatch.setenv("PARKWHIZ_ENV", "sandbox")
    monkeypatch.setenv("PARKWHIZ_SANDBOX_URL", "https://api-sandbox.parkwhiz.com/v4")
    monkeypatch.setenv("PARKWHIZ_TIMEOUT", "30")
    monkeypatch.setenv("PARKWHIZ_MAX_RETRIES", "3")
    monkeypatch.setenv("PARKWHIZ_CACHE_TTL", "120")


# ============================================================================
# CLIENT INITIALIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_oauth2_client_initialization_success(mock_env_oauth2):
    """Test successful OAuth2 client initialization with environment variables."""
    client = ParkWhizOAuth2Client()
    
    assert client.client_id == "test_client_id"
    assert client.client_secret == "test_client_secret"
    assert client.scope == "partner"
    assert client.base_url == "https://api-sandbox.parkwhiz.com/v4"
    assert client.timeout == 30
    assert client.max_retries == 3
    assert client._token is None
    assert client._token_expires_at is None
    
    await client.close()


@pytest.mark.asyncio
async def test_oauth2_client_initialization_missing_credentials(monkeypatch):
    """Test OAuth2 client initialization fails without credentials."""
    monkeypatch.delenv("PARKWHIZ_CLIENT_ID", raising=False)
    monkeypatch.delenv("PARKWHIZ_CLIENT_SECRET", raising=False)
    
    with pytest.raises(ParkWhizAuthenticationError) as exc_info:
        ParkWhizOAuth2Client()
    
    assert "credentials not configured" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_oauth2_client_production_url(monkeypatch):
    """Test OAuth2 client uses production URL when configured."""
    monkeypatch.setenv("PARKWHIZ_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("PARKWHIZ_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("PARKWHIZ_ENV", "production")
    monkeypatch.setenv("PARKWHIZ_PRODUCTION_URL", "https://api.parkwhiz.com/v4")
    
    client = ParkWhizOAuth2Client()
    
    assert client.base_url == "https://api.parkwhiz.com/v4"
    
    await client.close()


# ============================================================================
# CREDENTIAL VALIDATION TESTS
# ============================================================================

def test_validate_oauth2_credentials_success(mock_env_oauth2):
    """Test credential validation succeeds with valid credentials."""
    result = validate_oauth2_credentials()
    assert result is True


def test_validate_oauth2_credentials_missing(monkeypatch):
    """Test credential validation fails with missing credentials."""
    monkeypatch.delenv("PARKWHIZ_CLIENT_ID", raising=False)
    monkeypatch.delenv("PARKWHIZ_CLIENT_SECRET", raising=False)
    
    with pytest.raises(ParkWhizAuthenticationError) as exc_info:
        validate_oauth2_credentials()
    
    assert "credentials not configured" in str(exc_info.value).lower()
