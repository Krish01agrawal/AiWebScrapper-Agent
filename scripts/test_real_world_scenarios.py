#!/usr/bin/env python3
"""
Comprehensive real-world scenario testing script.
Tests actual user queries with deep content validation, quality metrics, and performance benchmarking.
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

# Import utilities
from scripts.test_scrape_endpoint import ScrapeEndpointTester, DEFAULT_BASE_URL, DEFAULT_TIMEOUT
from scripts.validate_response_schema import ResponseValidator
from scripts.utils.content_analyzer import ContentQualityAnalyzer, RelevanceMetrics
from scripts.utils.performance_benchmarker import PerformanceBenchmarker


# Real-world test queries
REAL_WORLD_QUERIES = {
    "ai_tools": [
        "best AI agents for coding",
        "AI tools for image generation",
        "open source LLMs",
        "best AI coding assistants",
        "AI agents for software development"
    ],
    "mutual_funds": [
        "best mutual funds for beginners",
        "low-risk index funds",
        "retirement planning funds",
        "best equity mutual funds",
        "mutual funds with high returns"
    ]
}

# Edge case queries
EDGE_CASE_QUERIES = {
    "empty": "",
    "long": "a" * 1000,
    "special_chars": "Test query with @#$%^&*() special chars",
    "ambiguous": "best tools for coding and investing",
    "non_english": "mejores herramientas de IA para codificación"
}


class RealWorldScenarioTester(ScrapeEndpointTester):
    """Extended tester for real-world scenario validation."""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT, api_key: Optional[str] = None):
        super().__init__(base_url, timeout, api_key)
        self.content_analyzer = ContentQualityAnalyzer()
        self.performance_benchmarker = PerformanceBenchmarker()
        self.validator = ResponseValidator()
        self.test_results = []
    
    def test_content_relevance(
        self, 
        response_data: Dict[str, Any], 
        query_text: str, 
        query_category: str
    ) -> Dict[str, Any]:
        """Test content relevance for scraped URLs.
        
        Args:
            response_data: API response data
            query_text: Original query text
            query_category: Query category
            
        Returns:
            Relevance analysis report
        """
        if response_data.get("status") != "success":
            return {
                "error": "Response status is not 'success'",
                "relevance_score": 0.0
            }
        
        results = response_data.get("results", {})
        processed_contents = results.get("processed_contents", [])
        
        if not processed_contents:
            return {
                "error": "No processed contents found",
                "relevance_score": 0.0,
                "total_items": 0
            }
        
        relevance_scores = []
        url_relevance_scores = []
        title_relevance_scores = []
        content_relevance_scores = []
        issues = []
        
        for content_item in processed_contents:
            original_content = content_item.get("original_content", {})
            url = original_content.get("url", "")
            title = original_content.get("title", "")
            content = original_content.get("content", "")
            
            if not url:
                continue
            
            # Analyze relevance
            metrics = self.content_analyzer.analyze_content_relevance(
                url=url,
                title=title or "",
                content=content or "",
                query_text=query_text,
                query_category=query_category
            )
            
            relevance_scores.append(metrics.overall_relevance)
            url_relevance_scores.append(metrics.url_relevance)
            title_relevance_scores.append(metrics.title_relevance)
            content_relevance_scores.append(metrics.content_relevance)
            
            if metrics.issues:
                issues.extend(metrics.issues)
        
        # Calculate average relevance
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        avg_url_relevance = sum(url_relevance_scores) / len(url_relevance_scores) if url_relevance_scores else 0.0
        avg_title_relevance = sum(title_relevance_scores) / len(title_relevance_scores) if title_relevance_scores else 0.0
        avg_content_relevance = sum(content_relevance_scores) / len(content_relevance_scores) if content_relevance_scores else 0.0
        
        # Check if at least 70% of URLs are relevant
        relevant_count = sum(1 for score in relevance_scores if score >= 0.7)
        relevance_percentage = (relevant_count / len(relevance_scores) * 100) if relevance_scores else 0.0
        meets_threshold = relevance_percentage >= 70.0
        
        return {
            "relevance_score": avg_relevance,
            "url_relevance": avg_url_relevance,
            "title_relevance": avg_title_relevance,
            "content_relevance": avg_content_relevance,
            "relevant_items": relevant_count,
            "total_items": len(relevance_scores),
            "relevance_percentage": relevance_percentage,
            "meets_threshold": meets_threshold,
            "issues": issues[:10]  # Limit to first 10 issues
        }
    
    def test_ai_analysis_quality(
        self, 
        response_data: Dict[str, Any], 
        query_text: str, 
        query_category: str
    ) -> Dict[str, Any]:
        """Test AI analysis quality.
        
        Args:
            response_data: API response data
            query_text: Original query text
            query_category: Query category
            
        Returns:
            AI analysis quality report
        """
        if response_data.get("status") != "success":
            return {
                "error": "Response status is not 'success'",
                "quality_score": 0.0
            }
        
        results = response_data.get("results", {})
        processed_contents = results.get("processed_contents", [])
        
        if not processed_contents:
            return {
                "error": "No processed contents found",
                "quality_score": 0.0,
                "total_items": 0
            }
        
        quality_scores = []
        all_issues = []
        themes_match_count = 0
        confidence_ok_count = 0
        
        for content_item in processed_contents:
            ai_insights = content_item.get("ai_insights")
            if not ai_insights:
                continue
            
            # Analyze AI insights quality
            quality_report = self.content_analyzer.analyze_ai_insights_quality(
                ai_insights=ai_insights,
                query_text=query_text,
                query_category=query_category
            )
            
            quality_scores.append(quality_report["overall_quality"])
            if quality_report["issues"]:
                all_issues.extend(quality_report["issues"])
            
            # Check themes match query
            themes = ai_insights.get("themes", [])
            query_lower = query_text.lower()
            if any(word in theme.lower() for theme in themes for word in query_lower.split() if len(word) > 2):
                themes_match_count += 1
            
            # Check confidence scores
            confidence = ai_insights.get("confidence_score", 0.0)
            if confidence > 0.7:
                confidence_ok_count += 1
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            "quality_score": avg_quality,
            "total_items": len(processed_contents),
            "items_with_ai_insights": len(quality_scores),
            "themes_match_percentage": (themes_match_count / len(quality_scores) * 100) if quality_scores else 0.0,
            "confidence_ok_percentage": (confidence_ok_count / len(quality_scores) * 100) if quality_scores else 0.0,
            "issues": all_issues[:10]  # Limit to first 10 issues
        }
    
    def test_structured_data_quality(
        self, 
        response_data: Dict[str, Any], 
        query_category: str
    ) -> Dict[str, Any]:
        """Test structured data extraction quality.
        
        Args:
            response_data: API response data
            query_category: Query category
            
        Returns:
            Structured data quality report
        """
        if response_data.get("status") != "success":
            return {
                "error": "Response status is not 'success'",
                "quality_score": 0.0
            }
        
        results = response_data.get("results", {})
        processed_contents = results.get("processed_contents", [])
        
        if not processed_contents:
            return {
                "error": "No processed contents found",
                "quality_score": 0.0,
                "total_items": 0
            }
        
        quality_scores = []
        total_entities = 0
        all_issues = []
        
        for content_item in processed_contents:
            structured_data = content_item.get("structured_data")
            if not structured_data:
                continue
            
            # Analyze structured data quality
            quality_report = self.content_analyzer.analyze_structured_data_quality(
                structured_data=structured_data,
                query_category=query_category
            )
            
            quality_scores.append(quality_report["quality_score"])
            total_entities += quality_report["entity_count"]
            if quality_report["issues"]:
                all_issues.extend(quality_report["issues"])
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Check if at least 3 entities per content item on average
        avg_entities_per_item = total_entities / len(processed_contents) if processed_contents else 0.0
        meets_threshold = avg_entities_per_item >= 3.0
        
        return {
            "quality_score": avg_quality,
            "total_items": len(processed_contents),
            "items_with_structured_data": len(quality_scores),
            "total_entities": total_entities,
            "avg_entities_per_item": avg_entities_per_item,
            "meets_threshold": meets_threshold,
            "issues": all_issues[:10]  # Limit to first 10 issues
        }
    
    def test_edge_case_comprehensive(self, json_mode: bool = False) -> Dict[str, Any]:
        """Test comprehensive edge cases.
        
        Args:
            json_mode: Whether to output in JSON format
            
        Returns:
            Edge case test results
        """
        if not json_mode:
            print("Testing Edge Cases...")
            print("-" * 60)
        
        edge_case_results = {}
        
        # Test empty query
        if not json_mode:
            print("  Testing empty query...")
        response_data, duration, status_code, _ = self.test_scrape_request("")
        edge_case_results["empty_query"] = {
            "expected_status": 400,
            "actual_status": status_code,
            "passed": status_code == 400,
            "duration": duration
        }
        
        # Test 1000-char query
        if not json_mode:
            print("  Testing 1000-character query...")
        long_query = "a" * 1000
        response_data, duration, status_code, _ = self.test_scrape_request(long_query)
        edge_case_results["long_query"] = {
            "expected_status": [200, 400],  # May work or fail validation
            "actual_status": status_code,
            "passed": status_code in [200, 400],
            "duration": duration
        }
        
        # Test special characters
        if not json_mode:
            print("  Testing query with special characters...")
        special_query = "Test query with @#$%^&*() special chars"
        response_data, duration, status_code, _ = self.test_scrape_request(special_query)
        edge_case_results["special_chars"] = {
            "status_code": status_code,
            "passed": status_code in [200, 400],
            "duration": duration
        }
        
        # Test ambiguous query (multi-domain)
        if not json_mode:
            print("  Testing ambiguous query...")
        ambiguous_query = "best tools for coding and investing"
        response_data, duration, status_code, _ = self.test_scrape_request(ambiguous_query)
        if status_code == 200 and response_data.get("status") == "success":
            category = response_data.get("query", {}).get("category", "")
            edge_case_results["ambiguous_query"] = {
                "status_code": status_code,
                "category": category,
                "passed": True,
                "duration": duration
            }
        else:
            edge_case_results["ambiguous_query"] = {
                "status_code": status_code,
                "passed": False,
                "duration": duration
            }
        
        # Test non-English query
        if not json_mode:
            print("  Testing non-English query...")
        non_english_query = "mejores herramientas de IA para codificación"
        response_data, duration, status_code, _ = self.test_scrape_request(non_english_query)
        edge_case_results["non_english"] = {
            "status_code": status_code,
            "passed": status_code in [200, 400],  # May or may not be supported
            "duration": duration
        }
        
        return edge_case_results
    
    def test_real_world_query(
        self, 
        query: str, 
        category: str, 
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """Test a real-world query with comprehensive validation.
        
        Args:
            query: Query text to test
            category: Expected category
            json_mode: Whether to output in JSON format
            
        Returns:
            Comprehensive test result
        """
        if not json_mode:
            print(f"\nTesting query: {query[:60]}...")
        
        # Make request
        response_data, duration, status_code, store_results = self.test_scrape_request(query)
        
        test_result = {
            "query": query,
            "category": category,
            "status_code": status_code,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if status_code != 200:
            test_result["error"] = f"Request failed with status {status_code}"
            test_result["passed"] = False
            return test_result
        
        # Validate response schema
        is_valid, validation_errors, _ = self.validator.validate_scrape_response(response_data)
        test_result["schema_validation"] = {
            "passed": is_valid,
            "errors": validation_errors
        }
        
        if not is_valid:
            test_result["passed"] = False
            return test_result
        
        if response_data.get("status") != "success":
            test_result["error"] = "Response status is not 'success'"
            test_result["passed"] = False
            return test_result
        
        # Test content relevance
        relevance_report = self.test_content_relevance(response_data, query, category)
        test_result["content_relevance"] = relevance_report
        
        # Test AI analysis quality
        ai_quality_report = self.test_ai_analysis_quality(response_data, query, category)
        test_result["ai_analysis_quality"] = ai_quality_report
        
        # Test structured data quality
        structured_data_report = self.test_structured_data_quality(response_data, category)
        test_result["structured_data_quality"] = structured_data_report
        
        # Test performance
        performance_report = self.performance_benchmarker.analyze_response_timing(response_data)
        test_result["performance"] = performance_report
        
        # Determine overall pass/fail
        passed = (
            is_valid and
            relevance_report.get("meets_threshold", False) and
            ai_quality_report.get("quality_score", 0.0) > 0.5 and
            structured_data_report.get("meets_threshold", False) and
            performance_report.get("overall_status") != "FAIL"
        )
        
        test_result["passed"] = passed
        
        return test_result
    
    def run_comprehensive_tests(self, json_mode: bool = False, save_report: bool = False) -> Dict[str, Any]:
        """Run comprehensive real-world scenario tests.
        
        Args:
            json_mode: Whether to output in JSON format
            save_report: Whether to save test report to file
            
        Returns:
            Comprehensive test results
        """
        if not json_mode:
            print("=" * 60)
            print("REAL-WORLD SCENARIO TEST SUITE")
            print("=" * 60)
            print()
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url,
            "test_categories": {}
        }
        
        # Test AI Tools queries
        if not json_mode:
            print("1. Testing AI Tools Queries")
            print("-" * 60)
        
        ai_tools_results = []
        for query in REAL_WORLD_QUERIES["ai_tools"]:
            test_result = self.test_real_world_query(query, "ai_tools", json_mode=json_mode)
            ai_tools_results.append(test_result)
            if not json_mode:
                status = "✓ PASSED" if test_result.get("passed") else "✗ FAILED"
                print(f"  {status}: {query[:50]}...")
        
        results["test_categories"]["ai_tools"] = {
            "queries": ai_tools_results,
            "passed": sum(1 for r in ai_tools_results if r.get("passed")),
            "total": len(ai_tools_results)
        }
        
        if not json_mode:
            print()
        
        # Test Mutual Funds queries
        if not json_mode:
            print("2. Testing Mutual Funds Queries")
            print("-" * 60)
        
        mutual_funds_results = []
        for query in REAL_WORLD_QUERIES["mutual_funds"]:
            test_result = self.test_real_world_query(query, "mutual_funds", json_mode=json_mode)
            mutual_funds_results.append(test_result)
            if not json_mode:
                status = "✓ PASSED" if test_result.get("passed") else "✗ FAILED"
                print(f"  {status}: {query[:50]}...")
        
        results["test_categories"]["mutual_funds"] = {
            "queries": mutual_funds_results,
            "passed": sum(1 for r in mutual_funds_results if r.get("passed")),
            "total": len(mutual_funds_results)
        }
        
        if not json_mode:
            print()
        
        # Test edge cases
        if not json_mode:
            print("3. Testing Edge Cases")
            print("-" * 60)
        
        edge_case_results = self.test_edge_case_comprehensive(json_mode=json_mode)
        results["edge_cases"] = edge_case_results
        
        if not json_mode:
            print()
        
        # Calculate summary
        total_tests = len(ai_tools_results) + len(mutual_funds_results) + len(edge_case_results)
        passed_tests = (
            sum(1 for r in ai_tools_results if r.get("passed")) +
            sum(1 for r in mutual_funds_results if r.get("passed")) +
            sum(1 for r in edge_case_results.values() if r.get("passed", False))
        )
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        # Save report if requested
        if save_report:
            self._save_report(results)
        
        return results
    
    def _save_report(self, results: Dict[str, Any]):
        """Save test report to file.
        
        Args:
            results: Test results dictionary
        """
        # Create test_results directory if it doesn't exist
        test_results_dir = Path("test_results")
        test_results_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = test_results_dir / f"real_world_scenarios_{timestamp}.json"
        
        # Save report
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Create symlink to latest
        latest_link = test_results_dir / "real_world_scenarios_latest.json"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(filename.name)
        
        print(f"\nTest report saved to: {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Real-world scenario testing script")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--query", help="Test specific query")
    parser.add_argument("--category", choices=["ai_tools", "mutual_funds"], help="Test all queries in category")
    parser.add_argument("--edge-cases", action="store_true", help="Test edge cases only")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks only")
    parser.add_argument("--all", action="store_true", help="Run comprehensive test suite")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--save-report", action="store_true", help="Save test report to file")
    
    args = parser.parse_args()
    
    tester = RealWorldScenarioTester(
        base_url=args.url,
        timeout=args.timeout,
        api_key=args.api_key
    )
    
    if args.query:
        # Test specific query
        category = args.category or "general"
        result = tester.test_real_world_query(args.query, category, json_mode=args.json)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("passed"):
                print("\n✓ Test PASSED")
            else:
                print("\n✗ Test FAILED")
            if args.verbose:
                pprint(result)
    
    elif args.category:
        # Test all queries in category
        queries = REAL_WORLD_QUERIES.get(args.category, [])
        results = []
        for query in queries:
            result = tester.test_real_world_query(query, args.category, json_mode=args.json)
            results.append(result)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            passed = sum(1 for r in results if r.get("passed"))
            print(f"\nResults: {passed}/{len(results)} passed")
    
    elif args.edge_cases:
        # Test edge cases only
        results = tester.test_edge_case_comprehensive(json_mode=args.json)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            passed = sum(1 for r in results.values() if r.get("passed", False))
            print(f"\nEdge Cases: {passed}/{len(results)} passed")
    
    elif args.performance:
        # Performance benchmarking
        if not args.json:
            print("Running Performance Benchmarks...")
            print("-" * 60)
        
        # Test a sample query for performance
        query = "best AI agents for coding"
        response_data, duration, status_code, _ = tester.test_scrape_request(query)
        
        if status_code == 200 and response_data.get("status") == "success":
            performance_report = tester.performance_benchmarker.analyze_response_timing(response_data)
            
            if args.json:
                print(json.dumps(performance_report, indent=2))
            else:
                print(f"Overall Status: {performance_report['overall_status']}")
                print(f"Total Execution Time: {performance_report['total_execution_time']:.2f}s")
                print("\nStage Performance:")
                for stage in performance_report["stages"]:
                    print(f"  {stage['stage_name']}: {stage['duration']:.2f}s ({stage['status']})")
                
                if performance_report["recommendations"]:
                    print("\nRecommendations:")
                    for rec in performance_report["recommendations"]:
                        print(f"  - {rec}")
        else:
            print("Error: Failed to get valid response for performance testing")
            sys.exit(1)
    
    elif args.all:
        # Run comprehensive test suite
        results = tester.run_comprehensive_tests(json_mode=args.json, save_report=args.save_report)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            summary = results["summary"]
            print(f"Total Tests: {summary['total_tests']}")
            print(f"Passed: {summary['passed']}")
            print(f"Failed: {summary['failed']}")
            print(f"Success Rate: {summary['success_rate']:.1f}%")
            print(f"Timestamp: {results['timestamp']}")
        
        # Exit with appropriate code
        if results["summary"]["success_rate"] == 100:
            sys.exit(0)
        else:
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

