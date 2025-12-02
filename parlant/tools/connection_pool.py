"""
Connection pooling for external API calls.

This module provides connection pooling to optimize API performance:
- HTTP connection reuse
- Configurable pool sizes
- Timeout management
- Connection lifecycle management
"""

import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    Manages HTTP connection pools for external APIs.
    
    This class provides singleton connection pools for different APIs
    to improve performance by reusing connections.
    """
    
    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0
    ):
        """
        Initialize connection pool manager.
        
        Args:
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum number of idle connections to keep
            keepalive_expiry: Seconds to keep idle connections alive
            timeout: Default timeout for requests in seconds
        """
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout
        
        # Connection pools for different APIs
        self._freshdesk_client: Optional[httpx.AsyncClient] = None
        self._parkwhiz_client: Optional[httpx.AsyncClient] = None
        self._lakera_client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "Connection pool manager initialized",
            extra={
                "max_connections": max_connections,
                "max_keepalive": max_keepalive_connections,
                "keepalive_expiry": keepalive_expiry
            }
        )
    
    def _create_client(self, base_url: Optional[str] = None) -> httpx.AsyncClient:
        """
        Create a new HTTP client with connection pooling.
        
        Args:
            base_url: Optional base URL for the client
            
        Returns:
            Configured AsyncClient with connection pooling
        """
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry
        )
        
        timeout = httpx.Timeout(self.timeout)
        
        return httpx.AsyncClient(
            base_url=base_url,
            limits=limits,
            timeout=timeout,
            http2=True  # Enable HTTP/2 for better performance
        )
    
    def get_freshdesk_client(self, base_url: str) -> httpx.AsyncClient:
        """
        Get or create Freshdesk API client.
        
        Args:
            base_url: Freshdesk API base URL
            
        Returns:
            Configured AsyncClient for Freshdesk
        """
        if self._freshdesk_client is None:
            self._freshdesk_client = self._create_client(base_url)
            logger.info("Created Freshdesk connection pool")
        
        return self._freshdesk_client
    
    def get_parkwhiz_client(self, base_url: str) -> httpx.AsyncClient:
        """
        Get or create ParkWhiz API client.
        
        Args:
            base_url: ParkWhiz API base URL
            
        Returns:
            Configured AsyncClient for ParkWhiz
        """
        if self._parkwhiz_client is None:
            self._parkwhiz_client = self._create_client(base_url)
            logger.info("Created ParkWhiz connection pool")
        
        return self._parkwhiz_client
    
    def get_lakera_client(self, base_url: str) -> httpx.AsyncClient:
        """
        Get or create Lakera API client.
        
        Args:
            base_url: Lakera API base URL
            
        Returns:
            Configured AsyncClient for Lakera
        """
        if self._lakera_client is None:
            self._lakera_client = self._create_client(base_url)
            logger.info("Created Lakera connection pool")
        
        return self._lakera_client
    
    async def close_all(self):
        """Close all connection pools."""
        if self._freshdesk_client:
            await self._freshdesk_client.aclose()
            self._freshdesk_client = None
            logger.info("Closed Freshdesk connection pool")
        
        if self._parkwhiz_client:
            await self._parkwhiz_client.aclose()
            self._parkwhiz_client = None
            logger.info("Closed ParkWhiz connection pool")
        
        if self._lakera_client:
            await self._lakera_client.aclose()
            self._lakera_client = None
            logger.info("Closed Lakera connection pool")


# Global connection pool manager instance
_pool_manager: Optional[ConnectionPoolManager] = None


def get_connection_pool_manager(
    max_connections: int = 100,
    max_keepalive_connections: int = 20,
    keepalive_expiry: float = 30.0,
    timeout: float = 30.0
) -> ConnectionPoolManager:
    """
    Get the global connection pool manager instance.
    
    Args:
        max_connections: Maximum number of connections in pool
        max_keepalive_connections: Maximum number of idle connections to keep
        keepalive_expiry: Seconds to keep idle connections alive
        timeout: Default timeout for requests in seconds
        
    Returns:
        The global ConnectionPoolManager instance
    """
    global _pool_manager
    
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            timeout=timeout
        )
    
    return _pool_manager


async def close_connection_pools():
    """Close all connection pools."""
    global _pool_manager
    
    if _pool_manager is not None:
        await _pool_manager.close_all()
        _pool_manager = None
