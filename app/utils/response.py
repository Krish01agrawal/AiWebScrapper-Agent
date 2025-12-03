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


def synthesize_answer_from_content(
    processed_contents: List[ProcessedContent],
    query_text: str
) -> Dict[str, Any]:
    """
    Synthesize a direct answer to the query from processed content.
    This creates a top-level answer section that directly addresses the user's query.
    
    Args:
        processed_contents: List of processed content items
        query_text: Original query text
        
    Returns:
        Dictionary with synthesized answer, recommendations, and key information
    """
    answer = {
        "direct_answer": "",
        "recommendations": [],
        "key_findings": [],
        "sources": [],
        "confidence": 0.0
    }
    
    if not processed_contents:
        answer["direct_answer"] = "No relevant content found to answer your query."
        return answer
    
    # Extract recommendations and specific answers from processed content
    all_recommendations = []
    all_key_findings = []
    sources = []
    confidence_scores = []
    
    # Sort by relevance score (highest first)
    def get_relevance_score(content):
        try:
            if content.ai_insights and hasattr(content.ai_insights, 'relevance_score'):
                return content.ai_insights.relevance_score
            return 0.0
        except Exception:
            return 0.0
    
    sorted_contents = sorted(
        processed_contents,
        key=lambda x: (
            get_relevance_score(x),
            x.enhanced_quality_score if hasattr(x, 'enhanced_quality_score') else 0.0
        ),
        reverse=True
    )
    
    # Extract from top 5 most relevant items
    for content in sorted_contents[:5]:
        try:
            # Get source URL
            source_url = str(content.original_content.url) if hasattr(content.original_content, 'url') else ""
            if source_url and source_url not in sources:
                sources.append(source_url)
            
            # Extract from summary
            if content.summary:
                # Use executive summary as direct answer if it contains specific recommendations
                exec_summary = content.summary.executive_summary
                if exec_summary and len(exec_summary) > 20:
                    # Check if it contains specific names/recommendations
                    if any(keyword in exec_summary.lower() for keyword in ['fund', 'ticker', 'vfiax', 'fxai', 'recommend', 'best']):
                        if not answer["direct_answer"] or len(exec_summary) > len(answer["direct_answer"]):
                            answer["direct_answer"] = exec_summary
                
                # Extract key points as recommendations
                if content.summary.key_points:
                    for point in content.summary.key_points:
                        if point and len(point) > 10:
                            # Check if it's a specific recommendation (contains names, numbers, etc.)
                            if any(char.isdigit() for char in point) or any(keyword in point.lower() for keyword in ['fund', 'ticker', 'expense', 'minimum', '%']):
                                if point not in all_recommendations:
                                    all_recommendations.append(point)
                            else:
                                if point not in all_key_findings:
                                    all_key_findings.append(point)
            
            # Extract from structured data (entities and key-value pairs)
            if content.structured_data:
                # Extract fund/product recommendations from entities
                for entity in content.structured_data.entities:
                    if isinstance(entity, dict):
                        entity_name = entity.get("name", "")
                        entity_type = entity.get("type", "")
                        properties = entity.get("properties", {})
                        
                        # If it's a product/fund recommendation
                        if entity_type in ["mutual_fund", "product", "ai_tool"] and entity_name:
                            recommendation_text = entity_name
                            
                            # Add key properties
                            if isinstance(properties, dict):
                                details = []
                                if "ticker" in properties:
                                    details.append(f"({properties['ticker']})")
                                if "expense_ratio" in properties:
                                    details.append(f"Expense: {properties['expense_ratio']}")
                                if "minimum_investment" in properties:
                                    details.append(f"Min: {properties['minimum_investment']}")
                                if "risk_level" in properties:
                                    details.append(f"Risk: {properties['risk_level']}")
                                
                                if details:
                                    recommendation_text += " - " + ", ".join(details)
                            
                            if recommendation_text not in all_recommendations:
                                all_recommendations.append(recommendation_text)
                
                # Extract from key_value_pairs
                if content.structured_data.key_value_pairs:
                    kv_pairs = content.structured_data.key_value_pairs
                    if "recommended_funds" in kv_pairs:
                        funds = kv_pairs["recommended_funds"]
                        if isinstance(funds, list):
                            for fund in funds:
                                if isinstance(fund, dict):
                                    fund_name = fund.get("name", "")
                                    ticker = fund.get("ticker", "")
                                    expense = fund.get("expense_ratio", "")
                                    min_inv = fund.get("minimum_investment", "")
                                    
                                    if fund_name:
                                        rec_text = fund_name
                                        if ticker:
                                            rec_text += f" ({ticker})"
                                        details = []
                                        if expense:
                                            details.append(f"Expense: {expense}")
                                        if min_inv:
                                            details.append(f"Min: {min_inv}")
                                        if details:
                                            rec_text += " - " + ", ".join(details)
                                        
                                        if rec_text not in all_recommendations:
                                            all_recommendations.append(rec_text)
            
            # Extract from AI insights recommendations
            try:
                if content.ai_insights and hasattr(content.ai_insights, 'recommendations') and content.ai_insights.recommendations:
                    for rec in content.ai_insights.recommendations:
                        if rec and len(rec) > 10 and rec not in all_recommendations:
                            # Check if it's specific (contains names, numbers, etc.)
                            if any(char.isdigit() for char in rec) or any(keyword in rec.lower() for keyword in ['fund', 'ticker', 'expense', 'minimum', '%', 'vfiax', 'fxai']):
                                all_recommendations.append(rec)
                            else:
                                if rec not in all_key_findings:
                                    all_key_findings.append(rec)
            except Exception:
                pass
            
            # Collect confidence scores
            try:
                if content.ai_insights and hasattr(content.ai_insights, 'confidence_score'):
                    confidence_scores.append(content.ai_insights.confidence_score)
                elif content.summary and hasattr(content.summary, 'confidence_score'):
                    confidence_scores.append(content.summary.confidence_score)
            except Exception:
                pass
        
        except Exception as e:
            # Skip items with errors
            continue
    
    # Check if we have relevant content
    relevant_contents = [
        c for c in sorted_contents 
        if get_relevance_score(c) > 0.5 and 
        c.summary and 
        not any(irrelevant in c.summary.executive_summary.lower() for irrelevant in [
            "does not contain", "cannot provide", "irrelevant", "not relevant", 
            "donation request", "not about", "unrelated"
        ])
    ]
    
    # Build final answer
    if not answer["direct_answer"]:
        if relevant_contents:
            # Use the most relevant content's executive summary
            best_content = relevant_contents[0]
            if best_content.summary and best_content.summary.executive_summary:
                answer["direct_answer"] = best_content.summary.executive_summary
                answer["direct_answer"] = best_content.summary.executive_summary
        elif all_recommendations:
            # Synthesize from recommendations
            answer["direct_answer"] = f"Here are the key recommendations: {', '.join(all_recommendations[:3])}"
        elif all_key_findings:
            answer["direct_answer"] = all_key_findings[0]
        else:
            # Check if all content is irrelevant
            all_irrelevant = all(
                any(irrelevant in (c.summary.executive_summary.lower() if c.summary and c.summary.executive_summary else "") 
                    for irrelevant in ["does not contain", "cannot provide", "irrelevant", "not relevant", "donation request"])
                for c in sorted_contents[:3]
            )
            
            if all_irrelevant:
                answer["direct_answer"] = "I couldn't find relevant content to answer your query. The sources I checked don't contain information about your specific question. Please try rephrasing your query or checking different sources."
            else:
                # Use best executive summary as fallback
                for content in sorted_contents[:3]:
                    if content.summary and content.summary.executive_summary:
                        answer["direct_answer"] = content.summary.executive_summary
                        break
    
    # Filter out irrelevant recommendations
    filtered_recommendations = [
        rec for rec in all_recommendations 
        if not any(irrelevant in rec.lower() for irrelevant in [
            "irrelevant", "does not contain", "cannot provide", "not relevant"
        ])
    ]
    
    # Limit recommendations to top 5 (more focused)
    answer["recommendations"] = filtered_recommendations[:5]
    
    # Filter key findings similarly
    filtered_findings = [
        finding for finding in all_key_findings 
        if not any(irrelevant in finding.lower() for irrelevant in [
            "irrelevant", "does not contain", "cannot provide", "not relevant"
        ])
    ]
    answer["key_findings"] = filtered_findings[:5]
    
    # Only include relevant sources
    answer["sources"] = sources[:3]  # Limit to top 3
    
    # Calculate confidence based on relevant content only
    if relevant_contents:
        relevant_confidence_scores = [
            get_relevance_score(c) for c in relevant_contents[:3]
        ]
        answer["confidence"] = sum(relevant_confidence_scores) / len(relevant_confidence_scores) if relevant_confidence_scores else 0.5
    else:
        answer["confidence"] = 0.1  # Low confidence if no relevant content
    
    return answer


