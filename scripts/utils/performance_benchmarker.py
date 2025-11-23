#!/usr/bin/env python3
"""
Performance benchmarking utility for measuring and validating response times.
"""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from statistics import mean, median
import math


class StagePerformance(BaseModel):
    """Model for individual stage performance."""
    stage_name: str = Field(..., description="Stage name")
    duration: float = Field(..., ge=0.0, description="Stage duration in seconds")
    threshold: float = Field(..., ge=0.0, description="Acceptable threshold in seconds")
    status: str = Field(..., description="Performance status (EXCELLENT, GOOD, ACCEPTABLE, SLOW, CRITICAL)")
    percentage_of_threshold: float = Field(..., description="Percentage of threshold used")
    warning: bool = Field(default=False, description="Whether this stage has a warning")


class PerformanceMetrics(BaseModel):
    """Pydantic model for timing metrics and thresholds."""
    total_execution_time: float = Field(..., ge=0.0, description="Total execution time in seconds")
    stages: List[StagePerformance] = Field(..., description="Individual stage performance")
    overall_status: str = Field(..., description="Overall performance status")
    slow_stages: List[str] = Field(default_factory=list, description="List of slow stage names")
    critical_stages: List[str] = Field(default_factory=list, description="List of critical stage names")
    recommendations: List[str] = Field(default_factory=list, description="Performance optimization recommendations")


