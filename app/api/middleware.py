"""
API middleware for request processing and monitoring.
"""
import json
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.utils.response import format_error_response
from app.core.auth import APIKeyManager, get_api_key_manager
from app.utils.logging import log_api_request, LogContext
from app.utils.metrics import get_metrics_collector
from app.core.cache import get_cache


logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware."""
    
    def __init__(self, app: ASGIApp, api_key_manager: Optional[APIKeyManager] = None):
        super().__init__(app)
        self.settings = get_settings()
        self.api_key_manager = api_key_manager or get_api_key_manager()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with authentication."""
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Skip authentication if disabled
        if not getattr(self.settings, 'api_auth_enabled', False):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("x-api-key")
        
        if not api_key:
            error_response = format_error_response(
                error_code="AUTHENTICATION_REQUIRED",
                message="API key required",
                status_code=401
            )
            return JSONResponse(content=error_response, status_code=401)
        
        # Validate API key
        if not self.api_key_manager:
            logger.error("API key manager not initialized")
            error_response = format_error_response(
                error_code="AUTHENTICATION_ERROR",
                message="Authentication service unavailable",
                status_code=503
            )
            return JSONResponse(content=error_response, status_code=503)
        
        api_key_obj = self.api_key_manager.validate_key(api_key)
        if not api_key_obj:
            error_response = format_error_response(
                error_code="INVALID_API_KEY",
                message="Invalid API key",
                status_code=401
            )
            return JSONResponse(content=error_response, status_code=401)
        
        # Record request for rate limiting (actual rate limiting handled by RateLimitingMiddleware)
        self.api_key_manager.record_request(api_key_obj.key_id)
        
        # Attach API key to request state
        request.state.api_key = api_key_obj
        
        # Process request
        response = await call_next(request)
        
        # Add authentication headers
        response.headers["x-authenticated"] = "true"
        response.headers["x-key-id"] = api_key_obj.key_id
        
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        public_endpoints = getattr(self.settings, 'api_public_endpoints', [
            "/health", "/docs", "/redoc", "/openapi.json", "/"
        ])
        return any(path.startswith(endpoint) for endpoint in public_endpoints)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Comprehensive request/response logging with timing and metadata."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with comprehensive logging."""
        # Skip logging for health checks and static files
        if self._should_skip_logging(request.url.path):
            return await call_next(request)
        
        # Generate request ID if not present
        request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex[:8]}")
        
        # Start timing
        start_time = time.time()
        
        # Extract request metadata
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get authentication context
        api_key_id = None
        if hasattr(request.state, 'api_key') and request.state.api_key:
            api_key_id = request.state.api_key.key_id
        
        # Use structured logging context
        with LogContext(
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            api_key_id=api_key_id
        ) as log_adapter:
            # Log request start
            if getattr(self.settings, 'api_enable_request_logging', True):
                log_adapter.info(
                    f"Request started: {request.method} {request.url.path}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": str(request.query_params),
                        "authenticated": api_key_id is not None
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Calculate timing
        duration = time.time() - start_time
        
        # Log API request with structured logging
        log_api_request(
            logger,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            request_id=request_id,
            api_key_id=api_key_id,
            client_ip=client_ip,
            user_agent=user_agent,
            cache_status=response.headers.get("x-cache-status", "N/A")
        )
        
        # Add response headers
        response.headers["x-request-id"] = request_id
        
        return response
    
    def _should_skip_logging(self, path: str) -> bool:
        """Determine if request should be skipped from detailed logging."""
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling and consistent error response formatting."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.metrics_collector = get_metrics_collector()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle errors and format responses consistently."""
        try:
            response = await call_next(request)
            return response
        
        except Exception as e:
            # Re-raise FastAPI validation errors and HTTP exceptions to preserve their status codes
            from fastapi.exceptions import RequestValidationError
            from starlette.exceptions import HTTPException as StarletteHTTPException
            
            if isinstance(e, (RequestValidationError, StarletteHTTPException)):
                raise e
            
            # Get request context for error logging
            request_id = request.headers.get("x-request-id", "unknown")
            api_key_id = None
            if hasattr(request.state, 'api_key') and request.state.api_key:
                api_key_id = request.state.api_key.key_id
            
            # Log the error with structured logging
            logger.error(
                f"Unhandled error in {request.url.path}: {str(e)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "api_key_id": api_key_id,
                    "error_type": type(e).__name__
                }
            )
            
            # Record error in metrics collector
            self.metrics_collector.record_error(
                endpoint=request.url.path,
                error_type=type(e).__name__
            )
            
            # Determine error details based on exception type
            if isinstance(e, ValueError):
                error_code = "VALIDATION_ERROR"
                status_code = 400
                message = "Invalid input provided"
            elif isinstance(e, TimeoutError):
                error_code = "TIMEOUT_ERROR"
                status_code = 408
                message = "Request timed out"
            elif isinstance(e, PermissionError):
                error_code = "PERMISSION_ERROR"
                status_code = 403
                message = "Permission denied"
            else:
                error_code = "INTERNAL_ERROR"
                status_code = 500
                message = "Internal server error"
            
            # Create error response
            error_response = format_error_response(
                error_code=error_code,
                message=message,
                status_code=status_code
            )
            
            # Add detailed error info in development
            if getattr(self.settings, 'api_enable_detailed_errors', True) and self.settings.debug:
                error_response["debug_info"] = {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            
            return JSONResponse(
                content=error_response,
                status_code=status_code
            )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Basic request validation and sanitization."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate and sanitize requests."""
        # Check request size limits
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                max_size = 10 * 1024 * 1024  # 10MB limit
                if size > max_size:
                    error_response = format_error_response(
                        error_code="REQUEST_TOO_LARGE",
                        message=f"Request body too large. Maximum size is {max_size} bytes",
                        status_code=413
                    )
                    return JSONResponse(content=error_response, status_code=413)
            except ValueError:
                pass  # Invalid content-length header, let it pass for now
        
        # Validate content type for POST/PUT requests
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith(("application/json", "multipart/form-data")):
                error_response = format_error_response(
                    error_code="INVALID_CONTENT_TYPE",
                    message="Content-Type must be application/json or multipart/form-data",
                    status_code=415
                )
                return JSONResponse(content=error_response, status_code=415)
        
        # Add security headers
        response = await call_next(request)
        
        # Add security headers to response
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["x-xss-protection"] = "1; mode=block"
        
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Track API performance metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.request_metrics: Dict[str, Any] = {}
        self.metrics_collector = get_metrics_collector()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Monitor request performance."""
        start_time = time.time()
        start_datetime = datetime.utcnow()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000
        duration_seconds = duration_ms / 1000
        
        # Track metrics by endpoint
        endpoint = f"{request.method} {request.url.path}"
        if endpoint not in self.request_metrics:
            self.request_metrics[endpoint] = {
                "count": 0,
                "total_time_ms": 0,
                "avg_time_ms": 0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0,
                "error_count": 0,
                "authenticated_count": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
        
        metrics = self.request_metrics[endpoint]
        metrics["count"] += 1
        metrics["total_time_ms"] += duration_ms
        metrics["avg_time_ms"] = metrics["total_time_ms"] / metrics["count"]
        metrics["min_time_ms"] = min(metrics["min_time_ms"], duration_ms)
        metrics["max_time_ms"] = max(metrics["max_time_ms"], duration_ms)
        
        if response.status_code >= 400:
            metrics["error_count"] += 1
        
        # Track authentication metrics
        if hasattr(request.state, 'api_key') and request.state.api_key:
            metrics["authenticated_count"] += 1
        
        # Track cache metrics
        cache_status = response.headers.get("x-cache-status")
        if cache_status == "HIT":
            metrics["cache_hits"] += 1
        elif cache_status == "MISS":
            metrics["cache_misses"] += 1
        
        # Record metrics in collector
        self.metrics_collector.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code
        )
        
        self.metrics_collector.record_duration(
            endpoint=request.url.path,
            method=request.method,
            duration_seconds=duration_seconds
        )
        
        if response.status_code >= 400:
            error_type = "client_error" if 400 <= response.status_code < 500 else "server_error"
            self.metrics_collector.record_error(
                endpoint=request.url.path,
                error_type=error_type
            )
        
        # Update cache metrics
        cache = get_cache()
        if cache:
            cache_stats = await cache.get_stats()
            self.metrics_collector.update_cache_hit_rate(cache_stats.get("hit_rate", 0.0))
            self.metrics_collector.update_cache_size(cache_stats.get("size", 0))
        
        # Add performance headers
        response.headers["x-response-time-ms"] = str(round(duration_ms, 2))
        
        # Log slow requests
        if duration_ms > 5000:  # 5 seconds
            logger.warning(
                f"Slow request detected: {endpoint} took {duration_ms:.1f}ms"
            )
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.request_metrics.copy()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting functionality."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path.endswith("/health"):
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Determine rate limit based on authentication
        rate_limit = getattr(self.settings, 'api_rate_limit_requests_per_minute', 60)
        
        # If authenticated, use API key rate limit
        if hasattr(request.state, 'api_key') and request.state.api_key:
            api_key_obj = request.state.api_key
            rate_limit = api_key_obj.rate_limit
            client_id = api_key_obj.key_id
        else:
            client_id = client_ip
        
        # Clean old entries (older than 1 minute)
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if rate_limit > 0:
            if self._is_rate_limited(client_id, current_time, rate_limit):
                error_response = format_error_response(
                    error_code="RATE_LIMIT_EXCEEDED",
                    message=f"Rate limit exceeded. Maximum {rate_limit} requests per minute",
                    status_code=429
                )
                return JSONResponse(
                    content=error_response,
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(current_time) + 60),
                        "Retry-After": "60"
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, rate_limit - self._get_request_count(client_id, current_time))
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time) + 60)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float, rate_limit: int) -> bool:
        """Check if client is rate limited."""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"requests": [], "last_request": current_time}
        
        client_data = self.request_counts[client_ip]
        
        # Remove requests older than 1 minute
        minute_ago = current_time - 60
        client_data["requests"] = [
            req_time for req_time in client_data["requests"] 
            if req_time > minute_ago
        ]
        
        # Add current request
        client_data["requests"].append(current_time)
        client_data["last_request"] = current_time
        
        # Check if rate limit exceeded
        return len(client_data["requests"]) > rate_limit
    
    def _get_request_count(self, client_ip: str, current_time: float) -> int:
        """Get current request count for client."""
        if client_ip not in self.request_counts:
            return 0
        
        minute_ago = current_time - 60
        return len([
            req_time for req_time in self.request_counts[client_ip]["requests"]
            if req_time > minute_ago
        ])
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old rate limiting entries."""
        cutoff_time = current_time - 120  # 2 minutes ago
        
        clients_to_remove = []
        for client_ip, data in self.request_counts.items():
            if data["last_request"] < cutoff_time:
                clients_to_remove.append(client_ip)
        
        for client_ip in clients_to_remove:
            del self.request_counts[client_ip]
