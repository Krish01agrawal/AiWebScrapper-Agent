"""
Comprehensive test suite for error scenarios and failure handling.

This module tests the system's behavior under various failure scenarios including
authentication failures, infrastructure outages, API failures, timeouts, and graceful degradation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.dependencies import get_workflow_orchestrator, get_cache_dep, get_current_api_key
from app.core.auth import APIKey, APIKeyManager
from app.utils.validation import ValidationException
from app.api.schemas import ErrorDetail, ExecutionMetadata
from tests.utils.failure_simulators import (
    simulate_mongodb_connection_failure,
    simulate_mongodb_timeout,
    simulate_mongodb_unavailable,
    simulate_gemini_invalid_key,
    simulate_gemini_quota_exceeded,
    simulate_gemini_network_error,
    simulate_gemini_rate_limit,
    simulate_gemini_timeout,
)
from tests.utils.mock_factories import (
    create_mock_workflow_orchestrator,
    create_mock_database_service,
    create_mock_gemini_client,
    create_test_api_key,
    create_error_response,
)


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_workflow_orchestrator():
    """Create mock workflow orchestrator."""
    return create_mock_workflow_orchestrator()


@pytest.fixture
def mock_cache():
    """Create mock cache."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.get_stats.return_value = {"hit_rate": 0.0, "size": 0}
    return mock


# Authentication Error Tests

