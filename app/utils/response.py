"""
Response formatting utilities for consistent API responses.
"""
import json
import gzip
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.api.schemas import APIResponse, ExecutionMetadata, ErrorDetail
from app.processing.schemas import ProcessedContent


def format_success_response(
    data: Any,
    message: str = "Request processed successfully",
    metadata: Optional[ExecutionMetadata] = None
) -> Dict[str, Any]:
    """
    Format standardized success response.
    
    Args:
        data: Response data
        message: Success message
        metadata: Optional execution metadata
        
    Returns:
        Formatted success response dictionary
    """
    response = {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "data": data
    }
    
    if metadata:
        response["execution_metadata"] = metadata.model_dump(mode='json')
    
    return response


def format_error_response(
    error_code: str,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    status_code: int = 400,
    metadata: Optional[ExecutionMetadata] = None
) -> Dict[str, Any]:
    """
    Format consistent error response structure.
    
    Args:
        error_code: Unique error code identifier
        message: Human-readable error message
        details: List of detailed error information
        status_code: HTTP status code
        metadata: Optional execution metadata
        
    Returns:
        Formatted error response dictionary
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
        response["error"]["details"] = [detail.model_dump() for detail in details]
    
    if metadata:
        response["execution_metadata"] = metadata.model_dump(mode='json')
    
    return response


def format_processing_results(
    processed_contents: List[ProcessedContent],
    query_text: str,
    total_processing_time: float,
    processing_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format processed content results with proper serialization.
    
    Args:
        processed_contents: List of processed content items
        query_text: Original query text
        total_processing_time: Total processing time in seconds
        processing_stats: Processing statistics
        
    Returns:
        Formatted processing results
    """
    # Serialize processed contents
    serialized_contents = []
    for content in processed_contents:
        try:
            # Convert to dict and handle any serialization issues
            content_dict = content.model_dump()
            
            # Ensure URLs are strings
            if 'original_content' in content_dict and 'url' in content_dict['original_content']:
                content_dict['original_content']['url'] = str(content_dict['original_content']['url'])
            
            serialized_contents.append(content_dict)
        except Exception as e:
            # Handle serialization errors gracefully
            serialized_contents.append({
                "error": f"Failed to serialize content: {str(e)}",
                "content_id": getattr(content, 'original_content_id', 'unknown')
            })
    
    # Calculate additional metrics
    successful_contents = len([c for c in serialized_contents if 'error' not in c])
    failed_contents = len(serialized_contents) - successful_contents
    
    # Calculate average processing time per content
    avg_processing_time = total_processing_time / len(processed_contents) if processed_contents else 0
    
    return {
        "query": {
            "text": query_text,
            "processed_at": datetime.utcnow().isoformat() + "Z"
        },
        "results": {
            "processed_contents": serialized_contents,
            "total_items": len(serialized_contents),
            "processed_items": successful_contents,
            "successful_items": successful_contents,
            "failed_items": failed_contents,
            "success_rate": successful_contents / len(serialized_contents) if serialized_contents else 0
        },
        "performance": {
            "total_processing_time_seconds": round(total_processing_time, 3),
            "average_processing_time_seconds": round(avg_processing_time, 3),
            "processing_stats": processing_stats
        }
    }


def calculate_response_metrics(
    start_time: datetime,
    end_time: datetime,
    stages_timing: Dict[str, float],
    processed_items: int,
    successful_items: int
) -> ExecutionMetadata:
    """
    Calculate response performance metrics.
    
    Args:
        start_time: Request start time
        end_time: Request end time
        stages_timing: Timing for each processing stage
        processed_items: Number of items processed
        successful_items: Number of successfully processed items
        
    Returns:
        ExecutionMetadata with calculated metrics
    """
    execution_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Calculate performance metrics
    performance_metrics = {
        "items_processed": processed_items,
        "items_successful": successful_items,
        "success_rate": successful_items / processed_items if processed_items > 0 else 0,
        "throughput_items_per_second": processed_items / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
    }
    
    # Add stage performance analysis
    if stages_timing:
        total_stage_time = sum(stages_timing.values())
        performance_metrics["stage_breakdown"] = {
            stage: {
                "time_ms": time_ms,
                "percentage": (time_ms / total_stage_time * 100) if total_stage_time > 0 else 0
            }
            for stage, time_ms in stages_timing.items()
        }
    
    return ExecutionMetadata(
        execution_time_ms=execution_time_ms,
        start_time=start_time,
        end_time=end_time,
        stages_timing=stages_timing,
        performance_metrics=performance_metrics
    )


