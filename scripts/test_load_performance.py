#!/usr/bin/env python3
"""
Load testing and performance validation script for the /api/v1/scrape endpoint.
Tests concurrent request handling, rate limiting, caching, memory usage, and connection pooling.
"""
import asyncio
import aiohttp
import json
import time
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from pprint import pprint

# Import utilities
from scripts.utils.load_test_monitor import (
    MemoryMonitor, ConnectionPoolMonitor, LoadTestMetrics,
    calculate_percentiles, format_memory_size, generate_load_test_report
)
from scripts.utils.rate_limit_validator import RateLimitValidator
from scripts.utils.cache_validator import CacheValidator
from app.core.config import get_settings
from app.core.database import get_client


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300


class LoadTester:
    """Load testing class for concurrent request testing."""
    
    def __init__(
        self, 
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """Initialize load tester.
        
        Args:
            base_url: Base API URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.memory_monitor = MemoryMonitor()
        self.pool_monitor = ConnectionPoolMonitor()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def send_request(
        self, 
        query: str,
        request_id: int
    ) -> Dict[str, Any]:
        """Send a single request and measure response time.
        
        Args:
            query: Query text
            request_id: Unique request identifier
            
        Returns:
            Dictionary with request results
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": query,
            "timeout_seconds": self.timeout,
            "store_results": False
        }
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                duration = time.time() - start_time
                
                # Read response body
                try:
                    response_data = await response.json()
                except:
                    response_data = {"error": "Invalid JSON response"}
                
                # Extract cache status
                cache_status = response.headers.get("X-Cache-Status", "").upper()
                
                # Check rate limit
                is_rate_limited = response.status == 429
                
                return {
                    "request_id": request_id,
                    "status_code": response.status,
                    "duration": duration,
                    "cache_status": cache_status,
                    "rate_limited": is_rate_limited,
                    "success": response.status == 200,
                    "response_size": len(str(response_data))
                }
        except asyncio.TimeoutError:
            return {
                "request_id": request_id,
                "status_code": 408,
                "duration": time.time() - start_time,
                "cache_status": "UNKNOWN",
                "rate_limited": False,
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "request_id": request_id,
                "status_code": 500,
                "duration": time.time() - start_time,
                "cache_status": "UNKNOWN",
                "rate_limited": False,
                "success": False,
                "error": str(e)
            }
    
    async def test_gradual_ramp_up(
        self, 
        max_concurrency: int = 50,
        query: str = "best AI tools for coding"
    ) -> LoadTestMetrics:
        """Test gradual ramp-up from 1 to max_concurrency.
        
        Args:
            max_concurrency: Maximum concurrent requests
            query: Query text to use
            
        Returns:
            LoadTestMetrics with test results
        """
        print(f"\n📈 Testing Gradual Ramp-Up (1 to {max_concurrency} concurrent requests)...")
        
        start_time = datetime.utcnow()
        self.memory_monitor.start_monitoring()
        
        all_results = []
        response_times = []
        cache_hits = 0
        cache_misses = 0
        rate_limit_hits = 0
        successful = 0
        failed = 0
        
        # Gradually increase concurrency
        for concurrency in range(1, max_concurrency + 1, max(1, max_concurrency // 10)):
            print(f"  Testing with {concurrency} concurrent requests...")
            
            # Create tasks for concurrent requests
            tasks = [
                self.send_request(query, i)
                for i in range(concurrency)
            ]
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    continue
                
                all_results.append(result)
                response_times.append(result["duration"])
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                
                if result["cache_status"] == "HIT":
                    cache_hits += 1
                elif result["cache_status"] == "MISS":
                    cache_misses += 1
                
                if result["rate_limited"]:
                    rate_limit_hits += 1
            
            # Small delay between concurrency levels
            await asyncio.sleep(1)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Stop memory monitoring
        memory_stats = self.memory_monitor.stop_monitoring()
        
        # Get connection pool stats
        try:
            client = get_client()
            self.pool_monitor.set_client(client)
            pool_stats = self.pool_monitor.get_pool_stats()
        except Exception:
            pool_stats = {"error": "Could not get connection pool stats"}
        
        return LoadTestMetrics(
            total_requests=len(all_results),
            successful_requests=successful,
            failed_requests=failed,
            response_times=response_times,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            rate_limit_hits=rate_limit_hits,
            memory_stats=memory_stats,
            connection_pool_stats=pool_stats,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
    
    async def test_burst_traffic(
        self, 
        concurrency: int = 50,
        query: str = "best AI tools for coding"
    ) -> LoadTestMetrics:
        """Test burst traffic with sudden spike of concurrent requests.
        
        Args:
            concurrency: Number of simultaneous requests
            query: Query text to use
            
        Returns:
            LoadTestMetrics with test results
        """
        print(f"\n💥 Testing Burst Traffic ({concurrency} simultaneous requests)...")
        
        start_time = datetime.utcnow()
        self.memory_monitor.start_monitoring()
        
        # Set up connection pool monitor
        try:
            client = get_client()
            self.pool_monitor.set_client(client)
        except Exception:
            pass  # Will handle error later
        
        # Create all tasks at once
        tasks = [
            self.send_request(query, i)
            for i in range(concurrency)
        ]
        
        # Start continuous pool monitoring during burst (estimate duration ~30s max)
        pool_monitoring_task = None
        try:
            if self.pool_monitor.client:
                # Monitor for up to 30 seconds to capture burst behavior
                pool_monitoring_task = asyncio.create_task(
                    self.pool_monitor.monitor_during_load(duration=30.0, interval=0.5)
                )
        except Exception:
            pass  # Continue without pool monitoring if it fails
        
        # Execute all requests simultaneously
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Wait for pool monitoring to complete if it was started
        if pool_monitoring_task:
            try:
                await pool_monitoring_task
            except Exception:
                pass
        
        # Process results
        response_times = []
        cache_hits = 0
        cache_misses = 0
        rate_limit_hits = 0
        successful = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                continue
            
            response_times.append(result["duration"])
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
            
            if result["cache_status"] == "HIT":
                cache_hits += 1
            elif result["cache_status"] == "MISS":
                cache_misses += 1
            
            if result["rate_limited"]:
                rate_limit_hits += 1
        
        # Stop memory monitoring
        memory_stats = self.memory_monitor.stop_monitoring()
        
        # Analyze connection pool behavior from continuous monitoring
        try:
            if self.pool_monitor.client:
                pool_analysis = self.pool_monitor.analyze_pool_behavior()
                # Merge analysis with current snapshot for comprehensive stats
                current_snapshot = self.pool_monitor.get_pool_stats()
                pool_stats = {
                    **current_snapshot,
                    "monitoring_analysis": pool_analysis,
                    "samples_collected": len(self.pool_monitor.pool_samples)
                }
            else:
                pool_stats = {"error": "MongoDB client not available"}
        except Exception as e:
            pool_stats = {"error": f"Could not analyze connection pool stats: {str(e)}"}
        
        return LoadTestMetrics(
            total_requests=len(results),
            successful_requests=successful,
            failed_requests=failed,
            response_times=response_times,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            rate_limit_hits=rate_limit_hits,
            memory_stats=memory_stats,
            connection_pool_stats=pool_stats,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
    
    async def test_sustained_load(
        self, 
        concurrency: int = 20,
        duration: int = 120,
        query: str = "best AI tools for coding"
    ) -> LoadTestMetrics:
        """Test sustained load for a duration.
        
        Args:
            concurrency: Number of concurrent requests
            duration: Test duration in seconds
            query: Query text to use
            
        Returns:
            LoadTestMetrics with test results
        """
        print(f"\n⏱️  Testing Sustained Load ({concurrency} concurrent requests for {duration}s)...")
        
        start_time = datetime.utcnow()
        self.memory_monitor.start_monitoring()
        
        # Set up connection pool monitor
        try:
            client = get_client()
            self.pool_monitor.set_client(client)
        except Exception:
            pass  # Will handle error later
        
        all_results = []
        end_time = time.time() + duration
        request_id = 0
        
        # Maintain concurrency level
        async def worker():
            """Worker coroutine that sends requests continuously."""
            nonlocal request_id
            while time.time() < end_time:
                result = await self.send_request(query, request_id)
                all_results.append(result)
                request_id += 1
                await asyncio.sleep(0.1)  # Small delay between requests
        
        # Start worker tasks and pool monitoring concurrently
        workers = [worker() for _ in range(concurrency)]
        
        # Start continuous pool monitoring during load
        pool_monitoring_task = None
        try:
            if self.pool_monitor.client:
                pool_monitoring_task = asyncio.create_task(
                    self.pool_monitor.monitor_during_load(duration=duration, interval=1.0)
                )
        except Exception:
            pass  # Continue without pool monitoring if it fails
        
        # Run workers and monitoring concurrently
        await asyncio.gather(*workers)
        
        # Wait for pool monitoring to complete if it was started
        if pool_monitoring_task:
            try:
                await pool_monitoring_task
            except Exception:
                pass
        
        end_datetime = datetime.utcnow()
        test_duration = (end_datetime - start_time).total_seconds()
        
        # Process results
        response_times = []
        cache_hits = 0
        cache_misses = 0
        rate_limit_hits = 0
        successful = 0
        failed = 0
        
        for result in all_results:
            response_times.append(result["duration"])
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
            
            if result["cache_status"] == "HIT":
                cache_hits += 1
            elif result["cache_status"] == "MISS":
                cache_misses += 1
            
            if result["rate_limited"]:
                rate_limit_hits += 1
        
        # Stop memory monitoring
        memory_stats = self.memory_monitor.stop_monitoring()
        
        # Analyze connection pool behavior from continuous monitoring
        try:
            if self.pool_monitor.client:
                pool_analysis = self.pool_monitor.analyze_pool_behavior()
                # Merge analysis with current snapshot for comprehensive stats
                current_snapshot = self.pool_monitor.get_pool_stats()
                pool_stats = {
                    **current_snapshot,
                    "monitoring_analysis": pool_analysis,
                    "samples_collected": len(self.pool_monitor.pool_samples)
                }
            else:
                pool_stats = {"error": "MongoDB client not available"}
        except Exception as e:
            pool_stats = {"error": f"Could not analyze connection pool stats: {str(e)}"}
        
        return LoadTestMetrics(
            total_requests=len(all_results),
            successful_requests=successful,
            failed_requests=failed,
            response_times=response_times,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            rate_limit_hits=rate_limit_hits,
            memory_stats=memory_stats,
            connection_pool_stats=pool_stats,
            start_time=start_time,
            end_time=end_datetime,
            duration_seconds=test_duration
        )
    
    async def test_cache_behavior(
        self, 
        query: str = "best AI tools for coding",
        num_requests: int = 10
    ) -> Dict[str, Any]:
        """Test cache behavior with identical requests.
        
        Args:
            query: Query text to test
            num_requests: Number of identical requests
            
        Returns:
            Dictionary with cache test results
        """
        print(f"\n💾 Testing Cache Behavior ({num_requests} identical requests)...")
        
        async with CacheValidator(self.base_url, self.api_key) as cache_validator:
            result = await cache_validator.test_cache_warming(query, num_requests)
            return result.model_dump()
    
    async def test_rate_limiting(
        self, 
        rate_limit: int = 60
    ) -> Dict[str, Any]:
        """Test rate limiting enforcement.
        
        Args:
            rate_limit: Expected rate limit (requests per minute)
            
        Returns:
            Dictionary with rate limit test results
        """
        print(f"\n🚦 Testing Rate Limiting (limit: {rate_limit} req/min)...")
        
        async with RateLimitValidator(self.base_url, self.api_key) as rate_validator:
            result = await rate_validator.test_rate_limit_enforcement(rate_limit, duration=60)
            return result.model_dump()
    
    async def run_all_scenarios(
        self, 
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run all load test scenarios.
        
        Args:
            verbose: Whether to show detailed output
            
        Returns:
            Dictionary with all test results
        """
        print("=" * 60)
        print("LOAD TEST SUITE - ALL SCENARIOS")
        print("=" * 60)
        
        all_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url,
            "scenarios": {}
        }
        
        # Scenario 1: Gradual Ramp-Up
        ramp_up_metrics = await self.test_gradual_ramp_up(max_concurrency=50)
        ramp_up_report = generate_load_test_report(ramp_up_metrics)
        all_results["scenarios"]["gradual_ramp_up"] = ramp_up_report
        if verbose:
            self._print_scenario_summary("Gradual Ramp-Up", ramp_up_report)
        
        # Scenario 2: Burst Traffic
        burst_metrics = await self.test_burst_traffic(concurrency=50)
        burst_report = generate_load_test_report(burst_metrics)
        all_results["scenarios"]["burst_traffic"] = burst_report
        if verbose:
            self._print_scenario_summary("Burst Traffic", burst_report)
        
        # Scenario 3: Sustained Load
        sustained_metrics = await self.test_sustained_load(concurrency=20, duration=120)
        sustained_report = generate_load_test_report(sustained_metrics)
        all_results["scenarios"]["sustained_load"] = sustained_report
        if verbose:
            self._print_scenario_summary("Sustained Load", sustained_report)
        
        # Scenario 4: Cache Validation
        cache_results = await self.test_cache_behavior()
        all_results["scenarios"]["cache_validation"] = cache_results
        if verbose:
            self._print_cache_summary("Cache Validation", cache_results)
        
        # Scenario 5: Rate Limit Validation
        rate_limit_results = await self.test_rate_limiting()
        all_results["scenarios"]["rate_limit_validation"] = rate_limit_results
        if verbose:
            self._print_rate_limit_summary("Rate Limit Validation", rate_limit_results)
        
        # Calculate aggregate summary across all scenarios
        total_requests = 0
        total_successful = 0
        total_failed = 0
        
        for scenario_data in all_results["scenarios"].values():
            if "summary" in scenario_data:
                summary = scenario_data["summary"]
                total_requests += summary.get("total_requests", 0)
                total_successful += summary.get("successful_requests", 0)
                total_failed += summary.get("failed_requests", 0)
        
        # Calculate aggregate success rate
        aggregate_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0.0
        
        all_results["summary"] = {
            "total_scenarios": len(all_results["scenarios"]),
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": aggregate_success_rate,
            "timestamp": all_results["timestamp"]
        }
        
        return all_results
    
    def _print_scenario_summary(self, scenario_name: str, report: Dict[str, Any]) -> None:
        """Print detailed summary for a load test scenario.
        
        Args:
            scenario_name: Name of the scenario
            report: Load test report dictionary
        """
        print(f"\n{'=' * 60}")
        print(f"📊 {scenario_name} - Detailed Summary")
        print(f"{'=' * 60}")
        
        summary = report.get("summary", {})
        print(f"\n📈 Request Statistics:")
        print(f"  Total Requests: {summary.get('total_requests', 0)}")
        print(f"  Successful: {summary.get('successful_requests', 0)}")
        print(f"  Failed: {summary.get('failed_requests', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"  Duration: {summary.get('duration_seconds', 0):.2f}s")
        
        response_times = report.get("response_times", {})
        if response_times:
            percentiles = response_times.get("percentiles", {})
            print(f"\n⏱️  Response Time Percentiles:")
            print(f"  p50 (median): {percentiles.get('p50', 0):.3f}s")
            print(f"  p90: {percentiles.get('p90', 0):.3f}s")
            print(f"  p95: {percentiles.get('p95', 0):.3f}s")
            print(f"  p99: {percentiles.get('p99', 0):.3f}s")
            print(f"  Min: {response_times.get('min', 0):.3f}s")
            print(f"  Max: {response_times.get('max', 0):.3f}s")
            print(f"  Avg: {response_times.get('avg', 0):.3f}s")
        
        cache = report.get("cache", {})
        if cache:
            print(f"\n💾 Cache Performance:")
            print(f"  Hits: {cache.get('hits', 0)}")
            print(f"  Misses: {cache.get('misses', 0)}")
            print(f"  Hit Rate: {cache.get('hit_rate', 0):.1f}%")
        
        rate_limiting = report.get("rate_limiting", {})
        if rate_limiting:
            print(f"\n🚦 Rate Limiting:")
            print(f"  Rate Limit Hits: {rate_limiting.get('rate_limit_hits', 0)}")
            print(f"  Rate Limit Percentage: {rate_limiting.get('rate_limit_percentage', 0):.1f}%")
    
    def _print_cache_summary(self, scenario_name: str, results: Dict[str, Any]) -> None:
        """Print detailed summary for cache validation scenario.
        
        Args:
            scenario_name: Name of the scenario
            results: Cache test results dictionary
        """
        print(f"\n{'=' * 60}")
        print(f"💾 {scenario_name} - Detailed Summary")
        print(f"{'=' * 60}")
        
        hits = results.get("cache_hits", results.get("hits", 0))
        misses = results.get("cache_misses", results.get("misses", 0))
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0
        
        print(f"\n📊 Cache Statistics:")
        print(f"  Hits: {hits}")
        print(f"  Misses: {misses}")
        print(f"  Total Requests: {total}")
        print(f"  Hit Rate: {hit_rate:.1f}%")
        
        if "avg_hit_response_time" in results:
            print(f"\n⏱️  Response Times:")
            print(f"  Avg Hit Time: {results.get('avg_hit_response_time', 0):.3f}s")
            print(f"  Avg Miss Time: {results.get('avg_miss_response_time', 0):.3f}s")
            speedup = results.get("speedup", 0)
            if speedup > 0:
                print(f"  Speedup: {speedup:.2f}x faster")
        
        if "time_saved_by_cache" in results:
            print(f"  Time Saved: {results.get('time_saved_by_cache', 0):.2f}s")
    
    def _print_rate_limit_summary(self, scenario_name: str, results: Dict[str, Any]) -> None:
        """Print detailed summary for rate limit validation scenario.
        
        Args:
            scenario_name: Name of the scenario
            results: Rate limit test results dictionary
        """
        print(f"\n{'=' * 60}")
        print(f"🚦 {scenario_name} - Detailed Summary")
        print(f"{'=' * 60}")
        
        print(f"\n📊 Rate Limit Statistics:")
        print(f"  Configured Limit: {results.get('rate_limit', 0)} req/min")
        print(f"  Requests Sent: {results.get('requests_sent', 0)}")
        print(f"  Requests Allowed: {results.get('requests_allowed', 0)}")
        print(f"  Requests Blocked: {results.get('requests_blocked', 0)}")
        
        requests_sent = results.get("requests_sent", 0)
        if requests_sent > 0:
            block_rate = (results.get("requests_blocked", 0) / requests_sent * 100)
            print(f"  Block Rate: {block_rate:.1f}%")
        
        print(f"\n✅ Validation:")
        print(f"  Header Validation: {'PASS' if results.get('header_validation_passed', False) else 'FAIL'}")
        print(f"  False Positives: {results.get('false_positives', 0)}")
        print(f"  False Negatives: {results.get('false_negatives', 0)}")
        print(f"  Status: {results.get('status', 'UNKNOWN')}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load testing and performance validation script")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--concurrency", type=int, default=20, help="Number of concurrent requests (default: 20)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--ramp-up", action="store_true", help="Run gradual ramp-up test")
    parser.add_argument("--burst", action="store_true", help="Run burst traffic test")
    parser.add_argument("--sustained", action="store_true", help="Run sustained load test")
    parser.add_argument("--cache-test", action="store_true", help="Run cache behavior test")
    parser.add_argument("--rate-limit-test", action="store_true", help="Run rate limit validation test")
    parser.add_argument("--all", action="store_true", help="Run all test scenarios")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--save-results", action="store_true", help="Save results to file")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    async with LoadTester(
        base_url=args.url,
        api_key=args.api_key,
        timeout=DEFAULT_TIMEOUT
    ) as tester:
        results = {}
        
        if args.all:
            results = await tester.run_all_scenarios(verbose=args.verbose)
        elif args.ramp_up:
            metrics = await tester.test_gradual_ramp_up(max_concurrency=args.concurrency)
            results = generate_load_test_report(metrics)
        elif args.burst:
            metrics = await tester.test_burst_traffic(concurrency=args.concurrency)
            results = generate_load_test_report(metrics)
        elif args.sustained:
            metrics = await tester.test_sustained_load(concurrency=args.concurrency, duration=args.duration)
            results = generate_load_test_report(metrics)
        elif args.cache_test:
            results = await tester.test_cache_behavior()
        elif args.rate_limit_test:
            settings = get_settings()
            rate_limit = getattr(settings, 'api_rate_limit_requests_per_minute', 60)
            results = await tester.test_rate_limiting(rate_limit=rate_limit)
        else:
            # Default: basic load test
            metrics = await tester.test_burst_traffic(concurrency=args.concurrency)
            results = generate_load_test_report(metrics)
        
        # Output results
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            # Pretty print summary
            if "summary" in results:
                summary = results["summary"]
                print("\n" + "=" * 60)
                print("LOAD TEST SUMMARY")
                print("=" * 60)
                print(f"Total Requests: {summary.get('total_requests', 0)}")
                print(f"Successful: {summary.get('successful_requests', 0)}")
                print(f"Failed: {summary.get('failed_requests', 0)}")
                print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
                print(f"Duration: {summary.get('duration_seconds', 0):.2f}s")
                
                if "response_times" in results:
                    rt = results["response_times"]
                    print(f"\nResponse Times:")
                    print(f"  Min: {rt.get('min', 0):.3f}s")
                    print(f"  Max: {rt.get('max', 0):.3f}s")
                    print(f"  Avg: {rt.get('avg', 0):.3f}s")
                    if "percentiles" in rt:
                        p = rt["percentiles"]
                        print(f"  p50: {p.get('p50', 0):.3f}s")
                        print(f"  p90: {p.get('p90', 0):.3f}s")
                        print(f"  p95: {p.get('p95', 0):.3f}s")
                        print(f"  p99: {p.get('p99', 0):.3f}s")
                
                if "cache" in results:
                    cache = results["cache"]
                    print(f"\nCache:")
                    print(f"  Hits: {cache.get('hits', 0)}")
                    print(f"  Misses: {cache.get('misses', 0)}")
                    print(f"  Hit Rate: {cache.get('hit_rate', 0):.1f}%")
            
            if args.verbose:
                print("\n" + "=" * 60)
                print("DETAILED RESULTS")
                print("=" * 60)
                pprint(results)
        
        # Save results if requested
        if args.save_results:
            test_results_dir = Path("test_results")
            test_results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = test_results_dir / f"load_test_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n✅ Results saved to: {filename}")
        
        # Exit with appropriate code
        if "summary" in results:
            success_rate = results["summary"].get("success_rate", 0)
            if success_rate < 50.0:
                sys.exit(1)
        elif "status" in results:
            if results["status"] == "FAIL":
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

