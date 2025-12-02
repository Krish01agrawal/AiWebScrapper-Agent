"""
Base scraper agent class extending BaseAgent with scraper-specific functionality.
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
import aiohttp

from app.agents.base import BaseAgent
from app.core.config import settings
from app.scraper.session import get_scraper_session
from app.scraper.rate_limiter import get_rate_limit_manager
from app.scraper.robots import get_robots_checker
from app.scraper.schemas import ScrapingError, ScrapingException, ErrorType

logger = logging.getLogger(__name__)


class BaseScraperAgent(BaseAgent):
    """Base class for scraper agents with common scraping functionality."""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        gemini_client: Optional[Any] = None,
        settings: Optional[Any] = None
    ):
        super().__init__(name, description, version, gemini_client, settings)
        self._session = None
        self._rate_limit_manager = None
        self._robots_checker = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get the scraper session."""
        if self._session is None:
            self._session = get_scraper_session()
        return self._session
    
    def _get_rate_limit_manager(self):
        """Get the rate limit manager."""
        if self._rate_limit_manager is None:
            self._rate_limit_manager = get_rate_limit_manager()
        return self._rate_limit_manager
    
    def _get_robots_checker(self):
        """Get the robots checker."""
        if self._robots_checker is None:
            self._robots_checker = get_robots_checker()
        return self._robots_checker
    
    async def _check_robots_compliance(self, url: str) -> bool:
        """Check if a URL is allowed according to robots.txt."""
        try:
            robots_checker = self._get_robots_checker()
            return await robots_checker.can_fetch(url)
        except Exception as e:
            logger.warning(f"Failed to check robots.txt for {url}: {e}")
            # Default to allowing access on error
            return True
    
    async def _apply_rate_limits(self, url: str):
        """Apply rate limiting for a domain."""
        try:
            rate_limit_manager = self._get_rate_limit_manager()
            return rate_limit_manager.acquire_domain_slot(url)
        except Exception as e:
            logger.warning(f"Failed to apply rate limits for {url}: {e}")
            # Return a dummy context manager that does nothing
            return self._dummy_context_manager()
    
    async def _dummy_context_manager(self):
        """Dummy context manager for when rate limiting fails."""
        class DummyContext:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return DummyContext()
    
    async def _fetch_url(self, url: str, timeout_seconds: Optional[int] = None) -> aiohttp.ClientResponse:
        """Fetch a URL with proper error handling and retries."""
        if timeout_seconds is None:
            timeout_seconds = settings.scraper_request_timeout_seconds
        
        # Check robots.txt compliance
        if not await self._check_robots_compliance(url):
            raise ScrapingException(ScrapingError(
                error_type=ErrorType.ROBOTS_DISALLOWED,
                message=f"URL {url} is disallowed by robots.txt",
                url=url,
                can_retry=False
            ))
        
        # Apply rate limiting
        async with await self._apply_rate_limits(url):
            session = await self._get_session()
            
            for attempt in range(settings.scraper_max_retries + 1):
                try:
                    start_time = time.time()
                    
                    async with session.get(url, timeout=timeout_seconds) as response:
                        processing_time = time.time() - start_time
                        
                        # Handle HTTP errors
                        if response.status >= 400:
                            if response.status == 429:  # Rate limited
                                raise ScrapingException(ScrapingError(
                                    error_type=ErrorType.RATE_LIMITED,
                                    message=f"Rate limited by {url} (status: {response.status})",
                                    url=url,
                                    status_code=response.status,
                                    retry_count=attempt,
                                    max_retries=settings.scraper_max_retries,
                                    processing_time=processing_time,
                                    can_retry=True,
                                    suggested_delay=60.0  # Wait 1 minute
                                ))
                            elif response.status >= 500:  # Server error
                                if attempt < settings.scraper_max_retries:
                                    logger.warning(f"Server error {response.status} for {url}, retrying...")
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                else:
                                    raise ScrapingException(ScrapingError(
                                        error_type=ErrorType.HTTP_ERROR,
                                        message=f"Server error {response.status} for {url}",
                                        url=url,
                                        status_code=response.status,
                                        retry_count=attempt,
                                        max_retries=settings.scraper_max_retries,
                                        processing_time=processing_time,
                                        can_retry=False
                                    ))
                            else:  # Client error (4xx)
                                raise ScrapingException(ScrapingError(
                                    error_type=ErrorType.HTTP_ERROR,
                                    message=f"Client error {response.status} for {url}",
                                    url=url,
                                    status_code=response.status,
                                    retry_count=attempt,
                                        max_retries=settings.scraper_max_retries,
                                        processing_time=processing_time,
                                        can_retry=False
                                    ))
                        
                        # Read content inside the context manager before it closes
                        html_content = await response.text()
                        # Create a mock response-like object to maintain compatibility
                        class ResponseWrapper:
                            def __init__(self, status, text_content, headers):
                                self.status = status
                                self._text = text_content
                                self.headers = headers
                            
                            async def text(self):
                                return self._text
                        
                        return ResponseWrapper(response.status, html_content, response.headers)
                        
                except asyncio.TimeoutError:
                    if attempt < settings.scraper_max_retries:
                        logger.warning(f"Timeout for {url}, retrying...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise ScrapingException(ScrapingError(
                            error_type=ErrorType.TIMEOUT,
                            message=f"Request timeout for {url}",
                            url=url,
                            retry_count=attempt,
                            max_retries=settings.scraper_max_retries,
                            can_retry=False
                        ))
                        
                except aiohttp.ClientError as e:
                    if attempt < settings.scraper_max_retries:
                        logger.warning(f"Connection error for {url}, retrying...: {e}")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise ScrapingException(ScrapingError(
                            error_type=ErrorType.CONNECTION_ERROR,
                            message=f"Connection error for {url}: {str(e)}",
                            url=url,
                            retry_count=attempt,
                            max_retries=settings.scraper_max_retries,
                            exception_type=type(e).__name__,
                            exception_details=str(e),
                            can_retry=False
                        ))
            
            # If we get here, all retries failed
            raise ScrapingException(ScrapingError(
                error_type=ErrorType.UNKNOWN,
                message=f"All retry attempts failed for {url}",
                url=url,
                retry_count=settings.scraper_max_retries,
                max_retries=settings.scraper_max_retries,
                can_retry=False
            ))
    
    def _validate_url(self, url: str) -> str:
        """Validate and normalize a URL."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            
            # Validate URL scheme - only allow http and https
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed.")
            
            if not parsed.netloc:
                raise ValueError(f"Invalid URL: {url}")
            
            # Additional validation for malformed URLs
            if '.' not in parsed.netloc:
                raise ValueError(f"Invalid URL: {url} - missing valid domain")
            
            return url
            
        except Exception as e:
            raise ValueError(f"Invalid URL format: {url}") from e
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _validate_content_size(self, content: str) -> str:
        """Validate content size and truncate if necessary using optimized binary search."""
        content_bytes = len(content.encode('utf-8'))
        
        if content_bytes <= settings.scraper_content_size_limit:
            return content
        
        # Truncate content to fit within limits using binary search for efficiency
        buffer_size = 1000  # Leave 1KB buffer for truncation message
        target_size = settings.scraper_content_size_limit - buffer_size
        
        # Binary search to find optimal truncation point
        left, right = 0, len(content)
        optimal_chars = 0
        
        while left <= right:
            mid = (left + right) // 2
            if mid == 0:
                break
                
            truncated_content = content[:mid]
            actual_bytes = len(truncated_content.encode('utf-8'))
            
            if actual_bytes <= target_size:
                # This size works, but try to find a larger one
                optimal_chars = mid
                left = mid + 1
            else:
                # This size is too large, try smaller
                right = mid - 1
        
        # If we found a valid size, use it; otherwise fall back to conservative approach
        if optimal_chars > 0:
            truncated_content = content[:optimal_chars]
        else:
            # Fallback: use conservative estimate
            max_chars = int(target_size * 0.8)  # Start at 80% of target
            truncated_content = content[:max_chars]
            
            # Fine-tune if still too large
            while max_chars > 0:
                truncated_content = content[:max_chars]
                actual_bytes = len(truncated_content.encode('utf-8'))
                
                if actual_bytes <= target_size:
                    break
                
                max_chars = int(max_chars * 0.9)  # Reduce more aggressively
        
        # Add truncation indicator
        final_content = truncated_content + "... [Content truncated due to size limits]"
        final_bytes = len(final_content.encode('utf-8'))
        
        logger.warning(f"Content truncated from {content_bytes} to {final_bytes} bytes using optimized algorithm")
        return final_content
    
    async def _cleanup_resources(self) -> None:
        """Clean up any resources used by this agent."""
        # Override in subclasses if needed
        pass
    
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent (required by abstract base class)."""
        # This is a base implementation - subclasses should override
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def execute_with_timeout(self, *args, timeout_seconds: Optional[int] = None, **kwargs) -> Any:
        """Execute the agent with timeout handling and resource cleanup."""
        try:
            return await super().execute_with_timeout(*args, timeout_seconds=timeout_seconds, **kwargs)
        finally:
            await self._cleanup_resources()
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information with scraper-specific details."""
        info = super().get_info()
        info.update({
            "scraper_type": "base",
            "respects_robots": settings.scraper_respect_robots,
            "rate_limited": True,
            "max_retries": settings.scraper_max_retries,
            "request_timeout": settings.scraper_request_timeout_seconds,
            "content_size_limit": settings.scraper_content_size_limit
        })
        return info
