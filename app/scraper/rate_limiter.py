"""
Rate limiting system for respectful web scraping.
"""
import asyncio
import logging
import time
from typing import Dict, Optional
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    """Manages rate limiting for a specific domain."""
    
    def __init__(self, domain: str, delay_seconds: float = None):
        self.domain = domain
        self.delay_seconds = delay_seconds or settings.scraper_delay_seconds
        self.last_request_time = 0.0
        self.semaphore = asyncio.Semaphore(1)  # Only one request at a time per domain
        self.request_count = 0
        self.crawl_delay = None  # Will be set from robots.txt if available
    
    def set_crawl_delay(self, delay: float) -> None:
        """Set crawl delay from robots.txt directive."""
        if delay is not None and delay > self.delay_seconds:
            self.delay_seconds = delay
            logger.debug(f"Updated crawl delay for {self.domain} to {delay}s")
    
    async def acquire_slot(self) -> None:
        """Acquire a rate limit slot for this domain."""
        await self.semaphore.acquire()
        
        # Calculate time since last request
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # If we need to wait, do so
        if time_since_last < self.delay_seconds:
            wait_time = self.delay_seconds - time_since_last
            logger.debug(f"Rate limiting {self.domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def release_slot(self) -> None:
        """Release the rate limit slot."""
        self.semaphore.release()
    
    @asynccontextmanager
    async def domain_slot(self):
        """Context manager for acquiring and releasing domain slots."""
        try:
            await self.acquire_slot()
            yield
        finally:
            self.release_slot()


class RateLimitManager:
    """Singleton manager for coordinating rate limiting across all domains."""
    
    def __init__(self):
        self._domain_limiters: Dict[str, DomainRateLimiter] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def get_domain_limiter(self, url: str) -> DomainRateLimiter:
        """Get or create a rate limiter for a domain."""
        domain = urlparse(url).netloc.lower()
        
        async with self._lock:
            if domain not in self._domain_limiters:
                self._domain_limiters[domain] = DomainRateLimiter(domain)
                logger.debug(f"Created rate limiter for domain: {domain}")
            
            return self._domain_limiters[domain]
    
    async def set_crawl_delay(self, url: str, delay: float) -> None:
        """Set crawl delay for a domain from robots.txt."""
        domain = urlparse(url).netloc.lower()
        
        async with self._lock:
            if domain in self._domain_limiters:
                self._domain_limiters[domain].set_crawl_delay(delay)
    
    @asynccontextmanager
    async def acquire_domain_slot(self, url: str):
        """Context manager for acquiring a rate-limited slot for a domain."""
        limiter = await self.get_domain_limiter(url)
        
        async with limiter.domain_slot():
            yield
    
    async def cleanup_unused_limiters(self, max_age_hours: int = 24) -> None:
        """Clean up rate limiters that haven't been used recently."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        async with self._lock:
            domains_to_remove = []
            
            for domain, limiter in self._domain_limiters.items():
                time_since_last = current_time - limiter.last_request_time
                if time_since_last > max_age_seconds:
                    domains_to_remove.append(domain)
            
            for domain in domains_to_remove:
                del self._domain_limiters[domain]
                logger.debug(f"Cleaned up unused rate limiter for domain: {domain}")
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get statistics about rate limiting across all domains."""
        stats = {}
        
        for domain, limiter in self._domain_limiters.items():
            stats[domain] = {
                "request_count": limiter.request_count,
                "last_request_time": limiter.last_request_time,
                "delay_seconds": limiter.delay_seconds,
                "crawl_delay": limiter.crawl_delay,
            }
        
        return stats
    
    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("Rate limiter cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.debug("Stopping rate limiter cleanup task...")
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
                logger.debug("Rate limiter cleanup task stopped gracefully")
            except asyncio.CancelledError:
                logger.debug("Rate limiter cleanup task cancelled")
            except Exception as e:
                logger.error(f"Error stopping rate limiter cleanup task: {e}")
            finally:
                self._cleanup_task = None
    
    async def _cleanup_loop(self) -> None:
        """Background loop for cleaning up unused rate limiters."""
        logger.debug("Rate limiter cleanup loop started")
        try:
            while True:
                try:
                    await asyncio.sleep(3600)  # Run cleanup every hour
                    await self.cleanup_unused_limiters()
                    logger.debug("Rate limiter cleanup completed successfully")
                except asyncio.CancelledError:
                    logger.debug("Rate limiter cleanup loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in rate limiter cleanup loop: {e}")
                    # Continue running despite errors, but log them
                    await asyncio.sleep(300)  # Wait 5 minutes before next attempt
        except Exception as e:
            logger.error(f"Fatal error in rate limiter cleanup loop: {e}")
        finally:
            logger.debug("Rate limiter cleanup loop ended")


# Global rate limit manager instance
_rate_limit_manager: Optional[RateLimitManager] = None


def get_rate_limit_manager() -> RateLimitManager:
    """Get the global rate limit manager instance."""
    global _rate_limit_manager
    
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    
    return _rate_limit_manager


async def init_rate_limit_manager() -> None:
    """Initialize the rate limit manager."""
    global _rate_limit_manager
    
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
        await _rate_limit_manager.start_cleanup_task()
        logger.info("Rate limit manager initialized")


async def close_rate_limit_manager() -> None:
    """Close the rate limit manager."""
    global _rate_limit_manager
    
    if _rate_limit_manager is not None:
        await _rate_limit_manager.stop_cleanup_task()
        _rate_limit_manager = None
        logger.info("Rate limit manager closed")
