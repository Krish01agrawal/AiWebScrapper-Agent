#!/usr/bin/env python3
"""
Load test results analysis and visualization script.
Reads JSON results from test_load_performance.py and generates comprehensive analysis reports.
"""
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from scripts.utils.load_test_monitor import calculate_percentiles, format_memory_size
from scripts.utils.performance_benchmarker import PerformanceBenchmarker


def load_test_results(filepath: str) -> Dict[str, Any]:
    """Load test results from JSON file.
    
    Args:
        filepath: Path to JSON results file
        
    Returns:
        Dictionary with test results
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_response_times(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze response times and identify outliers.
    
    Args:
        results: Test results dictionary
        
    Returns:
        Dictionary with response time analysis
    """
    # Handle both single scenario and multi-scenario results
    scenarios = results.get("scenarios", {})
    if not scenarios:
        # Single scenario results
        scenarios = {"single": results}
    
    analysis = {}
    
    for scenario_name, scenario_data in scenarios.items():
        response_times_data = scenario_data.get("response_times", {})
        # Read from "values" key where raw response times are stored
        response_times = response_times_data.get("values", [])
        
        if not response_times:
            # Fallback: try to get from summary (for backward compatibility)
            summary = scenario_data.get("summary", {})
            if "response_times" in summary:
                response_times = summary.get("response_times", [])
        
        if not response_times:
            continue
        
        percentiles = calculate_percentiles(response_times)
        avg = sum(response_times) / len(response_times) if response_times else 0.0
        min_time = min(response_times) if response_times else 0.0
        max_time = max(response_times) if response_times else 0.0
        
        # Identify outliers (values > p95)
        p95 = percentiles.get("p95", 0.0)
        outliers = [rt for rt in response_times if rt > p95]
        
        # Detect performance degradation
        # Compare first half vs second half
        mid_point = len(response_times) // 2
        first_half = response_times[:mid_point] if mid_point > 0 else []
        second_half = response_times[mid_point:] if mid_point > 0 else []
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0.0
        second_avg = sum(second_half) / len(second_half) if second_half else 0.0
        
        degradation = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0
        
        analysis[scenario_name] = {
            "count": len(response_times),
            "min": min_time,
            "max": max_time,
            "avg": avg,
            "percentiles": percentiles,
            "outliers_count": len(outliers),
            "outliers_percentage": (len(outliers) / len(response_times) * 100) if response_times else 0.0,
            "performance_degradation": degradation,
            "degradation_detected": degradation > 20.0  # >20% slower
        }
    
    return analysis


