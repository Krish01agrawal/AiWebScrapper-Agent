#!/usr/bin/env python3
"""
Comprehensive testing script for the /api/v1/scrape endpoint.
Tests sample queries, validates responses, and verifies workflow stages.
"""
import requests
import json
import time
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pprint import pprint


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300  # 5 minutes for scraping operations

# Sample queries by category
SAMPLE_QUERIES = {
    "ai_tools": [
        "Find AI tools for image generation with free tiers",
        "Best AI agents for coding and software development",
        "AI tools for content writing and copywriting",
        "Open source AI models for natural language processing"
    ],
    "mutual_funds": [
        "Best mutual funds for beginners with low risk",
        "Top performing index funds for long-term investment",
        "Mutual funds with high returns in technology sector",
        "Low-cost mutual funds for retirement planning"
    ],
    "general": [
        "Latest trends in artificial intelligence",
        "How to start investing in stock market",
        "Best practices for web scraping",
        "Comparison of cloud computing platforms"
    ]
}


class ScrapeEndpointTester:
    """Scrape endpoint testing class."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.api_key = api_key
        self.results = []
    
    def test_scrape_request(
        self, 
        query: str, 
        config: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        api_key: Optional[str] = None,
        store_results: bool = True
    ) -> Tuple[Dict[str, Any], float, int, bool]:
        """Send POST request to /api/v1/scrape endpoint.
        
        Returns:
            Tuple of (response_data, duration, status_code, store_results)
        """
        url = f"{self.base_url}/api/v1/scrape"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if api_key or self.api_key:
            headers["X-API-Key"] = api_key or self.api_key
        
        payload = {
            "query": query,
            "timeout_seconds": timeout or self.timeout,
            "store_results": store_results
        }
        
        if config:
            payload["processing_config"] = config
        
        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout or self.timeout)
            duration = time.time() - start_time
            
            try:
                response_data = response.json()
            except:
                response_data = {"error": "Invalid JSON response", "raw": response.text[:500]}
            
            return response_data, duration, response.status_code, store_results
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            return {
                "error": "Request timeout",
                "timeout_seconds": timeout or self.timeout
            }, duration, 408, store_results
        except Exception as e:
            duration = time.time() - start_time
            return {
                "error": str(e)
            }, duration, 500, store_results
    
    def validate_scrape_response(self, response_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate response structure matches ScrapeResponse schema."""
        errors = []
        
        # Check required top-level fields
        required_fields = ["status", "timestamp"]
        for field in required_fields:
            if field not in response_data:
                errors.append(f"Missing required field: {field}")
        
        # Check status
        status = response_data.get("status")
        if status not in ["success", "error"]:
            errors.append(f"Invalid status: {status}. Expected 'success' or 'error'")
        
        if status == "success":
            # Validate success response structure
            success_required = ["query", "results", "analytics", "execution_metadata"]
            for field in success_required:
                if field not in response_data:
                    errors.append(f"Missing required field in success response: {field}")
            
            # Validate query structure
            if "query" in response_data:
                query_data = response_data["query"]
                query_required = ["text", "category", "confidence_score"]
                for field in query_required:
                    if field not in query_data:
                        errors.append(f"Missing required field in query: {field}")
                
                # Validate category (check it's a non-empty string, but don't hard-code values)
                if "category" in query_data:
                    category = query_data["category"]
                    if not isinstance(category, str) or not category:
                        errors.append(f"Invalid category: {category}. Category must be a non-empty string")
                
                # Validate confidence_score
                if "confidence_score" in query_data:
                    confidence = query_data["confidence_score"]
                    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                        errors.append(f"Invalid confidence_score: {confidence}. Must be between 0.0 and 1.0")
            
            # Validate results structure
            if "results" in response_data:
                results_data = response_data["results"]
                results_required = ["total_items", "processed_items", "success_rate"]
                for field in results_required:
                    if field not in results_data:
                        errors.append(f"Missing required field in results: {field}")
                
                # Validate numeric fields
                if "total_items" in results_data:
                    if not isinstance(results_data["total_items"], int) or results_data["total_items"] < 0:
                        errors.append("total_items must be a non-negative integer")
                
                if "success_rate" in results_data:
                    success_rate = results_data["success_rate"]
                    if not isinstance(success_rate, (int, float)) or not (0.0 <= success_rate <= 1.0):
                        errors.append("success_rate must be between 0.0 and 1.0")
            
            # Validate analytics structure
            if "analytics" in response_data:
                analytics_data = response_data["analytics"]
                if "pages_scraped" not in analytics_data:
                    errors.append("Missing pages_scraped in analytics")
                if "processing_time_breakdown" not in analytics_data:
                    errors.append("Missing processing_time_breakdown in analytics")
        
        elif status == "error":
            # Validate error response structure
            if "error" not in response_data:
                errors.append("Missing error field in error response")
            else:
                error_data = response_data["error"]
                if "code" not in error_data:
                    errors.append("Missing error code")
                if "message" not in error_data:
                    errors.append("Missing error message")
        
        return len(errors) == 0, errors
    
    def verify_workflow_stages(self, response_data: Dict[str, Any], store_results: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """Verify all expected workflow stages completed.
        
        Args:
            response_data: The response data from the scrape endpoint
            store_results: Whether store_results was set to True in the request (default: True)
        """
        if response_data.get("status") != "success":
            return False, {"error": "Response status is not 'success'"}
        
        execution_metadata = response_data.get("execution_metadata", {})
        stages_timing = execution_metadata.get("stages_timing", {})
        
        expected_stages = ["query_processing", "web_scraping", "ai_processing"]
        
        # Database storage is expected when store_results=True
        if store_results:
            expected_stages.append("database_storage")
        
        missing_stages = [stage for stage in expected_stages if stage not in stages_timing]
        
        if missing_stages:
            return False, {
                "error": f"Missing stages: {missing_stages}",
                "found_stages": list(stages_timing.keys()),
                "expected_stages": expected_stages
            }
        
        # Check stage durations are reasonable
        stage_report = {}
        for stage, duration in stages_timing.items():
            if not isinstance(duration, (int, float)) or duration < 0:
                return False, {
                    "error": f"Invalid duration for stage {stage}: {duration}",
                    "stage_report": stage_report
                }
            stage_report[stage] = {
                "duration": duration,
                "status": "completed"
            }
        
        return True, {
            "stages_valid": True,
            "stage_report": stage_report,
            "total_stages": len(stages_timing),
            "total_duration": execution_metadata.get("execution_time_ms", 0) / 1000
        }
    
    def test_query_category(self, category: str, query: str, store_results: bool = True, json_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Test a specific query from a category."""
        if not json_mode:
            print(f"  Testing query: {query[:60]}...")
        
        response_data, duration, status_code, actual_store_results = self.test_scrape_request(query, store_results=store_results)
        
        if status_code != 200:
            return False, {
                "error": f"Request failed with status {status_code}",
                "response": response_data,
                "duration": duration
            }
        
        # Validate response
        is_valid, validation_errors = self.validate_scrape_response(response_data)
        if not is_valid:
            return False, {
                "error": "Response validation failed",
                "validation_errors": validation_errors,
                "response": response_data
            }
        
        # Check category matches
        response_category = response_data.get("query", {}).get("category", "")
        category_match = response_category == category
        
        # Check confidence score
        confidence_score = response_data.get("query", {}).get("confidence_score", 0.0)
        confidence_ok = confidence_score > 0.5
        
        # Verify workflow stages (use the store_results value from request, not response)
        stages_valid, stage_report = self.verify_workflow_stages(response_data, store_results=actual_store_results)
        
        # Comment 6: Make category and confidence checks affect pass/fail
        success = category_match and confidence_ok and stages_valid
        if not success:
            error_parts = []
            if not category_match:
                error_parts.append(f"category mismatch: expected '{category}', got '{response_category}'")
            if not confidence_ok:
                error_parts.append(f"low confidence: {confidence_score:.2f} (threshold: 0.5)")
            if not stages_valid:
                error_parts.append("workflow stages validation failed")
            error_msg = "; ".join(error_parts)
            return False, {
                "error": error_msg,
                "query": query,
                "category": response_category,
                "category_match": category_match,
                "confidence_score": confidence_score,
                "confidence_ok": confidence_ok,
                "stages_valid": stages_valid,
                "stage_report": stage_report,
                "duration": duration,
                "status_code": status_code,
                "total_items": response_data.get("results", {}).get("total_items", 0)
            }
        
        return True, {
            "query": query,
            "category": response_category,
            "category_match": category_match,
            "confidence_score": confidence_score,
            "confidence_ok": confidence_ok,
            "stages_valid": stages_valid,
            "stage_report": stage_report,
            "duration": duration,
            "status_code": status_code,
            "total_items": response_data.get("results", {}).get("total_items", 0)
        }
    
    def test_all_categories(self, json_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Test one query from each category."""
        if not json_mode:
            print("Testing queries from all categories...\n")
        
        category_results = {}
        overall_success = True
        
        for category, queries in SAMPLE_QUERIES.items():
            if not json_mode:
                print(f"Category: {category}")
            if queries:
                query = queries[0]  # Test first query from each category
                success, test_report = self.test_query_category(category, query, json_mode=json_mode)
                category_results[category] = {
                    "success": success,
                    "report": test_report
                }
                
                if not json_mode:
                    if not success:
                        overall_success = False
                        print(f"  ✗ FAILED: {test_report.get('error', 'Unknown error')}")
                    else:
                        print(f"  ✓ PASSED")
                        print(f"    Category: {test_report.get('category')}")
                        print(f"    Confidence: {test_report.get('confidence_score', 0):.2f}")
                        print(f"    Items: {test_report.get('total_items', 0)}")
                        print(f"    Duration: {test_report.get('duration', 0):.2f}s")
                else:
                    if not success:
                        overall_success = False
            if not json_mode:
                print()
        
        return overall_success, category_results
    
    def test_edge_cases(self, json_mode: bool = False) -> Dict[str, Any]:
        """Test edge cases and error conditions."""
        if not json_mode:
            print("Testing edge cases...\n")
        
        edge_case_results = {}
        
        # Test empty query
        if not json_mode:
            print("  Testing empty query...")
        response_data, duration, status_code, _ = self.test_scrape_request("")
        edge_case_results["empty_query"] = {
            "expected_status": 400,
            "actual_status": status_code,
            "passed": status_code == 400,
            "response": response_data
        }
        
        # Test very long query
        if not json_mode:
            print("  Testing very long query...")
        long_query = "a" * 1001
        response_data, duration, status_code, _ = self.test_scrape_request(long_query)
        edge_case_results["long_query"] = {
            "expected_status": 400,
            "actual_status": status_code,
            "passed": status_code == 400,
            "response": response_data
        }
        
        # Test query with special characters
        if not json_mode:
            print("  Testing query with special characters...")
        special_query = "Test query with @#$%^&*() special chars"
        response_data, duration, status_code, _ = self.test_scrape_request(special_query)
        edge_case_results["special_chars"] = {
            "status_code": status_code,
            "passed": status_code in [200, 400],  # Either works or validation error
            "response": response_data
        }
        
        # Test very short timeout
        if not json_mode:
            print("  Testing very short timeout...")
        response_data, duration, status_code, _ = self.test_scrape_request(
            "Test query", 
            timeout=1  # 1 second timeout
        )
        edge_case_results["short_timeout"] = {
            "timeout": 1,
            "duration": duration,
            "status_code": status_code,
            "passed": status_code in [408, 500],  # Timeout or error
            "response": response_data
        }
        
        return edge_case_results
    
    def test_caching(self, json_mode: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Test caching functionality."""
        if not json_mode:
            print("Testing cache functionality...\n")
        
        query = "Test query for caching"
        
        # Comment 7: Check cache headers instead of just timing
        # Use requests.post directly to capture headers
        url = f"{self.base_url}/api/v1/scrape"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {"query": query, "timeout_seconds": self.timeout, "store_results": True}
        
        # First request (should be cache MISS)
        if not json_mode:
            print("  First request (expected: cache MISS)...")
        start_time = time.time()
        try:
            response1 = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            duration1 = time.time() - start_time
            cache_status1 = response1.headers.get("X-Cache-Status", "").upper()
        except Exception as e:
            return False, {
                "error": f"First request failed: {str(e)}"
            }
        
        if response1.status_code != 200:
            try:
                response1_data = response1.json()
            except:
                response1_data = {"error": "Invalid JSON response", "raw": response1.text[:500]}
            return False, {
                "error": f"First request failed with status {response1.status_code}",
                "response": response1_data
            }
        
        # Wait a bit
        time.sleep(2)
        
        # Second request (should be cache HIT)
        if not json_mode:
            print("  Second request (expected: cache HIT)...")
        start_time = time.time()
        try:
            response2 = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            duration2 = time.time() - start_time
            cache_status2 = response2.headers.get("X-Cache-Status", "").upper()
        except Exception as e:
            return False, {
                "error": f"Second request failed: {str(e)}"
            }
        
        if response2.status_code != 200:
            return False, {
                "error": f"Second request failed with status {response2.status_code}"
            }
        
        # Check cache headers - first should be MISS, second should be HIT
        cache_header_valid = cache_status1 == "MISS" and cache_status2 == "HIT"
        
        # Also check timing as additional metric
        timing_improvement = duration2 < duration1 * 0.5
        
        caching_works = cache_header_valid
        
        return caching_works, {
            "first_request": {
                "duration": duration1,
                "cache_status": cache_status1,
                "status": "MISS" if cache_status1 == "MISS" else "UNKNOWN"
            },
            "second_request": {
                "duration": duration2,
                "cache_status": cache_status2,
                "status": "HIT" if cache_status2 == "HIT" else "UNKNOWN",
                "speedup": f"{(duration1 / duration2):.2f}x faster" if duration2 > 0 else "N/A"
            },
            "caching_works": caching_works,
            "cache_header_valid": cache_header_valid,
            "timing_improvement": timing_improvement
        }
    
    def analyze_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from response."""
        if response_data.get("status") != "success":
            return {"error": "Response is not successful"}
        
        execution_metadata = response_data.get("execution_metadata", {})
        results = response_data.get("results", {})
        analytics = response_data.get("analytics", {})
        
        return {
            "execution_time_ms": execution_metadata.get("execution_time_ms", 0),
            "execution_time_s": execution_metadata.get("execution_time_ms", 0) / 1000,
            "pages_scraped": analytics.get("pages_scraped", 0),
            "total_items": results.get("total_items", 0),
            "processed_items": results.get("processed_items", 0),
            "success_rate": results.get("success_rate", 0.0),
            "stages_timing": execution_metadata.get("stages_timing", {})
        }
    
    def run_comprehensive_tests(self, json_mode: bool = False) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        if not json_mode:
            print("="*60)
            print("COMPREHENSIVE SCRAPE ENDPOINT TEST SUITE")
            print("="*60)
            print()
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url
        }
        
        # Test all categories
        if not json_mode:
            print("1. Testing All Categories")
            print("-" * 60)
        success, category_results = self.test_all_categories(json_mode=json_mode)
        results["category_tests"] = {
            "success": success,
            "results": category_results
        }
        if not json_mode:
            print()
        
        # Test edge cases
        if not json_mode:
            print("2. Testing Edge Cases")
            print("-" * 60)
        edge_case_results = self.test_edge_cases(json_mode=json_mode)
        results["edge_cases"] = edge_case_results
        if not json_mode:
            print()
        
        # Test caching
        if not json_mode:
            print("3. Testing Caching")
            print("-" * 60)
        cache_success, cache_report = self.test_caching(json_mode=json_mode)
        results["caching"] = {
            "success": cache_success,
            "report": cache_report
        }
        if not json_mode:
            print()
        
        # Calculate summary
        total_tests = 1 + len(edge_case_results) + 1
        passed_tests = (1 if success else 0) + sum(1 for r in edge_case_results.values() if r.get("passed", False)) + (1 if cache_success else 0)
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scrape endpoint testing script")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--query", help="Test specific query")
    parser.add_argument("--category", choices=list(SAMPLE_QUERIES.keys()), help="Test all queries in category")
    parser.add_argument("--all", action="store_true", help="Run comprehensive test suite")
    parser.add_argument("--edge-cases", action="store_true", help="Test edge cases only")
    parser.add_argument("--cache", action="store_true", help="Test caching functionality")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--save-responses", action="store_true", help="Save full responses to files")
    
    args = parser.parse_args()
    
    tester = ScrapeEndpointTester(
        base_url=args.url,
        timeout=args.timeout,
        api_key=args.api_key
    )
    
    if args.query:
        # Test specific query
        print(f"Testing query: {args.query}\n")
        response_data, duration, status_code, _ = tester.test_scrape_request(args.query)
        
        if args.json:
            print(json.dumps({
                "query": args.query,
                "status_code": status_code,
                "duration": duration,
                "response": response_data
            }, indent=2))
        else:
            print(f"Status Code: {status_code}")
            print(f"Duration: {duration:.2f}s")
            if args.verbose:
                pprint(response_data)
            
            # Validate response
            is_valid, errors = tester.validate_scrape_response(response_data)
            if is_valid:
                print("\n✓ Response validation passed")
            else:
                print(f"\n✗ Response validation failed:")
                for error in errors:
                    print(f"  - {error}")
            
            # Analyze response
            if response_data.get("status") == "success":
                metrics = tester.analyze_response(response_data)
                print("\nMetrics:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
        
        if args.save_responses:
            filename = f"response_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(response_data, f, indent=2)
            print(f"\nResponse saved to: {filename}")
    
    elif args.category:
        # Test all queries in category
        queries = SAMPLE_QUERIES.get(args.category, [])
        print(f"Testing {len(queries)} queries in category: {args.category}\n")
        
        category_results = []
        for query in queries:
            success, report = tester.test_query_category(args.category, query)
            category_results.append({
                "query": query,
                "success": success,
                "report": report
            })
        
        if args.json:
            print(json.dumps(category_results, indent=2))
        else:
            passed = sum(1 for r in category_results if r["success"])
            print(f"\nResults: {passed}/{len(category_results)} passed")
    
    elif args.edge_cases:
        # Test edge cases only
        edge_case_results = tester.test_edge_cases()
        if args.json:
            print(json.dumps(edge_case_results, indent=2))
        else:
            passed = sum(1 for r in edge_case_results.values() if r.get("passed", False))
            print(f"\nEdge Cases: {passed}/{len(edge_case_results)} passed")
    
    elif args.cache:
        # Test caching only
        cache_success, cache_report = tester.test_caching()
        if args.json:
            print(json.dumps({
                "success": cache_success,
                "report": cache_report
            }, indent=2))
        else:
            if cache_success:
                print("\n✓ Caching test passed")
            else:
                print("\n✗ Caching test failed")
            if args.verbose:
                pprint(cache_report)
    
    elif args.all:
        # Run comprehensive test suite
        results = tester.run_comprehensive_tests(json_mode=args.json)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            summary = results["summary"]
            print(f"Total Tests: {summary['total_tests']}")
            print(f"Passed: {summary['passed']}")
            print(f"Failed: {summary['failed']}")
            print(f"Success Rate: {summary['success_rate']:.1f}%")
            print(f"Timestamp: {results['timestamp']}")
        
        if args.save_responses:
            filename = f"test_results_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {filename}")
        
        # Exit with appropriate code
        if summary["success_rate"] == 100:
            sys.exit(0)
        else:
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

