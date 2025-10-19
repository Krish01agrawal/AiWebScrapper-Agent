"""
MongoDB document models that extend existing Pydantic schemas for database storage.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from enum import Enum

from app.agents.schemas import ParsedQuery, QueryCategory, BaseQueryResult, AIToolsQuery, MutualFundsQuery, GeneralQuery
from app.scraper.schemas import ScrapedContent, ContentType
from app.processing.schemas import ProcessedContent, ContentSummary, StructuredData, AIInsights, DuplicateAnalysis


class DocumentStatus(str, Enum):
    """Status enumeration for database documents."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    ARCHIVED = "archived"


class BaseDocument(BaseModel):
    """Base class for all MongoDB documents with common fields."""
    id: Optional[ObjectId] = Field(None, alias="_id", description="MongoDB document ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Document creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Document last update timestamp")
    version: int = Field(default=1, ge=1, description="Document version for optimistic locking")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "version": 1
            }
        }
    )


class QueryDocument(BaseDocument):
    """MongoDB document model for parsed queries extending ParsedQuery."""
    # Core query data from ParsedQuery - embed the actual Pydantic models
    base_result: BaseQueryResult = Field(..., description="Base query result information")
    ai_tools_data: Optional[AIToolsQuery] = Field(None, description="AI tools specific data if applicable")
    mutual_funds_data: Optional[MutualFundsQuery] = Field(None, description="Mutual funds specific data if applicable")
    general_data: Optional[GeneralQuery] = Field(None, description="General query data if applicable")
    raw_entities: Optional[Dict[str, Any]] = Field(None, description="Raw extracted entities from the query")
    suggestions: Optional[List[str]] = Field(None, description="Suggested follow-up actions or clarifications")
    
    # Database-specific fields
    session_id: Optional[str] = Field(None, description="Session identifier for grouping related queries")
    user_id: Optional[str] = Field(None, description="User identifier if available")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Query processing status")
    execution_time: Optional[float] = Field(None, ge=0.0, description="Total execution time in seconds")
    
    # Analytics fields
    result_count: Optional[int] = Field(None, ge=0, description="Number of results generated")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall query quality score")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "base_result": {
                    "query_text": "Find AI tools for image generation",
                    "confidence_score": 0.95,
                    "timestamp": "2024-01-01T12:00:00Z",
                    "processing_time": 1.2,
                    "category": "ai_tools"
                },
                "ai_tools_data": {
                    "tool_type": "image generation",
                    "use_case": "creative design",
                    "features_required": ["high resolution", "multiple styles"],
                    "budget_range": "free to $50/month",
                    "technical_expertise": "beginner"
                },
                "session_id": "session_123",
                "user_id": "user_456",
                "status": "completed",
                "execution_time": 15.5,
                "result_count": 12,
                "quality_score": 0.87,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:01:00Z",
                "version": 1
            }
        }
    )