def analyze_cache_efficiency(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze cache efficiency and effectiveness.
    
    Args:
        results: Test results dictionary
        
    Returns:
        Dictionary with cache analysis
    """
    scenarios = results.get("scenarios", {})
    if not scenarios:
        scenarios = {"single": results}
    
    analysis = {}
    
    for scenario_name, scenario_data in scenarios.items():
        cache_data = scenario_data.get("cache", {})
        
        if not cache_data:
            # Try cache validation scenario
            if scenario_name == "cache_validation" or "cache" in scenario_name.lower():
                cache_data = scenario_data
        
        hits = cache_data.get("cache_hits", cache_data.get("hits", 0))
        misses = cache_data.get("cache_misses", cache_data.get("misses", 0))
        total = hits + misses
        
        if total == 0:
            continue
        
        hit_rate = (hits / total * 100) if total > 0 else 0.0
        
        # Get time saved
        time_saved = cache_data.get("time_saved_by_cache", 0.0)
        avg_hit_time = cache_data.get("avg_hit_response_time", 0.0)
        avg_miss_time = cache_data.get("avg_miss_response_time", 0.0)
        
        analysis[scenario_name] = {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": hit_rate,
            "time_saved_seconds": time_saved,
            "avg_hit_time": avg_hit_time,
            "avg_miss_time": avg_miss_time,
            "speedup": (avg_miss_time / avg_hit_time) if avg_hit_time > 0 else 0.0,
            "optimization_opportunities": []
        }
        
        # Identify optimization opportunities
        if hit_rate < 50.0:
            analysis[scenario_name]["optimization_opportunities"].append(
                f"Low cache hit rate ({hit_rate:.1f}%) - consider increasing cache TTL or size"
            )
        
        if avg_hit_time > avg_miss_time * 0.8:
            analysis[scenario_name]["optimization_opportunities"].append(
                "Cache hits are not significantly faster - verify cache implementation"
            )
    
    return analysis


def analyze_rate_limiting(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze rate limiting behavior.
    
    Args:
        results: Test results dictionary
        
    Returns:
        Dictionary with rate limiting analysis
    """
    scenarios = results.get("scenarios", {})
    if not scenarios:
        scenarios = {"single": results}
    
    analysis = {}
    
    for scenario_name, scenario_data in scenarios.items():
        # Check for rate limit validation scenario
        if scenario_name == "rate_limit_validation" or "rate_limit" in scenario_name.lower():
            rate_limit_data = scenario_data
            
            requests_sent = rate_limit_data.get("requests_sent", 0)
            requests_blocked = rate_limit_data.get("requests_blocked", 0)
            requests_allowed = rate_limit_data.get("requests_allowed", 0)
            false_positives = rate_limit_data.get("false_positives", 0)
            false_negatives = rate_limit_data.get("false_negatives", 0)
            header_validation = rate_limit_data.get("header_validation_passed", False)
            status = rate_limit_data.get("status", "UNKNOWN")
            
            analysis[scenario_name] = {
                "requests_sent": requests_sent,
                "requests_blocked": requests_blocked,
                "requests_allowed": requests_allowed,
                "block_rate": (requests_blocked / requests_sent * 100) if requests_sent > 0 else 0.0,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "header_validation_passed": header_validation,
                "status": status,
                "issues": []
            }
            
            if false_negatives > 0:
                analysis[scenario_name]["issues"].append(
                    f"{false_negatives} requests incorrectly blocked"
                )
            
            if not header_validation:
                analysis[scenario_name]["issues"].append(
                    "Rate limit headers validation failed"
                )
            
            if status == "FAIL":
                analysis[scenario_name]["issues"].append(
                    "Rate limiting test failed"
                )
        else:
            # Check rate limit hits in other scenarios
            rate_limit_hits = scenario_data.get("rate_limiting", {}).get("rate_limit_hits", 0)
            total_requests = scenario_data.get("summary", {}).get("total_requests", 0)
            
            if total_requests > 0:
                analysis[scenario_name] = {
                    "rate_limit_hits": rate_limit_hits,
                    "rate_limit_percentage": (rate_limit_hits / total_requests * 100),
                    "status": "INFO"
                }
    
    return analysis


def analyze_memory_usage(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze memory usage and detect leaks.
    
    Args:
        results: Test results dictionary
        
    Returns:
        Dictionary with memory analysis
    """
    scenarios = results.get("scenarios", {})
    if not scenarios:
        scenarios = {"single": results}
    
    analysis = {}
    
    for scenario_name, scenario_data in scenarios.items():
        memory_stats = scenario_data.get("memory", scenario_data.get("memory_stats", {}))
        
        if not memory_stats:
            continue
        
        start_memory = memory_stats.get("start", {}).get("rss_mb", 0)
        end_memory = memory_stats.get("end", {}).get("rss_mb", 0)
        peak_memory = memory_stats.get("peak", {}).get("rss_mb", 0)
        memory_growth = memory_stats.get("memory_growth_mb", end_memory - start_memory)
        
        total_requests = scenario_data.get("summary", {}).get("total_requests", 1)
        memory_per_request = memory_growth / total_requests if total_requests > 0 else 0.0
        
        # Detect potential memory leaks (>10MB growth per 100 requests)
        leak_threshold = 10.0  # MB per 100 requests
        potential_leak = memory_per_request * 100 > leak_threshold
        
        analysis[scenario_name] = {
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "peak_memory_mb": peak_memory,
            "memory_growth_mb": memory_growth,
            "memory_per_request_mb": memory_per_request,
            "potential_leak": potential_leak,
            "recommendations": []
        }
        
        if potential_leak:
            analysis[scenario_name]["recommendations"].append(
                f"Potential memory leak detected: {memory_growth:.2f}MB growth for {total_requests} requests"
            )
        
        if peak_memory > 1000:  # >1GB
            analysis[scenario_name]["recommendations"].append(
                f"High memory usage: {peak_memory:.2f}MB peak - consider memory limits"
            )
    
    return analysis


def analyze_connection_pool(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze connection pool behavior.
    
    Args:
        results: Test results dictionary
        
    Returns:
        Dictionary with connection pool analysis
    """
    scenarios = results.get("scenarios", {})
    if not scenarios:
        scenarios = {"single": results}
    
    analysis = {}
    
    for scenario_name, scenario_data in scenarios.items():
        pool_stats = scenario_data.get("connection_pool", scenario_data.get("connection_pool_stats", {}))
        
        if not pool_stats or "error" in pool_stats:
            continue
        
        max_pool_size = pool_stats.get("max_pool_size", 0)
        pool_size = pool_stats.get("pool_size", 0)
        available = pool_stats.get("available")
        in_use = pool_stats.get("in_use")
        approximate = pool_stats.get("approximate", False)
        
        # Only compute utilization if in_use is available (not None)
        utilization = None
        saturated = None
        if in_use is not None and max_pool_size > 0:
            utilization = (in_use / max_pool_size * 100)
            saturated = utilization > 80.0
        
        analysis[scenario_name] = {
            "max_pool_size": max_pool_size,
            "pool_size": pool_size,
            "available": available,
            "in_use": in_use,
            "approximate": approximate,
            "utilization_percentage": utilization,
            "saturated": saturated,
            "recommendations": []
        }
        
        if utilization is not None and utilization > 80.0:
            analysis[scenario_name]["recommendations"].append(
                f"Connection pool utilization is high ({utilization:.1f}%) - consider increasing pool size"
            )
        elif in_use is None:
            analysis[scenario_name]["recommendations"].append(
                "Connection pool utilization cannot be determined - Motor/pymongo does not expose real-time connection counts"
            )
        
        if max_pool_size == 0:
            analysis[scenario_name]["recommendations"].append(
                "Could not determine pool size - verify MongoDB connection"
            )
    
    return analysis


def generate_comparison_report(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare current results against baseline.
    
    Args:
        baseline: Baseline test results
        current: Current test results
        
    Returns:
        Dictionary with comparison report
    """
    comparison = {
        "baseline_timestamp": baseline.get("timestamp"),
        "current_timestamp": current.get("timestamp"),
        "regressions": [],
        "improvements": [],
        "unchanged": []
    }
    
    # Compare response times
    baseline_rt = analyze_response_times(baseline)
    current_rt = analyze_response_times(current)
    
    for scenario in set(list(baseline_rt.keys()) + list(current_rt.keys())):
        baseline_avg = baseline_rt.get(scenario, {}).get("avg", 0)
        current_avg = current_rt.get(scenario, {}).get("avg", 0)
        
        if baseline_avg > 0 and current_avg > 0:
            change = ((current_avg - baseline_avg) / baseline_avg * 100)
            
            if change > 20:  # >20% slower
                comparison["regressions"].append({
                    "scenario": scenario,
                    "metric": "response_time",
                    "baseline": baseline_avg,
                    "current": current_avg,
                    "change_percentage": change
                })
            elif change < -20:  # >20% faster
                comparison["improvements"].append({
                    "scenario": scenario,
                    "metric": "response_time",
                    "baseline": baseline_avg,
                    "current": current_avg,
                    "change_percentage": change
                })
            else:
                comparison["unchanged"].append({
                    "scenario": scenario,
                    "metric": "response_time"
                })
    
    return comparison


def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations based on analysis.
    
    Args:
        analysis: Complete analysis dictionary
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Response time recommendations
    response_times = analysis.get("response_times", {})
    for scenario, data in response_times.items():
        if data.get("degradation_detected"):
            recommendations.append(
                f"{scenario}: Performance degradation detected - investigate resource contention"
            )
        
        if data.get("outliers_percentage", 0) > 10:
            recommendations.append(
                f"{scenario}: High number of outliers ({data['outliers_percentage']:.1f}%) - check for intermittent issues"
            )
    
    # Cache recommendations
    cache = analysis.get("cache", {})
    for scenario, data in cache.items():
        if data.get("hit_rate", 100) < 50:
            recommendations.append(
                f"{scenario}: Low cache hit rate - consider increasing TTL or cache size"
            )
    
    # Memory recommendations
    memory = analysis.get("memory", {})
    for scenario, data in memory.items():
        if data.get("potential_leak"):
            recommendations.append(
                f"{scenario}: Potential memory leak detected - review memory management"
            )
    
    # Connection pool recommendations
    connection_pool = analysis.get("connection_pool", {})
    for scenario, data in connection_pool.items():
        if data.get("saturated"):
            recommendations.append(
                f"{scenario}: Connection pool saturated - consider increasing pool size"
            )
    
    return recommendations


def export_report(analysis: Dict[str, Any], format: str = "json", output: Optional[str] = None) -> str:
    """Export analysis report in specified format.
    
    Args:
        analysis: Analysis dictionary
        format: Export format (json/markdown/html)
        output: Output file path (optional)
        
    Returns:
        Exported report content
    """
    if format == "json":
        content = json.dumps(analysis, indent=2, default=str)
    elif format == "markdown":
        content = generate_markdown_report(analysis)
    elif format == "html":
        content = generate_html_report(analysis)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    if output:
        with open(output, 'w') as f:
            f.write(content)
        return output
    else:
        return content


def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """Generate Markdown report.
    
    Args:
        analysis: Analysis dictionary
        
    Returns:
        Markdown formatted report
    """
    lines = []
    lines.append("# Load Test Analysis Report")
    lines.append(f"\nGenerated: {datetime.utcnow().isoformat()}\n")
    
    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("\n### Overall Status")
    # Add summary based on analysis
    
    # Response Times
    if "response_times" in analysis:
        lines.append("\n## Response Time Analysis")
        for scenario, data in analysis["response_times"].items():
            lines.append(f"\n### {scenario}")
            lines.append(f"- Average: {data.get('avg', 0):.3f}s")
            lines.append(f"- p95: {data.get('percentiles', {}).get('p95', 0):.3f}s")
            lines.append(f"- Outliers: {data.get('outliers_count', 0)}")
    
    # Cache
    if "cache" in analysis:
        lines.append("\n## Cache Performance")
        for scenario, data in analysis["cache"].items():
            lines.append(f"\n### {scenario}")
            lines.append(f"- Hit Rate: {data.get('hit_rate', 0):.1f}%")
            lines.append(f"- Time Saved: {data.get('time_saved_seconds', 0):.2f}s")
    
    # Recommendations
    recommendations = generate_recommendations(analysis)
    if recommendations:
        lines.append("\n## Recommendations")
        for rec in recommendations:
            lines.append(f"- {rec}")
    
    return "\n".join(lines)


def generate_html_report(analysis: Dict[str, Any]) -> str:
    """Generate HTML report.
    
    Args:
        analysis: Analysis dictionary
        
    Returns:
        HTML formatted report
    """
    # Simple HTML report
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Load Test Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #666; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Load Test Analysis Report</h1>
        <p>Generated: {datetime.utcnow().isoformat()}</p>
        <pre>{json.dumps(analysis, indent=2, default=str)}</pre>
    </body>
    </html>
    """
    return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze load test results")
    parser.add_argument("--results-file", required=True, help="Path to JSON results file")
    parser.add_argument("--baseline-file", help="Path to baseline results file for comparison")
    parser.add_argument("--format", choices=["json", "markdown", "html"], default="markdown", help="Output format")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    # Load results
    results = load_test_results(args.results_file)
    
    # Perform analysis
    analysis = {
        "response_times": analyze_response_times(results),
        "cache": analyze_cache_efficiency(results),
        "rate_limiting": analyze_rate_limiting(results),
        "memory": analyze_memory_usage(results),
        "connection_pool": analyze_connection_pool(results)
    }
    
    # Add recommendations
    analysis["recommendations"] = generate_recommendations(analysis)
    
    # Comparison if baseline provided
    if args.baseline_file:
        baseline = load_test_results(args.baseline_file)
        analysis["comparison"] = generate_comparison_report(baseline, results)
    
    # Export report
    output_path = export_report(analysis, format=args.format, output=args.output)
    
    if args.verbose:
        print(f"Analysis complete. Report saved to: {output_path}")
    else:
        print(output_path)


if __name__ == "__main__":
    main()

