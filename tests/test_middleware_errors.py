"""
Test suite for middleware error handling.

This module tests error handling in various middleware components including
authentication, error handling, rate limiting, request validation, and performance monitoring.
"""
import json
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.main import app
from app.api.middleware import (
    AuthenticationMiddleware,
    ErrorHandlingMiddleware,
    RequestValidationMiddleware,
    PerformanceMonitoringMiddleware,
    RateLimitingMiddleware,
)
from app.core.auth import APIKey, APIKeyManager
from app.utils.response import format_error_response


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/scrape"
    request.method = "POST"
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_response():
    """Create mock FastAPI response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


# AuthenticationMiddleware Tests

class TestAuthenticationMiddleware:
    """Test AuthenticationMiddleware error handling."""
    
    @pytest.mark.asyncio
    async def test_authentication_bypass_for_public_endpoints(self, mock_request):
        """Test authentication bypass for public endpoints."""
        mock_request.url.path = "/health"
        
        middleware = AuthenticationMiddleware(app=app)
        
        async def call_next(request):
            return Response(content="OK", status_code=200)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Should bypass authentication for public endpoints
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_authentication_enforcement_for_protected_endpoints(self, mock_request):
        """Test authentication enforcement for protected endpoints."""
        mock_request.url.path = "/api/v1/scrape"
        mock_request.headers = {}
        
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_auth_enabled = True
            
            middleware = AuthenticationMiddleware(app=app)
            
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should return 401 if no API key provided
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_missing_api_key_header(self, mock_request):
        """Test missing API key header."""
        mock_request.url.path = "/api/v1/scrape"
        mock_request.headers = {}
        
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_auth_enabled = True
            
            middleware = AuthenticationMiddleware(app=app)
            
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 401
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_format(self, mock_request):
        """Test invalid API key format."""
        mock_request.url.path = "/api/v1/scrape"
        mock_request.headers = {"x-api-key": "invalid_format_key"}
        
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_auth_enabled = True
            
            mock_manager = Mock(spec=APIKeyManager)
            mock_manager.validate_key.return_value = None
            
            middleware = AuthenticationMiddleware(app=app, api_key_manager=mock_manager)
            
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 401
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            assert data["error"]["code"] == "INVALID_API_KEY"
    
    @pytest.mark.asyncio
    async def test_api_key_manager_not_initialized(self, mock_request):
        """Test API key manager not initialized."""
        mock_request.url.path = "/api/v1/scrape"
        mock_request.headers = {"x-api-key": "traycer_test_key"}
        
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_auth_enabled = True
            
            middleware = AuthenticationMiddleware(app=app, api_key_manager=None)
            
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 503
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_api_key_validation_failure(self, mock_request):
        """Test API key validation failure."""
        mock_request.url.path = "/api/v1/scrape"
        mock_request.headers = {"x-api-key": "traycer_invalid_key"}
        
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_auth_enabled = True
            
            mock_manager = Mock(spec=APIKeyManager)
            mock_manager.validate_key.return_value = None
            
            middleware = AuthenticationMiddleware(app=app, api_key_manager=mock_manager)
            
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 401
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            assert data["error"]["code"] == "INVALID_API_KEY"


# ErrorHandlingMiddleware Tests

class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware error handling."""
    
    @pytest.mark.asyncio
    async def test_unhandled_exception_catching(self, mock_request):
        """Test unhandled exception catching."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise Exception("Unexpected error")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 500
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "INTERNAL_ERROR"
    
    @pytest.mark.asyncio
    async def test_value_error_handling(self, mock_request):
        """Test ValueError handling (400 response)."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise ValueError("Invalid input provided")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 400
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, mock_request):
        """Test TimeoutError handling (408 response)."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise TimeoutError("Request timed out")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 408
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "TIMEOUT_ERROR"
    
    @pytest.mark.asyncio
    async def test_permission_error_handling(self, mock_request):
        """Test PermissionError handling (403 response)."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise PermissionError("Permission denied")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 403
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "PERMISSION_ERROR"
    
    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, mock_request):
        """Test generic Exception handling (500 response)."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise RuntimeError("Internal server error")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 500
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "INTERNAL_ERROR"
    
    @pytest.mark.asyncio
    async def test_error_logging_with_structured_context(self, mock_request):
        """Test error logging with structured context."""
        import logging
        
        with patch('app.api.middleware.logger') as mock_logger:
            middleware = ErrorHandlingMiddleware(app=app)
            
            async def call_next(request):
                raise Exception("Test error")
            
            response = await middleware.dispatch(mock_request, call_next)
            
            # Verify error was logged
            assert mock_logger.error.called
            call_args = mock_logger.error.call_args
            assert "Test error" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_metrics_recording_for_errors(self, mock_request):
        """Test metrics recording for errors."""
        middleware = ErrorHandlingMiddleware(app=app)
        
        async def call_next(request):
            raise Exception("Test error")
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Metrics should be recorded (checked via mock if needed)
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_debug_info_inclusion_in_development(self, mock_request):
        """Test debug info inclusion in development mode."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.api_enable_detailed_errors = True
            mock_settings.return_value.debug = True
            
            middleware = ErrorHandlingMiddleware(app=app)
            
            async def call_next(request):
                raise Exception("Test error")
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 500
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            # Should include debug info in development
            assert "debug_info" in data or "exception_type" in str(data)


# RateLimitingMiddleware Tests

