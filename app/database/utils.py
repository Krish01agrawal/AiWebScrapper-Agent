"""
Database utility functions for timeouts, retries, and error handling.
"""
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def run_with_timeout_and_retries(
    coro_factory: Callable[[], Any], 
    timeout_s: Optional[int] = None, 
    retries: Optional[int] = None,
    retry_exceptions: tuple = (Exception,)
) -> Any:
    """
    Run a coroutine factory with timeout and retry logic using exponential backoff.
    
    Args:
        coro_factory: Function that produces a fresh coroutine per attempt
        timeout_s: Timeout in seconds (defaults to settings.database_query_timeout_seconds)
        retries: Number of retries (defaults to settings.database_max_retries)
        retry_exceptions: Tuple of exception types to retry on
    
    Returns:
        The result of the coroutine execution
        
    Raises:
        asyncio.TimeoutError: If the operation times out
        Exception: If all retries are exhausted
    """
    timeout_s = timeout_s or settings.database_query_timeout_seconds
    retries = retries or settings.database_max_retries
    
    last_exception = None
    
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retrying database operation (attempt {attempt + 1}/{retries + 1})")
                # Exponential backoff: 0.2, 0.4, 0.8...
                await asyncio.sleep(0.2 * (2 ** (attempt - 1)))
            
            # Create fresh coroutine for this attempt
            coro = coro_factory()
            result = await asyncio.wait_for(coro, timeout=timeout_s)
            return result
            
        except asyncio.TimeoutError:
            last_exception = asyncio.TimeoutError(f"Database operation timed out after {timeout_s} seconds")
            logger.warning(f"Database operation timed out (attempt {attempt + 1}/{retries + 1})")
            
        except retry_exceptions as e:
            last_exception = e
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{retries + 1}): {e}")
            
            # Don't retry on certain types of errors
            if isinstance(e, (ValueError, TypeError, AttributeError)):
                raise e
        
        except Exception as e:
            # Non-retryable exceptions
            logger.error(f"Non-retryable database operation error: {e}")
            raise e
    
    # If we get here, all retries were exhausted
    logger.error(f"Database operation failed after {retries + 1} attempts")
    raise last_exception


def with_database_timeout_and_retries(
    timeout_s: Optional[int] = None,
    retries: Optional[int] = None
):
    """
    Decorator to add timeout and retry logic to database operations.
    
    Args:
        timeout_s: Timeout in seconds (defaults to settings.database_query_timeout_seconds)
        retries: Number of retries (defaults to settings.database_max_retries)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await run_with_timeout_and_retries(
                lambda: func(*args, **kwargs), timeout_s, retries
            )
        return wrapper
    return decorator


def apply_query_timeout(cursor_or_aggregation, timeout: Optional[int] = None):
    """
    Apply timeout to MongoDB cursor or aggregation.
    
    Args:
        cursor_or_aggregation: MongoDB cursor or aggregation object
        timeout: Timeout in milliseconds (defaults to settings.database_query_timeout_seconds * 1000)
    
    Returns:
        The cursor or aggregation with timeout applied
    """
    timeout_ms = (timeout or settings.database_query_timeout_seconds) * 1000
    
    if hasattr(cursor_or_aggregation, 'max_time_ms'):
        return cursor_or_aggregation.max_time_ms(timeout_ms)
    
    return cursor_or_aggregation
