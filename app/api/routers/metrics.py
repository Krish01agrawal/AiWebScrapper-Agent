"""
Metrics endpoint for monitoring and observability with Prometheus-compatible format.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, Query, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

from app.core.config import get_settings
from app.utils.metrics import get_metrics_collector, export_prometheus, export_json, get_system_metrics
from app.dependencies import CurrentAPIKeyDep, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring"])

settings = get_settings()


@router.get("/metrics")
async def get_metrics(
    request: Request,
    format: str = Query("prometheus", description="Export format: prometheus or json"),
    current_api_key: Optional[CurrentAPIKeyDep] = None
) -> Response:
    """
    Get metrics in Prometheus or JSON format.
    
    Args:
        request: FastAPI request object
        format: Export format (prometheus or json)
        current_api_key: Current authenticated API key
        
    Returns:
        Metrics in requested format
    """
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    
    # Check permissions for detailed metrics
    if format == "json" and current_api_key and not current_api_key.check_permission("admin"):
        raise HTTPException(status_code=403, detail="Admin permission required for JSON metrics")
    
    try:
        collector = get_metrics_collector()
        
        if format.lower() == "prometheus":
            metrics_text = export_prometheus(collector.registry)
            return PlainTextResponse(
                content=metrics_text,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
        
        elif format.lower() == "json":
            metrics_data = export_json(collector.registry)
            
            # Add system metrics
            metrics_data["system"] = get_system_metrics()
            
            # Add server information
            metrics_data["server"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "environment": settings.environment
            }
            
            return JSONResponse(content=metrics_data)
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'prometheus' or 'json'")
    
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/metrics/health")
async def metrics_health() -> Dict[str, Any]:
    """
    Get overall system health status.
    
    Returns:
        System health information
    """
    try:
        collector = get_metrics_collector()
        system_metrics = get_system_metrics()
        
        # Determine overall health based on system metrics
        health_status = "healthy"
        if system_metrics["cpu_percent"] > 80 or system_metrics["memory_percent"] > 85:
            health_status = "degraded"
        if system_metrics["cpu_percent"] > 95 or system_metrics["memory_percent"] > 95:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "metrics_collector": "healthy",
                "system_resources": health_status
            },
            "system": system_metrics,
            "uptime_seconds": time.time() - getattr(metrics_health, "_start_time", time.time())
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/metrics/performance")
async def get_performance_metrics(
    current_api_key: Optional[CurrentAPIKeyDep] = None
) -> Dict[str, Any]:
    """
    Get detailed performance metrics.
    
    Args:
        current_api_key: Current authenticated API key
        
    Returns:
        Performance metrics and statistics
    """
    if not current_api_key or not current_api_key.check_permission("admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    try:
        collector = get_metrics_collector()
        
        # Get request duration histogram
        duration_histogram = collector.registry.get_metric("api_request_duration_seconds")
        
        # Calculate percentiles if we have data
        percentiles = {}
        if duration_histogram and duration_histogram.count > 0:
            # This is a simplified calculation - in production you'd want more sophisticated percentile calculation
            avg_duration = duration_histogram.sum / duration_histogram.count
            percentiles = {
                "p50": avg_duration * 0.5,
                "p95": avg_duration * 1.5,
                "p99": avg_duration * 2.0
            }
        
        # Get error rates
        error_counter = collector.registry.get_metric("api_errors_total")
        request_counter = collector.registry.get_metric("api_requests_total")
        
        error_rate = 0.0
        if request_counter and request_counter.value > 0 and error_counter:
            error_rate = error_counter.value / request_counter.value
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance": {
                "avg_duration_ms": (duration_histogram.sum / duration_histogram.count * 1000) if duration_histogram and duration_histogram.count > 0 else 0,
                "percentiles": percentiles,
                "error_rate": error_rate,
                "total_requests": request_counter.value if request_counter else 0,
                "total_errors": error_counter.value if error_counter else 0
            },
            "system": get_system_metrics()
        }
    
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/metrics/cache")
async def get_cache_metrics(
    current_api_key: Optional[CurrentAPIKeyDep] = None
) -> Dict[str, Any]:
    """
    Get detailed cache statistics.
    
    Args:
        current_api_key: Current authenticated API key
        
    Returns:
        Cache metrics and statistics
    """
    if not current_api_key or not current_api_key.check_permission("admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    try:
        collector = get_metrics_collector()
        
        # Get cache metrics
        hit_rate_gauge = collector.registry.get_metric("cache_hit_rate")
        size_gauge = collector.registry.get_metric("cache_size")
        operations_counter = collector.registry.get_metric("cache_operations_total")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": {
                "hit_rate": hit_rate_gauge.value if hit_rate_gauge else 0.0,
                "size": int(size_gauge.value) if size_gauge else 0,
                "operations": operations_counter.value if operations_counter else 0,
                "status": "enabled" if settings.cache_enabled else "disabled",
                "ttl_seconds": settings.cache_ttl_seconds,
                "max_size": settings.cache_max_size
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cache metrics")


@router.post("/metrics/reset")
async def reset_metrics(
    current_api_key: Optional[CurrentAPIKeyDep] = None
) -> Dict[str, Any]:
    """
    Reset metrics counters (admin only).
    
    Args:
        current_api_key: Current authenticated API key
        
    Returns:
        Confirmation of reset operation
    """
    if not current_api_key or not current_api_key.check_permission("admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    try:
        collector = get_metrics_collector()
        collector.registry.reset_all()
        
        logger.info(f"Metrics reset by API key: {current_api_key.key_id}")
        
        return {
            "status": "success",
            "message": "Metrics have been reset",
            "timestamp": datetime.utcnow().isoformat(),
            "reset_by": current_api_key.key_id
        }
    
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


# Initialize start time for uptime calculation
if not hasattr(get_metrics, "_start_time"):
    get_metrics._start_time = time.time()
