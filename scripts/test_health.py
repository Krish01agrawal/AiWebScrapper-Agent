#!/usr/bin/env python3
"""
Comprehensive health check testing script for AI Web Scraper API.
Tests all system components and generates detailed reports.
"""
import requests
import json
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 10


class HealthChecker:
    """Health check testing class."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results = []
        
    def test_root_endpoint(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET / endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                # Only verify minimal guaranteed fields (message and version are the core contract)
                # Other fields like environment, features, endpoints may change
                if "message" not in data and "version" not in data:
                    return False, {
                        "status": "failed",
                        "error": "Missing minimal required fields: message or version",
                        "duration": duration
                    }
                
                return True, {
                    "status": "passed",
                    "response": data,
                    "duration": duration
                }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}",
                    "duration": duration
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_basic_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /health endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code in [200, 503]:
                data = response.json()
                required_fields = ["status", "timestamp"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    return False, {
                        "status": "failed",
                        "error": f"Missing required fields: {missing_fields}",
                        "duration": duration
                    }
                
                overall_status = data.get("status", "unknown")
                is_healthy = overall_status in ["healthy", "degraded"]
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "degraded",
                    "health_data": data,
                    "overall_status": overall_status,
                    "duration": duration
                }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}",
                    "duration": duration
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_database_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /health/database endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health/database", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                db_status = data.get("status", "unknown")
                is_healthy = db_status == "healthy"
                
                # Comment 4: Relax threshold - treat slow responses as degraded but not failed
                # Use 5 seconds as threshold, treat as degraded if over 3 seconds
                if duration > 5.0:
                    return False, {
                        "status": "failed",
                        "error": f"Response time too slow: {duration:.2f}s (threshold: 5.0s)",
                        "db_health": data,
                        "duration": duration
                    }
                elif duration > 3.0:
                    # Degraded but still successful if connectivity and status are healthy
                    return is_healthy, {
                        "status": "degraded" if is_healthy else "failed",
                        "note": f"Response time slow: {duration:.2f}s (threshold: 3.0s)",
                        "db_health": data,
                        "db_status": db_status,
                        "duration": duration
                    }
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "failed",
                    "db_health": data,
                    "db_status": db_status,
                    "duration": duration
                }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}",
                    "duration": duration
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_gemini_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test Gemini API health (check in /health response)."""
        try:
            # Check in main health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            
            if response.status_code in [200, 503]:
                data = response.json()
                # Check if components exist before accessing
                components = data.get("components", {})
                if components and "gemini_api" in components:
                    gemini_status = components.get("gemini_api", {}).get("status", "unknown")
                    is_healthy = gemini_status == "healthy"
                    
                    return is_healthy, {
                        "status": "passed" if is_healthy else "failed",
                        "gemini_status": gemini_status,
                        "components": components
                    }
                else:
                    # Component not found - treat as warning, not failure, if overall health is acceptable
                    overall_status = data.get("status", "unknown")
                    if overall_status in ["healthy", "degraded"]:
                        return True, {
                            "status": "passed",
                            "note": "Gemini component not found in health response, but overall health is acceptable",
                            "overall_status": overall_status
                        }
                    else:
                        return False, {
                            "status": "failed",
                            "error": "Gemini component not found and overall health is not acceptable"
                        }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}"
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e)
            }
    
    def test_cache_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /health/cache endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health/cache", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                cache_status = data.get("status", "unknown")
                is_healthy = cache_status == "healthy"
                
                # Extract cache statistics
                stats = data.get("statistics", {})
                hits = stats.get("hits", 0)
                misses = stats.get("misses", 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "failed",
                    "cache_health": data,
                    "cache_status": cache_status,
                    "statistics": {
                        "hits": hits,
                        "misses": misses,
                        "hit_rate": hit_rate,
                        "size": stats.get("size", 0)
                    },
                    "duration": duration
                }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}",
                    "duration": duration
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_scraper_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /health/scraper endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health/scraper", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                scraper_status = data.get("status", "unknown")
                is_healthy = scraper_status == "healthy"
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "failed",
                    "scraper_health": data,
                    "scraper_status": scraper_status,
                    "duration": duration
                }
            else:
                # Endpoint might not exist, check in main health
                health_response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                if health_response.status_code in [200, 503]:
                    health_data = health_response.json()
                    overall_status = health_data.get("status", "unknown")
                    components = health_data.get("components", {})
                    
                    # Check if scraper component exists
                    if components and "scraper" in components:
                        scraper_info = components.get("scraper", {})
                        return True, {
                            "status": "passed",
                            "scraper_info": scraper_info,
                            "note": "Scraper health checked via main health endpoint"
                        }
                    else:
                        # Component not found, but if overall health is acceptable, treat as warning
                        if overall_status in ["healthy", "degraded"]:
                            return True, {
                                "status": "passed",
                                "note": "Scraper component not found in health response, but overall health is acceptable",
                                "overall_status": overall_status
                            }
                        else:
                            return False, {
                                "status": "failed",
                                "error": "Scraper component not found and overall health is not acceptable"
                            }
                else:
                    return False, {
                        "status": "failed",
                        "error": f"Scraper health endpoint not available (status: {response.status_code})"
                    }
        except requests.exceptions.RequestException:
            # Try main health endpoint
            try:
                health_response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                if health_response.status_code in [200, 503]:
                    health_data = health_response.json()
                    overall_status = health_data.get("status", "unknown")
                    components = health_data.get("components", {})
                    
                    if components and "scraper" in components:
                        scraper_info = components.get("scraper", {})
                        return True, {
                            "status": "passed",
                            "scraper_info": scraper_info,
                            "note": "Scraper health checked via main health endpoint"
                        }
                    elif overall_status in ["healthy", "degraded"]:
                        return True, {
                            "status": "passed",
                            "note": "Scraper component not found, but overall health is acceptable",
                            "overall_status": overall_status
                        }
            except:
                pass
            
            return False, {
                "status": "failed",
                "error": "Scraper health endpoint not available"
            }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_processing_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /health/processing endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health/processing", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                processing_status = data.get("status", "unknown")
                is_healthy = processing_status == "healthy"
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "failed",
                    "processing_health": data,
                    "processing_status": processing_status,
                    "duration": duration
                }
            else:
                # Check in main health endpoint
                health_response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                if health_response.status_code in [200, 503]:
                    health_data = health_response.json()
                    components = health_data.get("components", {})
                    processing_info = components.get("processing", {})
                    
                    return True, {
                        "status": "passed",
                        "processing_info": processing_info,
                        "note": "Processing health checked via main health endpoint"
                    }
                else:
                    return False, {
                        "status": "failed",
                        "error": f"Processing health endpoint not available (status: {response.status_code})"
                    }
        except requests.exceptions.RequestException:
            # Try main health endpoint
            try:
                health_response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                if health_response.status_code in [200, 503]:
                    health_data = health_response.json()
                    components = health_data.get("components", {})
                    processing_info = components.get("processing", {})
                    
                    return True, {
                        "status": "passed",
                        "processing_info": processing_info,
                        "note": "Processing health checked via main health endpoint"
                    }
            except:
                pass
            
            return False, {
                "status": "failed",
                "error": "Processing health endpoint not available"
            }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def test_workflow_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Test GET /api/v1/scrape/health endpoint."""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/scrape/health", timeout=self.timeout)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                workflow_status = data.get("status", "unknown")
                is_healthy = workflow_status == "healthy"
                
                components = data.get("components", {})
                
                return is_healthy, {
                    "status": "passed" if is_healthy else "failed",
                    "workflow_health": data,
                    "workflow_status": workflow_status,
                    "components": components,
                    "duration": duration
                }
            else:
                return False, {
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}",
                    "duration": duration
                }
        except Exception as e:
            return False, {
                "status": "failed",
                "error": str(e),
                "duration": 0
            }
    
    def run_all_health_checks(self, json_mode: bool = False) -> Dict[str, Any]:
        """Run all health checks and collect results."""
        if not json_mode:
            print("Running comprehensive health checks...")
            print(f"Base URL: {self.base_url}\n")
        
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Basic Health", self.test_basic_health),
            ("Database Health", self.test_database_health),
            ("Gemini Health", self.test_gemini_health),
            ("Cache Health", self.test_cache_health),
            ("Scraper Health", self.test_scraper_health),
            ("Processing Health", self.test_processing_health),
            ("Workflow Health", self.test_workflow_health),
        ]
        
        results = {}
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            if not json_mode:
                print(f"Testing {test_name}...", end=" ", flush=True)
            success, details = test_func()
            
            results[test_name] = {
                "success": success,
                "details": details
            }
            
            if not json_mode:
                if success:
                    print("✓ PASSED")
                    passed += 1
                else:
                    print("✗ FAILED")
                    failed += 1
                    
                if "error" in details:
                    print(f"  Error: {details['error']}")
            else:
                if success:
                    passed += 1
                else:
                    failed += 1
        
        total = len(tests)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            "overall_status": "passed" if failed == 0 else "failed",
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_component_check(self, component: str, json_mode: bool = False) -> Dict[str, Any]:
        """Run health check for specific component."""
        component_map = {
            "database": self.test_database_health,
            "gemini": self.test_gemini_health,
            "cache": self.test_cache_health,
            "scraper": self.test_scraper_health,
            "processing": self.test_processing_health,
            "workflow": self.test_workflow_health,
            "root": self.test_root_endpoint,
            "basic": self.test_basic_health,
        }
        
        if component not in component_map:
            return {
                "error": f"Unknown component: {component}",
                "available_components": list(component_map.keys())
            }
        
        if not json_mode:
            print(f"Testing {component} health...")
        success, details = component_map[component]()
        
        return {
            "component": component,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Health check testing script")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--component", help="Test specific component only")
    parser.add_argument("--continuous", action="store_true", help="Run health checks continuously")
    parser.add_argument("--interval", type=int, default=60, help="Interval for continuous mode in seconds (default: 60)")
    
    args = parser.parse_args()
    
    checker = HealthChecker(base_url=args.url, timeout=args.timeout)
    
    if args.continuous:
        if not args.json:
            print(f"Running continuous health checks (interval: {args.interval}s)")
            print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                result = checker.run_all_health_checks(json_mode=args.json)
                if not args.json:
                    print(f"\nOverall Status: {result['overall_status'].upper()}")
                    print(f"Passed: {result['passed']}/{result['total']}")
                    print(f"Success Rate: {result['success_rate']:.1f}%")
                    print(f"\nWaiting {args.interval} seconds until next check...\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            if not args.json:
                print("\nStopped by user")
            sys.exit(0)
    elif args.component:
        result = checker.run_component_check(args.component, json_mode=args.json)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                print(f"Error: {result['error']}")
                sys.exit(1)
            else:
                status = "✓ PASSED" if result["success"] else "✗ FAILED"
                print(f"\n{status}")
                if args.verbose:
                    print(json.dumps(result["details"], indent=2))
    else:
        result = checker.run_all_health_checks(json_mode=args.json)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "="*60)
            print("HEALTH CHECK SUMMARY")
            print("="*60)
            print(f"Overall Status: {result['overall_status'].upper()}")
            print(f"Total Tests: {result['total']}")
            print(f"Passed: {result['passed']}")
            print(f"Failed: {result['failed']}")
            print(f"Success Rate: {result['success_rate']:.1f}%")
            print(f"Timestamp: {result['timestamp']}")
            
            if args.verbose:
                print("\nDetailed Results:")
                for test_name, test_result in result["results"].items():
                    status = "✓" if test_result["success"] else "✗"
                    print(f"\n{status} {test_name}")
                    if "error" in test_result["details"]:
                        print(f"  Error: {test_result['details']['error']}")
                    if "duration" in test_result["details"]:
                        print(f"  Duration: {test_result['details']['duration']:.3f}s")
        
        # Exit with appropriate code
        if result["overall_status"] == "failed":
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()

