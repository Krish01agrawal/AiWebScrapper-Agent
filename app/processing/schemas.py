from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator, model_validator
from bson import ObjectId
from app.scraper.schemas import ScrapedContent
from app.agents.schemas import ParsedQuery


class ContentSummary(BaseModel):
    """Content summary with multiple levels of detail."""
    executive_summary: str = Field(..., description="1-2 sentence executive summary")
    key_points: List[str] = Field(..., description="Bullet point key takeaways")
    detailed_summary: str = Field(..., description="Detailed paragraph summary")
    main_topics: List[str] = Field(..., description="Main topics and themes identified")
    sentiment: str = Field(..., description="Overall sentiment (positive, negative, neutral)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in summary quality")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Summarization metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "executive_summary": "This article discusses the latest developments in AI technology and its impact on various industries.",
                "key_points": [
                    "AI technology is rapidly advancing",
                    "Multiple industries are being transformed",
                    "Ethical considerations are important"
                ],
                "detailed_summary": "The article provides a comprehensive overview of current AI developments...",
                "main_topics": ["Artificial Intelligence", "Industry Transformation", "Technology Ethics"],
                "sentiment": "positive",
                "confidence_score": 0.92
            }
        }
    }


class StructuredData(BaseModel):
    """Extracted structured information from content."""
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Named entities and their properties")
    key_value_pairs: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs extracted from content")
    categories: List[str] = Field(default_factory=list, description="Content categories and tags")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence scores for extracted data")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted table data")
    measurements: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted measurements and metrics")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "entities": [
                    {"type": "product", "name": "ChatGPT", "properties": {"company": "OpenAI", "type": "AI Chatbot"}}
                ],
                "key_value_pairs": {"pricing": "$20/month", "launch_date": "2022-11-30"},
                "categories": ["AI Tools", "Chatbots", "Productivity"],
                "confidence_scores": {"pricing": 0.95, "launch_date": 0.88},
                "tables": [],
                "measurements": []
            }
        }
    }


class AIInsights(BaseModel):
    """AI-powered analysis results and insights."""
    themes: List[str] = Field(..., description="Key themes and patterns identified")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to original query")
    quality_metrics: Dict[str, float] = Field(..., description="Content quality assessment metrics")
    recommendations: List[str] = Field(..., description="Actionable recommendations and insights")
    credibility_indicators: Dict[str, Any] = Field(..., description="Credibility and reliability indicators")
    information_accuracy: float = Field(..., ge=0.0, le=1.0, description="Perceived information accuracy")
    source_reliability: float = Field(..., ge=0.0, le=1.0, description="Source reliability assessment")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in AI analysis")
    key_entities: List[str] = Field(default_factory=list, description="Key entities mentioned")
    categories: List[str] = Field(default_factory=list, description="Content categories/tags")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="AI processing metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "themes": ["AI Ethics", "Technology Innovation", "Industry Impact"],
                "relevance_score": 0.87,
                "quality_metrics": {"readability": 0.75, "information_density": 0.82, "coherence": 0.91},
                "recommendations": [
                    "Consider ethical implications when implementing AI",
                    "Stay updated on latest AI developments",
                    "Evaluate AI solutions for your specific use case"
                ],
                "credibility_indicators": {"expert_citations": 5, "recent_sources": True, "peer_reviewed": False},
                "information_accuracy": 0.88,
                "source_reliability": 0.85,
                "confidence_score": 0.92
            }
        }
    }


