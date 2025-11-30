#!/usr/bin/env python3
"""
Load test monitoring utilities for tracking system resources during load tests.
"""
import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LoadTestMetrics(BaseModel):
    """Pydantic model for structured load test metrics."""
    total_requests: int = Field(..., description="Total number of requests sent")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    response_times: List[float] = Field(default_factory=list, description="List of response times in seconds")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    rate_limit_hits: int = Field(default=0, description="Number of rate limit violations (429)")
    memory_stats: Dict[str, Any] = Field(default_factory=dict, description="Memory usage statistics")
    connection_pool_stats: Dict[str, Any] = Field(default_factory=dict, description="Connection pool statistics")
    start_time: datetime = Field(..., description="Test start time")
    end_time: Optional[datetime] = Field(None, description="Test end time")
    duration_seconds: float = Field(default=0.0, description="Test duration in seconds")


class MemoryMonitor:
    """Monitor memory usage during load tests."""
    
    def __init__(self):
        """Initialize memory monitor."""
        self.process = psutil.Process()
        self.monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.memory_samples: List[Dict[str, Any]] = []
        self.start_memory: Optional[Dict[str, Any]] = None
        self.peak_memory: Optional[Dict[str, Any]] = None
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start background memory monitoring.
        
        Args:
            interval: Sampling interval in seconds
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.start_memory = self.get_current_stats()
        self.peak_memory = self.start_memory.copy()
        self.memory_samples = []
        
        async def _monitor_loop():
            while self.monitoring:
                stats = self.get_current_stats()
                self.memory_samples.append(stats)
                
                # Update peak memory
                if stats["rss_mb"] > self.peak_memory["rss_mb"]:
                    self.peak_memory = stats.copy()
                
                await asyncio.sleep(interval)
        
        self.monitoring_task = asyncio.create_task(_monitor_loop())
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        self.monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            # Don't call run_until_complete here - it will raise RuntimeError
            # if called from within an active event loop. The task will be
            # cancelled and cleaned up by the event loop automatically.
        
        end_memory = self.get_current_stats()
        
        # Calculate statistics
        if self.memory_samples:
            rss_values = [s["rss_mb"] for s in self.memory_samples]
            vms_values = [s["vms_mb"] for s in self.memory_samples]
            percent_values = [s["percent"] for s in self.memory_samples]
            
            return {
                "start": self.start_memory,
                "end": end_memory,
                "peak": self.peak_memory,
                "avg_rss_mb": sum(rss_values) / len(rss_values),
                "avg_vms_mb": sum(vms_values) / len(vms_values),
                "avg_percent": sum(percent_values) / len(percent_values),
                "min_rss_mb": min(rss_values),
                "max_rss_mb": max(rss_values),
                "samples": len(self.memory_samples),
                "memory_growth_mb": end_memory["rss_mb"] - self.start_memory["rss_mb"],
                "peak_memory_mb": self.peak_memory["rss_mb"]
            }
        else:
            return {
                "start": self.start_memory,
                "end": end_memory,
                "peak": self.peak_memory,
                "memory_growth_mb": end_memory["rss_mb"] - self.start_memory["rss_mb"] if self.start_memory else 0
            }
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current memory snapshot.
        
        Returns:
            Dictionary with current memory statistics
        """
        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()
        
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),  # Resident Set Size in MB
            "vms_mb": mem_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
            "percent": mem_percent,
            "timestamp": time.time()
        }
    
    def get_peak_usage(self) -> Dict[str, Any]:
        """Get peak memory usage during monitoring.
        
        Returns:
            Dictionary with peak memory statistics
        """
        return self.peak_memory or self.get_current_stats()


class ConnectionPoolMonitor:
    """Monitor MongoDB connection pool metrics."""
    
    def __init__(self):
        """Initialize connection pool monitor."""
        self.client = None
        self.pool_samples: List[Dict[str, Any]] = []
    
    def set_client(self, client):
        """Set MongoDB client for monitoring.
        
        Args:
            client: Motor AsyncIOMotorClient instance
        """
        self.client = client
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        if not self.client:
            return {
                "error": "MongoDB client not set",
                "pool_size": 0,
                "available": None,
                "in_use": None,
                "approximate": False
            }
        
        try:
            # Motor doesn't expose pool stats directly, so we use a workaround
            # by checking the underlying pymongo client
            pymongo_client = self.client.delegate if hasattr(self.client, 'delegate') else self.client
            
            # Get pool information from pymongo
            pool_options = getattr(pymongo_client, '_topology_settings', None)
            if pool_options:
                max_pool_size = getattr(pool_options, 'max_pool_size', 0)
            else:
                max_pool_size = 0
            
            # Try to get active connections (this is approximate)
            # Motor/pymongo doesn't expose exact connection counts easily
            # Set in_use and available to None since they cannot be reliably determined
            return {
                "max_pool_size": max_pool_size,
                "pool_size": max_pool_size,  # Approximate
                "available": None,  # Cannot be determined reliably
                "in_use": None,  # Cannot be determined reliably
                "approximate": True,  # Flag indicating values are approximate
                "status": "active"
            }
        except Exception as e:
            return {
                "error": str(e),
                "pool_size": 0,
                "available": None,
                "in_use": None,
                "approximate": False,
                "status": "error"
            }
    
    async def monitor_during_load(self, duration: float, interval: float = 1.0) -> List[Dict[str, Any]]:
        """Monitor pool stats during load test.
        
        Args:
            duration: Monitoring duration in seconds
            interval: Sampling interval in seconds
            
        Returns:
            List of pool stat samples
        """
        self.pool_samples = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            stats = self.get_pool_stats()
            stats["timestamp"] = time.time()
            self.pool_samples.append(stats)
            await asyncio.sleep(interval)
        
        return self.pool_samples
    
    def analyze_pool_behavior(self) -> Dict[str, Any]:
        """Analyze connection pool behavior and provide recommendations.
        
        Returns:
            Dictionary with analysis and recommendations
        """
        if not self.pool_samples:
            return {
                "status": "no_data",
                "recommendations": ["No pool data collected"]
            }
        
        # Analyze pool utilization
        max_pool_sizes = [s.get("max_pool_size", 0) for s in self.pool_samples]
        avg_pool_size = sum(max_pool_sizes) / len(max_pool_sizes) if max_pool_sizes else 0
        
        # Check for errors
        errors = [s for s in self.pool_samples if "error" in s]
        
        recommendations = []
        
        if errors:
            recommendations.append("Connection pool errors detected - check MongoDB connectivity")
        
        if avg_pool_size > 0:
            # Check if pool might be saturated (if we had in_use data)
            recommendations.append(f"Current max pool size: {int(avg_pool_size)}")
            recommendations.append("Consider monitoring connection wait times for saturation")
        
        return {
            "status": "analyzed",
            "samples": len(self.pool_samples),
            "avg_pool_size": avg_pool_size,
            "errors": len(errors),
            "recommendations": recommendations
        }


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate percentiles from a list of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Dictionary with p50, p90, p95, p99 percentiles
    """
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    def percentile(p: float) -> float:
        """Calculate percentile value."""
        if n == 0:
            return 0.0
        index = (p / 100.0) * (n - 1)
        lower = int(index)
        upper = min(int(index) + 1, n - 1)
        weight = index - lower
        
        if upper >= n:
            return sorted_values[-1]
        
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    
    return {
        "p50": percentile(50),
        "p90": percentile(90),
        "p95": percentile(95),
        "p99": percentile(99)
    }