def format_processing_results(
    processed_contents: List[ProcessedContent],
    query_text: str,
    total_processing_time: float,
    processing_stats: Dict[str, Any],
    max_items_in_response: int = 3  # Limit items for concise response
) -> Dict[str, Any]:
    """
    Format processed content results with proper serialization.
    
    Args:
        processed_contents: List of processed content items
        query_text: Original query text
        total_processing_time: Total processing time in seconds
        processing_stats: Processing statistics
        
    Returns:
        Formatted processing results with synthesized answer
    """
    # Sort by relevance and limit to top N items for concise response
    def get_relevance_for_sorting(content):
        try:
            if content.ai_insights and hasattr(content.ai_insights, 'relevance_score'):
                return content.ai_insights.relevance_score or 0.0
            return 0.0
        except Exception:
            return 0.0
    
    # Sort by relevance (highest first) and take top N
    sorted_for_response = sorted(
        processed_contents,
        key=lambda x: (
            get_relevance_for_sorting(x),
            x.enhanced_quality_score if hasattr(x, 'enhanced_quality_score') else 0.0
        ),
        reverse=True
    )[:max_items_in_response]
    
    # Serialize processed contents (limited to top N)
    serialized_contents = []
    for content in sorted_for_response:
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
    
    # Synthesize direct answer from processed content
    synthesized_answer = synthesize_answer_from_content(processed_contents, query_text)
    
    return {
        "query": {
            "text": query_text,
            "processed_at": datetime.utcnow().isoformat() + "Z"
        },
        "answer": synthesized_answer,  # NEW: Direct answer section
        "results": {
            "processed_contents": serialized_contents,  # Limited to top N most relevant
            "total_items": len(processed_contents),  # Total items processed (not limited)
            "processed_items": len(serialized_contents),  # Items shown in response
            "successful_items": len([c for c in processed_contents if hasattr(c, 'summary')]),
            "failed_items": len(processed_contents) - len([c for c in processed_contents if hasattr(c, 'summary')]),
            "success_rate": len([c for c in processed_contents if hasattr(c, 'summary')]) / len(processed_contents) if processed_contents else 0.0,
            "note": f"Showing top {len(serialized_contents)} most relevant results out of {len(processed_contents)} total items processed"
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
