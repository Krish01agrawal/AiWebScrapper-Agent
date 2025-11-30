"""
Main scrape router with comprehensive request/response handling.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app.dependencies import WorkflowOrchestratorDep, CacheDep, CurrentAPIKeyDep
from app.core.cache import generate_cache_key
from app.api.schemas import APIResponse, ExecutionMetadata, ErrorDetail, RequestMetadata, ErrorResponse
from app.processing.schemas import ProcessingConfig
from app.utils.validation import (
    validate_query_text, validate_processing_config, validate_request_metadata,
    ValidationException
)
from app.utils.response import (
    format_success_response, format_error_response, format_processing_results,
    calculate_response_metrics
)
from app.core.config import get_settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["scraping"])


class ScrapeRequest(BaseModel):
    """Pydantic model for scrape request input validation."""
    query: str = Field(..., description="Natural language query to process")
    processing_config: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional processing configuration overrides"
    )
    timeout_seconds: Optional[int] = Field(
        None, 
        ge=30, 
        le=600, 
        description="Custom timeout for this request"
    )
    store_results: bool = Field(
        default=True, 
        description="Whether to store results in database"
    )
    metadata: Optional[RequestMetadata] = Field(
        None, 
        description="Optional request metadata for tracking"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Find AI tools for image generation with free tiers",
                "processing_config": {
                    "enable_ai_analysis": True,
                    "enable_summarization": True,
                    "max_summary_length": 300
                },
                "timeout_seconds": 180,
                "store_results": True,
                "metadata": {
                    "request_id": "req_12345",
                    "session_id": "sess_67890"
                }
            }
        }
    }


class ScrapeProgress(BaseModel):
    """Model for tracking workflow progress through different stages."""
    current_stage: str = Field(..., description="Current processing stage")
    completed_stages: List[str] = Field(..., description="List of completed stages")
    total_stages: int = Field(..., description="Total number of processing stages")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    stage_timings: Dict[str, float] = Field(..., description="Timing for each completed stage")
    estimated_completion_seconds: Optional[float] = Field(
        None, 
        description="Estimated time to completion"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "current_stage": "ai_processing",
                "completed_stages": ["query_processing", "web_scraping"],
                "total_stages": 4,
                "progress_percentage": 50.0,
                "stage_timings": {
                    "query_processing": 1.2,
                    "web_scraping": 8.5
                },
                "estimated_completion_seconds": 15.3
            }
        }
    }


class ScrapeError(BaseModel):
    """Model for detailed error reporting with stage information and recovery suggestions."""
    error_code: str = Field(..., description="Unique error code")
    error_message: str = Field(..., description="Human-readable error message")
    failed_stage: Optional[str] = Field(None, description="Stage where error occurred")
    partial_results: Optional[Dict[str, Any]] = Field(None, description="Any partial results")
    recovery_suggestions: List[str] = Field(..., description="Suggested recovery actions")
    retry_possible: bool = Field(..., description="Whether the request can be retried")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "SCRAPING_TIMEOUT",
                "error_message": "Web scraping timed out after 120 seconds",
                "failed_stage": "web_scraping",
                "partial_results": {
                    "query_processing": {"category": "ai_tools", "confidence": 0.95}
                },
                "recovery_suggestions": [
                    "Try increasing the timeout_seconds parameter",
                    "Simplify your query to reduce processing time"
                ],
                "retry_possible": True
            }
        }
    }


class ScrapeResponse(BaseModel):
    """Structured response model with processed results, analytics, and execution metadata."""
    status: str = Field(..., description="Response status")
    timestamp: datetime = Field(..., description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")
    
    # Main response data
    query: Dict[str, Any] = Field(..., description="Query information and categorization")
    results: Dict[str, Any] = Field(..., description="Processed results and content")
    
    # Analytics and metrics
    analytics: Dict[str, Any] = Field(..., description="Request analytics and performance metrics")
    execution_metadata: ExecutionMetadata = Field(..., description="Execution timing and metadata")
    
    # Progress and error handling
    progress: Optional[ScrapeProgress] = Field(None, description="Progress information if available")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    
    # Cache information
    cached: bool = Field(default=False, description="Whether response was served from cache")
    cache_age_seconds: int = Field(default=0, description="Age of cached response in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_12345",
                "query": {
                    "text": "Find AI tools for image generation",
                    "category": "ai_tools",
                    "confidence_score": 0.95
                },
                "results": {
                    "total_items": 12,
                    "processed_items": 10,
                    "success_rate": 0.83,
                    "processed_contents": []
                },
                "analytics": {
                    "pages_scraped": 15,
                    "processing_time_breakdown": {},
                    "quality_metrics": {}
                },
                "execution_metadata": {
                    "execution_time_ms": 45230.5,
                    "stages_timing": {}
                }
            }
        }
    }


@router.post(
    "/scrape", 
    response_model=ScrapeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def scrape_content(
    request: ScrapeRequest,
    http_request: Request,
    orchestrator: WorkflowOrchestratorDep,
    cache: CacheDep,
    current_api_key: CurrentAPIKeyDep
) -> ScrapeResponse:
    """
    Main scrape endpoint that orchestrates the complete AI web scraping workflow.
    
    This endpoint coordinates all three orchestrators (QueryProcessor, ScraperOrchestrator, 
    ProcessingOrchestrator) in sequence, with database storage integration and detailed 
    progress tracking.
    
    Args:
        request: Scrape request with query and configuration
        http_request: FastAPI request object for metadata
        orchestrator: Workflow orchestrator dependency
        
    Returns:
        Comprehensive scrape response with processed content and metadata
        
    Raises:
        HTTPException: For validation errors, timeouts, or processing failures
    """
    settings = get_settings()
    start_time = datetime.utcnow()
    request_id = None
    
    try:
        # Extract request metadata and generate request ID
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")
        
        if request.metadata:
            request_id = request.metadata.request_id
        
        if not request_id:
            import uuid
            request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Starting scrape request {request_id} from {client_ip}")
        
        # Generate cache key
        cache_key = generate_cache_key(
            "scrape",
            query=request.query,
            config=request.processing_config,
            api_key_id=current_api_key.key_id if current_api_key else None
        )
        
        # Check cache if enabled
        if settings.cache_enabled and cache:
            cached_response = await cache.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for request {request_id}")
                
                # Calculate cache age
                cache_age_seconds = int(time.time() - cached_response.get("cached_at", 0))
                
                # Create ScrapeResponse with cached flags
                cached_data = cached_response.copy()
                cached_data["cached"] = True
                cached_data["cache_age_seconds"] = cache_age_seconds
                
                # Remove cached_at from response data
                cached_data.pop("cached_at", None)
                
                # Create response with proper headers
                response = ScrapeResponse(**cached_data)
                response_body = response.model_dump()
                
                return JSONResponse(
                    content=response_body,
                    headers={
                        "X-Cache-Status": "HIT",
                        "X-Cache-Age": str(cache_age_seconds),
                        "Cache-Control": f"public, max-age={settings.cache_ttl_seconds}",
                        "Vary": "X-API-Key",
                    },
                )
        
        # Request validation
        try:
            validated_query = validate_query_text(request.query)
            validated_config = validate_processing_config(request.processing_config or {})
            validated_metadata = validate_request_metadata(
                request.metadata.model_dump() if request.metadata else {}
            )
        except ValidationException as e:
            error_detail = ErrorDetail(
                error_code="VALIDATION_ERROR",
                message=e.message,
                context={"field": e.field} if e.field else None,
                recovery_suggestions=e.recovery_suggestions
            )
            
            # Create minimal execution metadata for validation errors
            validation_end_time = datetime.utcnow()
            validation_metadata = ExecutionMetadata(
                execution_time_ms=(validation_end_time - start_time).total_seconds() * 1000,
                start_time=start_time,
                end_time=validation_end_time,
                stages_timing={}
            )
            
            error_response = format_error_response(
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                details=[error_detail],
                status_code=400,
                metadata=validation_metadata
            )
            error_response["request_id"] = request_id
            
            return JSONResponse(
                content=error_response,
                status_code=400
            )
        
        # Create processing configuration
        processing_config = None
        if validated_config:
            try:
                processing_config = ProcessingConfig(**validated_config)
            except ValidationError as e:
                error_detail = ErrorDetail(
                    error_code="VALIDATION_ERROR",
                    message=f"Invalid processing configuration: {str(e)}",
                    context={"validation_errors": str(e)},
                    recovery_suggestions=[
                        "Check the processing configuration parameters",
                        "Ensure all values are within valid ranges",
                        "Refer to the API documentation for valid configuration options"
                    ]
                )
                
                error_response = format_error_response(
                    error_code="VALIDATION_ERROR",
                    message="Processing configuration validation failed",
                    details=[error_detail],
                    status_code=400
                )
                error_response["request_id"] = request_id
                
                return JSONResponse(
                    content=error_response,
                    status_code=400
                )
        
        # Log request details
        if getattr(settings, 'api_enable_request_logging', True):
            logger.info(
                f"Request {request_id}: query='{validated_query[:100]}...', "
                f"timeout={request.timeout_seconds}, store={request.store_results}"
            )
        
        # Execute workflow
        workflow_result = await orchestrator.execute_scraping_workflow(
            query_text=validated_query,
            processing_config=processing_config,
            timeout_seconds=request.timeout_seconds,
            store_results=request.store_results
        )
        
        # Calculate execution metadata
        end_time = datetime.utcnow()
        
        # Get processed results to calculate successful items
        processed_results = format_processing_results(
            processed_contents=workflow_result.get("results", {}).get("processed_content", []),
            query_text=validated_query,
            total_processing_time=workflow_result.get("execution", {}).get("total_duration_seconds", 0),
            processing_stats=workflow_result.get("execution", {})
        )
        
        execution_metadata = calculate_response_metrics(
            start_time=start_time,
            end_time=end_time,
            stages_timing=workflow_result.get("execution", {}).get("stage_timings", {}),
            processed_items=workflow_result.get("results", {}).get("total_processed_items", 0),
            successful_items=processed_results.get("results", {}).get("successful_items", 0)
        )
        
        # Handle workflow errors
        if workflow_result.get("status") == "error":
            error_info = workflow_result.get("error", {})
            
            # Create detailed error response
            scrape_error = ScrapeError(
                error_code=error_info.get("code", "WORKFLOW_ERROR"),
                error_message=error_info.get("message", "Workflow execution failed"),
                failed_stage=workflow_result.get("execution", {}).get("failed_stage"),
                partial_results=workflow_result.get("partial_results"),
                recovery_suggestions=_get_recovery_suggestions(error_info.get("code", "WORKFLOW_ERROR")),
                retry_possible=_is_retry_possible(error_info.get("code", "WORKFLOW_ERROR"))
            )
            
            error_response = format_error_response(
                error_code=scrape_error.error_code,
                message=scrape_error.error_message,
                details=[ErrorDetail(
                    error_code=scrape_error.error_code,
                    message=scrape_error.error_message,
                    recovery_suggestions=scrape_error.recovery_suggestions
                )],
                status_code=500,
                metadata=execution_metadata
            )
            # Add retry_possible flag to error response
            error_response["error"]["retry_possible"] = scrape_error.retry_possible
            error_response["request_id"] = request_id
            
            return JSONResponse(
                content=error_response,
                status_code=500
            )
        
        # Format successful response (processed_results already calculated above)
        # processed_results = format_processing_results(...)  # Already calculated above
        
        # Create analytics data
        analytics = {
            "pages_scraped": workflow_result.get("results", {}).get("total_scraped_items", 0),
            "items_processed": workflow_result.get("results", {}).get("total_processed_items", 0),
            "success_rate": processed_results.get("results", {}).get("success_rate", 0),
            "processing_time_breakdown": workflow_result.get("execution", {}).get("stage_timings", {}),
            "quality_metrics": {
                "average_relevance_score": _calculate_average_relevance(
                    workflow_result.get("results", {}).get("processed_content", [])
                ),
                "content_quality_distribution": _calculate_quality_distribution(
                    workflow_result.get("results", {}).get("processed_content", [])
                )
            }
        }
        
        # Create progress information only if enabled
        progress = None
        if getattr(settings, 'api_enable_progress_tracking', True):
            completed_stages = workflow_result.get("execution", {}).get("completed_stages", [])
            total_stages = 4 if request.store_results else 3
            progress_percentage = 100.0 if workflow_result.get("status") == "success" else round(100 * len(completed_stages) / total_stages, 2)
            
            progress = ScrapeProgress(
                current_stage="completed" if workflow_result.get("status") == "success" else workflow_result.get("execution", {}).get("failed_stage", "unknown"),
                completed_stages=completed_stages,
                total_stages=total_stages,
                progress_percentage=progress_percentage,
                stage_timings=workflow_result.get("execution", {}).get("stage_timings", {}),
                estimated_completion_seconds=0.0
            )
        
        # Log successful completion
        logger.info(
            f"Request {request_id} completed successfully in "
            f"{execution_metadata.execution_time_ms:.1f}ms. "
            f"Processed {analytics['items_processed']} items with "
            f"{analytics['success_rate']:.1%} success rate"
        )
        
        # Convert error objects to warning strings
        error_warnings = []
        for error in workflow_result.get("execution", {}).get("errors", []):
            if isinstance(error, dict):
                error_warnings.append(f"{error.get('stage', 'unknown')}: {error.get('error_message', str(error))}")
            else:
                error_warnings.append(str(error))
        
        # Create response
        response = ScrapeResponse(
            status="success",
            timestamp=end_time,
            request_id=request_id,
            query={
                "text": validated_query,
                "category": workflow_result.get("query", {}).get("category", "unknown"),
                "confidence_score": workflow_result.get("query", {}).get("confidence_score", 0.0)
            },
            results=processed_results.get("results", {}),
            analytics=analytics,
            execution_metadata=execution_metadata,
            progress=progress,
            warnings=error_warnings
        )
        
        # Add validated request metadata to response for auditability
        if validated_metadata:
            response_dict = response.model_dump()
            response_dict["request_metadata"] = validated_metadata
            response = ScrapeResponse(**response_dict)
        
        # Store successful response in cache
        if settings.cache_enabled and cache and response.status == "success":
            cache_data = response.model_dump()
            cache_data["cached_at"] = time.time()
            await cache.set(cache_key, cache_data, ttl=settings.cache_ttl_seconds)
            logger.info(f"Cached response for request {request_id}")
        
        # Add cache headers
        response_dict = response.model_dump()
        response_dict["cached"] = False
        response_dict["cache_age_seconds"] = 0
        
        return ScrapeResponse(**response_dict)
    
    except Exception as e:
        # Handle unexpected errors
        end_time = datetime.utcnow()
        execution_metadata = ExecutionMetadata(
            execution_time_ms=(end_time - start_time).total_seconds() * 1000,
            start_time=start_time,
            end_time=end_time,
            stages_timing={}
        )
        
        logger.error(f"Unexpected error in request {request_id}: {e}", exc_info=True)
        
        error_detail = ErrorDetail(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred while processing your request",
            context={"error_type": type(e).__name__} if getattr(settings, 'api_enable_detailed_errors', True) else None,
            recovery_suggestions=["Please try again later", "Contact support if the problem persists"]
        )
        
        error_response = format_error_response(
            error_code="INTERNAL_ERROR",
            message="Internal server error",
            details=[error_detail],
            status_code=500,
            metadata=execution_metadata
        )
        error_response["request_id"] = request_id
        
        return JSONResponse(
            content=error_response,
            status_code=500
        )


@router.get("/scrape/health", response_model=Dict[str, Any])
async def scrape_health_check(
    orchestrator: WorkflowOrchestratorDep,
    cache: CacheDep
) -> Dict[str, Any]:
    """
    Health check endpoint for the scrape workflow.
    
    Args:
        orchestrator: Workflow orchestrator dependency
        cache: Cache dependency
        
    Returns:
        Health status of all workflow components including cache
    """
    try:
        health_status = await orchestrator.get_workflow_health()
        
        # Add cache health information
        if cache:
            cache_stats = await cache.get_stats()
            health_status["cache"] = {
                "status": "healthy",
                "statistics": cache_stats
            }
        else:
            health_status["cache"] = {
                "status": "disabled",
                "statistics": None
            }
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            content=format_error_response(
                error_code="SERVICE_UNAVAILABLE",
                message=f"Health check failed: {str(e)}",
                status_code=503
            ),
            status_code=503
        )


def _get_recovery_suggestions(error_code: str) -> List[str]:
    """Get recovery suggestions based on error code."""
    suggestions_map = {
        "WORKFLOW_TIMEOUT": [
            "Try increasing the timeout_seconds parameter",
            "Simplify your query to reduce processing time",
            "Try again during off-peak hours"
        ],
        "QUERY_PROCESSING_ERROR": [
            "Check your query text for special characters or formatting issues",
            "Try rephrasing your query more clearly",
            "Ensure your query is in English"
        ],
        "SCRAPING_ERROR": [
            "Check if the target websites are accessible",
            "Try a more specific query to target different websites",
            "Retry the request as this may be a temporary issue"
        ],
        "NO_CONTENT_FOUND": [
            "Try broadening your search query",
            "Use different keywords or phrases",
            "Check if your query topic has available online content"
        ],
        "VALIDATION_ERROR": [
            "Check your request format and required fields",
            "Ensure query text is within length limits",
            "Verify processing configuration parameters"
        ]
    }
    
    return suggestions_map.get(error_code, [
        "Please try again later",
        "Contact support if the problem persists"
    ])


def _is_retry_possible(error_code: str) -> bool:
    """Determine if a request can be retried based on error code."""
    non_retryable_errors = {
        "VALIDATION_ERROR",
        "RATE_LIMIT_EXCEEDED",
        "INVALID_CONFIGURATION"
    }
    return error_code not in non_retryable_errors


def _calculate_average_relevance(processed_contents: List[Any]) -> float:
    """Calculate average relevance score from processed contents."""
    if not processed_contents:
        return 0.0
    
    relevance_scores = []
    for content in processed_contents:
        if hasattr(content, 'ai_insights') and content.ai_insights:
            relevance_scores.append(content.ai_insights.relevance_score)
        elif hasattr(content, 'original_content') and hasattr(content.original_content, 'relevance_score'):
            relevance_scores.append(content.original_content.relevance_score or 0.0)
    
    return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0


def _calculate_quality_distribution(processed_contents: List[Any]) -> Dict[str, int]:
    """Calculate quality score distribution from processed contents."""
    distribution = {"high": 0, "medium": 0, "low": 0}
    
    for content in processed_contents:
        quality_score = 0.0
        if hasattr(content, 'enhanced_quality_score'):
            quality_score = content.enhanced_quality_score
        elif hasattr(content, 'original_content') and hasattr(content.original_content, 'content_quality_score'):
            quality_score = content.original_content.content_quality_score or 0.0
        
        if quality_score >= 0.8:
            distribution["high"] += 1
        elif quality_score >= 0.5:
            distribution["medium"] += 1
        else:
            distribution["low"] += 1
    
    return distribution