class ScrapedContentDocument(BaseDocument):
    """MongoDB document model for scraped content extending ScrapedContent."""
    # Core content data from ScrapedContent
    url: str = Field(..., description="Source URL of the scraped content")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Main content text")
    content_type: ContentType = Field(default=ContentType.GENERAL, description="Type of content")
    
    # Metadata
    author: Optional[str] = Field(None, description="Content author")
    publish_date: Optional[datetime] = Field(None, description="Publication date")
    description: Optional[str] = Field(None, description="Page description")
    keywords: Optional[List[str]] = Field(None, description="Page keywords")
    
    # Media and links
    images: Optional[List[Dict[str, str]]] = Field(None, description="List of images with alt text and URLs")
    links: Optional[List[Dict[str, str]]] = Field(None, description="List of links with text and URLs")
    
    # Processing info
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the content was scraped")
    processing_time: float = Field(..., ge=0.0, description="Time taken to scrape in seconds")
    content_size_bytes: int = Field(..., ge=0, description="Size of scraped content in bytes")
    
    # Quality metrics
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score for the query")
    content_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score of the content")
    
    # Extraction info
    extraction_method: str = Field(..., description="Method used to extract content")
    fallback_used: bool = Field(default=False, description="Whether fallback extraction was used")
    
    # Database-specific fields
    query_id: Optional[ObjectId] = Field(None, description="Reference to the query that generated this content")
    session_id: Optional[str] = Field(None, description="Session identifier")
    storage_path: Optional[str] = Field(None, description="Path to stored content if using file storage")
    indexed_at: Optional[datetime] = Field(None, description="When content was indexed for search")
    
    # Deduplication fields
    content_hash: Optional[str] = Field(None, description="Hash of content for duplicate detection")
    duplicate_of: Optional[ObjectId] = Field(None, description="Reference to original content if this is a duplicate")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439012",
                "url": "https://example.com/article",
                "title": "Sample Article Title",
                "content": "This is the main content of the article...",
                "content_type": "article",
                "author": "John Doe",
                "publish_date": "2024-01-01T12:00:00Z",
                "description": "A sample article description",
                "keywords": ["sample", "article", "example"],
                "images": [{"url": "https://example.com/image.jpg", "alt": "Sample image"}],
                "links": [{"url": "https://example.com/link", "text": "Sample link"}],
                "timestamp": "2024-01-01T12:00:00Z",
                "processing_time": 2.5,
                "content_size_bytes": 2048,
                "relevance_score": 0.85,
                "content_quality_score": 0.9,
                "extraction_method": "beautifulsoup_primary",
                "fallback_used": False,
                "query_id": "507f1f77bcf86cd799439011",
                "session_id": "session_123",
                "storage_path": "/storage/content/507f1f77bcf86cd799439012.txt",
                "indexed_at": "2024-01-01T12:01:00Z",
                "content_hash": "sha256:abc123...",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "version": 1
            }
        }
    )


class ProcessedContentDocument(BaseDocument):
    """MongoDB document model for processed content extending ProcessedContent."""
    # Original content reference
    original_content_id: ObjectId = Field(..., description="Reference to original scraped content")
    query_id: Optional[ObjectId] = Field(None, description="Reference to the query that generated this content")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Processing results - embed the actual Pydantic models
    cleaned_content: str = Field(..., description="Cleaned and processed text content")
    summary: ContentSummary = Field(..., description="Content summary and key points")
    structured_data: StructuredData = Field(..., description="Extracted structured information")
    ai_insights: Optional[AIInsights] = Field(None, description="AI-powered analysis and insights")
    duplicate_analysis: Optional[DuplicateAnalysis] = Field(None, description="Duplicate detection results")
    
    # Enhanced metadata
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When processing was completed")
    processing_duration: float = Field(..., description="Processing time in seconds")
    enhanced_quality_score: float = Field(..., ge=0.0, le=1.0, description="Enhanced quality score after processing")
    processing_errors: List[str] = Field(default_factory=list, description="Any errors encountered during processing")
    
    # Database-specific fields
    processing_version: str = Field(default="1.0", description="Version of processing pipeline used")
    cache_key: Optional[str] = Field(None, description="Cache key for processed results")
    expires_at: Optional[datetime] = Field(None, description="Cache expiration timestamp for cached documents")
    
    # Performance metrics
    memory_usage_mb: Optional[float] = Field(None, ge=0.0, description="Memory usage during processing")
    cpu_time_seconds: Optional[float] = Field(None, ge=0.0, description="CPU time used for processing")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "original_content_id": "507f1f77bcf86cd799439012",
                "query_id": "507f1f77bcf86cd799439011",
                "session_id": "session_123",
                "cleaned_content": "This is the cleaned and processed content...",
                "summary": {
                    "executive_summary": "AI technology overview article",
                    "key_points": ["AI is transforming industries"],
                    "detailed_summary": "Comprehensive overview...",
                    "main_topics": ["AI", "Technology"],
                    "sentiment": "positive",
                    "confidence_score": 0.92
                },
                "structured_data": {
                    "entities": [],
                    "key_value_pairs": {},
                    "categories": ["Technology"],
                    "confidence_scores": {},
                    "tables": [],
                    "measurements": []
                },
                "ai_insights": {
                    "themes": ["AI Technology"],
                    "relevance_score": 0.87,
                    "quality_metrics": {"readability": 0.75},
                    "recommendations": ["Stay updated on AI"],
                    "credibility_indicators": {},
                    "information_accuracy": 0.88,
                    "source_reliability": 0.85
                },
                "duplicate_analysis": None,
                "processing_timestamp": "2024-01-01T00:01:00Z",
                "processing_duration": 2.5,
                "enhanced_quality_score": 0.89,
                "processing_errors": [],
                "processing_version": "1.0",
                "cache_key": "processed_507f1f77bcf86cd799439012_v1.0",
                "memory_usage_mb": 45.2,
                "cpu_time_seconds": 1.8,
                "created_at": "2024-01-01T00:01:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
                "version": 1
            }
        }
    )