class DuplicateAnalysis(BaseModel):
    """Duplicate content analysis results."""
    content_id: str = Field(..., description="ID of the content this analysis belongs to")
    has_duplicates: bool = Field(..., description="Whether duplicates were found")
    duplicate_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in duplicate detection")
    duplicate_groups: List[List[str]] = Field(default_factory=list, description="Groups of duplicate content IDs")
    similarity_scores: Dict[str, float] = Field(default_factory=dict, description="Similarity scores for duplicate pairs")
    deduplication_recommendations: List[str] = Field(default_factory=list, description="Recommendations for handling duplicates")
    best_version_id: Optional[str] = Field(None, description="ID of the best version among duplicates")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata and context")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "content_id": "content_123",
                "has_duplicates": True,
                "duplicate_confidence": 0.89,
                "duplicate_groups": [["content_123", "content_789"]],
                "deduplication_recommendations": ["Keep content_123, remove content_789"],
                "best_version_id": "content_123",
                "processing_metadata": {
                    "analysis_method": "ai_similarity",
                    "confidence_reason": "High similarity detected"
                }
            }
        }
    }


class ProcessedContent(BaseModel):
    """Enhanced content with AI analysis and processing results."""
    # Original scraped content
    original_content: ScrapedContent = Field(..., description="Original scraped content")
    
    # Referential integrity fields for database linking
    original_content_id: Optional[Union[str, ObjectId]] = Field(None, description="Direct reference to original content ID")
    original_url: Optional[str] = Field(None, description="Original URL for content mapping")
    
    # Processing results
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
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "original_content": {
                    "id": "content_123",
                    "url": "https://example.com/article",
                    "title": "AI Technology Overview",
                    "content": "This is the original content...",
                    "metadata": {},
                    "quality_score": 0.75,
                    "scraped_at": "2024-01-01T00:00:00Z"
                },
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
                "processing_errors": []
            }
        }
    }


class ProcessingResult(BaseModel):
    """Complete processing pipeline result."""
    processed_contents: List[ProcessedContent] = Field(..., description="List of processed content items")
    total_processing_time: float = Field(..., description="Total time for all processing operations")
    processing_stats: Dict[str, Any] = Field(..., description="Processing statistics and metrics")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered during processing")
    query_context: ParsedQuery = Field(..., description="Original query context for processing")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "processed_contents": [],
                "total_processing_time": 15.2,
                "processing_stats": {"total_items": 5, "successful": 5, "failed": 0},
                "errors": [],
                "query_context": {
                    "query": "AI tools",
                    "category": "ai_tools",
                    "filters": {},
                    "parsed_at": "2024-01-01T00:00:00Z"
                }
            }
        }
    }


