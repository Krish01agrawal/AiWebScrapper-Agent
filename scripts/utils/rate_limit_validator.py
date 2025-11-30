#!/usr/bin/env python3
"""
Rate limiting validation utilities for load testing.
"""
import asyncio
import time
import aiohttp
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RateLimitTestResult(BaseModel):
    """Pydantic model for rate limit test results."""
    rate_limit: int = Field(..., description="Configured rate limit")
    requests_sent: int = Field(..., description="Total requests sent")
    requests_blocked: int = Field(..., description="Number of requests blocked (429)")
    requests_allowed: int = Field(..., description="Number of requests allowed")
    false_positives: int = Field(default=0, description="Requests allowed when should be blocked")
    false_negatives: int = Field(default=0, description="Requests blocked when should be allowed")
    header_validation_passed: bool = Field(default=False, description="Whether headers are correct")
    recovery_time_seconds: Optional[float] = Field(None, description="Time for rate limit to reset")
    status: str = Field(..., description="Test status: PASS/FAIL/WARN")


class RateLimitValidator:
    """Validate rate limiting behavior during load tests."""
    
    def __init__(self, api_url: str, api_key: Optional[str] = None):
        """Initialize rate limit validator.
        
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
    
    async def test_rate_limit_enforcement(
        self, 
        rate_limit: int, 
        duration: int = 60
    ) -> RateLimitTestResult:
        """Test rate limit enforcement by sending requests exceeding the limit.
        
        Args:
            rate_limit: Expected rate limit (requests per minute)
            duration: Test duration in seconds
            
        Returns:
            RateLimitTestResult with test outcomes
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        requests_sent = 0
        requests_blocked = 0
        requests_allowed = 0
        header_errors = []
        
        # Send requests at a rate that exceeds the limit
        # Send rate_limit + 10 requests in the first minute
        requests_per_second = (rate_limit + 10) / 60.0
        end_time = time.time() + duration
        
        async def send_request():
            """Send a single request and check response."""
            nonlocal requests_sent, requests_blocked, requests_allowed
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            payload = {
                "query": "test rate limit query",
                "timeout_seconds": 30,
                "store_results": False
            }
            
            try:
                async with self.session.post(
                    f"{self.api_url}/api/v1/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    requests_sent += 1
                    
                    # Check status code
                    if response.status == 429:
                        requests_blocked += 1
                        
                        # Validate rate limit headers
                        errors = self.validate_rate_limit_headers(response)
                        if errors:
                            header_errors.extend(errors)
                    elif response.status == 200:
                        requests_allowed += 1
                    else:
                        # Other error status
                        requests_allowed += 1
                    
                    await response.read()  # Consume response body
            except Exception as e:
                requests_sent += 1
                # Count exceptions as allowed (they're not rate limited)
                requests_allowed += 1
        
        # Send requests concurrently
        tasks = []
        while time.time() < end_time and requests_sent < (rate_limit * 2):
            task = asyncio.create_task(send_request())
            tasks.append(task)
            await asyncio.sleep(1.0 / requests_per_second)
        
        # Wait for all requests to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        # False positives: requests allowed when rate limit should have blocked them
        # In a sliding window, some requests might be allowed even if we exceed the limit
        # This is expected behavior, so we don't count them as false positives
        
        # False negatives: requests blocked when they should be allowed
        # If we send exactly rate_limit requests, all should be allowed
        false_negatives = 0
        if requests_sent <= rate_limit and requests_blocked > 0:
            false_negatives = requests_blocked
        
        header_validation_passed = len(header_errors) == 0
        
        # Determine status
        if false_negatives > 0:
            status = "FAIL"
        elif not header_validation_passed:
            status = "WARN"
        elif requests_blocked == 0 and requests_sent > rate_limit:
            status = "WARN"  # Rate limiting might not be working
        else:
            status = "PASS"
        
        return RateLimitTestResult(
            rate_limit=rate_limit,
            requests_sent=requests_sent,
            requests_blocked=requests_blocked,
            requests_allowed=requests_allowed,
            false_positives=0,  # Hard to determine with sliding window
            false_negatives=false_negatives,
            header_validation_passed=header_validation_passed,
            recovery_time_seconds=None,
            status=status
        )
    
    async def test_rate_limit_recovery(
        self, 
        rate_limit: int
    ) -> float:
        """Test rate limit recovery after being blocked.
        
        Args:
            rate_limit: Expected rate limit
            
        Returns:
            Recovery time in seconds
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # First, trigger rate limit
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": "test rate limit recovery",
            "timeout_seconds": 30,
            "store_results": False
        }
        
        # Send requests until we get rate limited
        rate_limited = False
        start_time = time.time()
        
        for _ in range(rate_limit + 5):
            try:
                async with self.session.post(
                    f"{self.api_url}/api/v1/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:
                        rate_limited = True
                        break
                    await response.read()
            except Exception:
                pass
        
        if not rate_limited:
            return 0.0  # Could not trigger rate limit
        
        # Wait and check when rate limit resets
        recovery_start = time.time()
        max_wait = 70  # Wait up to 70 seconds
        
        while time.time() - recovery_start < max_wait:
            await asyncio.sleep(5)
            
            try:
                async with self.session.post(
                    f"{self.api_url}/api/v1/scrape",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        recovery_time = time.time() - recovery_start
                        await response.read()
                        return recovery_time
                    await response.read()
            except Exception:
                pass
        
        return max_wait  # Did not recover within max wait time
    
    async def test_authenticated_vs_unauthenticated(
        self, 
        rate_limit_unauthenticated: int,
        rate_limit_authenticated: int
    ) -> Dict[str, Any]:
        """Compare rate limits for authenticated vs unauthenticated requests.
        
        Args:
            rate_limit_unauthenticated: Expected rate limit without API key
            rate_limit_authenticated: Expected rate limit with API key
            
        Returns:
            Dictionary with comparison results
        """
        # Preserve original API key
        original_api_key = self.api_key
        
        # Test unauthenticated
        self.api_key = None
        unauthenticated_result = await self.test_rate_limit_enforcement(
            rate_limit_unauthenticated,
            duration=60
        )
        
        # Restore API key for authenticated test
        self.api_key = original_api_key
        
        # Test authenticated
        if self.api_key:
            authenticated_result = await self.test_rate_limit_enforcement(
                rate_limit_authenticated,
                duration=60
            )
        else:
            authenticated_result = None
        
        return {
            "unauthenticated": unauthenticated_result.model_dump() if unauthenticated_result else None,
            "authenticated": authenticated_result.model_dump() if authenticated_result else None,
            "comparison": {
                "unauthenticated_limit": rate_limit_unauthenticated,
                "authenticated_limit": rate_limit_authenticated,
                "difference": rate_limit_authenticated - rate_limit_unauthenticated
            }
        }
    
    def validate_rate_limit_headers(
        self, 
        response: aiohttp.ClientResponse
    ) -> List[str]:
        """Validate rate limit headers in response.
        
        Args:
            response: aiohttp ClientResponse object
            
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check required headers for 429 responses
        if response.status == 429:
            required_headers = [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After"
            ]
            
            for header in required_headers:
                if header not in response.headers:
                    errors.append(f"Missing required header: {header}")
            
            # Validate Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    retry_seconds = int(retry_after)
                    if retry_seconds < 0 or retry_seconds > 120:
                        errors.append(f"Invalid Retry-After value: {retry_seconds}")
                except ValueError:
                    errors.append(f"Retry-After header is not a valid integer: {retry_after}")
        
        # Check headers for all responses
        rate_limit_limit = response.headers.get("X-RateLimit-Limit")
        if rate_limit_limit:
            try:
                limit = int(rate_limit_limit)
                if limit < 0:
                    errors.append(f"Invalid X-RateLimit-Limit value: {limit}")
            except ValueError:
                errors.append(f"X-RateLimit-Limit header is not a valid integer: {rate_limit_limit}")
        
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining < 0:
                    errors.append(f"Invalid X-RateLimit-Remaining value: {remaining}")
            except ValueError:
                errors.append(f"X-RateLimit-Remaining header is not a valid integer: {rate_limit_remaining}")
        
        return errors
    
    def analyze_rate_limit_behavior(
        self, 
        test_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze rate limiting behavior from test results.
        
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
        
        total_blocked = sum(r.get("requests_blocked", 0) for r in test_results)
        total_sent = sum(r.get("requests_sent", 0) for r in test_results)
        total_false_negatives = sum(r.get("false_negatives", 0) for r in test_results)
        header_validation_failures = sum(
            1 for r in test_results if not r.get("header_validation_passed", False)
        )
        
        recommendations = []
        
        if total_false_negatives > 0:
            recommendations.append(
                f"Rate limiting incorrectly blocked {total_false_negatives} requests that should have been allowed"
            )
        
        if header_validation_failures > 0:
            recommendations.append(
                f"Rate limit headers validation failed in {header_validation_failures} test(s)"
            )
        
        if total_blocked == 0 and total_sent > 0:
            recommendations.append(
                "No requests were blocked - verify rate limiting is enabled and configured correctly"
            )
        
        return {
            "status": "analyzed",
            "total_tests": len(test_results),
            "total_requests_sent": total_sent,
            "total_requests_blocked": total_blocked,
            "block_rate": (total_blocked / total_sent * 100) if total_sent > 0 else 0.0,
            "false_negatives": total_false_negatives,
            "header_validation_failures": header_validation_failures,
            "recommendations": recommendations
        }