class QuerySessionDocument(BaseDocument):
    """MongoDB document model for tracking query sessions with analytics data."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier if available")
    
    # Session metadata
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    duration_seconds: Optional[float] = Field(None, ge=0.0, description="Total session duration")
    
    # Query tracking
    query_count: int = Field(default=0, ge=0, description="Number of queries in this session")
    successful_queries: int = Field(default=0, ge=0, description="Number of successful queries")
    failed_queries: int = Field(default=0, ge=0, description="Number of failed queries")
    
    # Performance metrics
    total_processing_time: float = Field(default=0.0, ge=0.0, description="Total processing time across all queries")
    average_query_time: Optional[float] = Field(None, ge=0.0, description="Average time per query")
    total_content_scraped: int = Field(default=0, ge=0, description="Total number of content items scraped")
    total_content_processed: int = Field(default=0, ge=0, description="Total number of content items processed")
    
    # Quality metrics
    average_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average quality score across queries")
    average_relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average relevance score")
    
    # Session context
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    referrer: Optional[str] = Field(None, description="HTTP referrer")
    
    # Status
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Session status")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "session_id": "session_123",
                "user_id": "user_456",
                "start_time": "2024-01-01T12:00:00Z",
                "end_time": "2024-01-01T12:30:00Z",
                "duration_seconds": 1800.0,
                "query_count": 5,
                "successful_queries": 4,
                "failed_queries": 1,
                "total_processing_time": 45.2,
                "average_query_time": 9.04,
                "total_content_scraped": 25,
                "total_content_processed": 23,
                "average_quality_score": 0.85,
                "average_relevance_score": 0.82,
                "user_agent": "Mozilla/5.0...",
                "ip_address": "192.168.1.1",
                "referrer": "https://example.com",
                "status": "completed",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:30:00Z",
                "version": 1
            }
        }
    )


class AnalyticsDocument(BaseDocument):
    """MongoDB document model for storing aggregated analytics and metrics."""
    # Time period
    period_start: datetime = Field(..., description="Start of analytics period")
    period_end: datetime = Field(..., description="End of analytics period")
    period_type: str = Field(..., description="Type of period (hourly, daily, weekly, monthly)")
    
    # Query analytics
    total_queries: int = Field(default=0, ge=0, description="Total queries in period")
    successful_queries: int = Field(default=0, ge=0, description="Successful queries in period")
    failed_queries: int = Field(default=0, ge=0, description="Failed queries in period")
    unique_users: int = Field(default=0, ge=0, description="Unique users in period")
    unique_sessions: int = Field(default=0, ge=0, description="Unique sessions in period")
    
    # Content analytics
    total_content_scraped: int = Field(default=0, ge=0, description="Total content items scraped")
    total_content_processed: int = Field(default=0, ge=0, description="Total content items processed")
    average_content_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average content quality")
    average_processing_time: Optional[float] = Field(None, ge=0.0, description="Average processing time")
    
    # Performance metrics
    average_query_time: Optional[float] = Field(None, ge=0.0, description="Average query processing time")
    peak_concurrent_queries: int = Field(default=0, ge=0, description="Peak concurrent queries")
    total_processing_time: float = Field(default=0.0, ge=0.0, description="Total processing time")
    
    # Category breakdown
    category_breakdown: Dict[str, int] = Field(default_factory=dict, description="Queries by category")
    domain_breakdown: Dict[str, int] = Field(default_factory=dict, description="Content by domain")
    
    # Error analytics
    error_breakdown: Dict[str, int] = Field(default_factory=dict, description="Errors by type")
    retry_statistics: Dict[str, Any] = Field(default_factory=dict, description="Retry attempt statistics")
    
    # Quality metrics
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Quality score distribution")
    relevance_distribution: Dict[str, int] = Field(default_factory=dict, description="Relevance score distribution")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439015",
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-01-01T23:59:59Z",
                "period_type": "daily",
                "total_queries": 150,
                "successful_queries": 142,
                "failed_queries": 8,
                "unique_users": 45,
                "unique_sessions": 67,
                "total_content_scraped": 450,
                "total_content_processed": 420,
                "average_content_quality": 0.82,
                "average_processing_time": 12.5,
                "average_query_time": 8.3,
                "peak_concurrent_queries": 12,
                "total_processing_time": 1245.0,
                "category_breakdown": {"ai_tools": 60, "mutual_funds": 45, "general": 45},
                "domain_breakdown": {"example.com": 120, "test.com": 80, "demo.com": 60},
                "error_breakdown": {"timeout": 3, "connection_error": 2, "parse_error": 3},
                "retry_statistics": {"total_retries": 15, "successful_retries": 8},
                "quality_distribution": {"high": 85, "medium": 45, "low": 12},
                "relevance_distribution": {"high": 78, "medium": 52, "low": 20},
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "version": 1
            }
        }
    )


# Utility functions for document conversion
def convert_parsed_query_to_document(parsed_query: ParsedQuery, **kwargs) -> QueryDocument:
    """Convert ParsedQuery to QueryDocument for database storage."""
    return QueryDocument(
        base_result=parsed_query.base_result.model_dump(),
        ai_tools_data=parsed_query.ai_tools_data.model_dump() if parsed_query.ai_tools_data else None,
        mutual_funds_data=parsed_query.mutual_funds_data.model_dump() if parsed_query.mutual_funds_data else None,
        general_data=parsed_query.general_data.model_dump() if parsed_query.general_data else None,
        raw_entities=parsed_query.raw_entities,
        suggestions=parsed_query.suggestions,
        **kwargs
    )


def convert_scraped_content_to_document(scraped_content: ScrapedContent, **kwargs) -> ScrapedContentDocument:
    """Convert ScrapedContent to ScrapedContentDocument for database storage."""
    return ScrapedContentDocument(
        url=str(scraped_content.url),
        title=scraped_content.title,
        content=scraped_content.content,
        content_type=scraped_content.content_type.value,
        author=scraped_content.author,
        publish_date=scraped_content.publish_date,
        description=scraped_content.description,
        keywords=scraped_content.keywords,
        images=scraped_content.images,
        links=scraped_content.links,
        timestamp=scraped_content.timestamp,
        processing_time=scraped_content.processing_time,
        content_size_bytes=scraped_content.content_size_bytes,
        relevance_score=scraped_content.relevance_score,
        content_quality_score=scraped_content.content_quality_score,
        extraction_method=scraped_content.extraction_method,
        fallback_used=scraped_content.fallback_used,
        **kwargs
    )


def convert_processed_content_to_document(processed_content: ProcessedContent, **kwargs) -> ProcessedContentDocument:
    """Convert ProcessedContent to ProcessedContentDocument for database storage."""
    return ProcessedContentDocument(
        cleaned_content=processed_content.cleaned_content,
        summary=processed_content.summary.model_dump(),
        structured_data=processed_content.structured_data.model_dump(),
        ai_insights=processed_content.ai_insights.model_dump() if processed_content.ai_insights else None,
        duplicate_analysis=processed_content.duplicate_analysis.model_dump() if processed_content.duplicate_analysis else None,
        processing_timestamp=processed_content.processing_timestamp,
        processing_duration=processed_content.processing_duration,
        enhanced_quality_score=processed_content.enhanced_quality_score,
        processing_errors=processed_content.processing_errors,
        **kwargs
    )
