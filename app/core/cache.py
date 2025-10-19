"""
In-memory caching layer with TTL support for API responses and database queries.
"""

import asyncio
import time
import hashlib
import json
from typing import Any, Dict, Optional, Callable
from functools import wraps
import logging
from fastapi.responses import JSONResponse


class CacheEntry:
    """Cache entry with expiration and access tracking."""
    
    def __init__(self, value: Any, ttl: int):
        """Initialize cache entry."""
        self.value = value
        self.expiration_time = time.time() + ttl
        self.created_at = time.time()
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expiration_time
    
    def touch(self):
        """Update access information."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def get_value(self) -> Optional[Any]:
        """Get value if not expired."""
        if self.is_expired():
            return None
        self.touch()
        return self.value


class InMemoryCache:
    """In-memory cache with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """Initialize cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.logger = logging.getLogger(__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        if key not in self._cache:
            self.misses += 1
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return entry.get_value()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in cache."""
        if ttl is None:
            ttl = self.default_ttl
        
        # Check if we need to evict
        if len(self._cache) >= self.max_size and key not in self._cache:
            await self._evict_lru()
        
        self._cache[key] = CacheEntry(value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_size,
            "evictions": self.evictions
        }
    
    async def _evict_expired(self) -> int:
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self.evictions += 1
        
        return len(expired_keys)
    
    async def _evict_lru(self) -> None:
        """Remove least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self.evictions += 1


def generate_cache_key(*args, **kwargs) -> str:
    """Generate deterministic cache key from arguments."""
    # Convert args and kwargs to strings
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (dict, list)):
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            key_parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        for key, value in sorted_kwargs:
            if isinstance(value, (dict, list)):
                key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
            else:
                key_parts.append(f"{key}={value}")
    
    # Create hash
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching async function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = generate_cache_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Get cache instance (assuming it's available globally)
            cache = get_cache()
            if not cache:
                return await func(*args, **kwargs)
            
            # Check cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                # Cache successful results only
                await cache.set(cache_key, result, ttl)
                return result
            except Exception as e:
                # Don't cache errors
                raise e
        
        return wrapper
    return decorator


def cache_response(ttl: int = 300):
    """Decorator for caching FastAPI endpoint responses."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs if present
            request = kwargs.get('request')
            if not request:
                return await func(*args, **kwargs)
            
            # Generate cache key from request
            cache_key = generate_cache_key(
                func.__name__,
                request.url.path,
                request.query_params,
                request.headers.get('x-api-key', '')
            )
            
            # Get cache instance
            cache = get_cache()
            if not cache:
                return await func(*args, **kwargs)
            
            # Check cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                # Build new JSONResponse from cached dict
                cache_age_seconds = int(time.time() - cached_result.get("cached_at", 0))
                
                # Remove cached_at from response data
                response_data = cached_result.copy()
                response_data.pop("cached_at", None)
                
                response = JSONResponse(content=response_data)
                response.headers["X-Cache-Status"] = "HIT"
                response.headers["X-Cache-Age"] = str(cache_age_seconds)
                return response
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache successful responses - always cache as dict
            if hasattr(result, 'status_code') and result.status_code == 200:
                # Extract content from response
                if hasattr(result, 'model_dump'):
                    cache_data = result.model_dump()
                elif hasattr(result, 'body'):
                    import json
                    cache_data = json.loads(result.body.decode())
                else:
                    # For other response types, skip caching
                    return result
                
                # Add cache metadata
                cache_data["cached_at"] = time.time()
                await cache.set(cache_key, cache_data, ttl)
                
                # Add cache headers
                if hasattr(result, 'headers'):
                    result.headers["X-Cache-Status"] = "MISS"
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
_cache_instance: Optional[InMemoryCache] = None


def get_cache() -> Optional[InMemoryCache]:
    """Get global cache instance."""
    return _cache_instance


def initialize_cache(max_size: int = 1000, default_ttl: int = 300) -> InMemoryCache:
    """Initialize global cache instance."""
    global _cache_instance
    _cache_instance = InMemoryCache(max_size=max_size, default_ttl=default_ttl)
    return _cache_instance


async def cleanup_task():
    """Background task for cache cleanup."""
    cache = get_cache()
    if not cache:
        return
    
    while True:
        try:
            expired_count = await cache._evict_expired()
            if expired_count > 0:
                cache.logger.info(f"Cleaned up {expired_count} expired cache entries")
            
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            cache.logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)
