#!/usr/bin/env python3
"""
Interactive demo script for the AI Web Scraper API.
Showcases the API with colored output, example queries, and live progress tracking.
"""
import requests
import json
import time
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Global flag for no-color mode
NO_COLOR = False

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
    _Fore = Fore
    _Style = Style
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback colors for terminals that support ANSI
    class _Fore:
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        CYAN = '\033[96m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        RESET = '\033[0m'
    
    class _Style:
        BRIGHT = '\033[1m'
        RESET_ALL = '\033[0m'

# Create Fore and Style that respect NO_COLOR flag
class Fore:
    GREEN = ''
    RED = ''
    YELLOW = ''
    CYAN = ''
    BLUE = ''
    MAGENTA = ''
    RESET = ''

class Style:
    BRIGHT = ''
    RESET_ALL = ''

def _update_color_classes():
    """Update Fore and Style classes based on NO_COLOR flag."""
    global Fore, Style
    if NO_COLOR:
        # No-color mode: all attributes are empty strings
        Fore = type('Fore', (), {
            'GREEN': '',
            'RED': '',
            'YELLOW': '',
            'CYAN': '',
            'BLUE': '',
            'MAGENTA': '',
            'RESET': ''
        })
        Style = type('Style', (), {
            'BRIGHT': '',
            'RESET_ALL': ''
        })
    else:
        # Use colorama or fallback
        Fore = _Fore
        Style = _Style

# Initialize color classes
_update_color_classes()

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300

# Sample queries by category
SAMPLE_QUERIES = {
    "ai_tools": [
        "Best AI agents for coding and software development",
        "Find AI tools for image generation with free tiers",
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

# Quick demo query
QUICK_DEMO_QUERY = "Best AI agents for coding and software development"

# Expected characteristics for demo scenarios
DEMO_EXPECTATIONS = {
    "ai_tools": {
        "expected_category": ["ai_tools"],
        "expected_response_time_min": 20.0,
        "expected_response_time_max": 120.0,
        "expected_cache_hit_second_call": True
    },
    "mutual_funds": {
        "expected_category": ["mutual_funds", "investment"],
        "expected_response_time_min": 20.0,
        "expected_response_time_max": 120.0,
        "expected_cache_hit_second_call": True
    },
    "general": {
        "expected_category": ["general"],
        "expected_response_time_min": 20.0,
        "expected_response_time_max": 120.0,
        "expected_cache_hit_second_call": True
    },
    "quick_demo": {
        "expected_category": ["ai_tools"],
        "expected_response_time_min": 20.0,
        "expected_response_time_max": 120.0,
        "expected_cache_hit_second_call": True
    }
}


def print_header(text: str):
    """Print a formatted header."""
    if NO_COLOR:
        print(f"\n{'='*70}")
        print(f"{text.center(70)}")
        print(f"{'='*70}\n")
    elif COLORAMA_AVAILABLE:
        print(f"\n{Style.BRIGHT}{Fore.CYAN}{'='*70}")
        print(f"{text.center(70)}")
        print(f"{'='*70}{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{text.center(70)}")
        print(f"{'='*70}{Fore.RESET}\n")


def print_success(text: str):
    """Print success message."""
    if NO_COLOR:
        print(f"✓ {text}")
    elif COLORAMA_AVAILABLE:
        print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}✓ {text}{Fore.RESET}")


def print_error(text: str):
    """Print error message."""
    if NO_COLOR:
        print(f"✗ {text}")
    elif COLORAMA_AVAILABLE:
        print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ {text}{Fore.RESET}")


def print_warning(text: str):
    """Print warning message."""
    if NO_COLOR:
        print(f"⚠ {text}")
    elif COLORAMA_AVAILABLE:
        print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠ {text}{Fore.RESET}")


def print_info(text: str):
    """Print info message."""
    if NO_COLOR:
        print(f"ℹ {text}")
    elif COLORAMA_AVAILABLE:
        print(f"{Fore.CYAN}ℹ {text}{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}ℹ {text}{Fore.RESET}")


def print_stage(stage: str, duration: float = None):
    """Print processing stage."""
    if NO_COLOR:
        stage_text = f"→ {stage}"
        if duration:
            stage_text += f" ({duration:.2f}s)"
        print(stage_text)
    elif COLORAMA_AVAILABLE:
        stage_text = f"{Fore.BLUE}→ {stage}"
        if duration:
            stage_text += f" {Fore.YELLOW}({duration:.2f}s)"
        print(f"{stage_text}{Style.RESET_ALL}")
    else:
        stage_text = f"{Fore.BLUE}→ {stage}"
        if duration:
            stage_text += f" {Fore.YELLOW}({duration:.2f}s)"
        print(f"{stage_text}{Fore.RESET}")


def format_response_time(duration: float) -> str:
    """Format response time with color coding."""
    if duration < 30:
        color = Fore.GREEN
        status = "Fast"
    elif duration < 90:
        color = Fore.YELLOW
        status = "Normal"
    else:
        color = Fore.RED
        status = "Slow"
    
    if NO_COLOR:
        return f"{duration:.2f}s ({status})"
    elif COLORAMA_AVAILABLE:
        return f"{color}{duration:.2f}s ({status}){Style.RESET_ALL}"
    else:
        return f"{color}{duration:.2f}s ({status}){Fore.RESET}"


class DemoSession:
    """Demo session manager."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, no_color: bool = False):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.no_color = no_color
        self.session_log = []
        self.start_time = datetime.now()
        
        if no_color:
            global NO_COLOR
            NO_COLOR = True
            _update_color_classes()
    
    def log_request(self, query: str, response_data: Dict[str, Any], duration: float):
        """Log a request to session log."""
        self.session_log.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "duration": duration,
            "status": response_data.get("status", "unknown"),
            "total_items": response_data.get("results", {}).get("total_items", 0),
            "success_rate": response_data.get("results", {}).get("success_rate", 0.0)
        })
    
    def save_log(self):
        """Save session log to file."""
        if not self.session_log:
            return
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        log_file = f"demo_session_{timestamp}.log"
        
        log_data = {
            "session_start": self.start_time.isoformat(),
            "session_end": datetime.now().isoformat(),
            "total_requests": len(self.session_log),
            "base_url": self.base_url,
            "requests": self.session_log
        }
        
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            print_info(f"Session log saved to: {log_file}")
        except Exception as e:
            print_warning(f"Failed to save session log: {e}")
    
    def make_request(
        self,
        query: str,
        timeout: int = DEFAULT_TIMEOUT,
        processing_config: Optional[Dict[str, Any]] = None,
        store_results: bool = True,
        http_timeout: Optional[float] = None
    ) -> Tuple[Dict[str, Any], float, int]:
        """Make a scrape request and return response data and duration.
        
        Args:
            query: The query string to process
            timeout: API timeout_seconds value (must be >= 30 if provided, or None to omit)
            processing_config: Optional processing configuration
            store_results: Whether to store results in database
            http_timeout: Optional HTTP client timeout (separate from API timeout_seconds)
        """
        url = f"{self.base_url}/api/v1/scrape"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "query": query,
            "store_results": store_results
        }
        
        # Only include timeout_seconds in payload if it's valid (>= 30) or use default
        if timeout is not None and timeout >= 30:
            payload["timeout_seconds"] = timeout
        # If timeout is None or < 30, omit it from payload (API will use default)
        
        if processing_config:
            payload["processing_config"] = processing_config
        
        # Use http_timeout for client-side HTTP timeout, or fall back to timeout if provided
        client_timeout = http_timeout if http_timeout is not None else (timeout if timeout is not None else DEFAULT_TIMEOUT)
        
        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=client_timeout)
            duration = time.time() - start_time
            
            try:
                response_data = response.json()
            except:
                response_data = {"error": "Invalid JSON response", "raw": response.text[:500]}
            
            return response_data, duration, response.status_code
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            return {
                "status": "error",
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Request timeout after {client_timeout} seconds (HTTP client timeout)"
                }
            }, duration, 408
        except Exception as e:
            duration = time.time() - start_time
            return {
                "status": "error",
                "error": {
                    "code": "REQUEST_ERROR",
                    "message": str(e)
                }
            }, duration, 500
    
    def display_response(self, response_data: Dict[str, Any], duration: float, query: str):
        """Display formatted response."""
        print_header("Response Details")
        
        # Status
        status = response_data.get("status", "unknown")
        if status == "success":
            print_success(f"Status: {status.upper()}")
        else:
            print_error(f"Status: {status.upper()}")
        
        # Response time
        print_info(f"Response Time: {format_response_time(duration)}")
        
        # Cache status
        cache_status = response_data.get("cached", False)
        cache_age = response_data.get("cache_age_seconds", 0)
        if cache_status:
            if NO_COLOR:
                print_info(f"Cache: HIT (age: {cache_age}s)")
            else:
                print_info(f"Cache: {Fore.GREEN}HIT{Fore.RESET} (age: {cache_age}s)")
        else:
            if NO_COLOR:
                print_info(f"Cache: MISS")
            else:
                print_info(f"Cache: {Fore.YELLOW}MISS{Fore.RESET}")
        
        if status == "success":
            # Query information
            query_info = response_data.get("query", {})
            category = query_info.get("category", "unknown")
            confidence = query_info.get("confidence_score", 0.0)
            
            print_info(f"Category: {category}")
            print_info(f"Confidence: {confidence:.2%}")
            
            # Results summary
            results = response_data.get("results", {})
            total_items = results.get("total_items", 0)
            processed_items = results.get("processed_items", 0)
            success_rate = results.get("success_rate", 0.0)
            
            print_info(f"Total Items: {total_items}")
            print_info(f"Processed Items: {processed_items}")
            print_info(f"Success Rate: {success_rate:.1%}")
            
            # Execution metadata
            execution_metadata = response_data.get("execution_metadata", {})
            stages_timing = execution_metadata.get("stages_timing", {})
            
            if stages_timing:
                print_header("Processing Stages")
                for stage, stage_duration in stages_timing.items():
                    print_stage(stage.replace("_", " ").title(), stage_duration)
            
            # Analytics
            analytics = response_data.get("analytics", {})
            pages_scraped = analytics.get("pages_scraped", 0)
            if pages_scraped > 0:
                print_info(f"Pages Scraped: {pages_scraped}")
            
            # Quality metrics
            quality_metrics = analytics.get("quality_metrics", {})
            if quality_metrics:
                avg_relevance = quality_metrics.get("average_relevance_score", 0.0)
                if avg_relevance > 0:
                    print_info(f"Average Relevance: {avg_relevance:.2%}")
            
            # Warnings
            warnings = response_data.get("warnings", [])
            if warnings:
                print_header("Warnings")
                for warning in warnings:
                    print_warning(warning)
            
            # Sample results
            processed_contents = results.get("processed_contents", [])
            if processed_contents:
                print_header("Sample Results")
                for i, content in enumerate(processed_contents[:3], 1):
                    title = content.get("title", "No title")
                    url = content.get("url", "No URL")
                    print_info(f"{i}. {title}")
                    print(f"   URL: {url}")
                    if i < len(processed_contents[:3]):
                        print()
        else:
            # Error information
            error = response_data.get("error", {})
            error_code = error.get("code", "UNKNOWN")
            error_message = error.get("message", "Unknown error")
            
            print_error(f"Error Code: {error_code}")
            print_error(f"Error Message: {error_message}")
            
            # Recovery suggestions
            recovery_suggestions = error.get("recovery_suggestions", [])
            if recovery_suggestions:
                print_header("Recovery Suggestions")
                for suggestion in recovery_suggestions:
                    print_info(suggestion)
        
        # Log request
        self.log_request(query, response_data, duration)
    
    def compare_expected_vs_actual(
        self,
        response_data: Dict[str, Any],
        duration: float,
        status_code: int,
        expectations: Dict[str, Any]
    ):
        """Compare actual response against expected characteristics."""
        print_header("Expected vs Actual")
        
        # Status comparison
        expected_status = "success"
        actual_status = response_data.get("status", "unknown")
        status_match = actual_status == expected_status and status_code == 200
        if status_match:
            print_success(f"Status: Expected '{expected_status}', Got '{actual_status}' ✓")
        else:
            print_warning(f"Status: Expected '{expected_status}', Got '{actual_status}'")
        
        if actual_status == "success":
            # Category comparison
            query_info = response_data.get("query", {})
            actual_category = query_info.get("category", "unknown")
            expected_categories = expectations.get("expected_category", [])
            category_match = actual_category in expected_categories if expected_categories else True
            if category_match:
                print_success(f"Category: Expected one of {expected_categories}, Got '{actual_category}' ✓")
            else:
                print_warning(f"Category: Expected one of {expected_categories}, Got '{actual_category}'")
            
            # Response time comparison
            expected_time_min = expectations.get("expected_response_time_min", 0.0)
            expected_time_max = expectations.get("expected_response_time_max", 300.0)
            time_match = expected_time_min <= duration <= expected_time_max
            if time_match:
                print_success(f"Response Time: Expected {expected_time_min}-{expected_time_max}s, Got {duration:.2f}s ✓")
            else:
                print_warning(f"Response Time: Expected {expected_time_min}-{expected_time_max}s, Got {duration:.2f}s")
            
            # Cache status (if applicable)
            cache_status = response_data.get("cached", False)
            if "expected_cache_hit_second_call" in expectations:
                # This will be checked in cache_demo separately
                pass
    
    def quick_demo(self):
        """Run quick demo with pre-selected query."""
        print_header("Quick Demo - AI Tools Query")
        print_info(f"Query: {QUICK_DEMO_QUERY}")
        print()
        
        response_data, duration, status_code = self.make_request(QUICK_DEMO_QUERY)
        self.display_response(response_data, duration, QUICK_DEMO_QUERY)
        
        # Compare expected vs actual
        expectations = DEMO_EXPECTATIONS.get("quick_demo", {})
        self.compare_expected_vs_actual(response_data, duration, status_code, expectations)
        print()
        
        if status_code == 200:
            print_success("Quick demo completed successfully!")
        else:
            print_error("Quick demo failed. Check the error details above.")
    
    def category_demo(self, category: str):
        """Run demo for a specific category."""
        if category not in SAMPLE_QUERIES:
            print_error(f"Unknown category: {category}")
            return
        
        queries = SAMPLE_QUERIES[category]
        query = queries[0]  # Use first query from category
        
        print_header(f"Category Demo - {category.replace('_', ' ').title()}")
        print_info(f"Query: {query}")
        print()
        
        response_data, duration, status_code = self.make_request(query)
        self.display_response(response_data, duration, query)
        
        # Compare expected vs actual
        expectations = DEMO_EXPECTATIONS.get(category, {})
        self.compare_expected_vs_actual(response_data, duration, status_code, expectations)
        print()
        
        if status_code == 200:
            print_success(f"Category demo ({category}) completed successfully!")
        else:
            print_error(f"Category demo ({category}) failed.")
    
    def cache_demo(self):
        """Demonstrate caching functionality."""
        print_header("Cache Demonstration")
        
        query = "Test cache query for demonstration"
        
        # First request (cache MISS)
        print_info("First request (expected: cache MISS)...")
        response1, duration1, status1 = self.make_request(query)
        
        if status1 == 200:
            cache_status1 = response1.get("cached", False)
            print_info(f"Cache Status: {'HIT' if cache_status1 else 'MISS'}")
            print_info(f"Duration: {duration1:.2f}s")
        
        print()
        print_info("Waiting 2 seconds before second request...")
        time.sleep(2)
        print()
        
        # Second request (cache HIT)
        print_info("Second request (expected: cache HIT)...")
        response2, duration2, status2 = self.make_request(query)
        
        if status2 == 200:
            cache_status2 = response2.get("cached", False)
            cache_age = response2.get("cache_age_seconds", 0)
            
            print_info(f"Cache Status: {'HIT' if cache_status2 else 'MISS'}")
            print_info(f"Cache Age: {cache_age}s")
            print_info(f"Duration: {duration2:.2f}s")
            
            # Expected vs Actual comparison for cache demo
            print_header("Expected vs Actual - Cache Demo")
            expected_first_cache = False  # First call should be MISS
            if cache_status1 == expected_first_cache:
                print_success(f"First Request Cache: Expected MISS, Got {'HIT' if cache_status1 else 'MISS'} ✓")
            else:
                print_warning(f"First Request Cache: Expected MISS, Got {'HIT' if cache_status1 else 'MISS'}")
            
            expected_second_cache = True  # Second call should be HIT
            if cache_status2 == expected_second_cache:
                print_success(f"Second Request Cache: Expected HIT, Got {'HIT' if cache_status2 else 'MISS'} ✓")
            else:
                print_warning(f"Second Request Cache: Expected HIT, Got {'HIT' if cache_status2 else 'MISS'}")
            
            # Response time comparison
            if duration2 < duration1:
                speedup = duration1 / duration2 if duration2 > 0 else 0
                print_success(f"Performance: Cache working! {speedup:.1f}x faster with cache ✓")
            else:
                print_warning(f"Performance: Cache may not be working as expected (duration2: {duration2:.2f}s >= duration1: {duration1:.2f}s)")
    
    def custom_query_demo(self, query: str):
        """Run demo with custom query."""
        print_header("Custom Query Demo")
        print_info(f"Query: {query}")
        print()
        
        response_data, duration, status_code = self.make_request(query)
        self.display_response(response_data, duration, query)
        
        if status_code == 200:
            print_success("Custom query demo completed successfully!")
        else:
            print_error("Custom query demo failed.")
    
    def health_check_demo(self):
        """Display system health status."""
        print_header("System Health Check")
        
        try:
            # Overall health
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                
                if status == "healthy":
                    print_success(f"Overall Status: {status.upper()}")
                elif status == "degraded":
                    print_warning(f"Overall Status: {status.upper()}")
                else:
                    print_error(f"Overall Status: {status.upper()}")
                
                # Component status
                components = health_data.get("components", {})
                print_header("Component Status")
                for component, component_data in components.items():
                    comp_status = component_data.get("status", "unknown")
                    if comp_status == "healthy":
                        print_success(f"{component}: {comp_status}")
                    else:
                        print_warning(f"{component}: {comp_status}")
            else:
                print_error(f"Health check failed with status {response.status_code}")
        except Exception as e:
            print_error(f"Health check error: {e}")
    
    def metrics_demo(self):
        """Display metrics and performance statistics."""
        print_header("Metrics & Performance")
        
        try:
            # Metrics endpoint (may require admin API key)
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            response = requests.get(
                f"{self.base_url}/api/v1/metrics?format=json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                metrics_data = response.json()
                metrics = metrics_data.get("metrics", {})
                
                # Total requests
                total_requests = metrics.get("api_requests_total", {}).get("value", 0)
                print_info(f"Total Requests: {total_requests}")
                
                # Error rate
                total_errors = metrics.get("api_errors_total", {}).get("value", 0)
                if total_requests > 0:
                    error_rate = (total_errors / total_requests) * 100
                    print_info(f"Error Rate: {error_rate:.1f}%")
                
                # Cache hit rate
                cache_hit_rate = metrics.get("cache_hit_rate", {}).get("value", 0.0)
                print_info(f"Cache Hit Rate: {cache_hit_rate:.1%}")
                
                # Average response time
                duration_hist = metrics.get("api_request_duration_seconds", {})
                if duration_hist.get("count", 0) > 0:
                    avg_duration = (duration_hist.get("sum", 0) / duration_hist.get("count", 1)) * 1000
                    print_info(f"Average Response Time: {avg_duration:.0f}ms")
            elif response.status_code == 403:
                print_warning("Metrics endpoint requires admin API key")
            else:
                print_warning(f"Metrics endpoint returned status {response.status_code}")
        except Exception as e:
            print_warning(f"Could not fetch metrics: {e}")
    
    def error_handling_demo(self):
        """Demonstrate error handling."""
        print_header("Error Handling Demo")
        
        # Empty query
        print_info("Testing empty query (expected: validation error)...")
        response_data, duration, status_code = self.make_request("")
        if status_code == 400:
            print_success("Validation error caught correctly")
        else:
            print_warning(f"Unexpected status code: {status_code}")
        print()
        
        # Client-side timeout (HTTP timeout triggers, but API timeout_seconds is valid)
        print_info("Testing client-side HTTP timeout (expected: timeout error)...")
        response_data, duration, status_code = self.make_request(
            "Test query",
            timeout=180,  # Valid API timeout_seconds (>= 30)
            http_timeout=0.1  # Very small HTTP client timeout to trigger client-side timeout
        )
        if status_code == 408:
            print_success("Timeout handled correctly (client-side timeout)")
        else:
            print_warning(f"Unexpected status code: {status_code}")
    
    def interactive_menu(self):
        """Display interactive menu."""
        while True:
            print_header("AI Web Scraper - Interactive Demo")
            print("1. Quick Demo (pre-selected query)")
            print("2. Category Demo - AI Tools")
            print("3. Category Demo - Mutual Funds")
            print("4. Category Demo - General")
            print("5. Cache Demonstration")
            print("6. Custom Query")
            print("7. Health Check")
            print("8. Metrics & Performance")
            print("9. Error Handling Demo")
            print("0. Exit")
            print()
            
            choice = input("Select an option (0-9): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.quick_demo()
            elif choice == "2":
                self.category_demo("ai_tools")
            elif choice == "3":
                self.category_demo("mutual_funds")
            elif choice == "4":
                self.category_demo("general")
            elif choice == "5":
                self.cache_demo()
            elif choice == "6":
                query = input("Enter your query: ").strip()
                if query:
                    self.custom_query_demo(query)
                else:
                    print_warning("Empty query provided")
            elif choice == "7":
                self.health_check_demo()
            elif choice == "8":
                self.metrics_demo()
            elif choice == "9":
                self.error_handling_demo()
            else:
                print_warning("Invalid option. Please try again.")
            
            if choice != "0":
                input("\nPress Enter to continue...")
                print()
        
        # Save session log
        self.save_log()
        
        # Summary
        print_header("Demo Session Summary")
        print_info(f"Total Requests: {len(self.session_log)}")
        if self.session_log:
            total_duration = sum(r["duration"] for r in self.session_log)
            avg_duration = total_duration / len(self.session_log)
            print_info(f"Average Response Time: {avg_duration:.2f}s")
            
            successful = sum(1 for r in self.session_log if r["status"] == "success")
            print_info(f"Successful Requests: {successful}/{len(self.session_log)}")
        
        print_success("Demo session completed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive demo script for AI Web Scraper API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--quick", action="store_true", help="Run quick demo and exit")
    parser.add_argument("--category", choices=list(SAMPLE_QUERIES.keys()), help="Run category demo and exit")
    parser.add_argument("--query", help="Run custom query demo and exit")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()
    
    session = DemoSession(args.url, args.api_key, args.no_color)
    
    if args.quick:
        session.quick_demo()
        session.save_log()
    elif args.category:
        session.category_demo(args.category)
        session.save_log()
    elif args.query:
        session.custom_query_demo(args.query)
        session.save_log()
    else:
        session.interactive_menu()


if __name__ == "__main__":
    main()