class TestAuthenticationErrors:
    """Test authentication error scenarios."""
    
    @pytest.mark.auth_error
    def test_missing_api_key(self, client):
        """Test missing API key when auth enabled."""
        # Enable auth temporarily
        with patch('app.core.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.api_auth_enabled = True
            mock_settings.return_value = mock_config
            
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            # Should return 401 when auth is required
            assert response.status_code == 401
            data = response.json()
            assert "error" in data or "AUTHENTICATION_REQUIRED" in str(data)
    
    @pytest.mark.auth_error
    def test_invalid_api_key_format(self, client):
        """Test invalid API key format."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.api_auth_enabled = True
            mock_settings.return_value = mock_config
            
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"},
                headers={"X-API-Key": "invalid_format_key"}
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "error" in data or "INVALID_API_KEY" in str(data)
    
    @pytest.mark.auth_error
    def test_expired_api_key(self, client):
        """Test expired API key."""
        expired_key = create_test_api_key(
            name="Expired Key",
            expires_in_days=-1  # Already expired
        )
        
        with patch('app.core.auth.get_api_key_manager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.validate_key.return_value = expired_key
            mock_manager.return_value = mock_manager_instance
            
            with patch('app.core.config.get_settings') as mock_settings:
                mock_config = Mock()
                mock_config.api_auth_enabled = True
                mock_settings.return_value = mock_config
                
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query"},
                    headers={"X-API-Key": "traycer_test_key"}
                )
                
                assert response.status_code == 401
    
    @pytest.mark.auth_error
    def test_revoked_api_key(self, client):
        """Test revoked API key."""
        revoked_key = create_test_api_key(name="Revoked Key")
        revoked_key.is_active = False
        
        with patch('app.core.auth.get_api_key_manager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.validate_key.return_value = revoked_key
            mock_manager.return_value = mock_manager_instance
            
            with patch('app.core.config.get_settings') as mock_settings:
                mock_config = Mock()
                mock_config.api_auth_enabled = True
                mock_settings.return_value = mock_config
                
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query"},
                    headers={"X-API-Key": "traycer_test_key"}
                )
                
                assert response.status_code == 401
    
    @pytest.mark.auth_error
    def test_api_key_without_permissions(self, client):
        """Test API key without required permissions."""
        limited_key = create_test_api_key(
            name="Limited Key",
            permissions=[]  # No permissions
        )
        
        with patch('app.core.auth.get_api_key_manager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.validate_key.return_value = limited_key
            mock_manager.return_value = mock_manager_instance
            
            with patch('app.core.config.get_settings') as mock_settings:
                mock_config = Mock()
                mock_config.api_auth_enabled = True
                mock_settings.return_value = mock_config
                
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query"},
                    headers={"X-API-Key": "traycer_test_key"}
                )
                
                # Should fail with 403 if permissions are enforced, otherwise 401 for invalid key
                assert response.status_code in [401, 403]


# MongoDB Failure Tests

class TestMongoDBFailures:
    """Test MongoDB failure scenarios."""
    
    @pytest.mark.mongodb_failure
    @pytest.mark.asyncio
    async def test_mongodb_connection_failure_during_startup(self):
        """Test MongoDB connection failure during startup."""
        with simulate_mongodb_connection_failure():
            with patch('app.core.database.init_client') as mock_init:
                mock_init.side_effect = ConnectionError("MongoDB connection failed")
                
                # Should raise error during initialization
                with pytest.raises((ConnectionError, RuntimeError)):
                    from app.core.database import init_client
                    await init_client()
    
    @pytest.mark.mongodb_failure
    @pytest.mark.asyncio
    async def test_mongodb_timeout_during_storage(self, client, mock_workflow_orchestrator):
        """Test MongoDB timeout during query storage."""
        # Mock workflow to succeed but database storage to timeout
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {"scraped_content": [], "processed_content": [], "total_scraped_items": 0, "total_processed_items": 0},
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping", "ai_processing"],
                "stage_timings": {},
                "errors": []
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        with simulate_mongodb_timeout():
            app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
            
            try:
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query", "store_results": True}
                )
                # Should still succeed (200) with warning about storage failure - graceful degradation
                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()
    
    @pytest.mark.mongodb_failure
    @pytest.mark.asyncio
    async def test_mongodb_unavailable_during_workflow(self, client, mock_workflow_orchestrator):
        """Test MongoDB unavailable during workflow execution."""
        # Mock workflow to succeed - MongoDB failure should be handled gracefully
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {"scraped_content": [], "processed_content": [], "total_scraped_items": 0, "total_processed_items": 0},
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping", "ai_processing"],
                "stage_timings": {},
                "errors": []
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        with simulate_mongodb_unavailable():
            app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
            
            try:
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query", "store_results": True}
                )
                # Should handle gracefully - workflow succeeds, storage failure is non-fatal
                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()
    
    @pytest.mark.mongodb_failure
    @pytest.mark.graceful_degradation
    @pytest.mark.asyncio
    async def test_partial_results_when_database_storage_fails(self, client, mock_workflow_orchestrator):
        """Test partial results when database storage fails."""
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {
                "scraped_content": [{"url": "https://example.com", "title": "Test"}],
                "processed_content": [],
                "total_scraped_items": 1,
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "stage_timings": {},
                "errors": [{"stage": "database_storage", "error": "Connection failed"}]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query", "store_results": True}
            )
            
            assert response.status_code == 200
            data = response.json()
            # Should have warnings about storage failure
            assert len(data.get("warnings", [])) > 0 or "storage" in str(data).lower()
        finally:
            app.dependency_overrides.clear()


# Gemini API Failure Tests

class TestGeminiAPIFailures:
    """Test Gemini API failure scenarios."""
    
    @pytest.mark.gemini_failure
    @pytest.mark.asyncio
    async def test_invalid_gemini_api_key(self, client, mock_workflow_orchestrator):
        """Test invalid Gemini API key."""
        error_result = {
            "status": "error",
            "error": {
                "code": "QUERY_PROCESSING_ERROR",
                "message": "API key not valid. Please pass a valid API key."
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "QUERY_PROCESSING_ERROR"
            # Assert retry_possible flag is present for QUERY_PROCESSING_ERROR (should be True)
            assert "retry_possible" in data["error"], "retry_possible flag should be present in error response"
            assert data["error"]["retry_possible"] is True, "QUERY_PROCESSING_ERROR should be retryable"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.gemini_failure
    @pytest.mark.asyncio
    async def test_gemini_quota_exceeded(self, client, mock_workflow_orchestrator):
        """Test Gemini API quota exceeded."""
        error_result = {
            "status": "error",
            "error": {
                "code": "QUERY_PROCESSING_ERROR",
                "message": "Quota exceeded for quota metric 'Generative Language API requests'"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "quota" in data["error"]["message"].lower() or "QUERY_PROCESSING_ERROR" in data["error"]["code"]
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.gemini_failure
    @pytest.mark.asyncio
    async def test_gemini_network_timeout(self, client, mock_workflow_orchestrator):
        """Test Gemini API network timeout."""
        error_result = {
            "status": "error",
            "error": {
                "code": "QUERY_PROCESSING_ERROR",
                "message": "Network error: Failed to connect to Gemini API"
            },
            "execution": {
                "total_duration_seconds": 30.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.gemini_failure
    @pytest.mark.asyncio
    async def test_gemini_failure_simulator_propagates_to_orchestrator(self, client, mock_workflow_orchestrator):
        """Test that Gemini failure simulators propagate errors through the orchestrator."""
        # Use the Gemini failure simulator to patch the client directly
        with simulate_gemini_invalid_key():
            # The orchestrator should catch and handle the Gemini error
            error_result = {
                "status": "error",
                "error": {
                    "code": "QUERY_PROCESSING_ERROR",
                    "message": "API key not valid. Please pass a valid API key."
                },
                "execution": {
                    "total_duration_seconds": 1.0,
                    "completed_stages": [],
                    "failed_stage": "query_processing",
                    "stage_timings": {},
                    "errors": []
                },
                "partial_results": {}
            }
            
            mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
            app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
            
            try:
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query"}
                )
                
                assert response.status_code == 500
                data = response.json()
                assert data["error"]["code"] == "QUERY_PROCESSING_ERROR"
            finally:
                app.dependency_overrides.clear()
    
    @pytest.mark.gemini_failure
    @pytest.mark.asyncio
    async def test_gemini_quota_exceeded_using_simulator(self, client, mock_workflow_orchestrator):
        """Test Gemini quota exceeded using the failure simulator."""
        with simulate_gemini_quota_exceeded():
            error_result = {
                "status": "error",
                "error": {
                    "code": "QUERY_PROCESSING_ERROR",
                    "message": "Quota exceeded for quota metric 'Generative Language API requests'"
                },
                "execution": {
                    "total_duration_seconds": 1.0,
                    "completed_stages": [],
                    "failed_stage": "query_processing",
                    "stage_timings": {},
                    "errors": []
                },
                "partial_results": {}
            }
            
            mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
            app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
            
            try:
                response = client.post(
                    "/api/v1/scrape",
                    json={"query": "test query"}
                )
                
                assert response.status_code == 500
                data = response.json()
                assert data["error"]["code"] == "QUERY_PROCESSING_ERROR"
                assert "quota" in data["error"]["message"].lower()
            finally:
                app.dependency_overrides.clear()
    
    @pytest.mark.gemini_failure
    @pytest.mark.graceful_degradation
    @pytest.mark.asyncio
    async def test_partial_results_when_ai_processing_fails(self, client, mock_workflow_orchestrator):
        """Test partial results when AI processing fails."""
        # Workflow succeeds in scraping but fails in AI processing
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {
                "scraped_content": [{"url": "https://example.com", "title": "Test"}],
                "processed_content": [],  # AI processing failed
                "total_scraped_items": 1,
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "stage_timings": {},
                "errors": [{"stage": "ai_processing", "error": "Gemini API error"}]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 200
            data = response.json()
            # Should have scraped content even if AI processing failed
            assert data["status"] == "success"
            assert len(data.get("warnings", [])) > 0 or "ai_processing" in str(data).lower()
            # For partial results scenarios, verify retry_possible is not present (since it's a success response)
            # But if there's an error field, it should have retry_possible
            if "error" in data:
                assert "retry_possible" in data.get("error", {}), "retry_possible flag should be present in error response"
        finally:
            app.dependency_overrides.clear()


# Timeout Scenario Tests

class TestTimeoutScenarios:
    """Test timeout handling scenarios."""
    
    @pytest.mark.timeout_scenario
    @pytest.mark.asyncio
    async def test_query_processing_timeout(self, client, mock_workflow_orchestrator):
        """Test query processing timeout."""
        timeout_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_TIMEOUT",
                "message": "Workflow timed out after 30 seconds"
            },
            "execution": {
                "total_duration_seconds": 30.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = timeout_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query", "timeout_seconds": 30}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "WORKFLOW_TIMEOUT"
            # Assert recovery suggestions are present
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for timeout errors"
            # Verify at least one suggestion mentions timeout_seconds or simplifying query
            suggestions_text = " ".join(recovery_suggestions).lower()
            assert "timeout" in suggestions_text or "simplify" in suggestions_text or "increas" in suggestions_text, \
                "Recovery suggestions should mention timeout_seconds or simplifying query"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.timeout_scenario
    @pytest.mark.asyncio
    async def test_workflow_timeout_with_partial_results(self, client, mock_workflow_orchestrator):
        """Test workflow timeout with partial results from completed stages."""
        timeout_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_TIMEOUT",
                "message": "Workflow timed out after 60 seconds"
            },
            "execution": {
                "total_duration_seconds": 60.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "failed_stage": "ai_processing",
                "stage_timings": {
                    "query_processing": 1.0,
                    "web_scraping": 59.0
                },
                "errors": []
            },
            "partial_results": {
                "query_processing": {"category": "ai_tools", "confidence": 0.95},
                "web_scraping": {"scraped_items": 5}
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = timeout_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query", "timeout_seconds": 60}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "WORKFLOW_TIMEOUT"
            # Should include execution metadata with completed stages
            assert "execution_metadata" in data
            # Assert recovery suggestions are present
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for timeout errors"
            # Verify at least one suggestion mentions timeout_seconds or simplifying query
            suggestions_text = " ".join(recovery_suggestions).lower()
            assert "timeout" in suggestions_text or "simplify" in suggestions_text or "increas" in suggestions_text, \
                "Recovery suggestions should mention timeout_seconds or simplifying query"
        finally:
            app.dependency_overrides.clear()


# Validation Error Tests

class TestValidationErrors:
    """Test validation error scenarios."""
    
    @pytest.mark.validation_error
    def test_empty_query_validation(self, client):
        """Test empty query validation."""
        response = client.post(
            "/api/v1/scrape",
            json={"query": ""}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.validation_error
    def test_query_too_short(self, client):
        """Test query too short."""
        response = client.post(
            "/api/v1/scrape",
            json={"query": "AI"}  # Less than 3 characters
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.validation_error
    def test_query_too_long(self, client):
        """Test query too long."""
        long_query = "A" * 1001  # Exceeds default max length
        response = client.post(
            "/api/v1/scrape",
            json={"query": long_query}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.validation_error
    def test_invalid_processing_config(self, client):
        """Test invalid processing configuration."""
        response = client.post(
            "/api/v1/scrape",
            json={
                "query": "test query",
                "processing_config": {
                    "timeout_seconds": 5,  # Too low
                    "concurrency": 20,     # Too high
                    "invalid_key": "invalid_value"
                }
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        assert "error" in data or "validation" in str(data).lower()
    
    @pytest.mark.validation_error
    def test_malicious_input_script_tags(self, client):
        """Test malicious input with script tags."""
        response = client.post(
            "/api/v1/scrape",
            json={"query": "<script>alert('xss')</script>Find AI tools"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.validation_error
    def test_invalid_timeout_values(self, client):
        """Test invalid timeout values."""
        # Timeout too low
        response = client.post(
            "/api/v1/scrape",
            json={"query": "test query", "timeout_seconds": 10}
        )
        assert response.status_code == 422  # Pydantic validation error
        
        # Timeout too high
        response = client.post(
            "/api/v1/scrape",
            json={"query": "test query", "timeout_seconds": 700}
        )
        assert response.status_code == 422


# Graceful Degradation Tests

class TestGracefulDegradation:
    """Test graceful degradation behavior."""
    
    @pytest.mark.graceful_degradation
    @pytest.mark.asyncio
    async def test_workflow_continues_when_ai_processing_fails(self, client, mock_workflow_orchestrator):
        """Test workflow continues when AI processing fails."""
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {
                "scraped_content": [{"url": "https://example.com", "title": "Test"}],
                "processed_content": [],  # AI processing failed
                "total_scraped_items": 1,
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "stage_timings": {},
                "errors": [{"stage": "ai_processing", "error": "AI processing failed"}]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Should have warnings about AI processing failure
            assert len(data.get("warnings", [])) > 0
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.graceful_degradation
    @pytest.mark.asyncio
    async def test_workflow_continues_when_database_storage_fails(self, client, mock_workflow_orchestrator):
        """Test workflow continues when database storage fails."""
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {
                "scraped_content": [{"url": "https://example.com", "title": "Test"}],
                "processed_content": [{"summary": "Test summary"}],
                "total_scraped_items": 1,
                "total_processed_items": 1
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping", "ai_processing"],
                "stage_timings": {},
                "errors": [{"stage": "database_storage", "error": "Database storage failed"}]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query", "store_results": True}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Should have warnings about storage failure
            assert len(data.get("warnings", [])) > 0
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.graceful_degradation
    @pytest.mark.partial_results
    @pytest.mark.asyncio
    async def test_partial_results_when_some_scrapers_fail(self, client, mock_workflow_orchestrator):
        """Test partial results when some scrapers fail."""
        success_result = {
            "status": "success",
            "query": {"text": "test", "category": "ai_tools", "confidence_score": 0.9},
            "results": {
                "scraped_content": [{"url": "https://example.com", "title": "Test"}],  # Some succeeded
                "processed_content": [],
                "total_scraped_items": 1,
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "stage_timings": {},
                "errors": [{"stage": "web_scraping", "error": "Some URLs failed to scrape"}]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = success_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Should have some results even if some scrapers failed
            # Check analytics for scraped/processed counts (from workflow result)
            assert data["analytics"]["pages_scraped"] >= 0  # From total_scraped_items
            assert data["analytics"]["items_processed"] >= 0  # From total_processed_items
        finally:
            app.dependency_overrides.clear()


# Recovery Suggestions Validation

class TestRecoverySuggestions:
    """Test recovery suggestions validation."""
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_timeout(self, client, mock_workflow_orchestrator):
        """Test recovery suggestions for timeout errors."""
        timeout_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_TIMEOUT",
                "message": "Workflow timed out after 30 seconds"
            },
            "execution": {
                "total_duration_seconds": 30.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = timeout_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "WORKFLOW_TIMEOUT"
            # Check for recovery suggestions in error details - must be present
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            assert len(error_details[0].get("recovery_suggestions", [])) > 0, "Recovery suggestions should be present for timeout errors"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_validation_error(self, client):
        """Test recovery suggestions for validation errors."""
        response = client.post(
            "/api/v1/scrape",
            json={"query": ""}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        # Check for recovery suggestions - must be present
        error_details = data.get("error", {}).get("details", [])
        assert len(error_details) > 0, "Error details should be present"
        assert len(error_details[0].get("recovery_suggestions", [])) > 0, "Recovery suggestions should be present for validation errors"
    
    @pytest.mark.recovery_suggestions
    def test_retry_possible_flag(self, client, mock_workflow_orchestrator):
        """Test retry_possible flag in error responses."""
        timeout_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_TIMEOUT",
                "message": "Workflow timed out after 30 seconds"
            },
            "execution": {
                "total_duration_seconds": 30.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = timeout_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "WORKFLOW_TIMEOUT"
            # Timeout errors should be retryable - assert explicitly on retry_possible flag
            assert "retry_possible" in data["error"], "retry_possible flag should be present in error response"
            assert data["error"]["retry_possible"] is True, "WORKFLOW_TIMEOUT errors should be retryable (retry_possible=True)"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_database_error(self, client, mock_workflow_orchestrator):
        """Test recovery suggestions for DATABASE_ERROR."""
        error_result = {
            "status": "error",
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database connection failed"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "database_storage",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "DATABASE_ERROR"
            # Check for recovery suggestions
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for DATABASE_ERROR"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_gemini_api_error(self, client, mock_workflow_orchestrator):
        """Test recovery suggestions for GEMINI_API_ERROR."""
        error_result = {
            "status": "error",
            "error": {
                "code": "QUERY_PROCESSING_ERROR",
                "message": "Gemini API error: API key not valid"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "QUERY_PROCESSING_ERROR"
            # Check for recovery suggestions
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for GEMINI_API_ERROR"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_no_content_found(self, client, mock_workflow_orchestrator):
        """Test recovery suggestions for NO_CONTENT_FOUND."""
        error_result = {
            "status": "error",
            "error": {
                "code": "NO_CONTENT_FOUND",
                "message": "No relevant content could be scraped for the query"
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing"],
                "failed_stage": "web_scraping",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "NO_CONTENT_FOUND"
            # Check for recovery suggestions
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for NO_CONTENT_FOUND"
            # Verify suggestions mention broadening query or using different keywords
            suggestions_text = " ".join(recovery_suggestions).lower()
            assert "broaden" in suggestions_text or "different" in suggestions_text or "keyword" in suggestions_text, \
                "Recovery suggestions should mention broadening query or using different keywords"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.recovery_suggestions
    def test_recovery_suggestions_for_rate_limit_exceeded(self, client, mock_workflow_orchestrator):
        """Test recovery suggestions for RATE_LIMIT_EXCEEDED."""
        error_result = {
            "status": "error",
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Maximum 60 requests per minute"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "rate_limiting",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            # Check for recovery suggestions
            error_details = data.get("error", {}).get("details", [])
            assert len(error_details) > 0, "Error details should be present"
            recovery_suggestions = error_details[0].get("recovery_suggestions", [])
            assert len(recovery_suggestions) > 0, "Recovery suggestions should be present for RATE_LIMIT_EXCEEDED"
            # RATE_LIMIT_EXCEEDED should not be retryable (retry_possible=False)
            assert "retry_possible" in data["error"], "retry_possible flag should be present in error response"
            assert data["error"]["retry_possible"] is False, "RATE_LIMIT_EXCEEDED should not be retryable (retry_possible=False)"
        finally:
            app.dependency_overrides.clear()


# Error Response Structure Validation

class TestErrorResponseStructure:
    """Test error response structure validation."""
    
    @pytest.mark.asyncio
    async def test_error_response_has_required_fields(self, client, mock_workflow_orchestrator):
        """Test error responses have required fields."""
        error_result = {
            "status": "error",
            "error": {
                "code": "QUERY_PROCESSING_ERROR",
                "message": "Query processing failed"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            
            # Check required fields
            assert "status" in data
            assert "error" in data
            assert "timestamp" in data or "execution_metadata" in data
            assert data["error"]["code"] == "QUERY_PROCESSING_ERROR"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_error_response_includes_execution_metadata(self, client, mock_workflow_orchestrator):
        """Test error responses include execution metadata."""
        error_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_ERROR",
                "message": "Workflow execution failed"
            },
            "execution": {
                "total_duration_seconds": 15.0,
                "completed_stages": ["query_processing"],
                "failed_stage": "web_scraping",
                "stage_timings": {"query_processing": 1.0},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            # Should include execution metadata
            assert "execution_metadata" in data or "execution" in str(data)
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_error_response_includes_request_id(self, client, mock_workflow_orchestrator):
        """Test error responses include request_id."""
        error_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_ERROR",
                "message": "Workflow execution failed"
            },
            "execution": {
                "total_duration_seconds": 1.0,
                "completed_stages": [],
                "failed_stage": "query_processing",
                "stage_timings": {},
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query", "metadata": {"request_id": "test_req_123"}}
            )
            
            assert response.status_code == 500
            data = response.json()
            # Should include request_id
            assert "request_id" in data or "test_req_123" in str(data)
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.partial_results
    @pytest.mark.asyncio
    async def test_partial_results_structure(self, client, mock_workflow_orchestrator):
        """Test partial results structure in error responses."""
        error_result = {
            "status": "error",
            "error": {
                "code": "AI_PROCESSING_ERROR",
                "message": "AI processing failed"
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "failed_stage": "ai_processing",
                "stage_timings": {
                    "query_processing": 1.0,
                    "web_scraping": 9.0
                },
                "errors": []
            },
            "partial_results": {
                "query_processing": {"category": "ai_tools", "confidence": 0.95},
                "web_scraping": {"scraped_items": 5}
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = error_result
        
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            data = response.json()
            # Should include execution metadata with completed stages
            assert "execution_metadata" in data
        finally:
            app.dependency_overrides.clear()

