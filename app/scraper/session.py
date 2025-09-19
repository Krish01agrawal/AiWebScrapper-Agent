"""
HTTP session management for web scraping operations.
"""
import asyncio
import logging
from typing import Optional
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from aiohttp.resolver import AsyncResolver

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global client session
_client_session: Optional[aiohttp.ClientSession] = None


async def init_scraper_session() -> None:
    """Initialize the global aiohttp client session for web scraping."""
    global _client_session
    
    if _client_session is not None:
        logger.warning("Scraper session already initialized")
        return
    
    try:
        # Create custom connector with optimized settings for scraping
        connector = TCPConnector(
            limit=settings.scraper_concurrency * 2,  # Allow more connections than concurrency limit
            limit_per_host=settings.scraper_concurrency,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            resolver=AsyncResolver(),
            ttl_dns_cache=300,  # Cache DNS results for 5 minutes
        )
        
        # Create timeout configuration
        timeout = ClientTimeout(
            total=settings.scraper_request_timeout_seconds,
            connect=10,
            sock_read=settings.scraper_request_timeout_seconds
        )
        
        # Create session with custom headers and settings
        _client_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": settings.scraper_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            raise_for_status=False,  # Don't raise exceptions for HTTP error status codes
        )
        
        logger.info("Scraper session initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize scraper session: {e}")
        raise


async def close_scraper_session() -> None:
    """Close the global aiohttp client session."""
    global _client_session
    
    if _client_session is None:
        logger.warning("No scraper session to close")
        return
    
    try:
        await _client_session.close()
        _client_session = None
        logger.info("Scraper session closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing scraper session: {e}")
        raise


def get_scraper_session() -> aiohttp.ClientSession:
    """Get the global scraper session with error handling."""
    if _client_session is None:
        raise RuntimeError("Scraper session not initialized. Call init_scraper_session() first.")
    
    if _client_session.closed:
        raise RuntimeError("Scraper session is closed")
    
    return _client_session


async def test_scraper_session() -> bool:
    """Test the scraper session by making a simple request."""
    try:
        session = get_scraper_session()
        async with session.get("http://httpbin.org/get", timeout=settings.scraper_request_timeout_seconds) as response:
            return response.status == 200
    except Exception as e:
        logger.error(f"Scraper session test failed: {e}")
        return False