class ProcessingConfig(BaseModel):
    """Configuration for processing pipeline operations with comprehensive validation."""
    timeout_seconds: int = Field(60, ge=10, le=300, description="Processing operation timeout")
    max_retries: int = Field(2, ge=0, le=5, description="Maximum retry attempts for failed operations")
    concurrency: int = Field(3, ge=1, le=10, description="Parallel processing operations")
    enable_content_cleaning: bool = Field(True, description="Enable content cleaning stage")
    enable_ai_analysis: bool = Field(True, description="Enable AI analysis stage")
    enable_summarization: bool = Field(True, description="Enable summarization stage")
    enable_structured_extraction: bool = Field(True, description="Enable structured data extraction")
    enable_duplicate_detection: bool = Field(True, description="Enable duplicate detection")
    similarity_threshold: float = Field(0.8, ge=0.5, le=0.95, description="Duplicate detection sensitivity")
    min_content_quality_score: float = Field(0.4, ge=0.0, le=1.0, description="Minimum quality score for processing")
    max_summary_length: int = Field(500, ge=100, le=2000, description="Maximum summary length")
    batch_size: int = Field(10, ge=1, le=50, description="Batch processing size")
    content_processing_timeout: int = Field(30, ge=5, le=120, description="Timeout for individual content processing")
    max_concurrent_ai_analyses: int = Field(5, ge=1, le=20, description="Maximum concurrent AI analysis operations")
    gemini_max_similarity_content_length: int = Field(1000, ge=100, le=5000, description="Maximum content length for similarity analysis")
    max_similarity_content_pairs: int = Field(50, ge=10, le=200, description="Maximum content pairs for similarity analysis")
    max_similarity_batch_size: int = Field(10, ge=2, le=50, description="Maximum batch size for similarity analysis")
    memory_threshold_mb: int = Field(512, ge=128, le=2048, description="Memory threshold in MB for batch processing")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "timeout_seconds": 60,
                "max_retries": 2,
                "concurrency": 3,
                "enable_content_cleaning": True,
                "enable_ai_analysis": True,
                "enable_summarization": True,
                "enable_structured_extraction": True,
                "enable_duplicate_detection": True,
                "similarity_threshold": 0.8,
                "min_content_quality_score": 0.4,
                "max_summary_length": 500,
                "batch_size": 10,
                "content_processing_timeout": 30,
                "max_concurrent_ai_analyses": 5,
                "gemini_max_similarity_content_length": 1000,
                "max_similarity_content_pairs": 50,
                "max_similarity_batch_size": 10,
                "memory_threshold_mb": 512
            }
        }
    }
    
    # Individual field validators removed to prevent circular dependency issues
    # Cross-field validation moved to @model_validator(mode='after')
    
    @model_validator(mode='after')
    def validate_configuration_consistency(self):
        """Validate overall configuration consistency with realistic operational constraints."""
        warnings = []
        
        # Ensure at least one processing stage is enabled
        enabled_stages = sum([
            self.enable_content_cleaning,
            self.enable_ai_analysis,
            self.enable_summarization,
            self.enable_structured_extraction,
            self.enable_duplicate_detection
        ])
        if enabled_stages == 0:
            raise ValueError('At least one processing stage must be enabled')
        
        # Validate timeout relationships with realistic constraints
        if self.content_processing_timeout >= self.timeout_seconds:
            raise ValueError('Content processing timeout must be less than overall timeout')
        
        # Validate concurrency limits based on timeout and memory constraints
        max_recommended_concurrency = min(
            self.timeout_seconds // 15,  # Allow 15 seconds per concurrent task
            self.memory_threshold_mb // 100  # 100MB per concurrent task
        )
        if self.concurrency > max_recommended_concurrency:
            warnings.append(
                f'Concurrency ({self.concurrency}) exceeds recommended limit ({max_recommended_concurrency}) '
                f'for timeout={self.timeout_seconds}s and memory={self.memory_threshold_mb}MB. '
                f'Consider reducing concurrency to prevent resource exhaustion.'
            )
        
        # Validate batch size limits based on memory and processing constraints
        max_recommended_batch_size = min(
            self.memory_threshold_mb // 25,  # 25MB per content item
            self.concurrency * 3,  # 3x concurrency for efficient batching
            30  # Hard limit for memory management
        )
        if self.batch_size > max_recommended_batch_size:
            warnings.append(
                f'Batch size ({self.batch_size}) exceeds recommended limit ({max_recommended_batch_size}). '
                f'Large batches may cause memory pressure and slower processing.'
            )
        
        # Validate AI concurrency limits based on API rate limits and memory
        max_ai_concurrency = min(
            self.concurrency * 3,  # 3x general concurrency
            self.memory_threshold_mb // 150,  # 150MB per AI analysis
            15  # Hard limit for API stability
        )
        if self.max_concurrent_ai_analyses > max_ai_concurrency:
            raise ValueError(
                f'AI concurrency ({self.max_concurrent_ai_analyses}) exceeds maximum allowed limit ({max_ai_concurrency}). '
                f'High AI concurrency may cause API rate limiting and memory issues.'
            )
        
        # Validate similarity analysis limits based on memory and performance
        max_similarity_pairs = min(
            self.memory_threshold_mb // 8,  # 8MB per similarity pair
            self.batch_size * 2,  # 2x batch size for efficient comparison
            100  # Hard limit for performance
        )
        if self.max_similarity_content_pairs > max_similarity_pairs:
            warnings.append(
                f'Similarity content pairs ({self.max_similarity_content_pairs}) exceeds recommended limit ({max_similarity_pairs}). '
                f'Too many pairs may cause memory issues and slow processing.'
            )
        
        # Validate content length limits for AI processing
        if self.gemini_max_similarity_content_length > 3000:
            warnings.append(
                f'Content length limit ({self.gemini_max_similarity_content_length}) is high. '
                f'Consider reducing to 2000-3000 characters for optimal AI processing performance.'
            )
        
        # Validate quality score thresholds
        if self.min_content_quality_score < 0.3:
            warnings.append(
                f'Low quality score threshold ({self.min_content_quality_score}) may process poor quality content. '
                f'Consider increasing to 0.4-0.5 for better results.'
            )
        
        # Validate summary length for readability
        if self.max_summary_length > 1000:
            warnings.append(
                f'Long summary length ({self.max_summary_length}) may reduce readability. '
                f'Consider keeping summaries under 800 characters for better user experience.'
            )
        
        # Configuration recommendations based on use case
        if self.enable_ai_analysis and self.enable_summarization:
            if self.concurrency < 3:
                warnings.append(
                    'AI analysis + summarization enabled with low concurrency. '
                    'Consider increasing concurrency to 3-5 for better throughput.'
                )
        
        if self.enable_duplicate_detection:
            if self.batch_size > 20:
                warnings.append(
                    'Duplicate detection with large batch size may cause memory issues. '
                    'Consider reducing batch size to 15-20 for duplicate detection.'
                )
        
        # Log warnings if any (these don't prevent processing but provide guidance)
        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(f"ProcessingConfig validation warning: {warning}")
        
        return self
    
    @classmethod
    def from_settings(cls, settings) -> "ProcessingConfig":
        """Create ProcessingConfig from application settings with fallback defaults."""
        return cls(
            timeout_seconds=getattr(settings, 'processing_timeout_seconds', 60),
            max_retries=getattr(settings, 'processing_max_retries', 2),
            concurrency=getattr(settings, 'processing_concurrency', 3),
            enable_content_cleaning=getattr(settings, 'processing_enable_content_cleaning', True),
            enable_ai_analysis=getattr(settings, 'processing_enable_ai_analysis', True),
            enable_summarization=getattr(settings, 'processing_enable_summarization', True),
            enable_structured_extraction=getattr(settings, 'processing_enable_structured_extraction', True),
            enable_duplicate_detection=getattr(settings, 'processing_enable_duplicate_detection', True),
            similarity_threshold=getattr(settings, 'processing_similarity_threshold', 0.8),
            min_content_quality_score=getattr(settings, 'processing_min_content_quality_score', 0.4),
            max_summary_length=getattr(settings, 'processing_max_summary_length', 500),
            batch_size=getattr(settings, 'processing_batch_size', 10),
            content_processing_timeout=getattr(settings, 'processing_content_timeout', 30),
            max_concurrent_ai_analyses=getattr(settings, 'processing_max_concurrent_ai_analyses', 3),
            gemini_max_similarity_content_length=getattr(settings, 'gemini_max_similarity_content_length', 1000),
            max_similarity_content_pairs=getattr(settings, 'processing_max_similarity_content_pairs', 50),
            max_similarity_batch_size=getattr(settings, 'processing_max_similarity_batch_size', 10),
            memory_threshold_mb=getattr(settings, 'processing_memory_threshold_mb', 512)
        )


class ProcessingError(BaseModel):
    """Structured error reporting during processing."""
    error_type: str = Field(..., description="Type of processing error")
    error_message: str = Field(..., description="Detailed error message")
    content_id: Optional[str] = Field(None, description="ID of content that caused the error")
    stage: str = Field(..., description="Processing stage where error occurred")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")
    retry_count: int = Field(0, description="Number of retry attempts made")
    recoverable: bool = Field(True, description="Whether the error is recoverable")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_type": "timeout",
                "error_message": "Processing operation timed out after 60 seconds",
                "content_id": "content_123",
                "stage": "ai_analysis",
                "timestamp": "2024-01-01T00:00:00Z",
                "retry_count": 1,
                "recoverable": True
            }
        }
    }
