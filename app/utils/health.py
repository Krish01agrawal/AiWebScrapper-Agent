"""
Comprehensive health check utilities for monitoring system components.
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.core.database import get_database
from app.core.gemini import get_gemini_model
from app.core.cache import get_cache


logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    last_check: datetime = field(default_factory=datetime.utcnow)


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self, timeout_seconds: int = 10):
        """Initialize health checker."""
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    async def check_database(self) -> ComponentHealth:
        """Check MongoDB connection and basic operations."""
        start_time = time.time()
        
        try:
            db = get_database()
            
            # Ping database
            await asyncio.wait_for(db.command("ping"), timeout=self.timeout_seconds)
            
            # Check collections exist
            collections = await db.list_collection_names()
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "collections": len(collections),
                    "collection_names": collections[:5]  # Show first 5 collections
                }
            )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message="Database ping timed out"
            )
        
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Database error: {str(e)}"
            )
    
    async def check_gemini(self) -> ComponentHealth:
        """Check Gemini API connectivity."""
        start_time = time.time()
        
        try:
            model = get_gemini_model()
            if not model:
                return ComponentHealth(
                    name="gemini_api",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="Gemini model not initialized"
                )
            
            # Simple test query
            test_response = await asyncio.wait_for(
                model.generate_content_async("test"),
                timeout=self.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "model_available": True,
                    "test_response_length": len(test_response.text) if test_response.text else 0
                }
            )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message="Gemini API request timed out"
            )
        
        except Exception as e:
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Gemini API error: {str(e)}"
            )
    
    async def check_cache(self) -> ComponentHealth:
        """Check cache system."""
        start_time = time.time()
        
        try:
            cache = get_cache()
            if not cache:
                return ComponentHealth(
                    name="cache",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="Cache not initialized"
                )
            
            # Test cache operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            await cache.set(test_key, test_value, ttl=10)
            retrieved_value = await cache.get(test_key)
            await cache.delete(test_key)
            
            if retrieved_value != test_value:
                raise ValueError("Cache test failed - value mismatch")
            
            stats = await cache.get_stats()
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="cache",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details=stats
            )
        
        except Exception as e:
            return ComponentHealth(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Cache error: {str(e)}"
            )
    
    def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            if not PSUTIL_AVAILABLE:
                return ComponentHealth(
                    name="system_resources",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="psutil not available - system metrics disabled"
                )
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
                status = HealthStatus.DEGRADED
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                response_time_ms=(time.time() - start_time) * 1000,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024 * 1024 * 1024)
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"System resource check error: {str(e)}"
            )
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return aggregated status."""
        try:
            # Run async checks in parallel
            checks = await asyncio.gather(
                self.check_database(),
                self.check_gemini(),
                self.check_cache(),
                return_exceptions=True
            )
            
            # Add system resources check (synchronous)
            checks.append(self.check_system_resources())
            
            # Process results
            component_results = {}
            overall_status = HealthStatus.HEALTHY
            
            for check in checks:
                if isinstance(check, Exception):
                    overall_status = HealthStatus.UNHEALTHY
                    self.logger.error(f"Health check exception: {check}")
                    continue
                
                component_results[check.name] = {
                    "status": check.status,
                    "response_time_ms": check.response_time_ms,
                    "message": check.message,
                    "details": check.details,
                    "last_check": check.last_check.isoformat()
                }
                
                # Update overall status
                if check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            
            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "components": component_results,
                "uptime_seconds": time.time() - self.start_time
            }
        
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "uptime_seconds": time.time() - self.start_time
            }
    
    async def readiness_check(self) -> bool:
        """Check if application is ready to serve requests."""
        try:
            db_health = await self.check_database()
            return db_health.status != HealthStatus.UNHEALTHY
        except Exception:
            return False
    
    async def liveness_check(self) -> bool:
        """Check if application is alive."""
        return True  # If this code runs, app is alive


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def initialize_health_checker(timeout_seconds: int = 10) -> HealthChecker:
    """Initialize global health checker."""
    global _health_checker
    _health_checker = HealthChecker(timeout_seconds=timeout_seconds)
    return _health_checker