class PerformanceBenchmarker:
    """Performance benchmarking utility for API responses."""
    
    def __init__(self):
        self.thresholds = {
            "query_processing": 5.0,
            "web_scraping": 120.0,
            "ai_processing": 60.0,
            "database_storage": 10.0,
            "total": 300.0
        }
    
    def set_thresholds(self, thresholds: Dict[str, float]):
        """Set acceptable time limits for each stage.
        
        Args:
            thresholds: Dictionary mapping stage names to time limits in seconds
        """
        self.thresholds.update(thresholds)
    
    def _load_thresholds_from_config(self):
        """Load thresholds from app/core/config.py settings."""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            self.thresholds = {
                "query_processing": getattr(settings, 'agent_timeout_seconds', 5.0),
                "web_scraping": getattr(settings, 'scraper_request_timeout_seconds', 120.0) * 1.0,  # Allow full scraper timeout
                "ai_processing": getattr(settings, 'processing_timeout_seconds', 60.0),
                "database_storage": getattr(settings, 'database_query_timeout_seconds', 10.0),
                "total": getattr(settings, 'api_request_timeout_seconds', 300.0)
            }
        except Exception:
            # Use defaults if config loading fails
            pass
    
    def _categorize_performance(self, duration: float, threshold: float) -> Tuple[str, bool]:
        """Categorize performance based on duration and threshold.
        
        Args:
            duration: Actual duration in seconds
            threshold: Threshold in seconds
            
        Returns:
            Tuple of (status, warning) where status is performance category
        """
        if threshold == 0:
            return ("UNKNOWN", False)
        
        percentage = (duration / threshold) * 100
        
        if percentage < 50:
            return ("EXCELLENT", False)
        elif percentage < 80:
            return ("GOOD", False)
        elif percentage < 100:
            return ("ACCEPTABLE", True)  # Warning threshold
        elif percentage < 120:
            return ("SLOW", True)  # Warning
        else:
            return ("CRITICAL", True)  # Failure threshold
    
    def analyze_response_timing(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze response timing.
        
        Args:
            response_data: Response data from API
            
        Returns:
            Performance report with status, stage breakdowns, and recommendations
        """
        # Load thresholds from config
        self._load_thresholds_from_config()
        
        execution_metadata = response_data.get("execution_metadata", {})
        stages_timing = execution_metadata.get("stages_timing", {})
        execution_time_ms = execution_metadata.get("execution_time_ms", 0)
        total_execution_time = execution_time_ms / 1000.0  # Convert to seconds
        
        stage_performances = []
        slow_stages = []
        critical_stages = []
        recommendations = []
        
        # Analyze each stage
        for stage_name, duration in stages_timing.items():
            threshold = self.thresholds.get(stage_name, 60.0)  # Default 60s if not specified
            status, warning = self._categorize_performance(duration, threshold)
            percentage = (duration / threshold * 100) if threshold > 0 else 0.0
            
            stage_perf = StagePerformance(
                stage_name=stage_name,
                duration=duration,
                threshold=threshold,
                status=status,
                percentage_of_threshold=percentage,
                warning=warning
            )
            stage_performances.append(stage_perf)
            
            if status == "SLOW":
                slow_stages.append(stage_name)
                recommendations.append(f"Stage '{stage_name}' is slow ({duration:.2f}s, {percentage:.1f}% of threshold)")
            elif status == "CRITICAL":
                critical_stages.append(stage_name)
                recommendations.append(f"Stage '{stage_name}' exceeded threshold ({duration:.2f}s > {threshold:.2f}s)")
        
        # Analyze total execution time
        total_threshold = self.thresholds.get("total", 300.0)
        total_status, total_warning = self._categorize_performance(total_execution_time, total_threshold)
        
        if total_warning:
            if total_status == "CRITICAL":
                recommendations.append(f"Total execution time exceeded threshold ({total_execution_time:.2f}s > {total_threshold:.2f}s)")
            else:
                recommendations.append(f"Total execution time is approaching threshold ({total_execution_time:.2f}s, {total_threshold:.2f}s limit)")
        
        # Determine overall status
        if critical_stages:
            overall_status = "FAIL"
        elif slow_stages:
            overall_status = "WARN"
        elif total_status == "CRITICAL":
            overall_status = "FAIL"
        elif total_status == "SLOW" or total_warning:
            overall_status = "WARN"
        else:
            overall_status = "PASS"
        
        # Add optimization recommendations
        if slow_stages or critical_stages:
            recommendations.append("Consider optimizing slow stages or increasing timeout thresholds")
        
        if total_execution_time > total_threshold * 0.8:
            recommendations.append("Total execution time is high - consider optimizing workflow or increasing timeout")
        
        return {
            "overall_status": overall_status,
            "total_execution_time": total_execution_time,
            "total_threshold": total_threshold,
            "total_status": total_status,
            "stages": [stage.model_dump() for stage in stage_performances],
            "slow_stages": slow_stages,
            "critical_stages": critical_stages,
            "recommendations": recommendations
        }
    
    def calculate_stage_percentiles(self, stage_timings: List[float]) -> Dict[str, float]:
        """Calculate timing percentiles.
        
        Args:
            stage_timings: List of timing values for a stage
            
        Returns:
            Dictionary with p50, p90, p95, p99 percentiles
        """
        if not stage_timings:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_timings = sorted(stage_timings)
        n = len(sorted_timings)
        
        def percentile(p: float) -> float:
            """Calculate percentile value."""
            if n == 0:
                return 0.0
            index = (p / 100.0) * (n - 1)
            lower = math.floor(index)
            upper = math.ceil(index)
            weight = index - lower
            
            if upper >= n:
                return sorted_timings[-1]
            
            return sorted_timings[lower] * (1 - weight) + sorted_timings[upper] * weight
        
        return {
            "p50": percentile(50),
            "p90": percentile(90),
            "p95": percentile(95),
            "p99": percentile(99)
        }
    
    def generate_performance_report(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive performance report from multiple test runs.
        
        Args:
            test_results: List of test result dictionaries with execution_metadata
            
        Returns:
            Comprehensive performance report with aggregated statistics
        """
        if not test_results:
            return {
                "error": "No test results provided",
                "summary": {}
            }
        
        # Aggregate timing data by stage
        stage_data = {}
        total_times = []
        
        for result in test_results:
            execution_metadata = result.get("execution_metadata", {})
            stages_timing = execution_metadata.get("stages_timing", {})
            execution_time_ms = execution_metadata.get("execution_time_ms", 0)
            total_time = execution_time_ms / 1000.0
            total_times.append(total_time)
            
            for stage_name, duration in stages_timing.items():
                if stage_name not in stage_data:
                    stage_data[stage_name] = []
                stage_data[stage_name].append(duration)
        
        # Calculate statistics for each stage
        stage_statistics = {}
        for stage_name, timings in stage_data.items():
            if timings:
                percentiles = self.calculate_stage_percentiles(timings)
                stage_statistics[stage_name] = {
                    "count": len(timings),
                    "min": min(timings),
                    "max": max(timings),
                    "mean": mean(timings),
                    "median": median(timings),
                    "percentiles": percentiles
                }
        
        # Calculate total execution time statistics
        total_statistics = {}
        if total_times:
            percentiles = self.calculate_stage_percentiles(total_times)
            total_statistics = {
                "count": len(total_times),
                "min": min(total_times),
                "max": max(total_times),
                "mean": mean(total_times),
                "median": median(total_times),
                "percentiles": percentiles
            }
        
        # Identify outliers (values > p95)
        outliers = {}
        for stage_name, stats in stage_statistics.items():
            p95 = stats["percentiles"]["p95"]
            outliers[stage_name] = [t for t in stage_data[stage_name] if t > p95]
        
        # Generate recommendations
        recommendations = []
        for stage_name, stats in stage_statistics.items():
            threshold = self.thresholds.get(stage_name, 60.0)
            if stats["mean"] > threshold * 0.8:
                recommendations.append(
                    f"Stage '{stage_name}' average time ({stats['mean']:.2f}s) is high relative to threshold ({threshold:.2f}s)"
                )
            if stats["max"] > threshold:
                recommendations.append(
                    f"Stage '{stage_name}' maximum time ({stats['max']:.2f}s) exceeds threshold ({threshold:.2f}s)"
                )
        
        return {
            "summary": {
                "total_runs": len(test_results),
                "stages_analyzed": list(stage_statistics.keys())
            },
            "stage_statistics": stage_statistics,
            "total_execution_statistics": total_statistics,
            "outliers": {k: len(v) for k, v in outliers.items()},
            "recommendations": recommendations
        }
    
    def compare_against_baseline(
        self, 
        current_timing: Dict[str, float], 
        baseline_timing: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compare current timing against baseline.
        
        Args:
            current_timing: Current stage timings dictionary
            baseline_timing: Baseline stage timings dictionary
            
        Returns:
            Comparison report with percentage differences and regressions
        """
        comparisons = {}
        regressions = []
        improvements = []
        
        for stage_name in set(list(current_timing.keys()) + list(baseline_timing.keys())):
            current = current_timing.get(stage_name, 0.0)
            baseline = baseline_timing.get(stage_name, 0.0)
            
            if baseline == 0:
                percentage_diff = 0.0 if current == 0 else 100.0
            else:
                percentage_diff = ((current - baseline) / baseline) * 100
            
            comparisons[stage_name] = {
                "current": current,
                "baseline": baseline,
                "difference": current - baseline,
                "percentage_diff": percentage_diff
            }
            
            # Identify regressions (>20% slower)
            if percentage_diff > 20:
                regressions.append({
                    "stage": stage_name,
                    "current": current,
                    "baseline": baseline,
                    "regression": percentage_diff
                })
            
            # Identify improvements (>20% faster)
            elif percentage_diff < -20:
                improvements.append({
                    "stage": stage_name,
                    "current": current,
                    "baseline": baseline,
                    "improvement": abs(percentage_diff)
                })
        
        return {
            "comparisons": comparisons,
            "regressions": regressions,
            "improvements": improvements,
            "has_regressions": len(regressions) > 0,
            "has_improvements": len(improvements) > 0
        }

