"""
Utilities for metrics collection, aggregation, and export.
"""

import threading
import time
import collections
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class MetricType(str, Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class Counter:
    """Counter metric for counting events."""
    name: str
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def inc(self, amount: int = 1):
        """Increment counter by amount."""
        self.value += amount
    
    def reset(self):
        """Reset counter to zero."""
        self.value = 0


@dataclass
class Gauge:
    """Gauge metric for measuring values that can go up and down."""
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def set(self, value: float):
        """Set gauge value."""
        self.value = value
    
    def inc(self, amount: float = 1.0):
        """Increment gauge by amount."""
        self.value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class Histogram:
    """Histogram metric for measuring distributions."""
    name: str
    buckets: List[float]
    counts: List[int] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def __post_init__(self):
        """Initialize counts list."""
        if not self.counts:
            self.counts = [0] * len(self.buckets)
    
    def observe(self, value: float):
        """Observe a value in the histogram."""
        self.sum += value
        self.count += 1
        
        for i, bucket in enumerate(self.buckets):
            if value <= bucket:
                self.counts[i] += 1


class MetricsRegistry:
    """Registry for storing and managing metrics."""
    
    def __init__(self):
        """Initialize metrics registry."""
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register_counter(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Counter:
        """Register a counter metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            counter = Counter(name=name, description=description, labels=labels or {})
            self._metrics[name] = counter
            return counter
    
    def register_gauge(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Register a gauge metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            gauge = Gauge(name=name, description=description, labels=labels or {})
            self._metrics[name] = gauge
            return gauge
    
    def register_histogram(self, name: str, buckets: List[float], description: str = "", labels: Optional[Dict[str, str]] = None) -> Histogram:
        """Register a histogram metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            histogram = Histogram(name=name, buckets=buckets, description=description, labels=labels or {})
            self._metrics[name] = histogram
            return histogram
    
    def get_metric(self, name: str) -> Optional[Any]:
        """Get metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def get_all_metrics(self) -> List[Any]:
        """Get all registered metrics."""
        with self._lock:
            return list(self._metrics.values())
    
    def reset_all(self):
        """Reset all metrics."""
        with self._lock:
            for metric in self._metrics.values():
                if isinstance(metric, Counter):
                    metric.reset()
                elif isinstance(metric, Gauge):
                    metric.set(0.0)
                elif isinstance(metric, Histogram):
                    metric.counts = [0] * len(metric.buckets)
                    metric.sum = 0.0
                    metric.count = 0


class MetricsCollector:
    """Singleton metrics collector for global metrics collection."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize metrics collector."""
        if self._initialized:
            return
        
        self.registry = MetricsRegistry()
        self._setup_default_metrics()
        self._initialized = True
    
    def _setup_default_metrics(self):
        """Set up default metrics."""
        # API metrics
        self.registry.register_counter(
            "api_requests_total",
            "Total number of API requests",
            {"endpoint": "", "method": "", "status": ""}
        )
        
        self.registry.register_histogram(
            "api_request_duration_seconds",
            [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            "Request duration in seconds",
            {"endpoint": "", "method": ""}
        )
        
        self.registry.register_counter(
            "api_errors_total",
            "Total number of API errors",
            {"endpoint": "", "error_type": ""}
        )
        
        # Cache metrics
        self.registry.register_counter(
            "cache_operations_total",
            "Total cache operations",
            {"operation": "", "result": ""}
        )
        
        self.registry.register_gauge(
            "cache_hit_rate",
            "Cache hit rate (0-1)"
        )
        
        self.registry.register_gauge(
            "cache_size",
            "Current cache size"
        )
        
        # Authentication metrics
        self.registry.register_counter(
            "auth_requests_total",
            "Total authentication requests",
            {"result": ""}
        )
        
        self.registry.register_gauge(
            "active_requests",
            "Number of active requests"
        )
    
    def record_request(self, endpoint: str, method: str, status_code: int):
        """Record API request."""
        counter = self.registry.get_metric("api_requests_total")
        if counter:
            counter.labels = {"endpoint": endpoint, "method": method, "status": str(status_code)}
            counter.inc()
    
    def record_duration(self, endpoint: str, method: str, duration_seconds: float):
        """Record request duration."""
        histogram = self.registry.get_metric("api_request_duration_seconds")
        if histogram:
            histogram.labels = {"endpoint": endpoint, "method": method}
            histogram.observe(duration_seconds)
    
    def record_error(self, endpoint: str, error_type: str):
        """Record error."""
        counter = self.registry.get_metric("api_errors_total")
        if counter:
            counter.labels = {"endpoint": endpoint, "error_type": error_type}
            counter.inc()
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation."""
        counter = self.registry.get_metric("cache_operations_total")
        if counter:
            counter.labels = {"operation": operation, "result": result}
            counter.inc()
    
    def update_cache_hit_rate(self, hit_rate: float):
        """Update cache hit rate."""
        gauge = self.registry.get_metric("cache_hit_rate")
        if gauge:
            gauge.set(hit_rate)
    
    def update_cache_size(self, size: int):
        """Update cache size."""
        gauge = self.registry.get_metric("cache_size")
        if gauge:
            gauge.set(float(size))
    
    def record_auth_request(self, result: str):
        """Record authentication request."""
        counter = self.registry.get_metric("auth_requests_total")
        if counter:
            counter.labels = {"result": result}
            counter.inc()
    
    def update_active_requests(self, count: int):
        """Update active requests count."""
        gauge = self.registry.get_metric("active_requests")
        if gauge:
            gauge.set(float(count))


def export_prometheus(registry: MetricsRegistry) -> str:
    """Export metrics in Prometheus text format."""
    lines = []
    
    for metric in registry.get_all_metrics():
        if isinstance(metric, Counter):
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} counter")
            label_str = format_labels(metric.labels)
            lines.append(f"{metric.name}{label_str} {metric.value}")
        
        elif isinstance(metric, Gauge):
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} gauge")
            label_str = format_labels(metric.labels)
            lines.append(f"{metric.name}{label_str} {metric.value}")
        
        elif isinstance(metric, Histogram):
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} histogram")
            
            label_str = format_labels(metric.labels)
            
            # Bucket counts
            for i, bucket in enumerate(metric.buckets):
                lines.append(f"{metric.name}_bucket{{le=\"{bucket}\"}}{label_str} {metric.counts[i]}")
            
            # Sum and count
            lines.append(f"{metric.name}_sum{label_str} {metric.sum}")
            lines.append(f"{metric.name}_count{label_str} {metric.count}")
    
    return "\n".join(lines)


def export_json(registry: MetricsRegistry) -> Dict[str, Any]:
    """Export metrics in JSON format."""
    metrics = {}
    
    for metric in registry.get_all_metrics():
        metric_data = {
            "type": type(metric).__name__.lower(),
            "description": metric.description,
            "labels": metric.labels,
            "timestamp": time.time()
        }
        
        if isinstance(metric, Counter):
            metric_data["value"] = metric.value
        
        elif isinstance(metric, Gauge):
            metric_data["value"] = metric.value
        
        elif isinstance(metric, Histogram):
            metric_data.update({
                "sum": metric.sum,
                "count": metric.count,
                "buckets": dict(zip(metric.buckets, metric.counts))
            })
        
        metrics[metric.name] = metric_data
    
    return {
        "timestamp": time.time(),
        "metrics": metrics
    }


def format_labels(labels: Dict[str, str]) -> str:
    """Format labels for Prometheus."""
    if not labels:
        return ""
    
    label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
    return "{" + ",".join(label_pairs) + "}"


def sanitize_metric_name(name: str) -> str:
    """Ensure valid metric names."""
    # Replace invalid characters with underscores
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_:]', '_', name)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    
    return sanitized


def calculate_percentiles(values: List[float], percentiles: List[float]) -> Dict[str, float]:
    """Calculate percentiles from list of values."""
    if not values:
        return {f"p{int(p)}": 0.0 for p in percentiles}
    
    sorted_values = sorted(values)
    result = {}
    
    for p in percentiles:
        index = int(len(sorted_values) * p / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        result[f"p{int(p)}"] = sorted_values[index]
    
    return result


def get_system_metrics() -> Dict[str, float]:
    """Get system resource metrics."""
    try:
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_percent": psutil.disk_usage('/').percent,
            "disk_free_gb": psutil.disk_usage('/').free / (1024 * 1024 * 1024)
        }
    except ImportError:
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_available_mb": 0.0,
            "disk_percent": 0.0,
            "disk_free_gb": 0.0
        }


# Global metrics collector instance
def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    return MetricsCollector()