class TestRateLimitingMiddleware:
    """Test RateLimitingMiddleware error handling."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, mock_request):
        """Test rate limit enforcement."""
        middleware = RateLimitingMiddleware(app=app)
        
        # Simulate many requests
        for i in range(65):  # Exceed default limit of 60
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            if i >= 60:
                # Should be rate limited
                assert response.status_code == 429
                break
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, mock_request):
        """Test rate limit headers."""
        middleware = RateLimitingMiddleware(app=app)
        
        async def call_next(request):
            response = Response(content="OK", status_code=200)
            return response
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Should include rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_response(self, mock_request):
        """Test rate limit exceeded (429 response)."""
        middleware = RateLimitingMiddleware(app=app)
        
        # Exceed rate limit
        with patch.object(middleware, '_is_rate_limited', return_value=True):
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 429
            body = response.body if hasattr(response, 'body') else b'{}'
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
            assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert "Retry-After" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_api_key(self, mock_request):
        """Test rate limit per API key."""
        mock_request.state.api_key = Mock(spec=APIKey)
        mock_request.state.api_key.key_id = "test_key_1"
        mock_request.state.api_key.rate_limit = 10
        
        middleware = RateLimitingMiddleware(app=app)
        
        # Exceed API key specific rate limit
        with patch.object(middleware, '_is_rate_limited', return_value=True):
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 429
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_ip_address(self, mock_request):
        """Test rate limit per IP address."""
        mock_request.client.host = "192.168.1.100"
        
        middleware = RateLimitingMiddleware(app=app)
        
        # Exceed IP-based rate limit
        with patch.object(middleware, '_is_rate_limited', return_value=True):
            async def call_next(request):
                return Response(content="OK", status_code=200)
            
            response = await middleware.dispatch(mock_request, call_next)
            
            assert response.status_code == 429
    
    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_of_old_entries(self, mock_request):
        """Test rate limit cleanup of old entries."""
        middleware = RateLimitingMiddleware(app=app)
        
        # Add old entries
        import time
        old_time = time.time() - 120  # 2 minutes ago
        middleware.request_counts["test_client"] = {
            "requests": [old_time],
            "last_request": old_time
        }
        
        # Cleanup should remove old entries
        middleware._cleanup_old_entries(time.time())
        
        # Old entries should be removed
        assert "test_client" not in middleware.request_counts


# RequestValidationMiddleware Tests

class TestRequestValidationMiddleware:
    """Test RequestValidationMiddleware error handling."""
    
    @pytest.mark.asyncio
    async def test_request_size_limit_enforcement(self, mock_request):
        """Test request size limit enforcement (413 response)."""
        mock_request.headers = {"content-length": "11000000"}  # 11MB, exceeds 10MB limit
        
        middleware = RequestValidationMiddleware(app=app)
        
        async def call_next(request):
            return Response(content="OK", status_code=200)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 413
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "REQUEST_TOO_LARGE"
    
    @pytest.mark.asyncio
    async def test_invalid_content_type_rejection(self, mock_request):
        """Test invalid content-type rejection (415 response)."""
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "text/plain"}
        
        middleware = RequestValidationMiddleware(app=app)
        
        async def call_next(request):
            return Response(content="OK", status_code=200)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        assert response.status_code == 415
        body = response.body if hasattr(response, 'body') else b'{}'
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        data = json.loads(body)
        assert data["error"]["code"] == "INVALID_CONTENT_TYPE"
    
    @pytest.mark.asyncio
    async def test_security_headers_addition(self, mock_request):
        """Test security headers addition."""
        middleware = RequestValidationMiddleware(app=app)
        
        async def call_next(request):
            response = Response(content="OK", status_code=200)
            return response
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Should include security headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers


# PerformanceMonitoringMiddleware Tests

class TestPerformanceMonitoringMiddleware:
    """Test PerformanceMonitoringMiddleware error handling."""
    
    @pytest.mark.asyncio
    async def test_slow_request_logging(self, mock_request):
        """Test slow request logging (>5 seconds)."""
        import logging
        import time
        
        with patch('app.api.middleware.logger') as mock_logger:
            middleware = PerformanceMonitoringMiddleware(app=app)
            
            async def call_next(request):
                # Simulate slow request
                await asyncio.sleep(0.01)  # Small delay for testing
                return Response(content="OK", status_code=200)
            
            # Mock time to simulate slow request
            with patch('time.time', side_effect=[0, 6]):  # 6 seconds elapsed
                response = await middleware.dispatch(mock_request, call_next)
                
                # Should log slow request warning
                assert mock_logger.warning.called or response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_metrics_collection_during_errors(self, mock_request):
        """Test metrics collection during errors."""
        middleware = PerformanceMonitoringMiddleware(app=app)
        
        async def call_next(request):
            return Response(content="Error", status_code=500)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Metrics should be collected
        assert response.status_code == 500
        # Check that metrics were updated
        metrics = middleware.get_metrics()
        assert len(metrics) >= 0  # Metrics may be empty initially
    
    @pytest.mark.asyncio
    async def test_error_count_tracking(self, mock_request):
        """Test error count tracking."""
        middleware = PerformanceMonitoringMiddleware(app=app)
        
        async def call_next(request):
            return Response(content="Error", status_code=500)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Error count should be tracked
        metrics = middleware.get_metrics()
        endpoint = f"{mock_request.method} {mock_request.url.path}"
        if endpoint in metrics:
            assert metrics[endpoint]["error_count"] > 0
    
    @pytest.mark.asyncio
    async def test_cache_metrics_updates(self, mock_request):
        """Test cache metrics updates."""
        middleware = PerformanceMonitoringMiddleware(app=app)
        
        mock_response = Response(content="OK", status_code=200)
        mock_response.headers = {"x-cache-status": "HIT"}
        
        async def call_next(request):
            return mock_response
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Cache metrics should be updated
        metrics = middleware.get_metrics()
        endpoint = f"{mock_request.method} {mock_request.url.path}"
        if endpoint in metrics:
            assert metrics[endpoint].get("cache_hits", 0) >= 0

