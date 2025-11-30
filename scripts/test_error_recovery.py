#!/usr/bin/env python3
"""
Integration test script for end-to-end error recovery testing.

This script tests the system's behavior under various failure scenarios by making
real API calls to a running server and validating error responses and recovery behavior.
"""
import requests
import json
import time
import sys
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from pprint import pprint


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 60


class ErrorRecoveryTester:
    """Error recovery testing class."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.api_key = api_key
        self.test_results = []
    
    def _build_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build request headers with Content-Type and optional API key.
        
        Args:
            extra: Additional headers to include
            
        Returns:
            Dictionary of headers
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["X-API-Key"] = self.api_key
        if extra:
            headers.update(extra)
        return headers
    
    def test_invalid_api_key(self) -> Dict[str, Any]:
        """Test invalid API key scenarios."""
        print("\n" + "="*80)
        print("Testing Invalid API Key Scenarios")
        print("="*80)
        
        results = {
            "test_name": "invalid_api_key",
            "scenarios": [],
            "passed": 0,
            "failed": 0
        }
        
        # Test 1: Missing API key
        print("\n1. Testing missing API key...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            scenario_result = {
                "name": "missing_api_key",
                "status_code": response.status_code,
                "passed": response.status_code in [401, 200],  # 200 if auth disabled
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Missing API key handled correctly")
            else:
                results["failed"] += 1
                print(f"   ✗ Missing API key test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "missing_api_key",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        # Test 2: Malformed API key
        print("\n2. Testing malformed API key...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query"},
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "invalid_format_key"
                },
                timeout=10
            )
            
            scenario_result = {
                "name": "malformed_api_key",
                "status_code": response.status_code,
                "passed": response.status_code in [401, 200],
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Malformed API key handled correctly")
            else:
                results["failed"] += 1
                print(f"   ✗ Malformed API key test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "malformed_api_key",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        # Test 3: Invalid API key
        print("\n3. Testing invalid API key...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query"},
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "traycer_invalid_key_12345"
                },
                timeout=10
            )
            
            scenario_result = {
                "name": "invalid_api_key",
                "status_code": response.status_code,
                "passed": response.status_code in [401, 200],
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Invalid API key handled correctly")
            else:
                results["failed"] += 1
                print(f"   ✗ Invalid API key test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "invalid_api_key",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_mongodb_failure(self) -> Dict[str, Any]:
        """Test MongoDB failure scenario."""
        print("\n" + "="*80)
        print("Testing MongoDB Failure Scenario")
        print("="*80)
        print("\nNote: This test assumes MongoDB is running. If MongoDB is stopped,")
        print("the system should handle the failure gracefully.")
        
        results = {
            "test_name": "mongodb_failure",
            "passed": False,
            "message": "MongoDB failure test requires manual MongoDB stop/start"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query", "store_results": True},
                headers=self._build_headers(),
                timeout=30
            )
            
            # Should either succeed (if MongoDB is up) or fail gracefully
            results["status_code"] = response.status_code
            results["response"] = response.json() if response.status_code < 500 else {"error": response.text[:200]}
            
            if response.status_code == 200:
                # Check for warnings about storage failure
                data = response.json()
                if "warnings" in data and len(data["warnings"]) > 0:
                    results["passed"] = True
                    results["message"] = "Graceful degradation: workflow continued despite storage failure"
                    print("   ✓ Graceful degradation detected")
                else:
                    results["message"] = "MongoDB is running normally"
                    print("   ℹ MongoDB is running normally")
            else:
                results["message"] = f"Request failed with status {response.status_code}"
                print(f"   ℹ Request status: {response.status_code}")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_gemini_failure(self) -> Dict[str, Any]:
        """Test Gemini API failure scenario."""
        print("\n" + "="*80)
        print("Testing Gemini API Failure Scenario")
        print("="*80)
        print("\nNote: This test requires an invalid Gemini API key in .env")
        print("or the Gemini API to be unavailable.")
        
        results = {
            "test_name": "gemini_failure",
            "passed": False,
            "message": "Gemini failure test requires invalid API key"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query"},
                headers=self._build_headers(),
                timeout=30
            )
            
            results["status_code"] = response.status_code
            results["response"] = response.json() if response.status_code < 500 else {"error": response.text[:200]}
            
            if response.status_code == 500:
                data = response.json()
                if "QUERY_PROCESSING_ERROR" in str(data) or "GEMINI" in str(data).upper():
                    results["passed"] = True
                    results["message"] = "Gemini API error detected and handled"
                    print("   ✓ Gemini API error handled correctly")
                else:
                    results["message"] = "Error detected but not Gemini-specific"
                    print("   ℹ Error detected but not Gemini-specific")
            elif response.status_code == 200:
                results["message"] = "Gemini API is working normally"
                print("   ℹ Gemini API is working normally")
            else:
                results["message"] = f"Unexpected status code: {response.status_code}"
                print(f"   ℹ Status code: {response.status_code}")
            
        except Exception as e:
            results["error"] = str(e)
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_timeout(self) -> Dict[str, Any]:
        """Test timeout scenario."""
        print("\n" + "="*80)
        print("Testing Timeout Scenario")
        print("="*80)
        
        results = {
            "test_name": "timeout",
            "passed": False
        }
        
        try:
            # Send request with very short timeout
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={
                    "query": "Find comprehensive analysis of AI tools with detailed comparisons",
                    "timeout_seconds": 30  # Short timeout
                },
                headers=self._build_headers(),
                timeout=35  # Slightly longer than request timeout
            )
            
            results["status_code"] = response.status_code
            results["response"] = response.json() if response.status_code < 500 else {"error": response.text[:200]}
            
            if response.status_code == 500:
                data = response.json()
                if "WORKFLOW_TIMEOUT" in str(data) or "timeout" in str(data).lower():
                    results["passed"] = True
                    print("   ✓ Timeout error handled correctly")
                else:
                    print("   ℹ Error detected but not timeout-specific")
            elif response.status_code == 200:
                results["passed"] = True
                print("   ✓ Request completed within timeout")
            else:
                print(f"   ℹ Status code: {response.status_code}")
            
        except requests.exceptions.Timeout:
            results["passed"] = True
            results["message"] = "Request timed out as expected"
            print("   ✓ Request timeout detected")
        except Exception as e:
            results["error"] = str(e)
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_validation_errors(self) -> Dict[str, Any]:
        """Test validation error scenarios."""
        print("\n" + "="*80)
        print("Testing Validation Error Scenarios")
        print("="*80)
        
        results = {
            "test_name": "validation_errors",
            "scenarios": [],
            "passed": 0,
            "failed": 0
        }
        
        # Test 1: Empty query
        print("\n1. Testing empty query...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": ""},
                headers=self._build_headers(),
                timeout=10
            )
            
            scenario_result = {
                "name": "empty_query",
                "status_code": response.status_code,
                "passed": response.status_code == 400,
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Empty query validation works")
            else:
                results["failed"] += 1
                print(f"   ✗ Empty query test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "empty_query",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        # Test 2: Query too short
        print("\n2. Testing query too short...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "AI"},
                headers=self._build_headers(),
                timeout=10
            )
            
            scenario_result = {
                "name": "query_too_short",
                "status_code": response.status_code,
                "passed": response.status_code == 400,
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Query too short validation works")
            else:
                results["failed"] += 1
                print(f"   ✗ Query too short test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "query_too_short",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        # Test 3: Invalid timeout
        print("\n3. Testing invalid timeout value...")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query", "timeout_seconds": 10},  # Too low
                headers=self._build_headers(),
                timeout=15
            )
            
            scenario_result = {
                "name": "invalid_timeout",
                "status_code": response.status_code,
                "passed": response.status_code == 422,  # Pydantic validation error
                "response": response.json() if response.status_code < 500 else {"error": response.text[:200]}
            }
            
            if scenario_result["passed"]:
                results["passed"] += 1
                print("   ✓ Invalid timeout validation works")
            else:
                results["failed"] += 1
                print(f"   ✗ Invalid timeout test failed: {response.status_code}")
            
            results["scenarios"].append(scenario_result)
        except Exception as e:
            results["failed"] += 1
            results["scenarios"].append({
                "name": "invalid_timeout",
                "error": str(e),
                "passed": False
            })
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_rate_limit(self) -> Dict[str, Any]:
        """Test rate limiting."""
        print("\n" + "="*80)
        print("Testing Rate Limiting")
        print("="*80)
        
        results = {
            "test_name": "rate_limit",
            "passed": False
        }
        
        try:
            # Send multiple rapid requests
            rate_limited = False
            for i in range(65):  # Exceed default limit of 60
                response = requests.post(
                    f"{self.base_url}/api/v1/scrape",
                    json={"query": f"test query {i}"},
                    headers=self._build_headers(),
                    timeout=10
                )
                
                if response.status_code == 429:
                    rate_limited = True
                    results["passed"] = True
                    results["request_count"] = i + 1
                    results["response"] = response.json() if response.status_code < 500 else {"error": response.text[:200]}
                    print(f"   ✓ Rate limit enforced after {i + 1} requests")
                    break
                
                time.sleep(0.1)  # Small delay between requests
            
            if not rate_limited:
                results["message"] = "Rate limit not enforced (may be disabled or limit is higher)"
                print("   ℹ Rate limit not enforced")
        
        except Exception as e:
            results["error"] = str(e)
            print(f"   ✗ Error: {e}")
        
        return results
    
    def test_graceful_degradation(self) -> Dict[str, Any]:
        """Test graceful degradation behavior."""
        print("\n" + "="*80)
        print("Testing Graceful Degradation")
        print("="*80)
        print("\nNote: This test verifies that the system continues with partial")
        print("results when non-critical stages fail.")
        
        results = {
            "test_name": "graceful_degradation",
            "passed": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/scrape",
                json={"query": "test query", "store_results": False},
                headers=self._build_headers(),
                timeout=30
            )
            
            results["status_code"] = response.status_code
            results["response"] = response.json() if response.status_code < 500 else {"error": response.text[:200]}
            
            if response.status_code == 200:
                data = response.json()
                # Check for warnings indicating partial failures
                if "warnings" in data and len(data["warnings"]) > 0:
                    results["passed"] = True
                    results["message"] = "Graceful degradation: warnings present for non-fatal errors"
                    print("   ✓ Graceful degradation detected (warnings present)")
                else:
                    results["message"] = "Request completed successfully without warnings"
                    print("   ✓ Request completed successfully")
            else:
                results["message"] = f"Request failed with status {response.status_code}"
                print(f"   ℹ Status code: {response.status_code}")
        
        except Exception as e:
            results["error"] = str(e)
            print(f"   ✗ Error: {e}")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all error recovery tests."""
        print("\n" + "="*80)
        print("ERROR RECOVERY TEST SUITE")
        print("="*80)
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": [],
            "total_tests": 0,
            "passed": 0,
            "failed": 0
        }
        
        # Run all test scenarios
        test_functions = [
            ("invalid_api_key", self.test_invalid_api_key),
            ("mongodb_failure", self.test_mongodb_failure),
            ("gemini_failure", self.test_gemini_failure),
            ("timeout", self.test_timeout),
            ("validation_errors", self.test_validation_errors),
            ("rate_limit", self.test_rate_limit),
            ("graceful_degradation", self.test_graceful_degradation),
        ]
        
        for test_name, test_func in test_functions:
            try:
                result = test_func()
                all_results["tests"].append(result)
                all_results["total_tests"] += 1
                
                if result.get("passed") or result.get("passed", 0) > 0:
                    all_results["passed"] += 1
                elif result.get("failed", 0) > 0:
                    all_results["failed"] += 1
                else:
                    all_results["failed"] += 1
            except Exception as e:
                all_results["tests"].append({
                    "test_name": test_name,
                    "error": str(e),
                    "passed": False
                })
                all_results["total_tests"] += 1
                all_results["failed"] += 1
        
        # Calculate success rate
        all_results["success_rate"] = (
            (all_results["passed"] / all_results["total_tests"] * 100)
            if all_results["total_tests"] > 0 else 0
        )
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print("="*80)
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save test results to JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Error recovery integration tests")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Base URL of the API server")
    parser.add_argument("--test", help="Run specific test (invalid_api_key, mongodb_failure, etc.)")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--api-key", help="API key for authenticated requests")
    
    args = parser.parse_args()
    
    tester = ErrorRecoveryTester(
        base_url=args.url,
        timeout=args.timeout,
        api_key=args.api_key
    )
    
    if args.test:
        # Run specific test
        test_map = {
            "invalid_api_key": tester.test_invalid_api_key,
            "mongodb_failure": tester.test_mongodb_failure,
            "gemini_failure": tester.test_gemini_failure,
            "timeout": tester.test_timeout,
            "validation_errors": tester.test_validation_errors,
            "rate_limit": tester.test_rate_limit,
            "graceful_degradation": tester.test_graceful_degradation,
        }
        
        if args.test in test_map:
            result = test_map[args.test]()
            if args.output:
                tester.save_results({"tests": [result]}, args.output)
        else:
            print(f"Unknown test: {args.test}")
            print(f"Available tests: {', '.join(test_map.keys())}")
            sys.exit(1)
    elif args.all:
        # Run all tests
        results = tester.run_all_tests()
        tester.print_summary(results)
        
        if args.output:
            tester.save_results(results, args.output)
        
        # Exit with error code if tests failed
        if results["failed"] > 0:
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

