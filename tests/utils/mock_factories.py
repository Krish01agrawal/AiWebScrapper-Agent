"""
Mock factories for generating test objects and error scenarios.

This module provides factory functions for creating mock objects, error responses,
and test data for comprehensive error recovery testing.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, Mock, MagicMock

from app.api.schemas import ErrorResponse, ErrorDetail, ExecutionMetadata
from app.core.auth import APIKey, APIKeyManager
from app.utils.validation import ValidationException


# Error Response Factories

def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate ErrorResponse objects.
    
    Args:
        error_code: Error code identifier
        message: Human-readable error message
        status_code: HTTP status code
        details: List of error detail dictionaries
        metadata: Optional execution metadata
        
    Returns:
        Error response dictionary
    """
    response = {
        "status": "error",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": {
            "code": error_code,
            "message": message,
            "http_status": status_code
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    if metadata:
        response["execution_metadata"] = metadata
    
    return response


def create_validation_error(
    field: str,
    message: str,
    recovery_suggestions: Optional[List[str]] = None
) -> ValidationException:
    """
    Generate ValidationException objects.
    
    Args:
        field: Field name that failed validation
        message: Error message
        recovery_suggestions: List of recovery suggestions
        
    Returns:
        ValidationException instance
    """
    return ValidationException(
        message=message,
        field=field,
        recovery_suggestions=recovery_suggestions or [f"Check the {field} field"]
    )


def create_timeout_error(
    stage: str,
    duration: float
) -> Dict[str, Any]:
    """
    Generate timeout error responses.
    
    Args:
        stage: Stage name where timeout occurred
        duration: Timeout duration in seconds
        
    Returns:
        Timeout error response dictionary
    """
    return create_error_response(
        error_code="WORKFLOW_TIMEOUT",
        message=f"{stage} timed out after {duration} seconds",
        status_code=408,
        details=[{
            "error_code": "WORKFLOW_TIMEOUT",
            "message": f"Operation timed out at stage: {stage}",
            "context": {"stage": stage, "duration_seconds": duration},
            "recovery_suggestions": [
                "Try increasing the timeout_seconds parameter",
                "Simplify your query to reduce processing time"
            ]
        }]
    )


def create_partial_result_error(
    completed_stages: List[str],
    failed_stage: str,
    partial_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate partial result errors.
    
    Args:
        completed_stages: List of successfully completed stages
        failed_stage: Stage that failed
        partial_data: Partial results from completed stages
        
    Returns:
        Partial result error response dictionary
    """
    return create_error_response(
        error_code="PARTIAL_RESULT_ERROR",
        message=f"Workflow failed at {failed_stage} stage",
        status_code=500,
        details=[{
            "error_code": "PARTIAL_RESULT_ERROR",
            "message": f"Failed at stage: {failed_stage}",
            "context": {
                "completed_stages": completed_stages,
                "failed_stage": failed_stage
            },
            "recovery_suggestions": [
                "Review partial results for completed stages",
                "Retry the request",
                "Check system logs for detailed error information"
            ]
        }],
        metadata={
            "execution_time_ms": 0.0,
            "completed_stages": completed_stages,
            "failed_stage": failed_stage,
            "partial_results": partial_data
        }
    )


# Mock Component Factories

def create_mock_database_service(fail_on: Optional[str] = None) -> AsyncMock:
    """
    Mock DatabaseService with configurable failures.
    
    Args:
        fail_on: Operation to fail on ("store_query", "store_scraped_content", 
                "store_processed_content", "get_system_health", or None for no failures)
        
    Returns:
        Mock DatabaseService
    """
    mock_service = AsyncMock()
    
    if fail_on == "store_query":
        mock_service.store_query.side_effect = ConnectionError("MongoDB connection failed")
    elif fail_on == "store_scraped_content":
        mock_service.store_scraped_content.side_effect = ConnectionError("MongoDB connection failed")
    elif fail_on == "store_processed_content":
        mock_service.store_processed_content.side_effect = ConnectionError("MongoDB connection failed")
    elif fail_on == "get_system_health":
        mock_service.get_system_health.side_effect = ConnectionError("MongoDB connection failed")
    else:
        # Default successful responses - implement all methods used by WorkflowOrchestrator
        from bson import ObjectId
        mock_service.store_query.return_value = ObjectId()
        mock_service.store_scraped_content.return_value = ObjectId()
        mock_service.store_processed_content.return_value = ObjectId()
        mock_service.get_system_health.return_value = {"overall_status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
        # Also include higher-level methods if they exist
        mock_service.process_and_store_query.return_value = (None, "session_id")
        mock_service.store_scraping_results.return_value = ([], {})
        mock_service.store_processing_results.return_value = []
    
    return mock_service


def create_mock_gemini_client(fail_on: Optional[str] = None) -> AsyncMock:
    """
    Mock GeminiClient with configurable failures.
    
    Args:
        fail_on: Error type to simulate ("invalid_key", "quota_exceeded", 
                "network_error", "rate_limit", "timeout", or None for no failures)
        
    Returns:
        Mock GeminiClient
    """
    mock_client = AsyncMock()
    
    error_messages = {
        "invalid_key": Exception("API key not valid. Please pass a valid API key."),
        "quota_exceeded": Exception("Quota exceeded for quota metric 'Generative Language API requests'"),
        "network_error": ConnectionError("Network error: Failed to connect to Gemini API"),
        "rate_limit": Exception("429 Resource has been exhausted (e.g. check quota)."),
        "timeout": Exception("Request timed out"),
    }
    
    if fail_on and fail_on in error_messages:
        mock_client.generate_content.side_effect = error_messages[fail_on]
        # When failing, is_available should reflect the failure type
        if fail_on in ["invalid_key", "quota_exceeded"]:
            mock_client.is_available.return_value = False
        else:
            # Network/timeout errors might still report as available
            mock_client.is_available.return_value = True
    else:
        # Default successful response
        mock_response = MagicMock()
        mock_response.text = '{"category": "ai_tools", "confidence": 0.9}'
        mock_client.generate_content.return_value = mock_response
        mock_client.is_available.return_value = True
    
    # get_model_info should always be available (it's a metadata call)
    mock_client.get_model_info.return_value = {
        "model_name": "gemini-1.5-pro",
        "is_available": fail_on is None or fail_on not in ["invalid_key", "quota_exceeded"],
        "api_key_configured": True
    }
    
    return mock_client


def create_mock_api_key_manager(keys: Optional[Dict[str, Any]] = None) -> Mock:
    """
    Mock APIKeyManager with test keys.
    
    Args:
        keys: Dictionary of key configurations {key_id: {name, permissions, rate_limit}}
        
    Returns:
        Mock APIKeyManager
    """
    mock_manager = Mock(spec=APIKeyManager)
    mock_manager.keys = {}
    
    if keys:
        for key_id, key_config in keys.items():
            api_key_obj = APIKey(
                key_id=key_id,
                key_hash=f"hash_{key_id}",
                name=key_config.get("name", "Test Key"),
                created_at=datetime.utcnow(),
                expires_at=key_config.get("expires_at"),
                is_active=key_config.get("is_active", True),
                rate_limit=key_config.get("rate_limit", 120),
                permissions=key_config.get("permissions", ["scrape"])
            )
            mock_manager.keys[f"hash_{key_id}"] = api_key_obj
    
    def validate_key(api_key: str) -> Optional[APIKey]:
        if not api_key or not api_key.startswith("traycer_"):
            return None
        # Simple validation - check if key exists
        for key_obj in mock_manager.keys.values():
            if api_key.endswith(key_obj.key_id[:8]):
                return key_obj
        return None
    
    mock_manager.validate_key = Mock(side_effect=validate_key)
    mock_manager.record_request = Mock()
    mock_manager.check_rate_limit.return_value = True
    
    return mock_manager


def create_mock_workflow_orchestrator(fail_stage: Optional[str] = None) -> AsyncMock:
    """
    Mock WorkflowOrchestrator with stage failures.
    
    Args:
        fail_stage: Stage to fail on ("query_processing", "web_scraping", 
                   "ai_processing", "database_storage", or None for success)
        
    Returns:
        Mock WorkflowOrchestrator
    """
    mock_orchestrator = AsyncMock()
    
    if fail_stage:
        error_result = {
            "status": "error",
            "error": {
                "code": f"{fail_stage.upper()}_ERROR",
                "message": f"Failed at {fail_stage} stage"
            },
            "execution": {
                "total_duration_seconds": 10.0,
                "completed_stages": [],
                "failed_stage": fail_stage,
                "stage_timings": {},
                "errors": [{"stage": fail_stage, "error_type": "TestError"}]
            },
            "partial_results": {}
        }
        mock_orchestrator.execute_scraping_workflow.return_value = error_result
    else:
        success_result = {
            "status": "success",
            "query": {
                "text": "test query",
                "category": "ai_tools",
                "confidence_score": 0.95
            },
            "results": {
                "scraped_content": [],
                "processed_content": [],
                "total_scraped_items": 0,
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 15.0,
                "completed_stages": ["query_processing", "web_scraping", "ai_processing"],
                "stage_timings": {
                    "query_processing": 1.0,
                    "web_scraping": 10.0,
                    "ai_processing": 4.0
                },
                "errors": []
            }
        }
        mock_orchestrator.execute_scraping_workflow.return_value = success_result
    
    mock_orchestrator.get_workflow_health.return_value = {
        "status": "healthy",
        "components": {
            "query_processor": {"status": "healthy"},
            "scraper_orchestrator": {"status": "healthy"},
            "processing_orchestrator": {"status": "healthy"},
            "database_service": {"status": "healthy"}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return mock_orchestrator


# Test Data Factories

def create_test_api_key(
    name: str = "Test Key",
    permissions: List[str] = None,
    rate_limit: int = 120,
    expires_in_days: Optional[int] = None
) -> APIKey:
    """
    Generate test APIKey objects.
    
    Args:
        name: Key name
        permissions: List of permissions
        rate_limit: Rate limit per minute
        expires_in_days: Days until expiration (None for no expiration)
        
    Returns:
        APIKey instance
    """
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    return APIKey(
        key_id=f"test_key_{name.lower().replace(' ', '_')}",
        key_hash=f"hash_{name.lower().replace(' ', '_')}",
        name=name,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        is_active=True,
        rate_limit=rate_limit,
        permissions=permissions or ["scrape"]
    )


def create_test_error_detail(
    code: str,
    message: str,
    suggestions: Optional[List[str]] = None
) -> ErrorDetail:
    """
    Generate ErrorDetail objects.
    
    Args:
        code: Error code
        message: Error message
        suggestions: Recovery suggestions
        
    Returns:
        ErrorDetail instance
    """
    return ErrorDetail(
        error_code=code,
        message=message,
        recovery_suggestions=suggestions or ["Please try again"]
    )


def create_test_execution_metadata(
    duration: float = 1.0,
    stages: Optional[Dict[str, float]] = None,
    errors: Optional[List[Dict[str, Any]]] = None
) -> ExecutionMetadata:
    """
    Generate ExecutionMetadata.
    
    Args:
        duration: Total duration in seconds
        stages: Stage timings dictionary
        errors: List of error dictionaries
        
    Returns:
        ExecutionMetadata instance
    """
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=duration)
    
    return ExecutionMetadata(
        execution_time_ms=duration * 1000,
        start_time=start_time,
        end_time=end_time,
        stages_timing=stages or {},
        performance_metrics={
            "success_rate": 1.0 if not errors else 0.5
        }
    )


# Failure Scenario Factories

def create_mongodb_error(error_type: str = "connection_failure") -> Exception:
    """
    Generate MongoDB-specific errors.
    
    Args:
        error_type: One of "connection_failure", "timeout", "unavailable"
        
    Returns:
        Exception instance
    """
    error_messages = {
        "connection_failure": ConnectionError("MongoDB connection failed"),
        "timeout": Exception("MongoDB operation timed out"),
        "unavailable": RuntimeError("MongoDB service unavailable")
    }
    return error_messages.get(error_type, Exception("MongoDB error"))


def create_gemini_error(error_type: str = "invalid_key") -> Exception:
    """
    Generate Gemini API-specific errors.
    
    Args:
        error_type: One of "invalid_key", "quota_exceeded", "network_error", 
                   "rate_limit", "timeout"
        
    Returns:
        Exception instance
    """
    error_messages = {
        "invalid_key": Exception("API key not valid. Please pass a valid API key."),
        "quota_exceeded": Exception("Quota exceeded for quota metric 'Generative Language API requests'"),
        "network_error": ConnectionError("Network error: Failed to connect to Gemini API"),
        "rate_limit": Exception("429 Resource has been exhausted (e.g. check quota)."),
        "timeout": Exception("Gemini API request timed out")
    }
    return error_messages.get(error_type, Exception("Gemini API error"))


def create_timeout_scenario(
    stage: str,
    timeout: float
) -> Dict[str, Any]:
    """
    Generate timeout test scenarios.
    
    Args:
        stage: Stage name
        timeout: Timeout duration in seconds
        
    Returns:
        Timeout scenario dictionary
    """
    return {
        "stage": stage,
        "timeout_seconds": timeout,
        "error_code": "WORKFLOW_TIMEOUT",
        "message": f"{stage} timed out after {timeout} seconds",
        "recovery_suggestions": [
            "Try increasing the timeout_seconds parameter",
            "Simplify your query to reduce processing time"
        ]
    }