def format_memory_size(bytes: int) -> str:
    """Format memory size in human-readable format.
    
    Args:
        bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def generate_load_test_report(metrics: LoadTestMetrics) -> Dict[str, Any]:
    """Generate formatted load test report.
    
    Args:
        metrics: LoadTestMetrics instance
        
    Returns:
        Dictionary with formatted report
    """
    # Calculate response time statistics
    response_times = metrics.response_times
    percentiles = calculate_percentiles(response_times) if response_times else {}
    
    # Calculate cache hit rate
    total_cache_requests = metrics.cache_hits + metrics.cache_misses
    cache_hit_rate = (metrics.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0
    
    # Calculate success rate
    success_rate = (metrics.successful_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0.0
    
    report = {
        "summary": {
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "success_rate": success_rate,
            "duration_seconds": metrics.duration_seconds
        },
        "response_times": {
            "values": response_times,  # Store raw response times for percentile/degradation analysis
            "count": len(response_times),
            "min": min(response_times) if response_times else 0.0,
            "max": max(response_times) if response_times else 0.0,
            "avg": sum(response_times) / len(response_times) if response_times else 0.0,
            "percentiles": percentiles
        },
        "cache": {
            "hits": metrics.cache_hits,
            "misses": metrics.cache_misses,
            "hit_rate": cache_hit_rate
        },
        "rate_limiting": {
            "rate_limit_hits": metrics.rate_limit_hits,
            "rate_limit_percentage": (metrics.rate_limit_hits / metrics.total_requests * 100) if metrics.total_requests > 0 else 0.0
        },
        "memory": metrics.memory_stats,
        "connection_pool": metrics.connection_pool_stats,
        "timestamps": {
            "start": metrics.start_time.isoformat(),
            "end": metrics.end_time.isoformat() if metrics.end_time else None
        }
    }
    
    return report

