"""
Shared API schemas for common request/response patterns.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Base model with status, timestamp, and message fields for consistent API responses."""
    status: str = Field(..., description="Response status (success, error, partial)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    message: str = Field(..., description="Human-readable status message")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "timestamp": "2024-01-01T12:00:00Z",
                "message": "Request processed successfully"
            }
        }
    }


class PaginationParams(BaseModel):
    """Model for future pagination support with page, limit, and offset parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "limit": 20,
                "offset": 0
            }
        }
    }


class ErrorDetail(BaseModel):
    """Model for structured error information with error code, message, and context."""
    error_code: str = Field(..., description="Unique error code identifier")
    message: str = Field(..., description="Human-readable error message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    recovery_suggestions: Optional[List[str]] = Field(None, description="Suggested recovery actions")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "Query text is required and cannot be empty",
                "context": {"field": "query", "value": ""},
                "recovery_suggestions": ["Provide a non-empty query string"]
            }
        }
    }


class ErrorResponse(BaseModel):
    """Model for error responses matching format_error_response structure."""
    status: str = Field(..., description="Response status (always 'error')")
    timestamp: str = Field(..., description="Response timestamp in ISO format")
    error: Dict[str, Any] = Field(..., description="Error information")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata if available")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "timestamp": "2024-01-01T12:00:00Z",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "http_status": 400,
                    "details": [
                        {
                            "error_code": "VALIDATION_ERROR",
                            "message": "Query text is required",
                            "context": {"field": "query"},
                            "recovery_suggestions": ["Provide a valid query string"]
                        }
                    ]
                },
                "execution_metadata": {
                    "execution_time_ms": 45.2,
                    "start_time": "2024-01-01T12:00:00Z",
                    "end_time": "2024-01-01T12:00:00Z",
                    "stages_timing": {}
                }
            }
        }
    }


class ExecutionMetadata(BaseModel):
    """Model for tracking request execution with timing, resource usage, and performance metrics."""
    execution_time_ms: float = Field(..., ge=0, description="Total execution time in milliseconds")
    start_time: datetime = Field(..., description="Request start timestamp")
    end_time: datetime = Field(..., description="Request completion timestamp")
    stages_timing: Dict[str, float] = Field(default_factory=dict, description="Timing for each processing stage")
    resource_usage: Optional[Dict[str, Any]] = Field(None, description="Resource usage metrics")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "execution_time_ms": 5432.1,
                "start_time": "2024-01-01T12:00:00Z",
                "end_time": "2024-01-01T12:00:05Z",
                "stages_timing": {
                    "query_processing": 1200.5,
                    "web_scraping": 2800.3,
                    "ai_processing": 1431.3
                },
                "resource_usage": {
                    "memory_mb": 245.6,
                    "cpu_percent": 78.2
                },
                "performance_metrics": {
                    "pages_scraped": 15,
                    "content_processed": 12,
                    "success_rate": 0.8
                }
            }
        }
    }


class RequestMetadata(BaseModel):
    """Model for optional request tracking with client information and request context."""
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent string")
    session_id: Optional[str] = Field(None, description="Session identifier")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional request context")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id": "req_12345",
                "client_ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "session_id": "sess_67890",
                "additional_context": {"source": "web_ui", "version": "1.0.0"}
            }
        }
    }
