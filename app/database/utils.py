import asyncio
import math
import logging
from typing import Awaitable, Callable, TypeVar
from app.core.config import settings

T = TypeVar('T')
logger = logging.getLogger(__name__)

async def run_with_timeout_and_retries(func: Callable[[], Awaitable[T]], timeout_s: int, retries: int) -> T:
    attempt = 0
    last_exc = None
    backoff_base = 0.3
    while attempt <= retries:
        try:
            return await asyncio.wait_for(func(), timeout=timeout_s)
        except Exception as e:
            last_exc = e
            if attempt == retries:
                break
            delay = backoff_base * (2 ** attempt)
            await asyncio.sleep(delay)
            attempt += 1
    raise last_exc

def apply_query_timeout(cursor):
    try:
        # Motor cursors (find/aggregate) support max_time_ms
        timeout_ms = int(settings.database_query_timeout_seconds * 1000)
        if hasattr(cursor, 'max_time_ms'):
            return cursor.max_time_ms(timeout_ms)
    except Exception as e:
        logger.debug(f"apply_query_timeout noop: {e}")
    return cursor