def format_execution_metadata(
    start_time: datetime,
    end_time: datetime,
    stages_timing: Dict[str, float],
    resource_usage: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format execution timing and resource usage.
    
    Args:
        start_time: Request start time
        end_time: Request end time
        stages_timing: Timing for each stage
        resource_usage: Optional resource usage data
        
    Returns:
        Formatted execution metadata
    """
    execution_time_ms = (end_time - start_time).total_seconds() * 1000
    
    metadata = {
        "execution_time_ms": round(execution_time_ms, 2),
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z",
        "stages_timing": {k: round(v, 2) for k, v in stages_timing.items()}
    }
    
    if resource_usage:
        metadata["resource_usage"] = resource_usage
    
    return metadata


def paginate_results(
    items: List[Any],
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Paginate results for future pagination support.
    
    Args:
        items: List of items to paginate
        page: Page number (1-based)
        limit: Items per page
        
    Returns:
        Paginated results with metadata
    """
    total_items = len(items)
    total_pages = (total_items + limit - 1) // limit  # Ceiling division
    
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    paginated_items = items[start_index:end_index]
    
    return {
        "items": paginated_items,
        "pagination": {
            "current_page": page,
            "items_per_page": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None
        }
    }


def compress_large_responses(
    response_data: Dict[str, Any],
    size_threshold_bytes: int = 1024 * 1024  # 1MB
) -> Dict[str, Any]:
    """
    Compress large response payloads.
    
    Args:
        response_data: Response data to potentially compress
        size_threshold_bytes: Size threshold for compression
        
    Returns:
        Response data (compressed if necessary) with compression metadata
    """
    # Serialize response to check size
    response_json = json.dumps(response_data, default=str)
    response_size = len(response_json.encode('utf-8'))
    
    if response_size > size_threshold_bytes:
        # Compress the response
        compressed_data = gzip.compress(response_json.encode('utf-8'))
        compression_ratio = len(compressed_data) / response_size
        
        return {
            "compressed": True,
            "compression_ratio": round(compression_ratio, 3),
            "original_size_bytes": response_size,
            "compressed_size_bytes": len(compressed_data),
            "data": compressed_data.hex()  # Hex encode for JSON transport
        }
    else:
        return {
            "compressed": False,
            "size_bytes": response_size,
            "data": response_data
        }


def serialize_complex_objects(obj: Any) -> Any:
    """
    Serialize complex objects for JSON response.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable object
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, datetime):
        return obj.isoformat() + "Z"
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    elif isinstance(obj, (list, tuple)):
        return [serialize_complex_objects(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_complex_objects(value) for key, value in obj.items()}
    else:
        return obj


def create_partial_success_response(
    successful_results: List[Any],
    failed_results: List[Dict[str, Any]],
    message: str = "Request partially completed",
    metadata: Optional[ExecutionMetadata] = None
) -> Dict[str, Any]:
    """
    Create response for partially successful operations.
    
    Args:
        successful_results: Successfully processed results
        failed_results: Failed results with error information
        message: Response message
        metadata: Optional execution metadata
        
    Returns:
        Formatted partial success response
    """
    total_items = len(successful_results) + len(failed_results)
    success_rate = len(successful_results) / total_items if total_items > 0 else 0
    
    response = {
        "status": "partial_success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "data": {
            "successful_results": successful_results,
            "failed_results": failed_results,
            "summary": {
                "total_items": total_items,
                "successful_items": len(successful_results),
                "failed_items": len(failed_results),
                "success_rate": round(success_rate, 3)
            }
        }
    }
    
    if metadata:
        response["execution_metadata"] = metadata.model_dump(mode='json')
    
    return response
