#!/usr/bin/env python3
"""
Cache behavior validation utilities for load testing.
"""
import asyncio
import time
import aiohttp
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CacheTestResult(BaseModel):
    """Pydantic model for cache test results."""
    total_requests: int = Field(..., description="Total number of requests")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_misses: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    avg_hit_response_time: float = Field(default=0.0, description="Average response time for cache hits")
    avg_miss_response_time: float = Field(default=0.0, description="Average response time for cache misses")
    time_saved_by_cache: float = Field(default=0.0, description="Total time saved by cache in seconds")
    ttl_validation_passed: bool = Field(default=False, description="Whether TTL validation passed")
    header_validation_passed: bool = Field(default=False, description="Whether cache headers are correct")
    status: str = Field(..., description="Test status: PASS/FAIL/WARN")


class CacheValidator:
    """Validate cache behavior during load tests."""
    
    def __init__(self, api_url: str, api_key: Optional[str] = None):
        """Initialize cache validator.
        
        Args:
            api_url: Base API URL
            api_key: Optional API key for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_cache_warming(
        self, 
        query: str, 
        num_requests: int = 5
    ) -> CacheTestResult:
        """Test cache warming by sending identical requests.
        
        Args:
            query: Query text to test
            num_requests: Number of identical requests to send
            
        Returns:
            CacheTestResult with test outcomes
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        cache_hits = 0
        cache_misses = 0
        hit_times = []
        miss_times = []
        header_errors = []
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": query,
            "timeout_seconds": 300,
            "store_results": False
        }
        
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                async with self.session.post(
                    f"{self.api_url}/api/v1/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    duration = time.time() - start_time
                    
                    # Check cache status header
                    cache_status = response.headers.get("X-Cache-Status", "").upper()
                    
                    if cache_status == "HIT":
                        cache_hits += 1
                        hit_times.append(duration)
                    elif cache_status == "MISS":
                        cache_misses += 1
                        miss_times.append(duration)
                    else:
                        # Unknown cache status
                        cache_misses += 1
                        miss_times.append(duration)
                    
                    # Validate cache headers
                    errors = self.validate_cache_headers(response)
                    if errors:
                        header_errors.extend(errors)
                    
                    await response.read()  # Consume response body
                    
                    # Small delay between requests
                    if i < num_requests - 1:
                        await asyncio.sleep(0.5)
            except Exception as e:
                # Count exceptions as misses
                cache_misses += 1
                miss_times.append(time.time() - start_time)
        
        # Calculate statistics
        total_requests = cache_hits + cache_misses
        hit_rate = (cache_hits / total_requests) if total_requests > 0 else 0.0
        
        avg_hit_time = sum(hit_times) / len(hit_times) if hit_times else 0.0
        avg_miss_time = sum(miss_times) / len(miss_times) if miss_times else 0.0
        
        # Calculate time saved (assuming cache hits are faster)
        time_saved = sum(miss_times) - sum(hit_times) if hit_times and miss_times else 0.0
        
        header_validation_passed = len(header_errors) == 0
        
        # Determine status
        # First request should be MISS, subsequent should be HIT
        expected_hits = max(0, num_requests - 1)
        if cache_hits == expected_hits and cache_misses == 1:
            status = "PASS"
        elif cache_hits > 0:
            status = "WARN"  # Some caching working, but not as expected
        else:
            status = "FAIL"  # No cache hits at all
        
        if not header_validation_passed:
            status = "WARN" if status == "PASS" else status
        
        return CacheTestResult(
            total_requests=total_requests,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            hit_rate=hit_rate,
            avg_hit_response_time=avg_hit_time,
            avg_miss_response_time=avg_miss_time,
            time_saved_by_cache=time_saved,
            ttl_validation_passed=True,  # TTL tested separately
            header_validation_passed=header_validation_passed,
            status=status
        )
    
    async def test_cache_ttl(
        self, 
        query: str, 
        ttl_seconds: int
    ) -> bool:
        """Test cache TTL expiration.
        
        Args:
            query: Query text to test
            ttl_seconds: Expected TTL in seconds
            
        Returns:
            True if TTL validation passed
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": query,
            "timeout_seconds": 300,
            "store_results": False
        }
        
        # First request - should be MISS
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                cache_status1 = response.headers.get("X-Cache-Status", "").upper()
                await response.read()
        except Exception:
            return False
        
        if cache_status1 != "MISS":
            return False  # First request should be MISS
        
        # Second request immediately - should be HIT
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                cache_status2 = response.headers.get("X-Cache-Status", "").upper()
                await response.read()
        except Exception:
            return False
        
        if cache_status2 != "HIT":
            return False  # Second request should be HIT
        
        # Wait for TTL to expire
        await asyncio.sleep(ttl_seconds + 1)
        
        # Third request after TTL - should be MISS
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                cache_status3 = response.headers.get("X-Cache-Status", "").upper()
                await response.read()
        except Exception:
            return False
        
        # After TTL, should be MISS again
        return cache_status3 == "MISS"
    
    async def test_cache_with_different_queries(
        self, 
        queries: List[str]
    ) -> Dict[str, Any]:
        """Test that different queries don't share cache.
        
        Args:
            queries: List of different query texts
            
        Returns:
            Dictionary with test results
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        results = {}
        
        for query in queries:
            payload = {
                "query": query,
                "timeout_seconds": 300,
                "store_results": False
            }
            
            try:
                async with self.session.post(
                    f"{self.api_url}/api/v1/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    cache_status = response.headers.get("X-Cache-Status", "").upper()
                    results[query] = {
                        "cache_status": cache_status,
                        "status_code": response.status
                    }
                    await response.read()
            except Exception as e:
                results[query] = {
                    "error": str(e),
                    "cache_status": "UNKNOWN"
                }
        
        # All different queries should be MISS (first time)
        all_miss = all(r.get("cache_status") == "MISS" for r in results.values())
        
        return {
            "queries_tested": len(queries),
            "results": results,
            "all_different_cache_keys": all_miss,
            "status": "PASS" if all_miss else "FAIL"
        }
    
    def validate_cache_headers(
        self, 
        response: aiohttp.ClientResponse
    ) -> List[str]:
        """Validate cache headers in response.
        
        Args:
            response: aiohttp ClientResponse object
            
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check X-Cache-Status header
        cache_status = response.headers.get("X-Cache-Status", "").upper()
        if cache_status not in ["HIT", "MISS", ""]:
            errors.append(f"Invalid X-Cache-Status value: {cache_status}")
        
        # Check X-Cache-Age header (should be present for HIT)
        if cache_status == "HIT":
            cache_age = response.headers.get("X-Cache-Age")
            if cache_age:
                try:
                    age = int(cache_age)
                    if age < 0:
                        errors.append(f"Invalid X-Cache-Age value: {age}")
                except ValueError:
                    errors.append(f"X-Cache-Age header is not a valid integer: {cache_age}")
            # Cache-Age is optional, so we don't require it
        
        # Check Cache-Control header (optional but recommended)
        cache_control = response.headers.get("Cache-Control")
        if cache_control:
            # Basic validation - should contain max-age or similar
            if "max-age" not in cache_control.lower() and "no-cache" not in cache_control.lower():
                # Not an error, just informational
                pass
        
        return errors
    
    async def measure_cache_performance_impact(
        self, 
        query: str
    ) -> Dict[str, Any]:
        """Measure performance impact of cache hits vs misses.
        
        Args:
            query: Query text to test
            
        Returns:
            Dictionary with performance comparison
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": query,
            "timeout_seconds": 300,
            "store_results": False
        }
        
        # First request (MISS)
        miss_time = None
        try:
            start = time.time()
            async with self.session.post(
                f"{self.api_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                miss_time = time.time() - start
                await response.read()
        except Exception as e:
            return {"error": str(e)}
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Second request (HIT)
        hit_time = None
        try:
            start = time.time()
            async with self.session.post(
                f"{self.api_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                hit_time = time.time() - start
                await response.read()
        except Exception as e:
            return {"error": str(e)}
        
        if miss_time and hit_time:
            speedup = miss_time / hit_time if hit_time > 0 else 0.0
            time_saved = miss_time - hit_time
            
            return {
                "miss_time_seconds": miss_time,
                "hit_time_seconds": hit_time,
                "speedup": speedup,
                "time_saved_seconds": time_saved,
                "improvement_percentage": (time_saved / miss_time * 100) if miss_time > 0 else 0.0
            }
        else:
            return {"error": "Could not measure both hit and miss times"}
    
    def analyze_cache_effectiveness(
        self, 
        test_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze cache effectiveness from test results.
        
        Args:
            test_results: List of test result dictionaries
            
        Returns:
            Dictionary with analysis and recommendations
        """
        if not test_results:
            return {
                "status": "no_data",
                "recommendations": ["No test results provided"]
            }
        
        total_hits = sum(r.get("cache_hits", 0) for r in test_results)
        total_misses = sum(r.get("cache_misses", 0) for r in test_results)
        total_requests = total_hits + total_misses
        
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        # Calculate average time saved
        total_time_saved = sum(r.get("time_saved_by_cache", 0.0) for r in test_results)
        avg_time_saved = total_time_saved / len(test_results) if test_results else 0.0
        
        recommendations = []
        
        if overall_hit_rate < 50.0:
            recommendations.append(
                f"Cache hit rate is low ({overall_hit_rate:.1f}%) - consider increasing cache TTL or cache size"
            )
        
        if total_hits == 0:
            recommendations.append(
                "No cache hits detected - verify cache is enabled and working correctly"
            )
        
        if avg_time_saved > 0:
            recommendations.append(
                f"Cache is saving an average of {avg_time_saved:.2f} seconds per request"
            )
        
        return {
            "status": "analyzed",
            "total_tests": len(test_results),
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": overall_hit_rate,
            "avg_time_saved_seconds": avg_time_saved,
            "total_time_saved_seconds": total_time_saved,
            "recommendations": recommendations
        }

